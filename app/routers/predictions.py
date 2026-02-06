from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from .. import crud, dataschemas
from ..database import get_db

router = APIRouter(
    prefix="/api",
    tags=["Predictions & Explanations"]
)

# --- [예측 (Predictions)] ---

# GET /api/predictions?commodity=corn
@router.get("/predictions", response_model=dataschemas.PredictionsWithPricesResponse)
def get_predictions(
    commodity: str,
    db: Session = Depends(get_db)
):
    """
    최신 배치의 예측 데이터 + 과거 30일 실제 가격 반환
    - predictions: 각 target_date별 created_at 최신 (오늘-30일 ~ 오늘+60일)
    - historical_prices: 과거 30일 ~ 오늘까지의 실제 가격
    """
    pred = crud.get_latest_predictions(db, commodity)
    if not pred:
        raise HTTPException(
            status_code=404,
            detail=f"{commodity}의 최신 예측 데이터가 없습니다."
        )
    
    # 과거 30일 ~ 오늘까지의 실제 가격 조회 (휴장일 처리 포함)
    today = datetime.now().date()
    start_date = today - timedelta(days=30)
    prices = crud.get_historical_prices(db, commodity, start_date, today)
    
    # DB에서 가져온 거래일 데이터를 dict로 변환
    price_dict = {p.date: float(p.actual_price) for p in prices} if prices else {}
    
    # 모든 날짜에 대해 연속된 리스트 생성 (휴장일 포함)
    prices_list = []
    last_price = None
    
    current_date = start_date
    while current_date <= today:
        if current_date in price_dict:
            # 거래일: 실제 가격
            last_price = price_dict[current_date]
            prices_list.append(dataschemas.HistoricalPriceItem(
                date=current_date.isoformat(),
                actual_price=last_price,
                is_trading_day=True
            ))
        elif last_price is not None:
            # 휴장일: 이전 거래일의 가격으로 채움
            prices_list.append(dataschemas.HistoricalPriceItem(
                date=current_date.isoformat(),
                actual_price=last_price,
                is_trading_day=False
            ))
        
        current_date += timedelta(days=1)
    
    return dataschemas.PredictionsWithPricesResponse(
        predictions=pred,
        historical_prices=prices_list
    )

# GET /api/predictions/2025-12-01?commodity=corn
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

# GET /api/explanations/2025-12-01?commodity=corn
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