"""
TFT ONNX 모델 테스트 스크립트 (Mock 데이터 사용)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.ml.prediction_service import get_prediction_service
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_mock_historical_data(days=60):
    """
    과거 60일의 Mock 시계열 데이터 생성
    """
    dates = []
    features = {
        # 가격/거래량 (6개)
        'close': [],
        'open': [],
        'high': [],
        'low': [],
        'volume': [],
        'EMA': [],
        # 뉴스 PCA (32개)
        **{f'news_pca_{i}': [] for i in range(32)},
        # 기후 (3개)
        'pdsi': [],
        'spi30d': [],
        'spi90d': [],
        # 거시경제 (2개)
        '10Y_Yield': [],
        'USD_Index': [],
        # Hawkes (2개)
        'lambda_price': [],
        'lambda_news': [],
        # Known features
        'time_idx': [],
        'day_of_year': [],
        'news_count': []
    }
    
    # 60일간 데이터 생성
    base_price = 450.0
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).date()
        dates.append(str(date))
        
        # 가격 데이터 (약간의 변동)
        price = base_price + (i * 0.5)  # 서서히 상승
        features['close'].append(price)
        features['open'].append(price - 1.0)
        features['high'].append(price + 2.0)
        features['low'].append(price - 2.0)
        features['volume'].append(1000000.0)
        features['EMA'].append(price - 0.5)
        
        # 뉴스 PCA (랜덤 값)
        for j in range(32):
            features[f'news_pca_{j}'].append(0.0)
        
        # 기후 지수
        features['pdsi'].append(0.5)
        features['spi30d'].append(0.0)
        features['spi90d'].append(0.0)
        
        # 거시경제
        features['10Y_Yield'].append(4.2)
        features['USD_Index'].append(103.5)
        
        # Hawkes
        features['lambda_price'].append(0.8)
        features['lambda_news'].append(0.2)
        
        # Known features
        features['time_idx'].append(float(i))
        features['day_of_year'].append(float(date.timetuple().tm_yday))
        features['news_count'].append(10.0)
    
    return {
        'dates': dates,
        'features': features
    }

def test_basic_prediction():
    """기본 예측 테스트"""
    print("\n" + "="*70)
    print("1️⃣ 기본 예측 테스트 (Override 없음)")
    print("="*70)
    
    try:
        # Mock 데이터 생성
        historical_data = create_mock_historical_data(60)
        print(f"✅ Mock 데이터 생성 완료: {len(historical_data['dates'])}일")
        
        # 예측 서비스
        pred_service = get_prediction_service()
        
        # 예측 실행
        result = pred_service.predict_tft("corn", historical_data, feature_overrides=None)
        
        print(f"\n📊 예측 결과:")
        print(f"   7일 예측 (중앙값): {[f'{p:.2f}' for p in result['predictions']]}")
        print(f"   하한: {[f'{p:.2f}' for p in result['lower_bounds']]}")
        print(f"   상한: {[f'{p:.2f}' for p in result['upper_bounds']]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_feature_overrides():
    """Feature Override 테스트"""
    print("\n" + "="*70)
    print("2️⃣ Feature Override 테스트")
    print("="*70)
    
    scenarios = [
        {
            "name": "금리 인상",
            "overrides": {"10Y_Yield": 5.0}
        },
        {
            "name": "가뭄 상황",
            "overrides": {
                "pdsi": -3.0,
                "spi30d": -2.0,
                "spi90d": -1.5
            }
        },
        {
            "name": "복합 시나리오",
            "overrides": {
                "10Y_Yield": 5.0,
                "USD_Index": 110.0,
                "pdsi": -2.0
            }
        }
    ]
    
    try:
        # Mock 데이터 생성
        historical_data = create_mock_historical_data(60)
        pred_service = get_prediction_service()
        
        # 기준 예측
        baseline = pred_service.predict_tft("corn", historical_data, None)
        baseline_price = baseline['predictions'][0]
        print(f"\n📌 기준 예측: ${baseline_price:.2f}")
        
        # 각 시나리오 테스트
        for scenario in scenarios:
            print(f"\n{'─'*70}")
            print(f"📋 시나리오: {scenario['name']}")
            print(f"   변경 Feature: {scenario['overrides']}")
            
            result = pred_service.predict_tft(
                "corn", 
                historical_data, 
                feature_overrides=scenario['overrides']
            )
            
            new_price = result['predictions'][0]
            change = new_price - baseline_price
            change_pct = (change / baseline_price) * 100
            
            print(f"   예측: ${new_price:.2f}")
            print(f"   변화: ${change:+.2f} ({change_pct:+.2f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_data_lengths():
    """다양한 데이터 길이 테스트"""
    print("\n" + "="*70)
    print("3️⃣ 데이터 길이 테스트")
    print("="*70)
    
    try:
        pred_service = get_prediction_service()
        
        for days in [60]:  # TFT는 정확히 60일 필요
            print(f"\n📏 {days}일 데이터:")
            historical_data = create_mock_historical_data(days)
            result = pred_service.predict_tft("corn", historical_data, None)
            print(f"   예측: ${result['predictions'][0]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*35)
    print("TFT ONNX 모델 테스트")
    print("🚀"*35)
    
    # 환경 체크
    print(f"\n📂 작업 디렉토리: {os.getcwd()}")
    temp_path = Path("temp")
    if temp_path.exists():
        onnx_files = list(temp_path.glob("*.onnx"))
        pkl_files = list(temp_path.glob("*.pkl"))
        print(f"📁 temp/ 폴더:")
        print(f"   ONNX: {[f.name for f in onnx_files if f.stat().st_size > 100]}")
        print(f"   PKL: {[f.name for f in pkl_files if f.stat().st_size > 100]}")
    
    # 테스트 실행
    tests = [
        ("기본 예측", test_basic_prediction),
        ("Feature Override", test_with_feature_overrides),
        ("데이터 길이", test_different_data_lengths),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 테스트 예외 발생: {e}")
            results.append((name, False))
    
    # 최종 결과
    print("\n" + "="*70)
    print("🎯 테스트 결과 요약")
    print("="*70)
    
    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{name:20s}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
