from sqlalchemy.orm import Session
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


# --- [읽기 (Read)] ---

# 3. 특정 품목의 '모든' 예측 기록 조회 (날짜 내림차순, 기본 30개)
def get_tft_predictions(db: Session, commodity: str, limit: int = 30):
    return db.query(datatable.TftPred)\
        .filter(datatable.TftPred.commodity == commodity)\
        .order_by(datatable.TftPred.target_date.desc())\
        .limit(limit)\
        .all()

# 4. 특정 품목의 '최신' 예측값 1개만 조회
def get_latest_prediction(db: Session, commodity: str):
    return db.query(datatable.TftPred)\
        .filter(datatable.TftPred.commodity == commodity)\
        .order_by(datatable.TftPred.target_date.desc())\
        .first()

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