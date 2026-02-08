"""
빠른 Override 테스트 (1회 호출)
서버 로그를 확인하세요!
"""
import requests
from datetime import date, timedelta

base_date = (date.today() - timedelta(days=1)).isoformat()

print('=' * 80)
print('빠른 Override 테스트')
print('=' * 80)
print()
print('⚠️  서버 터미널을 확인하세요!')
print('    다음과 같은 출력이 보여야 합니다:')
print('    - "🔧 Feature override 적용 시작"')
print('    - "✓ 10Y_Yield: X.XX → 10.00"')
print('    - "✓ USD_Index: X.XX → 150.00"')
print('    - "결과 비교: 원본 평균 vs 시뮬 평균"')
print()
print('=' * 80)

request_data = {
    "commodity": "corn",
    "base_date": base_date,
    "feature_overrides": {
        "10Y_Yield": 10.0,  # 매우 큰 값
        "USD_Index": 150.0   # 매우 큰 값
    }
}

print(f'\n요청 보내는 중...')
print(f'  commodity: {request_data["commodity"]}')
print(f'  base_date: {request_data["base_date"]}')
print(f'  overrides: {request_data["feature_overrides"]}')
print()

try:
    response = requests.post(
        'http://localhost:8000/api/simulate',
        json=request_data,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        summary = data.get('summary', {})
        
        print('✅ 성공!')
        print()
        print('결과:')
        print(f'  평균 원본: ${summary.get("avg_original_price", 0):.2f}')
        print(f'  평균 시뮬: ${summary.get("avg_simulated_price", 0):.2f}')
        print(f'  평균 변화: ${summary.get("avg_change", 0):.2f} ({summary.get("avg_change_percent", 0):.2f}%)')
        
        # Feature impacts
        print()
        print('Feature 영향도:')
        for impact in data.get('feature_impacts', []):
            print(f'  {impact["feature"]}: {impact["current_value"]:.2f} → {impact["new_value"]:.2f} (기여도: {impact["contribution"]:.2f})')
        
        print()
        print('=' * 80)
        print('💡 서버 터미널을 확인하여 디버깅 정보를 보세요!')
        print('=' * 80)
        
    else:
        print(f'❌ 실패: {response.status_code}')
        print(response.text)

except Exception as e:
    print(f'❌ 오류: {e}')
