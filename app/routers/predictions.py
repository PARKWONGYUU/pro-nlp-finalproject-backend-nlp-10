from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from .. import crud, dataschemas
from ..database import get_db

router = APIRouter(
    prefix="/api",
    tags=["Predictions & Explanations"]
)

# --- [예측 (Predictions)] ---

# 1. [저장] 예측 데이터
# POST /api/predictions
@router.post("/predictions", response_model=dataschemas.TftPredResponse)
def create_prediction(item: dataschemas.TftPredCreate, db: Session = Depends(get_db)):
    return crud.create_tft_prediction(db, item)

# 2. [조회] 예측 데이터 목록 (차트 & 최신값 통합)
# - 전체 목록(30개): GET /api/predictions?commodity=Corn
# - 최신 1개만:      GET /api/predictions?commodity=Corn&limit=1
@router.get("/predictions", response_model=List[dataschemas.TftPredResponse])
def get_predictions(
    commodity: str, 
    limit: int = 30, 
    db: Session = Depends(get_db)
):
    """
    특정 품목의 예측 목록을 조회합니다.
    - limit=1로 설정하면 '최신 데이터'만 가져올 수 있습니다.
    """
    return crud.get_tft_predictions(db, commodity, limit)

# 3. [조회] 특정 날짜의 예측값 (New RESTful Style)
# GET /api/predictions/2025-12-01?commodity=Corn
@router.get("/predictions/{target_date}", response_model=dataschemas.TftPredResponse)
def get_prediction_by_date(
    target_date: date, 
    commodity: str, 
    db: Session = Depends(get_db)
):
    """
    달력에서 특정 날짜를 클릭했을 때 상세 정보를 가져옵니다.
    """
    pred = crud.get_prediction_by_date(db, commodity, target_date)
    if not pred:
        raise HTTPException(status_code=404, detail="해당 날짜의 데이터가 없습니다.")
    return pred


# --- [설명 (Explanations)] ---

# 4. [저장] 설명 데이터
# POST /api/explanations
@router.post("/explanations", response_model=dataschemas.ExpPredResponse)
def create_explanation(item: dataschemas.ExpPredCreate, db: Session = Depends(get_db)):
    return crud.create_explanation(db, item)

# 5. [조회] 특정 날짜의 설명 데이터 (New RESTful Style)
# GET /api/explanations/2025-12-01?commodity=Corn
@router.get("/explanations/{target_date}", response_model=dataschemas.ExpPredResponse)
def get_explanation_by_date(
    target_date: date, 
    commodity: str, 
    db: Session = Depends(get_db)
):
    """
    해당 날짜의 AI 분석 리포트(설명)를 가져옵니다.
    """
    exp = crud.get_explanation_by_date(db, commodity, target_date)
    if not exp:
        raise HTTPException(status_code=404, detail="해당 날짜의 설명이 없습니다.")
    return exp