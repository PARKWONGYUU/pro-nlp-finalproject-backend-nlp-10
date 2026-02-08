"""
옵션 1 테스트: 실제 데이터(DB) + 더미 데이터(실시간)
"""
import requests
from datetime import date, timedelta

# 최근 DB에 데이터가 있는 날짜로 테스트
test_date = (date.today() - timedelta(days=3)).isoformat()
commodity = 'corn'

print('=' * 60)
print(f'API 테스트: /api/market-metrics?commodity={commodity}&date={test_date}')
print('=' * 60)
print()

try:
    response = requests.get(
        f'http://localhost:8000/api/market-metrics',
        params={'commodity': commodity, 'date': test_date},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        metrics = data.get('metrics', [])
        
        print(f'✅ 성공: {response.status_code}')
        print(f'총 Metrics: {len(metrics)}개')
        print()
        
        # 데이터 분류
        real_data = []
        dummy_data = []
        
        for m in metrics:
            metric_id = m['metric_id']
            if metric_id in ['close', 'open', 'high', 'low', 'volume', 'EMA', '10Y_Yield', 'USD_Index']:
                real_data.append(metric_id)
            else:
                dummy_data.append(metric_id)
        
        print('📊 데이터 구성:')
        print(f'  ✅ DB에서 가져온 실제 데이터: {len(real_data)}개')
        for rd in real_data[:5]:  # 처음 5개만 출력
            m = next((x for x in metrics if x['metric_id'] == rd), None)
            if m:
                print(f'     - {rd}: {m["numeric_value"]:.2f} ({m["label"]})')
        if len(real_data) > 5:
            print(f'     ... 외 {len(real_data) - 5}개')
        
        print()
        print(f'  🔄 실시간 생성된 더미 데이터: {len(dummy_data)}개')
        print(f'     - 뉴스 PCA: {sum(1 for d in dummy_data if d.startswith("news_pca_"))}개')
        print(f'     - 기후 지수: {sum(1 for d in dummy_data if d in ["pdsi", "spi30d", "spi90d"])}개')
        print(f'     - Hawkes: {sum(1 for d in dummy_data if d in ["lambda_price", "lambda_news"])}개')
        print(f'     - 기타: {sum(1 for d in dummy_data if d == "news_count")}개')
        
        print()
        print('=' * 60)
        if len(metrics) == 46:
            print('✅ 성공: 46개 feature 모두 반환됨!')
            print('   - 실제 데이터: DB에서 조회')
            print('   - 더미 데이터: 실시간 생성')
        else:
            print(f'⚠️  예상과 다름: {len(metrics)}개 반환됨 (46개 예상)')
        
    else:
        print(f'❌ 실패: {response.status_code}')
        print(response.text)
        
except requests.exceptions.Timeout:
    print('❌ 타임아웃: 서버가 응답하지 않습니다.')
    print('서버가 실행 중인지 확인해주세요: uvicorn main:app --reload')
except requests.exceptions.ConnectionError:
    print('❌ 연결 오류: 서버에 연결할 수 없습니다.')
    print('서버가 실행 중인지 확인해주세요: uvicorn main:app --reload')
except Exception as e:
    print(f'❌ 오류: {e}')
    import traceback
    traceback.print_exc()
