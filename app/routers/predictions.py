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

# POST /api/predictions
@router.post("/predictions", response_model=dataschemas.TftPredResponse)
def create_prediction(item: dataschemas.TftPredCreate, db: Session = Depends(get_db)):
    return crud.create_tft_prediction(db, item)

# GET /api/predictions?commodity=Corn&start_date=2024-01-01&end_date=2024-01-31
@router.get("/predictions", response_model=List[dataschemas.TftPredResponse])
def get_predictions(
    commodity: str, 
    start_date: date = Query(..., description="조회 시작일"),
    end_date: date = Query(..., description="조회 종료일"),
    db: Session = Depends(get_db)
):
    pred = crud.get_tft_predictions(db, commodity, start_date, end_date)
    if not pred:
        raise HTTPException(status_code=404, detail="해당 날짜의 데이터가 없습니다.")
    return pred

# GET /api/predictions/2025-12-01?commodity=Corn
@router.get("/predictions/{target_date}", response_model=dataschemas.TftPredResponse)
def get_prediction_by_date(
    target_date: date, 
    commodity: str, 
    db: Session = Depends(get_db)
):
    pred = crud.get_prediction_by_date(db, commodity, target_date)
    if not pred:
        raise HTTPException(status_code=404, detail="해당 날짜의 데이터가 없습니다.")
    return pred


# --- [설명 (Explanations)] ---

# POST /api/explanations
@router.post("/explanations", response_model=dataschemas.ExpPredResponse)
def create_explanation(item: dataschemas.ExpPredCreate, db: Session = Depends(get_db)):
    return crud.create_explanation(db, item)

# GET /api/explanations/2025-12-01?commodity=Corn
@router.get("/explanations/{target_date}", response_model=dataschemas.ExpPredResponse)
def get_explanation_by_date(
    target_date: date, 
    commodity: str, 
    db: Session = Depends(get_db)
):
    exp = crud.get_explanation_by_date(db, commodity, target_date)
    if not exp:
        raise HTTPException(status_code=404, detail="해당 날짜의 설명이 없습니다.")
    return exp