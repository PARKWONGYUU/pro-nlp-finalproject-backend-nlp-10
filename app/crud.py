from sqlalchemy.orm import Session, defer
from datetime import date
from . import datatable, dataschemas

# --- [쓰기 (Create)] ---

# 1. 예측 데이터 저장
def create_tft_prediction(db: Session, item: dataschemas.TftPredCreate):
    db_obj = datatable.TftPred(**item.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 2. 설명 데이터 저장
def create_explanation(db: Session, item: dataschemas.ExpPredCreate):
    db_obj = datatable.ExpPred(**item.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 3. 뉴스 데이터 저장
def create_doc_embedding(db: Session, item: dataschemas.NewsCreate):
    db_obj = datatable.DocEmbeddings(**item.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# --- [읽기 (Read)] ---

# 4. 특정 품목의 시작 날짜부터 끝 날짜까지의 예측값 조회
def get_tft_predictions(db: Session, commodity: str, start_date: date, end_date: date):
    return db.query(datatable.TftPred)\
        .filter(datatable.TftPred.commodity == commodity)\
        .filter(datatable.TftPred.target_date >= start_date)\
        .filter(datatable.TftPred.target_date <= end_date)\
        .order_by(datatable.TftPred.target_date.desc())\
        .all()

# 5. 특정 예측값에 딸린 설명 조회
def get_explanation_by_pred_id(db: Session, pred_id: int):
    return db.query(datatable.ExpPred)\
        .filter(datatable.ExpPred.pred_id == pred_id)\
        .first()

# 6. 특정 품목의 '특정 날짜' 예측값 조회
def get_prediction_by_date(db: Session, commodity: str, target_date: date):
    return db.query(datatable.TftPred)\
        .filter(datatable.TftPred.commodity == commodity)\
        .filter(datatable.TftPred.target_date == target_date)\
        .first()

# 7. 특정 품목 & 특정 날짜의 '설명(Explanation)' 조회
def get_explanation_by_date(db: Session, commodity: str, target_date: date):
    return db.query(datatable.ExpPred)\
        .join(datatable.TftPred, datatable.ExpPred.pred_id == datatable.TftPred.id)\
        .filter(datatable.TftPred.commodity == commodity)\
        .filter(datatable.TftPred.target_date == target_date)\
        .first()

# 8. 벡터 제외 뉴스 목록
def get_doc_embeddings_light(db: Session, skip: int = 0, limit: int = 10):
    return db.query(datatable.DocEmbeddings)\
        .options(defer(datatable.DocEmbeddings.embedding))\
        .order_by(datatable.DocEmbeddings.created_at.desc())\
        .offset(skip).limit(limit)\
        .all()

"""
def search_similar_docs(db: Session, query_vector: list, top_k: int = 5):
    # 주의: query_vector는 [0.1, 0.2, ...] 형태의 리스트여야 함
    
    return db.query(datatable.DocEmbeddings)\
        .order_by(datatable.DocEmbeddings.embedding.op('<=>')(query_vector))\
        .limit(top_k)\
        .all()
"""