"""
간단한 시뮬레이션 테스트
1. Override 없이 실행
2. Override 있게 실행
3. 결과 비교
"""
import requests
from datetime import date, timedelta
import json

base_date = (date.today() - timedelta(days=1)).isoformat()
commodity = 'corn'

print('=' * 80)
print('간단한 Override 테스트')
print('=' * 80)
print()

# 테스트 1: Override 없이
print('📊 테스트 1: Override 없이')
print('-' * 80)

request1 = {
    "commodity": commodity,
    "base_date": base_date,
    "feature_overrides": {}
}

response1 = requests.post(
    'http://localhost:8000/api/simulate',
    json=request1,
    timeout=120
)

if response1.status_code == 200:
    data1 = response1.json()
    summary1 = data1.get('summary', {})
    
    print(f'✅ 성공')
    print(f'평균 원본: ${summary1.get("avg_original_price", 0):.2f}')
    print(f'평균 시뮬레이션: ${summary1.get("avg_simulated_price", 0):.2f}')
    print(f'평균 변화: ${summary1.get("avg_change", 0):.2f}')
    
    # 처음 3일 예측값
    predictions1 = data1.get('predictions', [])
    print(f'\n처음 3일 예측:')
    for i in range(min(3, len(predictions1))):
        p = predictions1[i]
        print(f'  {p["date"]}: 원본=${p["original_price"]:.2f}, 시뮬=${p["simulated_price"]:.2f}, 변화=${p["change"]:.2f}')
else:
    print(f'❌ 실패: {response1.status_code}')
    print(response1.text)
    exit(1)

print()
print('=' * 80)

# 테스트 2: 큰 Override 적용
print('📊 테스트 2: 큰 Override 적용')
print('-' * 80)

request2 = {
    "commodity": commodity,
    "base_date": base_date,
    "feature_overrides": {
        "10Y_Yield": 10.0,  # 매우 큰 값
        "USD_Index": 150.0,  # 매우 큰 값
    }
}

response2 = requests.post(
    'http://localhost:8000/api/simulate',
    json=request2,
    timeout=120
)

if response2.status_code == 200:
    data2 = response2.json()
    summary2 = data2.get('summary', {})
    
    print(f'✅ 성공')
    print(f'평균 원본: ${summary2.get("avg_original_price", 0):.2f}')
    print(f'평균 시뮬레이션: ${summary2.get("avg_simulated_price", 0):.2f}')
    print(f'평균 변화: ${summary2.get("avg_change", 0):.2f}')
    
    # 처음 3일 예측값
    predictions2 = data2.get('predictions', [])
    print(f'\n처음 3일 예측:')
    for i in range(min(3, len(predictions2))):
        p = predictions2[i]
        print(f'  {p["date"]}: 원본=${p["original_price"]:.2f}, 시뮬=${p["simulated_price"]:.2f}, 변화=${p["change"]:.2f}')
    
    # Feature impacts
    print(f'\nFeature 영향도:')
    for impact in data2.get('feature_impacts', []):
        print(f'  {impact["feature"]}: {impact["current_value"]:.2f} → {impact["new_value"]:.2f} (기여도: {impact["contribution"]:.2f})')
else:
    print(f'❌ 실패: {response2.status_code}')
    print(response2.text)
    exit(1)

print()
print('=' * 80)
print('📈 결과 비교')
print('=' * 80)

# 원본 가격 비교 (두 테스트에서 동일해야 함)
print(f'\n원본 가격 (두 테스트에서 동일해야 함):')
print(f'  테스트 1: ${summary1.get("avg_original_price", 0):.2f}')
print(f'  테스트 2: ${summary2.get("avg_original_price", 0):.2f}')
orig_diff = abs(summary1.get("avg_original_price", 0) - summary2.get("avg_original_price", 0))
if orig_diff < 0.01:
    print(f'  ✅ 동일함 (차이: ${orig_diff:.4f})')
else:
    print(f'  ❌ 다름! (차이: ${orig_diff:.2f})')

# 시뮬레이션 가격 비교 (달라야 함)
print(f'\n시뮬레이션 가격 (달라야 함):')
print(f'  테스트 1 (no override): ${summary1.get("avg_simulated_price", 0):.2f}')
print(f'  테스트 2 (override): ${summary2.get("avg_simulated_price", 0):.2f}')
sim_diff = abs(summary1.get("avg_simulated_price", 0) - summary2.get("avg_simulated_price", 0))
if sim_diff > 0.01:
    print(f'  ✅ 다름! (차이: ${sim_diff:.2f})')
else:
    print(f'  ❌ 동일함 (차이: ${sim_diff:.4f}) - 문제 있음!')

print()
print('=' * 80)
print('💡 서버 로그를 확인하여 "🔧 Feature override 적용" 메시지를 찾으세요.')
print('=' * 80)
