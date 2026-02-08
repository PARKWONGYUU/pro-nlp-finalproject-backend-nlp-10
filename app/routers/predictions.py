from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
import logging

from .. import crud, dataschemas
from ..database import get_db
from ..dummy_data_generator import get_generator

logger = logging.getLogger(__name__)

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
    
    # DB에 데이터가 없으면 실시간으로 수집
    if not prices or len(price_dict) < 20:  # 최소 20일 이상 데이터 필요
        logger.warning(f"DB에 {commodity}의 historical prices가 부족합니다. 실시간 수집합니다.")
        try:
            from ..data_fetcher import fetch_realtime_features
            from ..config import settings
            
            # 30일치 가격 데이터 수집
            result = fetch_realtime_features(
                commodity=commodity,
                end_date=today,
                days=30,
                fred_api_key=settings.fred_api_key
            )
            
            # 수집한 데이터를 DB에 저장
            if result.get('is_real_data') and 'close' in result['features']:
                dates = result['dates']
                prices_data = result['features']['close']
                
                price_items = []
                for i, date_str in enumerate(dates):
                    if i < len(prices_data):
                        price_items.append(dataschemas.HistoricalPriceItem(
                            date=date_str,
                            actual_price=float(prices_data[i]),
                            is_trading_day=True
                        ))
                
                if price_items:
                    crud.create_historical_prices_bulk(db, commodity, price_items)
                    logger.info(f"✅ Historical prices 저장 완료: {len(price_items)}일치")
                    
                    # 다시 조회
                    prices = crud.get_historical_prices(db, commodity, start_date, today)
                    price_dict = {p.date: float(p.actual_price) for p in prices} if prices else {}
        except Exception as e:
            logger.error(f"Historical prices 실시간 수집 실패: {e}")
    
    # 모든 날짜에 대해 연속된 리스트 생성 (휴장일 포함)
    prices_list = []
    
    current_date = start_date
    while current_date <= today:
        if current_date in price_dict:
            # 거래일: 실제 가격
            prices_list.append(dataschemas.HistoricalPriceItem(
                date=current_date.isoformat(),
                actual_price=price_dict[current_date],
                is_trading_day=True
            ))
        else:
            # 휴장일: null
            prices_list.append(dataschemas.HistoricalPriceItem(
                date=current_date.isoformat(),
                actual_price=None,
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
    """
    특정 날짜의 예측 설명 조회
    - DB에 있으면 실제 데이터 반환
    - 없으면 더미 데이터 생성하여 반환
    """
    # 1. DB에서 조회 시도
    exp = crud.get_explanation_by_date(db, commodity, target_date)
    
    if exp:
        logger.info(f"✅ DB에서 설명 조회 성공: {commodity} {target_date}")
        return exp
    
    # 2. DB에 없으면 더미 데이터 생성
    logger.warning(f"⚠️ DB에 설명 없음, 더미 생성: {commodity} {target_date}")
    
    try:
        # 해당 날짜의 예측 데이터 조회 (가격 정보 사용)
        prediction = crud.get_prediction_by_date(db, commodity, target_date)
        
        # 더미 생성기로 설명 생성
        generator = get_generator()
        dummy_exp = generator.generate_explanation(
            commodity=commodity,
            target_date=target_date,
            prediction=prediction
        )
        
        logger.info(f"✅ 더미 설명 생성 완료: {commodity} {target_date}")
        return dummy_exp
        
    except Exception as e:
        logger.error(f"❌ 더미 설명 생성 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"설명 데이터 생성 실패: {str(e)}"
        )