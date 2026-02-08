"""
DB 상태 확인 스크립트
- 각 테이블의 레코드 수 확인
- corn 품목 데이터 날짜 범위 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func
from app.database import SessionLocal
from app import datatable
from datetime import datetime

def check_db_status():
    """DB 상태 확인 및 리포트 출력"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("📊 데이터베이스 상태 확인 리포트")
        print("=" * 80)
        print()
        
        # 1. TFT 예측 데이터 (tft_pred)
        print("1️⃣  TFT 예측 데이터 (tft_pred)")
        print("-" * 80)
        tft_count = db.query(datatable.TftPred).count()
        print(f"   전체 레코드 수: {tft_count}")
        
        if tft_count > 0:
            corn_count = db.query(datatable.TftPred)\
                .filter(datatable.TftPred.commodity == 'corn').count()
            print(f"   corn 품목 레코드 수: {corn_count}")
            
            if corn_count > 0:
                min_date = db.query(func.min(datatable.TftPred.target_date))\
                    .filter(datatable.TftPred.commodity == 'corn').scalar()
                max_date = db.query(func.max(datatable.TftPred.target_date))\
                    .filter(datatable.TftPred.commodity == 'corn').scalar()
                print(f"   날짜 범위: {min_date} ~ {max_date}")
        else:
            print("   ⚠️  데이터 없음 - 더미 데이터 생성 필요")
        print()
        
        # 2. 예측 설명 데이터 (exp_pred)
        print("2️⃣  예측 설명 데이터 (exp_pred)")
        print("-" * 80)
        exp_count = db.query(datatable.ExpPred).count()
        print(f"   전체 레코드 수: {exp_count}")
        
        if exp_count > 0:
            # pred_id를 통해 corn 품목 설명 개수 확인
            corn_exp_count = db.query(datatable.ExpPred)\
                .join(datatable.TftPred, datatable.ExpPred.pred_id == datatable.TftPred.id)\
                .filter(datatable.TftPred.commodity == 'corn').count()
            print(f"   corn 품목 설명 레코드 수: {corn_exp_count}")
        else:
            print("   ⚠️  데이터 없음 - 더미 데이터 생성 필요")
        print()
        
        # 3. 뉴스 데이터 (doc_embeddings)
        print("3️⃣  뉴스 데이터 (doc_embeddings)")
        print("-" * 80)
        news_count = db.query(datatable.DocEmbeddings).count()
        print(f"   전체 레코드 수: {news_count}")
        
        if news_count > 0:
            latest_news = db.query(datatable.DocEmbeddings)\
                .order_by(datatable.DocEmbeddings.created_at.desc()).first()
            print(f"   최신 뉴스: {latest_news.created_at}")
        else:
            print("   ⚠️  데이터 없음 - 더미 데이터 생성 필요")
        print()
        
        # 4. 시장 지표 (market_metrics)
        print("4️⃣  시장 지표 (market_metrics)")
        print("-" * 80)
        metrics_count = db.query(datatable.MarketMetrics).count()
        print(f"   전체 레코드 수: {metrics_count}")
        
        if metrics_count > 0:
            corn_metrics_count = db.query(datatable.MarketMetrics)\
                .filter(datatable.MarketMetrics.commodity == 'corn').count()
            print(f"   corn 품목 레코드 수: {corn_metrics_count}")
            
            if corn_metrics_count > 0:
                min_date = db.query(func.min(datatable.MarketMetrics.date))\
                    .filter(datatable.MarketMetrics.commodity == 'corn').scalar()
                max_date = db.query(func.max(datatable.MarketMetrics.date))\
                    .filter(datatable.MarketMetrics.commodity == 'corn').scalar()
                print(f"   날짜 범위: {min_date} ~ {max_date}")
        else:
            print("   ⚠️  데이터 없음 - API에서 실시간 수집")
        print()
        
        # 5. 실제 가격 (historical_prices)
        print("5️⃣  실제 가격 (historical_prices)")
        print("-" * 80)
        prices_count = db.query(datatable.HistoricalPrices).count()
        print(f"   전체 레코드 수: {prices_count}")
        
        if prices_count > 0:
            corn_prices_count = db.query(datatable.HistoricalPrices)\
                .filter(datatable.HistoricalPrices.commodity == 'corn').count()
            print(f"   corn 품목 레코드 수: {corn_prices_count}")
            
            if corn_prices_count > 0:
                min_date = db.query(func.min(datatable.HistoricalPrices.date))\
                    .filter(datatable.HistoricalPrices.commodity == 'corn').scalar()
                max_date = db.query(func.max(datatable.HistoricalPrices.date))\
                    .filter(datatable.HistoricalPrices.commodity == 'corn').scalar()
                print(f"   날짜 범위: {min_date} ~ {max_date}")
        else:
            print("   ⚠️  데이터 없음 - API에서 실시간 수집")
        print()
        
        # 요약
        print("=" * 80)
        print("📋 요약")
        print("=" * 80)
        
        missing_data = []
        if tft_count == 0:
            missing_data.append("예측 데이터 (tft_pred)")
        if exp_count == 0:
            missing_data.append("예측 설명 (exp_pred)")
        if news_count == 0:
            missing_data.append("뉴스 (doc_embeddings)")
        
        if missing_data:
            print(f"⚠️  누락된 데이터: {', '.join(missing_data)}")
            print("✅ 더미 데이터 생성 로직으로 보완 예정")
        else:
            print("✅ 모든 주요 데이터가 DB에 존재")
        
        print()
        print(f"확인 완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ DB 확인 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_db_status()
