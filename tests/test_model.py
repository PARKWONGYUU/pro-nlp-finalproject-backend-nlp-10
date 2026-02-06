"""
ONNX 모델 테스트 스크립트
temp/ 폴더의 모델을 로드하고 추론을 테스트합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.ml.model_loader import get_model_loader
from app.ml.prediction_service import get_prediction_service
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_model_loading():
    """모델 로딩 테스트"""
    print("\n" + "="*60)
    print("1️⃣ 모델 로딩 테스트")
    print("="*60)
    
    try:
        model_loader = get_model_loader()
        print(f"✅ 모델 로더 초기화 성공")
        print(f"   - 모드: {model_loader.mode}")
        print(f"   - 경로: {model_loader.local_path}")
        
        # 세션 로드
        session = model_loader.load_session()
        print(f"✅ ONNX 세션 로드 성공")
        
        # 입력/출력 정보 확인
        input_info = session.get_inputs()[0]
        output_info = session.get_outputs()[0]
        
        print(f"\n📊 모델 정보:")
        print(f"   입력 이름: {input_info.name}")
        print(f"   입력 shape: {input_info.shape}")
        print(f"   입력 type: {input_info.type}")
        print(f"   출력 이름: {output_info.name}")
        print(f"   출력 shape: {output_info.shape}")
        print(f"   출력 type: {output_info.type}")
        
        # 전처리 정보 확인
        preprocessing_info = model_loader.get_preprocessing_info()
        if preprocessing_info:
            print(f"\n📦 전처리 정보:")
            if 'scaler' in preprocessing_info:
                print(f"   스케일러: {type(preprocessing_info['scaler']).__name__}")
            if 'feature_names' in preprocessing_info:
                print(f"   Feature 순서: {preprocessing_info['feature_names']}")
        
        return True
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediction_with_mock_features():
    """Mock feature 값으로 예측 테스트"""
    print("\n" + "="*60)
    print("2️⃣ Mock Feature로 예측 테스트")
    print("="*60)
    
    # Mock feature 값들 (시나리오별)
    test_scenarios = [
        {
            "name": "정상 시장 상황",
            "features": {
                "US_10Y_YIELD": 4.2,
                "DXY": 103.5,
                "PDSI": 0.5,
                "SPI_30D": 0.0,
                "SPI_90D": 0.0
            }
        },
        {
            "name": "금리 인상 + 달러 강세",
            "features": {
                "US_10Y_YIELD": 5.0,
                "DXY": 110.0,
                "PDSI": 0.5,
                "SPI_30D": 0.0,
                "SPI_90D": 0.0
            }
        },
        {
            "name": "가뭄 상황",
            "features": {
                "US_10Y_YIELD": 4.2,
                "DXY": 103.5,
                "PDSI": -3.0,
                "SPI_30D": -2.0,
                "SPI_90D": -1.5
            }
        },
        {
            "name": "최악의 시나리오",
            "features": {
                "US_10Y_YIELD": 5.5,
                "DXY": 115.0,
                "PDSI": -4.0,
                "SPI_30D": -3.0,
                "SPI_90D": -3.0
            }
        },
        {
            "name": "최선의 시나리오",
            "features": {
                "US_10Y_YIELD": 3.0,
                "DXY": 95.0,
                "PDSI": 3.0,
                "SPI_30D": 2.0,
                "SPI_90D": 2.0
            }
        }
    ]
    
    try:
        pred_service = get_prediction_service()
        print(f"✅ 예측 서비스 초기화 성공\n")
        
        results = []
        
        for scenario in test_scenarios:
            print(f"\n📋 시나리오: {scenario['name']}")
            print(f"   입력 Features:")
            for key, value in scenario['features'].items():
                print(f"      {key}: {value}")
            
            try:
                # 예측 실행
                prediction = pred_service.predict("corn", scenario['features'])
                print(f"   ✅ 예측 결과: {prediction:.2f}")
                
                results.append({
                    "scenario": scenario['name'],
                    "prediction": prediction,
                    "features": scenario['features']
                })
            except Exception as e:
                print(f"   ❌ 예측 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 결과 요약
        if results:
            print("\n" + "="*60)
            print("📊 예측 결과 요약")
            print("="*60)
            
            for result in results:
                print(f"{result['scenario']:25s} → {result['prediction']:8.2f}")
            
            # 변화율 계산
            if len(results) >= 2:
                baseline = results[0]['prediction']
                print(f"\n💡 기준(정상 시장) 대비 변화율:")
                for result in results[1:]:
                    change = result['prediction'] - baseline
                    change_pct = (change / baseline) * 100
                    print(f"   {result['scenario']:25s} → {change:+8.2f} ({change_pct:+.2f}%)")
        
        return True
    except Exception as e:
        print(f"❌ 예측 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feature_sensitivity():
    """각 Feature의 민감도 테스트"""
    print("\n" + "="*60)
    print("3️⃣ Feature 민감도 분석")
    print("="*60)
    
    # 기준 값
    baseline_features = {
        "US_10Y_YIELD": 4.2,
        "DXY": 103.5,
        "PDSI": 0.0,
        "SPI_30D": 0.0,
        "SPI_90D": 0.0
    }
    
    try:
        pred_service = get_prediction_service()
        
        # 기준 예측
        baseline_pred = pred_service.predict("corn", baseline_features)
        print(f"📌 기준 예측값: {baseline_pred:.2f}\n")
        
        # 각 Feature를 10% 증가시켜보기
        for feature_name, baseline_value in baseline_features.items():
            test_features = baseline_features.copy()
            
            # 10% 증가
            increased_value = baseline_value * 1.1 if baseline_value != 0 else 0.1
            test_features[feature_name] = increased_value
            
            new_pred = pred_service.predict("corn", test_features)
            change = new_pred - baseline_pred
            change_pct = (change / baseline_pred) * 100
            
            print(f"{feature_name:15s}: {baseline_value:6.2f} → {increased_value:6.2f}")
            print(f"   예측 변화: {baseline_pred:.2f} → {new_pred:.2f} ({change:+.2f}, {change_pct:+.2f}%)\n")
        
        return True
    except Exception as e:
        print(f"❌ 민감도 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*30)
    print("ONNX 모델 테스트 시작")
    print("🚀"*30)
    
    # 환경 체크
    print(f"\n📂 작업 디렉토리: {os.getcwd()}")
    print(f"📂 temp/ 폴더 존재: {Path('temp').exists()}")
    if Path('temp').exists():
        onnx_files = list(Path('temp').glob('*.onnx'))
        pkl_files = list(Path('temp').glob('*.pkl'))
        print(f"   - ONNX 파일: {[f.name for f in onnx_files]}")
        print(f"   - PKL 파일: {[f.name for f in pkl_files]}")
    
    # 테스트 실행
    test_results = []
    
    # 1. 모델 로딩 테스트
    test_results.append(("모델 로딩", test_model_loading()))
    
    # 2. 예측 테스트
    test_results.append(("Mock Feature 예측", test_prediction_with_mock_features()))
    
    # 3. 민감도 분석
    test_results.append(("Feature 민감도", test_feature_sensitivity()))
    
    # 최종 결과
    print("\n" + "="*60)
    print("🎯 최종 테스트 결과")
    print("="*60)
    
    for test_name, result in test_results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(result for _, result in test_results)
    
    if all_passed:
        print("\n🎉 모든 테스트 통과! 모델이 정상적으로 작동합니다.")
    else:
        print("\n⚠️ 일부 테스트 실패. 위 로그를 확인하세요.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
