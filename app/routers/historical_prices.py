from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from .. import crud, dataschemas
from ..database import get_db

router = APIRouter(
    prefix="/api",
    tags=["Historical Prices"]
)

# GET /api/historical-prices?commodity=corn&start_date=2026-01-01&end_date=2026-01-31
@router.get("/historical-prices", response_model=dataschemas.HistoricalPricesResponse)
def get_historical_prices(
    commodity: str = Query(..., description="품목명"),
    start_date: date = Query(..., description="조회 시작일"),
    end_date: date = Query(..., description="조회 종료일"),
    db: Session = Depends(get_db)
):
    prices = crud.get_historical_prices(db, commodity, start_date, end_date)
    
    if not prices:
        raise HTTPException(status_code=404, detail="해당 기간의 실제 가격 데이터가 없습니다.")
    
    # 응답 포맷 변환
    prices_list = [
        dataschemas.HistoricalPriceItem(
            date=p.date.isoformat(),
            actual_price=float(p.actual_price)
        )
        for p in prices
    ]
    
    return dataschemas.HistoricalPricesResponse(
        commodity=commodity,
        prices=prices_list
    )
