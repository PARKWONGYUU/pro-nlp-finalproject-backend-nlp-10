from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
import logging

from ..ml.prediction_service import get_prediction_service
from .. import crud, dataschemas
from ..database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Simulation"]
)


class SimulationValidator:
    """시뮬레이션 요청 검증"""
    
    # 조정 가능한 Features
    VALID_FEATURES = {
        '10Y_Yield', 'USD_Index', 'pdsi', 'spi30d', 'spi90d',
        'close', 'open', 'high', 'low', 'volume', 'news_count'
    }
    
    @staticmethod
    def validate_feature_overrides(feature_overrides: Dict[str, float]) -> None:
        """Feature override 유효성 검증"""
        invalid_features = set(feature_overrides.keys()) - SimulationValidator.VALID_FEATURES
        
        if invalid_features:
            raise HTTPException(
                status_code=400,
                detail=f"조정 불가능한 feature: {invalid_features}. "
                       f"가능한 features: {SimulationValidator.VALID_FEATURES}"
            )


class FeatureImpactCalculator:
    """Feature 영향도 계산"""
    
    @staticmethod
    def calculate_impacts(
        feature_overrides: Dict[str, float],
        historical_data: Dict[str, any]
    ) -> List[dataschemas.FeatureImpact]:
        """
        변경된 Feature들의 영향도 계산
        
        Args:
            feature_overrides: 사용자가 변경한 Feature들
            historical_data: 과거 데이터
        
        Returns:
            Feature 영향도 리스트
        """
        impacts = []
        
        for feature_name, new_value in feature_overrides.items():
            current_value = FeatureImpactCalculator._get_current_value(
                feature_name, 
                historical_data
            )
            
            impacts.append(
                dataschemas.FeatureImpact(
                    feature=feature_name,
                    current_value=current_value,
                    new_value=new_value,
                    value_change=new_value - current_value,
                    contribution=0  # TODO: SHAP으로 정확한 기여도 계산
                )
            )
        
        return impacts
    
    @staticmethod
    def _get_current_value(feature_name: str, historical_data: Dict[str, any]) -> float:
        """현재(최근) Feature 값 가져오기"""
        if feature_name in historical_data['features']:
            current_values = historical_data['features'][feature_name]
            return current_values[-1] if current_values else 0.0
        return 0.0


@router.post("/simulate", response_model=dataschemas.SimulationResponse)
def simulate_prediction(
    request: dataschemas.SimulationRequest,
    db: Session = Depends(get_db)
):
    """
    TFT ONNX 모델을 사용한 실시간 시뮬레이션
    
    과거 60일의 시계열 데이터를 DB에서 로드하고,
    feature_overrides를 적용하여 재예측합니다.
    
    조정 가능한 Features:
    - 10Y_Yield: 미국 10년물 국채 금리
    - USD_Index: 달러 인덱스
    - pdsi: Palmer Drought Severity Index
    - spi30d: Standardized Precipitation Index (30일)
    - spi90d: Standardized Precipitation Index (90일)
    """
    logger.info(f"시뮬레이션 시작 - {request.commodity}, {request.base_date}")
    logger.info(f"Feature overrides: {request.feature_overrides}")
    
    # 1. 기준 예측 조회
    base_prediction = _get_base_prediction(db, request)
    
    # 2. Feature overrides 검증
    SimulationValidator.validate_feature_overrides(request.feature_overrides)
    
    # 3. 과거 데이터 로드
    historical_data = _load_historical_data(db, request)
    
    # 4. 예측 실행
    original_forecast, simulated_forecast = _run_predictions(
        request, 
        historical_data
    )
    
    # 5. Feature 영향도 계산
    feature_impacts = FeatureImpactCalculator.calculate_impacts(
        request.feature_overrides,
        historical_data
    )
    
    # 6. 변화량 계산
    change, change_percent = _calculate_changes(original_forecast, simulated_forecast)
    
    logger.info(f"예측 완료 - 원본: {original_forecast:.2f}, 시뮬레이션: {simulated_forecast:.2f}")
    
    return dataschemas.SimulationResponse(
        original_forecast=round(original_forecast, 2),
        simulated_forecast=round(simulated_forecast, 2),
        change=round(change, 2),
        change_percent=round(change_percent, 2),
        feature_impacts=feature_impacts
    )


def _get_base_prediction(db: Session, request: dataschemas.SimulationRequest):
    """기준 예측 조회"""
    base_prediction = crud.get_prediction_by_date(
        db, request.commodity, request.base_date
    )
    
    if not base_prediction:
        raise HTTPException(
            status_code=404,
            detail=f"{request.commodity}의 {request.base_date} 예측이 없습니다."
        )
    
    return base_prediction


def _load_historical_data(db: Session, request: dataschemas.SimulationRequest) -> Dict:
    """과거 60일의 시계열 데이터 로드"""
    try:
        historical_data = crud.get_historical_features(
            db, request.commodity, request.base_date, days=60
        )
        
        if not historical_data['dates']:
            raise HTTPException(
                status_code=404,
                detail=f"{request.commodity}의 과거 60일 시계열 데이터가 없습니다. "
                       f"market_metrics 테이블에 데이터를 먼저 저장하세요."
            )
        
        logger.info(f"과거 데이터 로드 완료: {len(historical_data['dates'])}일")
        return historical_data
        
    except Exception as e:
        logger.error(f"과거 데이터 로드 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"과거 데이터 로드 실패: {str(e)}"
        )


def _run_predictions(
    request: dataschemas.SimulationRequest,
    historical_data: Dict
) -> tuple[float, float]:
    """원본 및 시뮬레이션 예측 실행"""
    pred_service = get_prediction_service()
    
    try:
        # 원본 예측 (override 없이)
        original_result = pred_service.predict_tft(
            request.commodity, 
            historical_data,
            feature_overrides=None
        )
        
        # 시뮬레이션 예측 (override 적용)
        simulated_result = pred_service.predict_tft(
            request.commodity,
            historical_data,
            feature_overrides=request.feature_overrides
        )
        
        # 첫 날 예측값 사용 (7일 중 1일차)
        original_forecast = original_result['predictions'][0]
        simulated_forecast = simulated_result['predictions'][0]
        
        return original_forecast, simulated_forecast
        
    except Exception as e:
        logger.error(f"예측 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"예측 실행 실패: {str(e)}"
        )


def _calculate_changes(original: float, simulated: float) -> tuple[float, float]:
    """변화량 및 변화율 계산"""
    change = simulated - original
    change_percent = (change / original) * 100 if original != 0 else 0
    return change, change_percent
