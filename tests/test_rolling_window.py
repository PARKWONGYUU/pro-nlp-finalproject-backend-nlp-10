"""
Rolling Window 테스트
60일 예측을 위해 9번의 7일 예측이 반복되는지 확인
"""
import requests
from datetime import date, timedelta

base_date = (date.today() - timedelta(days=1)).isoformat()
commodity = 'corn'

print('=' * 80)
print('Rolling Window 테스트')
print('=' * 80)
print()
print('60일 예측을 위해:')
print('- 7일씩 예측 × 9 cycle = 63일')
print('- 각 cycle에서 예측 결과를 다음 입력으로 사용 (rolling)')
print('- Override된 feature는 rolling 시에도 계속 적용되어야 함')
print()
print('=' * 80)

request_data = {
    "commodity": commodity,
    "base_date": base_date,
    "feature_overrides": {
        "10Y_Yield": 5.0,
        "USD_Index": 110.0
    }
}

print(f'\n요청:')
print(f'  commodity: {commodity}')
print(f'  base_date: {base_date}')
print(f'  feature_overrides: {request_data["feature_overrides"]}')
print()

try:
    print('⏳ 시뮬레이션 실행 중... (최대 2분 소요)')
    response = requests.post(
        'http://localhost:8000/api/simulate',
        json=request_data,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        predictions = data.get('predictions', [])
        summary = data.get('summary', {})
        feature_impacts = data.get('feature_impacts', [])
        
        print()
        print('=' * 80)
        print('✅ 성공!')
        print('=' * 80)
        print()
        
        print('📊 요약:')
        print(f'  총 예측 일수: {summary.get("total_days", 0)}일')
        print(f'  평균 원본 가격: ${summary.get("avg_original_price", 0):.2f}')
        print(f'  평균 시뮬레이션 가격: ${summary.get("avg_simulated_price", 0):.2f}')
        print(f'  평균 변화: ${summary.get("avg_change", 0):.2f} ({summary.get("avg_change_percent", 0):.2f}%)')
        print()
        
        print('📈 Feature 영향도:')
        for impact in feature_impacts:
            print(f'  {impact["feature"]}:')
            print(f'    현재: {impact["current_value"]:.2f} → 변경: {impact["new_value"]:.2f}')
            print(f'    변화량: {impact["value_change"]:.2f}, 기여도: {impact["contribution"]:.2f}')
        print()
        
        print('📅 예측 결과 샘플 (처음 7일, 마지막 7일):')
        print()
        print('처음 7일 (1차 예측):')
        for i in range(min(7, len(predictions))):
            p = predictions[i]
            print(f'  Day {i+1} ({p["date"]}): 원본=${p["original_price"]:.2f}, '
                  f'시뮬=${p["simulated_price"]:.2f}, 변화=${p["change"]:.2f} ({p["change_percent"]:.2f}%)')
        
        if len(predictions) > 7:
            print()
            print('마지막 7일 (9차 rolling 후):')
            for i in range(max(0, len(predictions) - 7), len(predictions)):
                p = predictions[i]
                day_num = i + 1
                print(f'  Day {day_num} ({p["date"]}): 원본=${p["original_price"]:.2f}, '
                      f'시뮬=${p["simulated_price"]:.2f}, 변화=${p["change"]:.2f} ({p["change_percent"]:.2f}%)')
        
        print()
        print('=' * 80)
        print('💡 서버 로그 확인 사항:')
        print('=' * 80)
        print('1. "Rolling prediction cycle X/9" 메시지가 9번 나타나야 함')
        print('2. "🔄 Rolling window 업데이트" 메시지가 8번 나타나야 함 (마지막 제외)')
        print('3. "🔧 Feature override 적용" 메시지가 18번 나타나야 함 (원본 9번 + 시뮬 9번)')
        print('4. Override된 feature (10Y_Yield, USD_Index)가 rolling 시에도 적용되는지 확인')
        print()
        
        # 변화 분석
        print('=' * 80)
        print('📊 변화 분석:')
        print('=' * 80)
        
        first_7_changes = [p['change'] for p in predictions[:7]]
        last_7_changes = [p['change'] for p in predictions[-7:]]
        
        avg_first = sum(first_7_changes) / len(first_7_changes) if first_7_changes else 0
        avg_last = sum(last_7_changes) / len(last_7_changes) if last_7_changes else 0
        
        print(f'처음 7일 평균 변화: ${avg_first:.2f}')
        print(f'마지막 7일 평균 변화: ${avg_last:.2f}')
        print()
        
        if abs(avg_first - avg_last) > 1.0:
            print('✅ Rolling window가 작동하는 것으로 보입니다 (시간에 따라 변화가 누적됨)')
        else:
            print('⚠️  모든 구간에서 비슷한 변화 - rolling이 제대로 작동하는지 확인 필요')
        
    else:
        print(f'❌ 실패: {response.status_code}')
        print(response.text)

except requests.exceptions.Timeout:
    print('❌ 타임아웃: 2분이 지났습니다.')
    print('서버가 응답하지 않거나 예측이 너무 오래 걸립니다.')
except Exception as e:
    print(f'❌ 오류: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 80)
