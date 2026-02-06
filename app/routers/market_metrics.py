from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from .. import crud, dataschemas
from ..database import get_db

router = APIRouter(
    prefix="/api",
    tags=["Market Metrics"]
)

# GET /api/market-metrics?commodity=corn&date=2026-02-03
@router.get("/market-metrics", response_model=dataschemas.MarketMetricsResponse)
def get_market_metrics(
    commodity: str = Query(..., description="품목명"),
    date: Optional[date] = Query(None, description="조회 날짜 (기본값: 오늘)"),
    db: Session = Depends(get_db)
):
    target_date = date if date else datetime.now().date()
    
    metrics = crud.get_market_metrics(db, commodity, target_date)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="해당 날짜의 시장 지표가 없습니다.")
    
    # 응답 포맷 변환
    metrics_list = [
        dataschemas.MarketMetricItem(
            metric_id=m.metric_id,
            label=m.label,
            value=m.value,
            numeric_value=m.numeric_value,
            trend=m.trend,
            impact=m.impact
        )
        for m in metrics
    ]
    
    return dataschemas.MarketMetricsResponse(
        commodity=commodity,
        date=target_date.isoformat(),
        metrics=metrics_list
    )
