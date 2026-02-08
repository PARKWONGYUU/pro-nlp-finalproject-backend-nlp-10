"""
잘못된 가격 데이터(로그 변환된 값) 삭제 스크립트

yfinance 데이터가 로그 변환된 상태로 DB에 저장된 경우(예: 6.06) 이를 감지하여 삭제합니다.
대상:
1. historical_prices 테이블: actual_price < 100
2. market_metrics 테이블: price 관련 metric_id의 numeric_value < 100
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import SessionLocal, engine

def cleanup_invalid_prices():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("🧹 잘못된 가격 데이터 삭제 시작")
        print("=" * 60)
        
        # 1. historical_prices 정리
        print("\n1️⃣  Historical Prices 확인...")
        # 옥수수 가격이 100 미만일 수 없음 (보통 400~600)
        query = text("DELETE FROM historical_prices WHERE actual_price < 100 AND commodity = 'corn'")
        result = db.execute(query)
        db.commit()
        print(f"   ✅ {result.rowcount}개의 잘못된 레코드 삭제됨")
        
        # 2. market_metrics 정리
        print("\n2️⃣  Market Metrics 확인...")
        price_metrics = ['close', 'open', 'high', 'low', 'EMA']
        metrics_str = "', '".join(price_metrics)
        
        query = text(f"""
            DELETE FROM market_metrics 
            WHERE commodity = 'corn' 
            AND metric_id IN ('{metrics_str}') 
            AND numeric_value < 100
        """)
        result = db.execute(query)
        db.commit()
        print(f"   ✅ {result.rowcount}개의 잘못된 레코드 삭제됨")
        
        print("\n✨ 정리 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_invalid_prices()
