from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import timedelta, date
import logging
import math

from ..ml.prediction_service import get_prediction_service
from .. import crud, dataschemas
from ..database import get_db
from ..dummy_data_generator import get_generator
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Simulation"]
)


def sanitize_float(value: float, default: float = 0.0) -> float:
    """
    무한대(inf) 및 NaN 값을 안전한 값으로 변환
    
    Args:
        value: 검사할 float 값
        default: inf/nan일 경우 반환할 기본값
    
    Returns:
        안전한 float 값
    """
    if math.isinf(value) or math.isnan(value):
        logger.warning(f"무한대/NaN 값 감지: {value} -> {default}로 대체")
        return default
    return value


def sanitize_dict(data: dict) -> dict:
    """
    딕셔너리의 모든 float 값에서 inf/nan을 제거
    
    Args:
        data: 정리할 딕셔너리
    
    Returns:
        정리된 딕셔너리
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, float):
            sanitized[key] = sanitize_float(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_float(v) if isinstance(v, float) else v 
                for v in value
            ]
        else:
            sanitized[key] = value
    return sanitized


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
    logger.info(f"모드: {settings.simulation_mode}")
    logger.info(f"Feature overrides: {request.feature_overrides}")
    
    # 1. Feature overrides 검증
    SimulationValidator.validate_feature_overrides(request.feature_overrides)
    
    # 2. 변경 사항 확인 (비어있거나 의미 있는 변경이 없는 경우)
    has_changes = False
    if request.feature_overrides:
        # 여기에 실제 값과 비교하는 로직을 추가할 수도 있지만, 
        # 일단 overrides가 비어있지 않으면 변경된 것으로 간주
        # 단, 값이 비어있는 dict인 경우는 제외
        has_changes = len(request.feature_overrides) > 0
        
    # 3. 변경 사항이 없으면 DB 원본 반환 (계산 생략)
    if not has_changes and settings.simulation_mode == "dummy":
        logger.info("ℹ️ 변경된 변수가 없어 DB 원본 예측을 반환합니다.")
        return _get_original_predictions_response(request, db)
    
    # 4. 시뮬레이션 모드 분기
    if settings.simulation_mode == "dummy":
        return _simulate_with_dummy(request, db)
    
    # 3. ONNX 모드 (기존 로직)
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
    
    # 7. inf/nan 값 정리 (JSON 직렬화 오류 방지)
    summary = sanitize_dict(summary)
    
    # 8. predictions의 각 항목도 정리
    for pred in predictions:
        pred.original_price = sanitize_float(pred.original_price)
        pred.simulated_price = sanitize_float(pred.simulated_price)
        pred.change = sanitize_float(pred.change)
        pred.change_percent = sanitize_float(pred.change_percent)
    
    # 9. feature_impacts도 정리
    for impact in feature_impacts:
        impact.current_value = sanitize_float(impact.current_value)
        impact.new_value = sanitize_float(impact.new_value)
        impact.value_change = sanitize_float(impact.value_change)
        impact.contribution = sanitize_float(impact.contribution)
    
    logger.info(f"예측 완료 - {len(predictions)}일치, 평균 변화: {summary.get('avg_change', 0):.2f}")
    
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
    미래 60일 예측 실행 (한 번에)
    
    🔥 변경: Rolling Window 제거, 60일 한 번에 예측
    - 이전: 7일씩 9번 반복 (누적 오차 발생 가능)
    - 현재: 60일 한 번에 예측 (배치 서버와 동일)
    """
    pred_service = get_prediction_service()
    predictions = []
    
    try:
        # 원본 및 시뮬레이션용 historical data 복사
        original_hist = _copy_historical_data(historical_data)
        simulated_hist = _copy_historical_data(historical_data)
        
        # 🔄 현재 ONNX 모델이 7일용이므로 9번 반복 필요
        # TODO: 60일 ONNX 모델로 교체 후 num_cycles = 1로 변경
        num_cycles = (60 + 6) // 7  # 9 cycles (7-day predictions)
        
        for cycle in range(num_cycles):
            if len(predictions) >= 60:
                break
            
            logger.info(f"Rolling prediction cycle {cycle + 1}/{num_cycles}")
            
            # 원본 예측 (override 없이)
            print(f"\n{'='*80}")
            print(f"📊 Cycle {cycle + 1}/{num_cycles}: 원본 예측 수행 (override 없음)")
            print(f"{'='*80}")
            logger.info(f"📊 원본 예측 수행 (override 없음)")
            original_result = pred_service.predict_tft(
                request.commodity, 
                original_hist,
                feature_overrides=None
            )
            
            # 시뮬레이션 예측 (override 적용)
            print(f"\n{'='*80}")
            print(f"📊 Cycle {cycle + 1}/{num_cycles}: 시뮬레이션 예측 수행")
            print(f"   Override: {request.feature_overrides}")
            print(f"{'='*80}")
            logger.info(f"📊 시뮬레이션 예측 수행 (override 적용: {request.feature_overrides})")
            simulated_result = pred_service.predict_tft(
                request.commodity,
                simulated_hist,
                feature_overrides=request.feature_overrides
            )
            
            # 결과 비교 로깅
            original_avg = sum(original_result['predictions']) / len(original_result['predictions'])
            simulated_avg = sum(simulated_result['predictions']) / len(simulated_result['predictions'])
            diff = simulated_avg - original_avg
            # 0으로 나누기 및 inf 방지
            if original_avg != 0 and abs(original_avg) > 1e-10:
                diff_pct = sanitize_float((diff / original_avg) * 100)
            else:
                diff_pct = 0.0
            
            print(f"\n결과 비교:")
            print(f"  원본 평균: ${original_avg:.2f}")
            print(f"  시뮬 평균: ${simulated_avg:.2f}")
            print(f"  차이: ${diff:.2f} ({diff_pct:.2f}%)")
            print(f"{'='*80}\n")
            
            logger.info(f"  원본 평균 가격: {original_avg:.2f}")
            logger.info(f"  시뮬레이션 평균 가격: {simulated_avg:.2f}")
            logger.info(f"  차이: {diff:.2f} ({diff_pct:.2f}%)")
            
            # 7일 예측 결과 추가
            original_prices = original_result['predictions']
            simulated_prices = simulated_result['predictions']
            
            for day_idx in range(len(original_prices)):
                if len(predictions) >= 60:
                    break
                
                pred_date = request.base_date + timedelta(days=len(predictions) + 1)
                original_price = sanitize_float(original_prices[day_idx])
                simulated_price = sanitize_float(simulated_prices[day_idx])
                
                change = simulated_price - original_price
                # 0으로 나누기 방지 및 inf 방지
                if original_price != 0 and abs(original_price) > 1e-10:
                    change_percent = (change / original_price) * 100
                    change_percent = sanitize_float(change_percent)
                else:
                    change_percent = 0.0
                
                predictions.append(dataschemas.SimulationPredictionItem(
                    date=pred_date.isoformat(),
                    original_price=round(original_price, 2),
                    simulated_price=round(simulated_price, 2),
                    change=round(change, 2),
                    change_percent=round(change_percent, 2)
                ))
            
            # Rolling window: 예측된 7일을 다음 입력으로 사용
            if len(predictions) < 60:
                logger.info(f"🔄 Rolling window 업데이트 시작 (cycle {cycle + 1})")
                logger.info(f"   원본: 예측 {len(original_prices)}일을 다음 입력으로 추가")
                _update_historical_data_with_predictions(
                    original_hist, 
                    original_prices, 
                    None
                )
                logger.info(f"   시뮬레이션: 예측 {len(simulated_prices)}일을 다음 입력으로 추가 (override: {list(request.feature_overrides.keys())})")
                _update_historical_data_with_predictions(
                    simulated_hist, 
                    simulated_prices, 
                    request.feature_overrides
                )
                logger.info(f"🔄 Rolling window 업데이트 완료")
        
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
    - 60일 window 유지
    """
    num_days = len(predicted_prices)
    
    logger.info(f"  📝 Rolling window 상세: {num_days}일 예측을 다음 입력으로 사용")
    if feature_overrides:
        logger.info(f"     Override 적용: {feature_overrides}")
    
    # 날짜 업데이트 (가장 오래된 N일 제거하고 새 날짜 추가)
    old_dates_count = len(historical_data['dates'])
    historical_data['dates'] = historical_data['dates'][num_days:]
    logger.debug(f"     날짜: {old_dates_count}일 → {len(historical_data['dates'])}일 (최근 {num_days}일 제거)")
    
    # 슬라이싱 전에 필요한 값들을 미리 저장 (순서 문제 방지)
    old_features = {
        name: values.copy() 
        for name, values in historical_data['features'].items()
    }
    
    # 각 feature 업데이트
    for feature_name in historical_data['features']:
        feature_values = old_features[feature_name]
        
        # 최소 필요 길이 확인 (60일 유지 필요)
        if len(feature_values) < num_days:
            logger.warning(f"⚠️ feature '{feature_name}'의 데이터가 {len(feature_values)}일로 부족합니다 (최소 {num_days}일 필요). 원본 유지")
            historical_data['features'][feature_name] = feature_values
            continue
        
        # 가장 오래된 N일 제거
        feature_values_trimmed = feature_values[num_days:]
        
        # 예측 기반 새 값 생성
        if feature_name == 'close':
            # 가격: 예측값 사용
            new_values = predicted_prices
        elif feature_name in ['open', 'high', 'low']:
            # 가격 관련: close 기반으로 생성
            # 최근 close와의 비율을 유지
            old_close_last = old_features['close'][-1]
            old_feature_last = feature_values[-1]
            
            if old_close_last != 0:
                ratio = old_feature_last / old_close_last
                new_values = [p * ratio for p in predicted_prices]
            else:
                new_values = predicted_prices
        elif feature_name == 'volume':
            # 거래량: 최근 평균 유지
            recent_values = feature_values[-min(7, len(feature_values)):]
            avg_volume = sum(recent_values) / len(recent_values) if recent_values else 0
            new_values = [avg_volume] * num_days
        elif feature_overrides and feature_name in feature_overrides:
            # Override된 feature: 고정값 사용
            override_value = feature_overrides[feature_name]
            new_values = [override_value] * num_days
            logger.debug(f"  🔧 Rolling window - {feature_name}: override 값 {override_value} 적용 ({num_days}일)")
        else:
            # 기타 feature: 마지막 값 유지
            last_value = feature_values[-1] if len(feature_values) > 0 else 0
            new_values = [last_value] * num_days
        
        # 업데이트 후 길이 확인
        updated_values = feature_values_trimmed + new_values
        historical_data['features'][feature_name] = updated_values
        
        # 디버깅: 주요 feature 로그
        if feature_name == 'close':
            logger.debug(f"     close: {len(feature_values)} → {len(updated_values)}일 (제거 {num_days}, 추가 {num_days})")
            logger.debug(f"           추가된 값: {[round(v, 2) for v in new_values[:3]]}...")
        elif feature_overrides and feature_name in feature_overrides:
            logger.debug(f"     {feature_name}: override 값 {feature_overrides[feature_name]} 적용됨 ({num_days}일)")
    
    # 업데이트 완료 로그
    total_features = len(historical_data['features'])
    override_count = len(feature_overrides) if feature_overrides else 0
    logger.debug(f"  ✅ Rolling window 업데이트 완료: {total_features}개 feature, {override_count}개 override 적용")


def _calculate_summary(predictions: List[dataschemas.SimulationPredictionItem]) -> dict:
    """전체 예측의 요약 통계 계산 (inf/nan 방지)"""
    if not predictions:
        return {}
    
    # 안전한 합계 계산 (inf/nan 필터링)
    total_change = sum(sanitize_float(p.change) for p in predictions)
    avg_change = total_change / len(predictions) if len(predictions) > 0 else 0
    
    total_change_percent = sum(sanitize_float(p.change_percent) for p in predictions)
    avg_change_percent = total_change_percent / len(predictions) if len(predictions) > 0 else 0
    
    avg_original = sum(sanitize_float(p.original_price) for p in predictions) / len(predictions) if len(predictions) > 0 else 0
    avg_simulated = sum(sanitize_float(p.simulated_price) for p in predictions) / len(predictions) if len(predictions) > 0 else 0
    
    # 안전한 min/max 계산
    changes = [sanitize_float(p.change) for p in predictions]
    max_change = max(changes) if changes else 0
    min_change = min(changes) if changes else 0
    
    # max/min date 찾기
    max_pred = max(predictions, key=lambda p: sanitize_float(p.change))
    min_pred = min(predictions, key=lambda p: sanitize_float(p.change))
    
    return {
        "total_days": len(predictions),
        "avg_original_price": round(sanitize_float(avg_original), 2),
        "avg_simulated_price": round(sanitize_float(avg_simulated), 2),
        "avg_change": round(sanitize_float(avg_change), 2),
        "avg_change_percent": round(sanitize_float(avg_change_percent), 2),
        "total_change": round(sanitize_float(total_change), 2),
        "max_change": round(sanitize_float(max_change), 2),
        "min_change": round(sanitize_float(min_change), 2),
        "max_change_date": max_pred.date,
        "min_change_date": min_pred.date
    }


# ===========================
# 더미 시뮬레이션 (시연용)
# ===========================

def _get_original_predictions_response(
    request: dataschemas.SimulationRequest,
    db: Session
) -> dataschemas.SimulationResponse:
    """
    변경 사항이 없을 때 DB의 원본 예측값을 반환
    """
    # 1. DB에서 원본 예측 가져오기
    today = request.base_date
    end_date = today + timedelta(days=60)
    
    original_predictions = crud.get_tft_predictions(
        db, 
        request.commodity, 
        start_date=today + timedelta(days=1),
        end_date=end_date
    )
    
    # 2. Response 형식으로 변환 (변화량 0)
    predictions = []
    for i, pred in enumerate(original_predictions):
        if i >= 60: break
        price = float(pred.price_pred)
        predictions.append(dataschemas.SimulationPredictionItem(
            date=pred.target_date.isoformat(),
            original_price=price,
            simulated_price=price,
            change=0.0,
            change_percent=0.0
        ))
    
    # 3. 부족한 일수는 더미로 채움 (만약 DB 데이터가 부족하다면)
    if len(predictions) < 60:
        generator = get_generator()
        dummy_preds = generator.generate_simulation_result(
            base_date=request.base_date,
            original_predictions=original_predictions,
            feature_overrides={},
            days=60
        )
        # 이미 있는 날짜는 유지하고 부족한 부분만 채움
        existing_dates = set(p.date for p in predictions)
        for d_pred in dummy_preds:
            if d_pred.date not in existing_dates:
                # 변화량 0으로 강제 설정
                d_pred.simulated_price = d_pred.original_price
                d_pred.change = 0.0
                d_pred.change_percent = 0.0
                predictions.append(d_pred)
        
        # 날짜순 정렬
        predictions.sort(key=lambda x: x.date)
    
    # 4. Summary 생성 (변화량 0)
    avg_price = sum(p.original_price for p in predictions) / len(predictions) if predictions else 0
    summary = {
        "total_days": len(predictions),
        "avg_original_price": round(avg_price, 2),
        "avg_simulated_price": round(avg_price, 2),
        "avg_change": 0.0,
        "avg_change_percent": 0.0,
        "total_change": 0.0,
        "max_change": 0.0,
        "min_change": 0.0,
        "feature_contributions": {},
        "total_contribution": 0.0
    }
    
    return dataschemas.SimulationResponse(
        base_date=request.base_date.isoformat(),
        predictions=predictions,
        feature_impacts=[],
        summary=summary
    )


def _simulate_with_dummy(
    request: dataschemas.SimulationRequest,
    db: Session
) -> dataschemas.SimulationResponse:
    """
    빠른 더미 시뮬레이션 (시연용)
    
    ONNX 모델 대신 간단한 선형 모델을 사용하여 즉시 응답
    - DB에서 원본 예측 가져오기
    - feature_override 기반으로 가격 변화 계산
    - 60일 예측 즉시 반환
    
    Args:
        request: 시뮬레이션 요청
        db: DB 세션
    
    Returns:
        SimulationResponse
    """
    logger.info("🚀 더미 시뮬레이션 모드 시작 (빠른 응답)")
    
    # 0. 현재 Feature 값 조회 (Baseline으로 사용)
    current_values = {}
    try:
        # 최근 30일 데이터만 가져와서 마지막 값 확인
        hist_data = crud.get_historical_features(
            db, request.commodity, request.base_date, days=30
        )
        if hist_data and hist_data.get('features'):
            for feat, vals in hist_data['features'].items():
                if vals:
                    current_values[feat] = vals[-1]
            logger.info(f"현재 Feature 값 조회 성공: {list(current_values.keys())}")
    except Exception as e:
        logger.warning(f"현재 Feature 값 조회 실패 (기본값 사용): {e}")

    # 1. DB에서 원본 예측 가져오기
    today = request.base_date
    end_date = today + timedelta(days=60)
    
    original_predictions = crud.get_tft_predictions(
        db, 
        request.commodity, 
        start_date=today + timedelta(days=1),
        end_date=end_date
    )
    
    logger.info(f"원본 예측 {len(original_predictions)}개 조회 완료")
    
    # 2. 더미 데이터 생성기로 시뮬레이션 실행
    generator = get_generator()
    
    predictions = generator.generate_simulation_result(
        base_date=request.base_date,
        original_predictions=original_predictions,
        feature_overrides=request.feature_overrides,
        days=60,
        current_values=current_values  # 현재 값 전달
    )
    
    logger.info(f"시뮬레이션 예측 {len(predictions)}개 생성 완료")
    
    # 3. 요약 통계 계산
    summary = _calculate_summary(predictions)
    
    # 4. Feature 영향도 계산 (간단한 버전)
    feature_impacts = _calculate_dummy_feature_impacts(
        request.feature_overrides,
        predictions,
        current_values  # 현재 값 전달
    )
    
    # 5. Summary에 feature별 기여도 추가
    summary["feature_contributions"] = {
        impact.feature: impact.contribution 
        for impact in feature_impacts
    }
    summary["total_contribution"] = round(sum(impact.contribution for impact in feature_impacts), 2)
    
    logger.info(f"✅ 더미 시뮬레이션 완료 - 평균 변화: {summary['avg_change']:.2f}")
    
    return dataschemas.SimulationResponse(
        base_date=request.base_date.isoformat(),
        predictions=predictions,
        feature_impacts=feature_impacts,
        summary=summary
    )


def _calculate_dummy_feature_impacts(
    feature_overrides: Dict[str, float],
    predictions: List[dataschemas.SimulationPredictionItem],
    current_values: Dict[str, float] = None
) -> List[dataschemas.FeatureImpact]:
    """
    더미 모드의 Feature 영향도 계산 (간단한 버전)
    
    Args:
        feature_overrides: 변경한 feature들
        predictions: 예측 결과
        current_values: 현재 feature 값들
    
    Returns:
        FeatureImpact 리스트
    """
    impacts = []
    if current_values is None:
        current_values = {}
    
    # 전체 평균 변화량
    total_avg_change = sum(p.change for p in predictions) / len(predictions) if predictions else 0
    
    # Feature별 기준값 (현재 값 우선, 없으면 기본값)
    DEFAULT_BASELINES = {
        '10Y_Yield': 4.0,
        'USD_Index': 100.0,
        'pdsi': 0.0,
        'spi30d': 0.0,
        'spi90d': 0.0,
    }
    
    # 각 feature의 변화량 비율 계산
    total_abs_change = 0
    feature_changes = {}
    
    for feature_name, new_value in feature_overrides.items():
        # DB에서 가져온 현재 값이 있으면 그것을 사용, 없으면 기본값
        current_value = current_values.get(feature_name, DEFAULT_BASELINES.get(feature_name, 0.0))
        
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
