"""
더미 데이터를 DB에서 삭제하는 스크립트
실제 데이터만 남기고 나머지 삭제
"""
from app.database import SessionLocal
from app import datatable
from sqlalchemy import or_

db = SessionLocal()

try:
    # 더미 데이터 metric_id 목록
    dummy_metric_ids = [
        # 뉴스 PCA (32개)
        *[f'news_pca_{i}' for i in range(32)],
        # 기후 지수 (3개)
        'pdsi', 'spi30d', 'spi90d',
        # Hawkes Intensity (2개)
        'lambda_price', 'lambda_news',
        # 뉴스 카운트 (1개)
        'news_count'
    ]
    
    print('=' * 60)
    print('더미 데이터 삭제 시작')
    print('=' * 60)
    print()
    
    # 삭제 전 카운트
    total_before = db.query(datatable.MarketMetrics).count()
    print(f'삭제 전 총 레코드: {total_before}개')
    
    # 더미 데이터 삭제
    deleted = db.query(datatable.MarketMetrics).filter(
        datatable.MarketMetrics.metric_id.in_(dummy_metric_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    
    # 삭제 후 카운트
    total_after = db.query(datatable.MarketMetrics).count()
    print(f'삭제된 레코드: {deleted}개')
    print(f'삭제 후 총 레코드: {total_after}개')
    print()
    
    # 남은 데이터 확인
    remaining = db.query(
        datatable.MarketMetrics.metric_id,
        datatable.MarketMetrics.commodity
    ).distinct().all()
    
    print('=' * 60)
    print('남은 데이터:')
    print('=' * 60)
    for metric_id, commodity in remaining:
        count = db.query(datatable.MarketMetrics).filter(
            datatable.MarketMetrics.metric_id == metric_id,
            datatable.MarketMetrics.commodity.ilike(commodity)
        ).count()
        print(f'  {metric_id} ({commodity}): {count}개')
    
    print()
    print('✅ 완료: 실제 데이터만 DB에 남았습니다.')
    
except Exception as e:
    print(f'❌ 오류 발생: {e}')
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
