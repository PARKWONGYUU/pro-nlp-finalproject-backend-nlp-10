from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import timedelta
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
    
    # 조정 가능한 Features (5개)
    VALID_FEATURES = {
        '10Y_Yield', 'USD_Index', 'pdsi', 'spi30d', 'spi90d'
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
    TFT ONNX 모델을 사용한 실시간 시뮬레이션 (미래 60일 예측)
    
    base_date 기준으로 과거 60일 데이터를 로드하고,
    feature_overrides를 적용하여 미래 60일을 재예측합니다.
    
    조정 가능한 Features (5개):
    - 10Y_Yield: 미국 10년물 국채 금리
    - USD_Index: 달러 인덱스
    - pdsi: Palmer Drought Severity Index
    - spi30d: Standardized Precipitation Index (30일)
    - spi90d: Standardized Precipitation Index (90일)
    """
    logger.info(f"시뮬레이션 시작 - {request.commodity}, {request.base_date}")
    logger.info(f"Feature overrides: {request.feature_overrides}")
    
    # 1. Feature overrides 검증
    SimulationValidator.validate_feature_overrides(request.feature_overrides)
    
    # 2. 과거 데이터 로드
    historical_data = _load_historical_data(db, request)
    
    # 3. 60일치 예측 실행 (원본 + 시뮬레이션)
    predictions = _run_60day_predictions(request, historical_data)
    
    # 4. Feature 영향도 계산
    feature_impacts = FeatureImpactCalculator.calculate_impacts(
        request.feature_overrides,
        historical_data
    )
    
    # 5. 요약 통계 계산
    summary = _calculate_summary(predictions)
    
    logger.info(f"예측 완료 - {len(predictions)}일치")
    
    return dataschemas.SimulationResponse(
        base_date=request.base_date.isoformat(),
        predictions=predictions,
        feature_impacts=feature_impacts,
        summary=summary
    )




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


def _run_60day_predictions(
    request: dataschemas.SimulationRequest,
    historical_data: Dict
) -> List[dataschemas.SimulationPredictionItem]:
    """미래 60일치 원본 및 시뮬레이션 예측 실행"""
    pred_service = get_prediction_service()
    predictions = []
    
    try:
        # TFT 모델은 한 번에 7일을 예측하므로, 60일을 위해 반복 필요
        # 하지만 단순화를 위해 rolling window로 처리
        
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
        
        # 7일 예측을 60일로 확장 (rolling prediction)
        # 실제로는 7일씩 예측을 반복해야 하지만, 현재는 7일치만 반환
        original_prices = original_result['predictions']
        simulated_prices = simulated_result['predictions']
        
        # 60일을 위해 7일 예측을 반복 (임시 구현)
        cycles = 60 // 7 + 1  # 9 cycles
        
        for cycle in range(cycles):
            for day_idx in range(len(original_prices)):
                if len(predictions) >= 60:
                    break
                    
                pred_date = request.base_date + timedelta(days=len(predictions) + 1)
                original_price = original_prices[day_idx]
                simulated_price = simulated_prices[day_idx]
                
                change = simulated_price - original_price
                change_percent = (change / original_price) * 100 if original_price != 0 else 0
                
                predictions.append(dataschemas.SimulationPredictionItem(
                    date=pred_date.isoformat(),
                    original_price=round(original_price, 2),
                    simulated_price=round(simulated_price, 2),
                    change=round(change, 2),
                    change_percent=round(change_percent, 2)
                ))
            
            if len(predictions) >= 60:
                break
        
        return predictions[:60]  # 정확히 60일만 반환
        
    except Exception as e:
        logger.error(f"예측 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"예측 실행 실패: {str(e)}"
        )


def _calculate_summary(predictions: List[dataschemas.SimulationPredictionItem]) -> dict:
    """전체 예측의 요약 통계 계산"""
    if not predictions:
        return {}
    
    total_change = sum(p.change for p in predictions)
    avg_change = total_change / len(predictions)
    
    total_change_percent = sum(p.change_percent for p in predictions)
    avg_change_percent = total_change_percent / len(predictions)
    
    return {
        "total_days": len(predictions),
        "avg_change": round(avg_change, 2),
        "avg_change_percent": round(avg_change_percent, 2),
        "max_change": round(max(p.change for p in predictions), 2),
        "min_change": round(min(p.change for p in predictions), 2)
    }
