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
        historical_data: Dict[str, any],
        predictions: List[dataschemas.SimulationPredictionItem]
    ) -> List[dataschemas.FeatureImpact]:
        """
        변경된 Feature들의 영향도 계산
        
        Args:
            feature_overrides: 사용자가 변경한 Feature들
            historical_data: 과거 데이터
            predictions: 예측 결과 리스트
        
        Returns:
            Feature 영향도 리스트 (기여도 포함)
        """
        impacts = []
        
        # 전체 평균 변화량
        total_avg_change = sum(p.change for p in predictions) / len(predictions) if predictions else 0
        
        # 각 feature의 변화량 비율 계산
        total_abs_change = 0
        feature_changes = {}
        
        for feature_name, new_value in feature_overrides.items():
            current_value = FeatureImpactCalculator._get_current_value(
                feature_name, 
                historical_data
            )
            value_change = new_value - current_value
            abs_change = abs(value_change)
            
            feature_changes[feature_name] = {
                'current_value': current_value,
                'new_value': new_value,
                'value_change': value_change,
                'abs_change': abs_change
            }
            total_abs_change += abs_change
        
        # 기여도 계산: 전체 변화량을 각 feature의 변화 비율로 배분
        for feature_name, changes in feature_changes.items():
            if total_abs_change > 0:
                contribution_ratio = changes['abs_change'] / total_abs_change
                # 변화 방향 고려
                contribution = total_avg_change * contribution_ratio * (1 if changes['value_change'] >= 0 else -1)
            else:
                contribution = 0
            
            impacts.append(
                dataschemas.FeatureImpact(
                    feature=feature_name,
                    current_value=round(changes['current_value'], 2),
                    new_value=round(changes['new_value'], 2),
                    value_change=round(changes['value_change'], 2),
                    contribution=round(contribution, 2)
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
    
    # 4. 요약 통계 계산
    summary = _calculate_summary(predictions)
    
    # 5. Feature 영향도 계산 (예측 결과 기반)
    feature_impacts = FeatureImpactCalculator.calculate_impacts(
        request.feature_overrides,
        historical_data,
        predictions
    )
    
    # 6. Summary에 feature별 기여도 추가
    summary["feature_contributions"] = {
        impact.feature: impact.contribution 
        for impact in feature_impacts
    }
    summary["total_contribution"] = round(sum(impact.contribution for impact in feature_impacts), 2)
    
    logger.info(f"예측 완료 - {len(predictions)}일치, 평균 변화: {summary['avg_change']:.2f}")
    
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
    """
    미래 60일치 Rolling Prediction 실행
    
    7일씩 예측하고, 예측 결과를 다음 입력으로 사용하여
    실제 rolling window 방식으로 60일 예측 수행
    """
    pred_service = get_prediction_service()
    predictions = []
    
    try:
        # 원본 및 시뮬레이션용 historical data 복사
        original_hist = _copy_historical_data(historical_data)
        simulated_hist = _copy_historical_data(historical_data)
        
        # 60일 예측을 위해 9번 반복 (7일 * 9 = 63일, 처음 60일만 사용)
        num_cycles = (60 + 6) // 7  # 9 cycles
        
        for cycle in range(num_cycles):
            if len(predictions) >= 60:
                break
            
            logger.info(f"Rolling prediction cycle {cycle + 1}/{num_cycles}")
            
            # 원본 예측 (override 없이)
            original_result = pred_service.predict_tft(
                request.commodity, 
                original_hist,
                feature_overrides=None
            )
            
            # 시뮬레이션 예측 (override 적용)
            simulated_result = pred_service.predict_tft(
                request.commodity,
                simulated_hist,
                feature_overrides=request.feature_overrides
            )
            
            # 7일 예측 결과 추가
            original_prices = original_result['predictions']
            simulated_prices = simulated_result['predictions']
            
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
            
            # Rolling window: 예측된 7일을 다음 입력으로 사용
            if len(predictions) < 60:
                _update_historical_data_with_predictions(
                    original_hist, 
                    original_prices, 
                    None
                )
                _update_historical_data_with_predictions(
                    simulated_hist, 
                    simulated_prices, 
                    request.feature_overrides
                )
        
        return predictions[:60]  # 정확히 60일만 반환
        
    except Exception as e:
        logger.error(f"예측 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"예측 실행 실패: {str(e)}"
        )


def _copy_historical_data(historical_data: Dict) -> Dict:
    """Historical data 깊은 복사"""
    import copy
    return {
        'dates': historical_data['dates'].copy(),
        'features': {k: v.copy() for k, v in historical_data['features'].items()}
    }


def _update_historical_data_with_predictions(
    historical_data: Dict,
    predicted_prices: List[float],
    feature_overrides: Optional[Dict[str, float]]
):
    """
    예측된 가격으로 historical data 업데이트 (rolling window)
    
    - 가장 오래된 N일 제거
    - 예측된 N일 추가
    - 모든 feature를 적절히 채움
    """
    num_days = len(predicted_prices)
    
    # 날짜 업데이트 (가장 오래된 N일 제거하고 새 날짜 추가)
    historical_data['dates'] = historical_data['dates'][num_days:]
    
    # 각 feature 업데이트
    for feature_name in historical_data['features']:
        feature_values = historical_data['features'][feature_name]
        
        # 가장 오래된 N일 제거
        feature_values = feature_values[num_days:]
        
        # 예측 기반 새 값 생성
        if feature_name == 'close':
            # 가격: 예측값 사용
            new_values = predicted_prices
        elif feature_name in ['open', 'high', 'low']:
            # 가격 관련: close 기반으로 생성
            new_values = [
                p * (1 + (feature_values[-1] / historical_data['features']['close'][-1] - 1))
                for p in predicted_prices
            ]
        elif feature_name == 'volume':
            # 거래량: 최근 평균 유지
            avg_volume = sum(feature_values[-7:]) / 7
            new_values = [avg_volume] * num_days
        elif feature_overrides and feature_name in feature_overrides:
            # Override된 feature: 고정값 사용
            new_values = [feature_overrides[feature_name]] * num_days
        else:
            # 기타 feature: 마지막 값 유지
            last_value = feature_values[-1]
            new_values = [last_value] * num_days
        
        # 업데이트
        historical_data['features'][feature_name] = feature_values + new_values


def _calculate_summary(predictions: List[dataschemas.SimulationPredictionItem]) -> dict:
    """전체 예측의 요약 통계 계산"""
    if not predictions:
        return {}
    
    total_change = sum(p.change for p in predictions)
    avg_change = total_change / len(predictions)
    
    total_change_percent = sum(p.change_percent for p in predictions)
    avg_change_percent = total_change_percent / len(predictions)
    
    avg_original = sum(p.original_price for p in predictions) / len(predictions)
    avg_simulated = sum(p.simulated_price for p in predictions) / len(predictions)
    
    return {
        "total_days": len(predictions),
        "avg_original_price": round(avg_original, 2),
        "avg_simulated_price": round(avg_simulated, 2),
        "avg_change": round(avg_change, 2),
        "avg_change_percent": round(avg_change_percent, 2),
        "total_change": round(total_change, 2),
        "max_change": round(max(p.change for p in predictions), 2),
        "min_change": round(min(p.change for p in predictions), 2),
        "max_change_date": max(predictions, key=lambda p: p.change).date,
        "min_change_date": min(predictions, key=lambda p: p.change).date
    }
