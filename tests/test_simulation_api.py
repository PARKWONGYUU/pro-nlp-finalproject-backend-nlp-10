"""
Simulation API 테스트 스크립트 (Mock 값 사용)
실제 서버 없이 시뮬레이션 로직을 테스트합니다.
"""

import sys
from pathlib import Path
from datetime import date
from unittest.mock import Mock, MagicMock

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.ml.prediction_service import get_prediction_service
from app import dataschemas
from app.config import settings
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_mock_base_prediction(price_pred=450.0):
    """Mock base_prediction 객체 생성"""
    mock_pred = Mock()
    mock_pred.id = 1
    mock_pred.target_date = date(2026, 2, 10)
    mock_pred.commodity = "corn"
    mock_pred.price_pred = price_pred
    mock_pred.conf_lower = price_pred - 20.0
    mock_pred.conf_upper = price_pred + 20.0
    return mock_pred

def create_mock_base_features():
    """Mock base_features 생성 (market_metrics에서 가져온 것처럼)"""
    return {
        "US_10Y_YIELD": 4.2,
        "DXY": 103.5,
        "PDSI": 0.5,
        "SPI_30D": 0.0,
        "SPI_90D": 0.0
    }

def simulate_with_mock(base_prediction, base_features, feature_overrides):
    """
    시뮬레이션 로직 테스트 (실제 API 로직과 동일)
    """
    print(f"\n{'='*60}")
    print(f"시뮬레이션 실행")
    print(f"{'='*60}")
    
    # feature_overrides 검증
    invalid_features = set(feature_overrides.keys()) - set(settings.adjustable_features)
    if invalid_features:
        print(f"❌ 조정 불가능한 feature: {invalid_features}")
        print(f"   가능한 features: {settings.adjustable_features}")
        return None
    
    print(f"\n📌 기준 정보:")
    print(f"   품목: {base_prediction.commodity}")
    print(f"   날짜: {base_prediction.target_date}")
    print(f"   원래 예측: ${base_prediction.price_pred:.2f}")
    
    print(f"\n📊 기준 Features:")
    for key, value in base_features.items():
        print(f"   {key:15s}: {value:7.2f}")
    
    print(f"\n🔧 변경할 Features:")
    for key, value in feature_overrides.items():
        old_value = base_features.get(key, 0)
        print(f"   {key:15s}: {old_value:7.2f} → {value:7.2f} (변화: {value - old_value:+.2f})")
    
    # 특징 오버라이드 적용
    modified_features = {**base_features, **feature_overrides}
    
    print(f"\n⚙️ ONNX 모델 추론 실행 중...")
    
    # 예측 서비스
    pred_service = get_prediction_service()
    
    try:
        # 실시간 예측
        original_forecast = float(base_prediction.price_pred)
        simulated_forecast = pred_service.predict(base_prediction.commodity, modified_features)
        
        # Feature 영향도 계산
        feature_impacts = []
        for feature_name in settings.adjustable_features:
            if feature_name in feature_overrides:
                current_value = base_features.get(feature_name, 0)
                new_value = feature_overrides[feature_name]
                
                feature_impacts.append({
                    "feature": feature_name,
                    "current_value": current_value,
                    "new_value": new_value,
                    "value_change": new_value - current_value,
                    "contribution": 0  # TODO: SHAP
                })
        
        change = simulated_forecast - original_forecast
        change_percent = (change / original_forecast) * 100 if original_forecast != 0 else 0
        
        # 결과 출력
        print(f"\n{'='*60}")
        print(f"✅ 시뮬레이션 결과")
        print(f"{'='*60}")
        print(f"원래 예측:       ${original_forecast:8.2f}")
        print(f"시뮬레이션 예측: ${simulated_forecast:8.2f}")
        print(f"변화:            ${change:+8.2f}")
        print(f"변화율:          {change_percent:+8.2f}%")
        
        if feature_impacts:
            print(f"\n📈 Feature별 변화:")
            for impact in feature_impacts:
                print(f"   {impact['feature']:15s}: "
                      f"{impact['current_value']:7.2f} → {impact['new_value']:7.2f} "
                      f"(변화: {impact['value_change']:+.2f})")
        
        return {
            "original_forecast": original_forecast,
            "simulated_forecast": simulated_forecast,
            "change": change,
            "change_percent": change_percent,
            "feature_impacts": feature_impacts
        }
    
    except Exception as e:
        print(f"\n❌ 시뮬레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_scenario_1():
    """시나리오 1: 금리 인상"""
    print("\n" + "🎬"*30)
    print("시나리오 1: 금리 인상 영향 분석")
    print("🎬"*30)
    
    base_prediction = create_mock_base_prediction(price_pred=450.0)
    base_features = create_mock_base_features()
    feature_overrides = {
        "US_10Y_YIELD": 5.0  # 4.2 → 5.0
    }
    
    return simulate_with_mock(base_prediction, base_features, feature_overrides)

def test_scenario_2():
    """시나리오 2: 가뭄 시뮬레이션"""
    print("\n" + "🎬"*30)
    print("시나리오 2: 가뭄 시뮬레이션")
    print("🎬"*30)
    
    base_prediction = create_mock_base_prediction(price_pred=450.0)
    base_features = create_mock_base_features()
    feature_overrides = {
        "PDSI": -3.5,    # 심각한 가뭄
        "SPI_30D": -2.0,
        "SPI_90D": -1.5
    }
    
    return simulate_with_mock(base_prediction, base_features, feature_overrides)

def test_scenario_3():
    """시나리오 3: 복합 시나리오 (금리 인상 + 달러 강세)"""
    print("\n" + "🎬"*30)
    print("시나리오 3: 금리 인상 + 달러 강세")
    print("🎬"*30)
    
    base_prediction = create_mock_base_prediction(price_pred=450.0)
    base_features = create_mock_base_features()
    feature_overrides = {
        "US_10Y_YIELD": 5.0,
        "DXY": 110.0
    }
    
    return simulate_with_mock(base_prediction, base_features, feature_overrides)

def test_scenario_4():
    """시나리오 4: 최악의 상황"""
    print("\n" + "🎬"*30)
    print("시나리오 4: 최악의 상황 (All Negative)")
    print("🎬"*30)
    
    base_prediction = create_mock_base_prediction(price_pred=450.0)
    base_features = create_mock_base_features()
    feature_overrides = {
        "US_10Y_YIELD": 5.5,
        "DXY": 115.0,
        "PDSI": -4.0,
        "SPI_30D": -3.0,
        "SPI_90D": -3.0
    }
    
    return simulate_with_mock(base_prediction, base_features, feature_overrides)

def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*30)
    print("시뮬레이션 API Mock 테스트")
    print("🚀"*30)
    
    scenarios = [
        ("금리 인상", test_scenario_1),
        ("가뭄", test_scenario_2),
        ("금리+달러", test_scenario_3),
        ("최악 상황", test_scenario_4)
    ]
    
    results = []
    
    for name, test_func in scenarios:
        try:
            result = test_func()
            results.append((name, result is not None, result))
        except Exception as e:
            print(f"\n❌ {name} 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, None))
    
    # 최종 결과 요약
    print("\n" + "="*60)
    print("🎯 테스트 결과 요약")
    print("="*60)
    
    for name, success, result in results:
        status = "✅" if success else "❌"
        print(f"{status} {name:15s}", end="")
        if result:
            print(f": ${result['simulated_forecast']:8.2f} ({result['change_percent']:+.2f}%)")
        else:
            print(": 실패")
    
    all_passed = all(success for _, success, _ in results)
    
    if all_passed:
        print("\n🎉 모든 시나리오 테스트 통과!")
        
        # 시나리오별 비교
        print("\n📊 시나리오별 가격 비교:")
        baseline = results[0][2]['simulated_forecast'] if results[0][1] else 450.0
        for name, success, result in results:
            if success and result:
                diff = result['simulated_forecast'] - baseline
                print(f"   {name:15s}: ${result['simulated_forecast']:8.2f} "
                      f"(기준 대비 {diff:+.2f})")
    else:
        print("\n⚠️ 일부 테스트 실패")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
