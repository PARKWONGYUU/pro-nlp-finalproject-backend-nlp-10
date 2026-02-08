"""
DB 저장 테스트 스크립트

실제 데이터를 수집하고 DB에 저장하는 기능을 테스트합니다.
"""

import os
from datetime import date, timedelta

# FRED API 키 설정 (테스트용)
# 실제 키가 있으면 주석 해제하고 입력하세요
# os.environ['FRED_API_KEY'] = 'your_api_key_here'

def test_db_save():
    """DB 저장 테스트"""
    print("=" * 60)
    print("DB 저장 기능 테스트")
    print("=" * 60)
    
    # FRED API 키 확인
    fred_key = os.environ.get('FRED_API_KEY')
    if fred_key:
        print(f"\n✅ FRED API 키 설정됨: {fred_key[:10]}...")
        print("실제 경제 데이터를 가져올 수 있습니다.")
    else:
        print("\n⚠️  FRED API 키 미설정")
        print("경제 지표는 더미 데이터로 대체됩니다.")
        print("실제 데이터 저장 테스트를 하려면 FRED API 키가 필요합니다.")
        print("\n발급 방법:")
        print("1. https://fred.stlouisfed.org/ 방문")
        print("2. 계정 생성 및 로그인")
        print("3. https://fred.stlouisfed.org/docs/api/api_key.html 에서 API 키 발급")
        print("4. .env 파일에 FRED_API_KEY=your_key 추가")
    
    print("\n" + "-" * 60)
    print("실시간 데이터 수집 테스트")
    print("-" * 60)
    
    from app.data_fetcher import fetch_realtime_features
    
    commodity = "corn"
    end_date = date.today()
    days = 90
    
    print(f"\n품목: {commodity}")
    print(f"종료 날짜: {end_date}")
    print(f"조회 일수: {days}일")
    print(f"\n데이터 수집 중...\n")
    
    result = fetch_realtime_features(
        commodity=commodity,
        end_date=end_date,
        days=days,
        fred_api_key=fred_key
    )
    
    is_real_data = result.get('is_real_data', False)
    
    print(f"수집 완료:")
    print(f"  - 날짜: {len(result['dates'])}일")
    print(f"  - Feature: {len(result['features'])}개")
    print(f"  - 실제 데이터: {'✅ Yes' if is_real_data else '❌ No (더미 데이터)'}")
    
    if is_real_data:
        print("\n" + "-" * 60)
        print("DB 저장 테스트")
        print("-" * 60)
        
        from app.database import SessionLocal
        from app import crud, dataschemas
        from datetime import datetime
        
        db = SessionLocal()
        
        try:
            # 데이터 저장
            dates = result['dates']
            features = result['features']
            
            saved_count = 0
            
            for i, date_str in enumerate(dates):
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # 이미 있으면 스킵
                existing = crud.get_market_metrics(db, commodity, current_date)
                if existing:
                    continue
                
                # Metrics 생성
                metrics_items = []
                for feature_name, values in features.items():
                    if i < len(values):
                        numeric_value = float(values[i])
                        
                        # Trend 계산
                        trend = 0.0
                        if i > 0:
                            prev_value = float(values[i-1])
                            if prev_value != 0:
                                trend = ((numeric_value - prev_value) / prev_value) * 100
                        
                        # Impact
                        if trend > 2:
                            impact = "상승"
                        elif trend < -2:
                            impact = "하락"
                        else:
                            impact = "중립"
                        
                        metrics_items.append(
                            dataschemas.MarketMetricItem(
                                metric_id=feature_name,
                                label=feature_name,
                                value=str(numeric_value),
                                numeric_value=numeric_value,
                                trend=round(trend, 2),
                                impact=impact
                            )
                        )
                
                # DB 저장
                if metrics_items:
                    crud.create_market_metrics_bulk(db, commodity, current_date, metrics_items)
                    saved_count += 1
                    if saved_count % 10 == 0:
                        print(f"  저장 중... {saved_count}/{len(dates)}일")
            
            print(f"\n✅ DB 저장 완료: {saved_count}일치 데이터")
            
            # 검증
            print("\n" + "-" * 60)
            print("DB 검증")
            print("-" * 60)
            
            for i in range(min(7, len(dates))):
                check_date = datetime.strptime(dates[-(i+1)], '%Y-%m-%d').date()
                metrics = crud.get_market_metrics(db, commodity, check_date)
                
                if metrics:
                    print(f"  ✅ {check_date}: {len(metrics)}개 metrics")
                else:
                    print(f"  ❌ {check_date}: 데이터 없음")
            
        finally:
            db.close()
    else:
        print("\n⚠️  더미 데이터이므로 DB 저장을 건너뜁니다.")
        print("실제 데이터로 테스트하려면 FRED API 키를 설정하세요.")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_db_save()
