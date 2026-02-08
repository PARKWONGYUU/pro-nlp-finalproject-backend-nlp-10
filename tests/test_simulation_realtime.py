"""
시뮬레이션 API 실시간 데이터 테스트

DB가 비어있을 때 실시간으로 데이터를 가져와서 시뮬레이션이 작동하는지 테스트합니다.
"""

import requests
import json
from datetime import date, timedelta

# API 설정
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/simulate"

def test_simulation_api():
    """시뮬레이션 API 테스트"""
    print("=" * 60)
    print("시뮬레이션 API 실시간 데이터 테스트")
    print("=" * 60)
    
    # 테스트 요청 데이터
    base_date = (date.today() - timedelta(days=1)).isoformat()
    
    payload = {
        "commodity": "corn",
        "base_date": base_date,
        "feature_overrides": {
            "10Y_Yield": 4.5,
            "USD_Index": 110.0
        }
    }
    
    print(f"\n요청 데이터:")
    print(f"  품목: {payload['commodity']}")
    print(f"  기준 날짜: {payload['base_date']}")
    print(f"  Feature 변경:")
    for key, value in payload['feature_overrides'].items():
        print(f"    - {key}: {value}")
    
    print(f"\nAPI 호출 중: {API_ENDPOINT}")
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            timeout=60  # 60초 타임아웃
        )
        
        print(f"\n응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ API 호출 성공!")
            print(f"\n응답 데이터:")
            print(f"  기준 날짜: {result.get('base_date')}")
            print(f"  예측 일수: {len(result.get('predictions', []))}일")
            print(f"  Feature 영향도: {len(result.get('feature_impacts', []))}개")
            
            # 요약 정보 출력
            summary = result.get('summary', {})
            print(f"\n요약 정보:")
            print(f"  평균 원본 가격: ${summary.get('avg_original_price', 0):.2f}")
            print(f"  평균 시뮬레이션 가격: ${summary.get('avg_simulated_price', 0):.2f}")
            print(f"  평균 변화: ${summary.get('avg_change', 0):.2f} ({summary.get('avg_change_percent', 0):.2f}%)")
            print(f"  총 변화: ${summary.get('total_change', 0):.2f}")
            
            # 처음 5일 예측 출력
            predictions = result.get('predictions', [])
            if predictions:
                print(f"\n예측 샘플 (처음 5일):")
                for i, pred in enumerate(predictions[:5], 1):
                    print(f"  {i}. {pred['date']}: "
                          f"원본 ${pred['original_price']:.2f} → "
                          f"시뮬 ${pred['simulated_price']:.2f} "
                          f"({pred['change_percent']:+.2f}%)")
            
            # Feature 영향도 출력
            impacts = result.get('feature_impacts', [])
            if impacts:
                print(f"\nFeature 영향도:")
                for impact in impacts:
                    print(f"  - {impact['feature']}: "
                          f"{impact['current_value']:.2f} → {impact['new_value']:.2f} "
                          f"(기여도: {impact['contribution']:+.2f})")
            
            print("\n✅ 시뮬레이션 API 테스트 통과!")
            return True
            
        else:
            print(f"\n❌ API 호출 실패")
            print(f"응답: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 서버에 연결할 수 없습니다.")
        print(f"서버가 실행 중인지 확인하세요: {BASE_URL}")
        print(f"\n서버 실행 명령:")
        print(f"  cd /Users/jsshin/Documents/pro-nlp-finalproject-backend-nlp-10")
        print(f"  source venv/bin/activate")
        print(f"  uvicorn main:app --reload")
        return False
        
    except requests.exceptions.Timeout:
        print(f"\n❌ 요청 타임아웃 (60초 초과)")
        print(f"데이터 수집에 시간이 오래 걸릴 수 있습니다.")
        return False
        
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 시뮬레이션 API 실시간 데이터 테스트 시작\n")
    
    success = test_simulation_api()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 테스트 완료: 시뮬레이션 API가 정상 작동합니다!")
        print("=" * 60)
    else:
        print("❌ 테스트 실패")
        print("=" * 60)
