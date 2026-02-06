"""
EC2에서 S3 모델 로딩 및 예측 테스트

실행 방법:
    python tests/test_s3_model_loading.py

환경 변수 필요:
    MODEL_LOAD_MODE=s3
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    DATABASE_URL=... (필수, 하지만 DB는 사용 안함)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ml.model_loader import get_model_loader
from app.ml.prediction_service import ONNXPredictionService
from app.config import settings


def generate_mock_60d_data():
    """
    과거 60일 Mock 데이터 생성
    
    Returns:
        Dict with 'dates' and 'features'
    """
    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') 
             for i in range(59, -1, -1)]
    
    # 기본 가격 데이터 (무작위 변동)
    base_price = 450.0
    prices = []
    current_price = base_price
    
    for _ in range(60):
        change = np.random.uniform(-5, 5)
        current_price = max(400, min(500, current_price + change))
        prices.append(current_price)
    
    # Feature 데이터 생성 (52개 중 46개는 DB에서, 6개는 동적 생성)
    features = {
        # 가격/거래량 (6개)
        'close': prices,
        'open': [p - np.random.uniform(-2, 2) for p in prices],
        'high': [p + abs(np.random.uniform(0, 3)) for p in prices],
        'low': [p - abs(np.random.uniform(0, 3)) for p in prices],
        'volume': [np.random.uniform(80000, 120000) for _ in range(60)],
        'EMA': [p * 0.98 + np.random.uniform(-1, 1) for p in prices],
        
        # 뉴스 PCA (32개) - 0 근처 작은 값
        **{f'news_pca_{i}': [np.random.uniform(-0.5, 0.5) for _ in range(60)] 
           for i in range(32)},
        
        # 기후 지수 (3개)
        'pdsi': [np.random.uniform(-2, 2) for _ in range(60)],
        'spi30d': [np.random.uniform(-1.5, 1.5) for _ in range(60)],
        'spi90d': [np.random.uniform(-1.5, 1.5) for _ in range(60)],
        
        # 거시경제 (2개)
        '10Y_Yield': [np.random.uniform(4.0, 4.5) for _ in range(60)],
        'USD_Index': [np.random.uniform(103, 107) for _ in range(60)],
        
        # Hawkes Intensity (2개)
        'lambda_price': [np.random.uniform(0, 0.5) for _ in range(60)],
        'lambda_news': [np.random.uniform(0, 0.3) for _ in range(60)],
        
        # 뉴스 개수 (1개)
        'news_count': [np.random.randint(0, 10) for _ in range(60)],
    }
    
    return {
        'dates': dates,
        'features': features
    }


def test_s3_model_loading():
    """S3 모델 로딩 테스트"""
    print("=" * 80)
    print("🧪 EC2 S3 모델 로딩 테스트")
    print("=" * 80)
    print()
    
    # Step 1: 설정 확인
    print("📋 Step 1: 설정 확인")
    print("-" * 80)
    print(f"모델 로딩 모드: {settings.model_load_mode}")
    print(f"S3 버킷: {settings.model_s3_bucket}")
    print(f"S3 프리픽스: {settings.model_s3_prefix}")
    print(f"AWS 리전: {settings.aws_region}")
    print(f"Encoder 길이: {settings.encoder_length}")
    print(f"예측 길이: {settings.prediction_length}")
    print()
    
    if settings.model_load_mode != "s3":
        print(f"ℹ️  현재 모드: {settings.model_load_mode}")
        print(f"   로컬 경로: {settings.local_model_path}")
        print()
    
    # Step 2: 모델 로드
    print(f"📥 Step 2: 모델 로드 중... (모드: {settings.model_load_mode})")
    print("-" * 80)
    
    try:
        model_loader = get_model_loader()
        session = model_loader.load_session("corn")
        
        print(f"✅ 모델 로드 성공!")
        print(f"   ONNX 세션: {session}")
        
        # 입력/출력 확인
        input_names = [inp.name for inp in session.get_inputs()]
        output_names = [out.name for out in session.get_outputs()]
        
        print(f"   입력 개수: {len(input_names)}")
        print(f"   입력 이름: {input_names}")
        print(f"   출력 개수: {len(output_names)}")
        print(f"   출력 이름: {output_names}")
        print()
        
        # 입력 shape 확인
        print(f"   📐 입력 Shape:")
        for inp in session.get_inputs():
            print(f"      {inp.name}: {inp.shape}")
        print()
        
        # 전처리 정보 확인
        preprocessing = model_loader.get_preprocessing_info("corn")
        if preprocessing:
            print(f"✅ 전처리 정보 로드 성공!")
            print(f"   키: {list(preprocessing.keys())[:5]}... (총 {len(preprocessing)} 항목)")
        else:
            print(f"⚠️  전처리 정보 없음 (선택사항)")
        print()
        
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Mock 데이터 생성
    print("🎲 Step 3: 과거 60일 Mock 데이터 생성")
    print("-" * 80)
    
    try:
        historical_data = generate_mock_60d_data()
        print(f"✅ Mock 데이터 생성 완료")
        print(f"   날짜 범위: {historical_data['dates'][0]} ~ {historical_data['dates'][-1]}")
        print(f"   Feature 개수: {len(historical_data['features'])}")
        print(f"   각 Feature 데이터 포인트: {len(historical_data['features']['close'])}개")
        
        # 샘플 데이터 출력
        print(f"\n   📊 최근 5일 가격 샘플:")
        for i in range(-5, 0):
            date = historical_data['dates'][i]
            close = historical_data['features']['close'][i]
            open_price = historical_data['features']['open'][i]
            print(f"      {date}: Close=${close:.2f}, Open=${open_price:.2f}")
        print()
        
    except Exception as e:
        print(f"❌ Mock 데이터 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: 예측 실행
    print("🔮 Step 4: TFT 모델 예측 실행")
    print("-" * 80)
    
    try:
        prediction_service = ONNXPredictionService()
        
        # Feature override 테스트 (선택사항)
        feature_overrides = {
            "10Y_Yield": 4.3,
            "USD_Index": 105.5,
            "pdsi": -1.2,
        }
        
        print(f"Feature Override 적용:")
        for key, val in feature_overrides.items():
            print(f"   {key}: {val}")
        print()
        
        result = prediction_service.predict_tft(
            commodity="corn",
            historical_data=historical_data,
            feature_overrides=feature_overrides
        )
        
        print(f"✅ 예측 성공!")
        print()
        print(f"📈 예측 결과 (7일):")
        print("-" * 80)
        
        predictions = result.get('predictions', [])
        lower_bounds = result.get('lower_bounds', [])
        upper_bounds = result.get('upper_bounds', [])
        
        start_date = datetime.now().date() + timedelta(days=1)
        
        for i in range(len(predictions)):
            pred_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            pred = predictions[i]
            lower = lower_bounds[i] if i < len(lower_bounds) else None
            upper = upper_bounds[i] if i < len(upper_bounds) else None
            
            if lower is not None and upper is not None:
                print(f"   Day {i+1} ({pred_date}): ${pred:.2f}  [${lower:.2f} ~ ${upper:.2f}]")
            else:
                print(f"   Day {i+1} ({pred_date}): ${pred:.2f}")
        
        print()
        print("=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"❌ 예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_s3_model_loading()
    sys.exit(0 if success else 1)
