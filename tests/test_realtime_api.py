"""
실시간 API 데이터 수집 테스트 스크립트

DB가 비어있을 때 실시간으로 데이터를 가져오는지 테스트합니다.
"""

import sys
from datetime import date, timedelta
from app.data_fetcher import fetch_realtime_features

def test_fetch_realtime_features():
    """실시간 데이터 수집 테스트"""
    print("=" * 60)
    print("실시간 데이터 수집 테스트")
    print("=" * 60)
    
    commodity = "corn"
    end_date = date.today()
    days = 60
    
    print(f"\n품목: {commodity}")
    print(f"종료 날짜: {end_date}")
    print(f"조회 일수: {days}일")
    print(f"\n데이터 수집 시작...\n")
    
    try:
        result = fetch_realtime_features(
            commodity=commodity,
            end_date=end_date,
            days=days,
            fred_api_key=None  # API 키 없어도 더미 데이터로 폴백
        )
        
        print("✅ 데이터 수집 성공!")
        print(f"\n날짜 개수: {len(result['dates'])}일")
        print(f"Feature 개수: {len(result['features'])}개")
        
        print(f"\nFeature 목록 (처음 10개):")
        for i, feature_name in enumerate(list(result['features'].keys())[:10], 1):
            values = result['features'][feature_name]
            print(f"  {i}. {feature_name}: {len(values)}개 값 (예: {values[0]:.4f})")
        
        # 필수 feature 확인
        required_features = [
            'close', 'open', 'high', 'low', 'volume', 'EMA',
            '10Y_Yield', 'USD_Index',
            'pdsi', 'spi30d', 'spi90d',
            'lambda_price', 'lambda_news',
            'news_count'
        ]
        
        print(f"\n필수 Feature 확인:")
        missing = []
        for feature in required_features:
            if feature in result['features']:
                print(f"  ✅ {feature}")
            else:
                print(f"  ❌ {feature} (누락)")
                missing.append(feature)
        
        # 뉴스 PCA 확인
        news_pca_count = sum(1 for f in result['features'] if f.startswith('news_pca_'))
        print(f"\n뉴스 PCA: {news_pca_count}개 (예상: 32개)")
        
        if missing:
            print(f"\n⚠️  경고: {len(missing)}개 feature 누락")
            return False
        
        if news_pca_count != 32:
            print(f"⚠️  경고: 뉴스 PCA 개수 불일치 (기대: 32, 실제: {news_pca_count})")
            return False
        
        print(f"\n총 Feature 개수: {len(result['features'])} (예상: 52)")
        
        if len(result['features']) >= 46:  # 최소 46개 (52개 중 일부 누락 가능)
            print("\n✅ 모든 테스트 통과!")
            return True
        else:
            print(f"\n❌ Feature 개수 부족 (최소 46개 필요)")
            return False
            
    except Exception as e:
        print(f"\n❌ 데이터 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_fetcher_components():
    """개별 컴포넌트 테스트"""
    print("\n" + "=" * 60)
    print("개별 컴포넌트 테스트")
    print("=" * 60)
    
    from app.data_fetcher import DataFetcher
    
    fetcher = DataFetcher(fred_api_key=None)
    end_date = date.today()
    days = 30
    
    # 1. 가격 데이터 테스트
    print("\n1. 가격 데이터 수집 테스트...")
    try:
        price_df = fetcher.fetch_price_data("corn", end_date, days)
        print(f"   ✅ 성공: {len(price_df)}일")
        print(f"   컬럼: {list(price_df.columns)}")
        print(f"   샘플 (최근 3일):")
        print(price_df.tail(3).to_string(index=False))
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    # 2. 경제 지표 테스트
    print("\n2. 경제 지표 수집 테스트...")
    try:
        econ_df = fetcher.fetch_economic_data(end_date, days)
        print(f"   ✅ 성공: {len(econ_df)}일")
        print(f"   컬럼: {list(econ_df.columns)}")
        print(f"   샘플 (최근 3일):")
        print(econ_df.tail(3).to_string(index=False))
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    # 3. 더미 feature 테스트
    print("\n3. 더미 Feature 생성 테스트...")
    try:
        dummy = fetcher.generate_dummy_features(days)
        print(f"   ✅ 성공: {len(dummy)}개 feature")
        print(f"   Feature 목록: {list(dummy.keys())[:5]}...")
    except Exception as e:
        print(f"   ❌ 실패: {e}")


if __name__ == "__main__":
    print("\n🚀 실시간 API 데이터 수집 테스트 시작\n")
    
    # 개별 컴포넌트 테스트
    test_data_fetcher_components()
    
    # 통합 테스트
    success = test_fetch_realtime_features()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 테스트 완료: 모든 테스트 통과!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ 테스트 실패: 일부 테스트가 실패했습니다.")
        print("=" * 60)
        sys.exit(1)
