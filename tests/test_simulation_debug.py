"""
시뮬레이션 디버깅 테스트
feature_overrides를 크게 변경해서 실제로 결과가 달라지는지 확인
"""
import requests
from datetime import date, timedelta
import json

base_date = (date.today() - timedelta(days=1)).isoformat()
commodity = 'corn'

print('=' * 80)
print('시뮬레이션 디버깅 테스트')
print('=' * 80)
print()

# 테스트 1: Override 없이 (베이스라인)
print('📊 테스트 1: Override 없이 (베이스라인)')
print('-' * 80)

request_data_baseline = {
    "commodity": commodity,
    "base_date": base_date,
    "feature_overrides": {}
}

try:
    response = requests.post(
        'http://localhost:8000/api/simulate',
        json=request_data_baseline,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        predictions = data.get('predictions', [])
        summary = data.get('summary', {})
        
        print(f'✅ 성공: {response.status_code}')
        print(f'예측 일수: {len(predictions)}일')
        print(f'평균 원본 가격: ${summary.get("avg_original_price", 0):.2f}')
        print(f'평균 시뮬레이션 가격: ${summary.get("avg_simulated_price", 0):.2f}')
        print(f'평균 변화: ${summary.get("avg_change", 0):.2f}')
        print()
        
        baseline_avg_original = summary.get("avg_original_price", 0)
        baseline_avg_simulated = summary.get("avg_simulated_price", 0)
        
    else:
        print(f'❌ 실패: {response.status_code}')
        print(response.text)
        baseline_avg_original = None
        baseline_avg_simulated = None

except Exception as e:
    print(f'❌ 오류: {e}')
    baseline_avg_original = None
    baseline_avg_simulated = None

print()
print('=' * 80)

# 테스트 2: 큰 변화 적용
print('📊 테스트 2: 큰 변화 적용 (10Y_Yield +50%, USD_Index +20%)')
print('-' * 80)

request_data_changed = {
    "commodity": commodity,
    "base_date": base_date,
    "feature_overrides": {
        "10Y_Yield": 6.0,  # 큰 값
        "USD_Index": 120.0,  # 큰 값
        "pdsi": 5.0,  # 큰 값
        "spi30d": 3.0,  # 큰 값
        "spi90d": 3.0  # 큰 값
    }
}

try:
    response = requests.post(
        'http://localhost:8000/api/simulate',
        json=request_data_changed,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        predictions = data.get('predictions', [])
        summary = data.get('summary', {})
        feature_impacts = data.get('feature_impacts', [])
        
        print(f'✅ 성공: {response.status_code}')
        print(f'예측 일수: {len(predictions)}일')
        print(f'평균 원본 가격: ${summary.get("avg_original_price", 0):.2f}')
        print(f'평균 시뮬레이션 가격: ${summary.get("avg_simulated_price", 0):.2f}')
        print(f'평균 변화: ${summary.get("avg_change", 0):.2f}')
        print()
        
        print('Feature 영향도:')
        for impact in feature_impacts:
            print(f'  {impact["feature"]}: {impact["current_value"]:.2f} → {impact["new_value"]:.2f} '
                  f'(변화: {impact["value_change"]:.2f}, 기여도: {impact["contribution"]:.2f})')
        print()
        
        changed_avg_original = summary.get("avg_original_price", 0)
        changed_avg_simulated = summary.get("avg_simulated_price", 0)
        
        # 비교
        if baseline_avg_original and baseline_avg_simulated:
            print('=' * 80)
            print('📈 결과 비교')
            print('=' * 80)
            print(f'베이스라인 원본: ${baseline_avg_original:.2f}')
            print(f'베이스라인 시뮬레이션: ${baseline_avg_simulated:.2f}')
            print(f'변경 후 원본: ${changed_avg_original:.2f}')
            print(f'변경 후 시뮬레이션: ${changed_avg_simulated:.2f}')
            print()
            
            original_diff = changed_avg_original - baseline_avg_original
            simulated_diff = changed_avg_simulated - baseline_avg_simulated
            
            print(f'원본 가격 차이: ${original_diff:.2f} ({(original_diff / baseline_avg_original * 100):.2f}%)')
            print(f'시뮬레이션 가격 차이: ${simulated_diff:.2f} ({(simulated_diff / baseline_avg_simulated * 100):.2f}%)')
            print()
            
            if abs(original_diff) < 0.01 and abs(simulated_diff) < 0.01:
                print('❌ 문제 확인: 큰 변화를 줬는데도 결과가 거의 동일합니다!')
                print('   → feature_overrides가 실제로 적용되지 않았거나,')
                print('   → 모델이 해당 feature들을 무시하고 있습니다.')
            else:
                print('✅ 정상: 변화가 감지되었습니다!')
        
    else:
        print(f'❌ 실패: {response.status_code}')
        print(response.text)

except Exception as e:
    print(f'❌ 오류: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 80)
print('💡 팁: 서버 로그를 확인하여 feature override가 실제로 적용되는지 확인하세요.')
print('=' * 80)
