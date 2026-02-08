from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
import logging

from .. import crud, dataschemas
from ..database import get_db
from ..config import settings

logger = logging.getLogger(__name__)

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
    
    # 1. DB에서 데이터 조회 시도
    metrics = crud.get_market_metrics(db, commodity, target_date)
    
    # 2. 데이터가 없거나 부족하면 실시간으로 API에서 가져오기
    # 최소 10개 이상의 지표가 있어야 유효한 데이터로 간주 (가격 5개 + 경제지표 2개 등)
    if not metrics or len(metrics) < 10:
        if metrics:
            logger.warning(
                f"DB에 {commodity} {target_date}의 데이터가 불충분합니다 ({len(metrics)}개). "
                f"실시간 API로 다시 가져옵니다."
            )
        else:
            logger.warning(
                f"DB에 {commodity} {target_date}의 시장 지표가 없습니다. "
                f"실시간 API로 데이터를 가져옵니다."
            )
        
        try:
            from ..data_fetcher import fetch_realtime_features
            from datetime import timedelta
            
            # 어제 날짜 계산 (trend 계산용)
            yesterday = target_date - timedelta(days=1)
            
            # 2일치 데이터 수집 (오늘 + 어제)
            result = fetch_realtime_features(
                commodity=commodity,
                end_date=target_date,
                days=2,
                fred_api_key=settings.fred_api_key
            )
            
            if not result['dates'] or not result['features']:
                raise HTTPException(
                    status_code=404, 
                    detail=f"실시간 데이터 수집 실패: {commodity} {target_date}"
                )
            
            # 실제 데이터인 경우 DB에 저장
            is_real_data = result.get('is_real_data', False)
            logger.info(f"데이터 타입: {'실제 데이터' if is_real_data else '더미 데이터'}")
            
            # 데이터를 MarketMetricItem 형식으로 변환
            metrics_list = []
            features = result['features']
            dates = result['dates']
            
            for feature_name, values in features.items():
                if values and len(values) >= 1:
                    # 오늘 값 (마지막 값)
                    today_value = float(values[-1])
                    
                    # Trend 계산 (2일치 데이터가 있으면)
                    trend = 0.0
                    if len(values) >= 2:
                        yesterday_value = float(values[-2])
                        if yesterday_value != 0:
                            trend = ((today_value - yesterday_value) / yesterday_value) * 100
                    
                    # Impact 결정
                    if trend > 2:
                        impact = "상승"
                    elif trend < -2:
                        impact = "하락"
                    else:
                        impact = "중립"
                    
                    metrics_list.append(
                        dataschemas.MarketMetricItem(
                            metric_id=feature_name,
                            label=_get_feature_label(feature_name),
                            value=str(today_value),
                            numeric_value=today_value,
                            trend=round(trend, 2),
                            impact=impact
                        )
                    )
            
            logger.info(f"실시간 API에서 {len(metrics_list)}개 지표 수집 완료 (trend 포함)")
            
            # 실제 데이터라면 즉시 DB에 저장 (오늘 날짜만)
            if is_real_data and metrics_list:
                try:
                    # 실제 데이터 feature만 저장 (더미 제외)
                    real_features = {
                        'close', 'open', 'high', 'low', 'volume', 'EMA',  # 가격 데이터
                        '10Y_Yield', 'USD_Index'  # 경제 지표
                    }
                    real_metrics = [m for m in metrics_list if m.metric_id in real_features]
                    
                    if real_metrics:
                        crud.create_market_metrics_bulk(db, commodity, target_date, real_metrics)
                        logger.info(f"✅ DB 저장 완료: {target_date} - {len(real_metrics)}개 지표")
                        
                        # Historical prices도 저장
                        if 'close' in features and len(features['close']) > 0:
                            close_price = float(features['close'][-1])
                            _save_historical_price(db, commodity, target_date, close_price)
                            logger.info(f"✅ Historical price 저장 완료: {target_date} - ${close_price:.2f}")
                except Exception as e:
                    logger.error(f"DB 저장 실패: {e}")
                    # 저장 실패해도 데이터는 반환
            
            return dataschemas.MarketMetricsResponse(
                commodity=commodity,
                date=target_date.isoformat(),
                metrics=metrics_list
            )
            
        except Exception as e:
            logger.error(f"실시간 데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=404,
                detail=f"해당 날짜의 시장 지표를 찾을 수 없습니다: {str(e)}"
            )
    
    # 3. DB 데이터 + 실시간 더미 데이터 반환
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
    
    # DB에 실제 데이터만 있으므로, 더미 데이터를 실시간 생성하여 추가
    if len(metrics_list) < 46:  # 전체 feature 개수보다 적으면
        logger.info(f"더미 데이터 추가: {len(metrics_list)}개 → 46개")
        dummy_metrics = _generate_dummy_metrics()
        
        # 이미 있는 metric_id는 제외
        existing_ids = {m.metric_id for m in metrics_list}
        for dummy in dummy_metrics:
            if dummy.metric_id not in existing_ids:
                metrics_list.append(dummy)
    
    return dataschemas.MarketMetricsResponse(
        commodity=commodity,
        date=target_date.isoformat(),
        metrics=metrics_list
    )


def _save_historical_price(db: Session, commodity: str, target_date: date, price: float):
    """
    Historical price 저장 (단일 날짜)
    
    Args:
        db: 데이터베이스 세션
        commodity: 품목명
        target_date: 날짜
        price: 가격
    """
    try:
        # 이미 존재하는지 확인
        existing = crud.get_historical_prices(db, commodity, target_date, target_date)
        if existing:
            logger.debug(f"Historical price 이미 존재: {target_date}")
            return
        
        # 저장
        price_item = dataschemas.HistoricalPriceItem(
            date=target_date.isoformat(),
            actual_price=price,
            is_trading_day=True
        )
        crud.create_historical_prices_bulk(db, commodity, [price_item])
    except Exception as e:
        logger.error(f"Historical price 저장 실패: {e}")


def _save_to_database_old(db: Session, commodity: str, end_date: date):
    """
    실제 데이터만 DB에 저장 (90일치)
    더미 데이터는 저장하지 않음
    
    Args:
        db: 데이터베이스 세션
        commodity: 품목명
        end_date: 종료 날짜
    """
    try:
        from ..data_fetcher import fetch_realtime_features
        from datetime import timedelta
        
        logger.info(f"90일치 실제 데이터 수집 시작: {commodity}, {end_date}")
        
        # 90일치 데이터 수집
        result = fetch_realtime_features(
            commodity=commodity,
            end_date=end_date,
            days=90,
            fred_api_key=settings.fred_api_key
        )
        
        if not result['dates'] or not result['features']:
            logger.error("데이터 수집 실패")
            return
        
        dates = result['dates']
        features = result['features']
        
        # 실제 데이터 feature만 선택 (더미 제외)
        real_features = {
            'close', 'open', 'high', 'low', 'volume', 'EMA',  # 가격 데이터
            '10Y_Yield', 'USD_Index'  # 경제 지표
        }
        
        # 날짜별로 데이터 저장
        from datetime import datetime
        saved_count = 0
        
        for i, date_str in enumerate(dates):
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # 이미 DB에 있는 날짜는 스킵
            existing = crud.get_market_metrics(db, commodity, current_date)
            if existing:
                continue
            
            # 실제 데이터만 metrics 생성
            metrics_items = []
            for feature_name, values in features.items():
                # 실제 데이터만 저장
                if feature_name not in real_features:
                    continue
                
                if i < len(values):
                    numeric_value = float(values[i])
                    
                    # Trend 계산 (이전 날짜와 비교)
                    trend = 0.0
                    if i > 0:
                        prev_value = float(values[i-1])
                        if prev_value != 0:
                            trend = ((numeric_value - prev_value) / prev_value) * 100
                    
                    # Impact 결정
                    if trend > 2:
                        impact = "상승"
                    elif trend < -2:
                        impact = "하락"
                    else:
                        impact = "중립"
                    
                    metrics_items.append(
                        dataschemas.MarketMetricItem(
                            metric_id=feature_name,
                            label=_get_feature_label(feature_name),
                            value=str(numeric_value),
                            numeric_value=numeric_value,
                            trend=round(trend, 2),
                            impact=impact
                        )
                    )
            
            # DB에 저장
            if metrics_items:
                crud.create_market_metrics_bulk(db, commodity, current_date, metrics_items)
                saved_count += 1
        
        logger.info(f"✅ DB 저장 완료: {saved_count}일치 데이터 (실제 데이터만)")
        
        # Historical prices도 저장
        _save_historical_prices(db, commodity, dates, features)
        
    except Exception as e:
        logger.error(f"DB 저장 실패: {e}")
        import traceback
        traceback.print_exc()


def _save_historical_prices(db: Session, commodity: str, dates: list, features: dict):
    """Historical prices 저장"""
    try:
        if 'close' not in features:
            return
        
        prices_items = []
        from datetime import datetime
        
        for i, date_str in enumerate(dates):
            if i < len(features['close']):
                prices_items.append(
                    dataschemas.HistoricalPriceItem(
                        date=date_str,
                        actual_price=float(features['close'][i]),
                        is_trading_day=True
                    )
                )
        
        if prices_items:
            crud.create_historical_prices_bulk(db, commodity, prices_items)
            logger.info(f"✅ Historical prices 저장 완료: {len(prices_items)}일치")
            
    except Exception as e:
        logger.error(f"Historical prices 저장 실패: {e}")


def _generate_dummy_metrics() -> List[dataschemas.MarketMetricItem]:
    """
    더미 데이터 실시간 생성
    
    Returns:
        더미 metrics 리스트
    """
    import numpy as np
    
    dummy_metrics = []
    
    # 뉴스 PCA (32개)
    for i in range(32):
        dummy_metrics.append(
            dataschemas.MarketMetricItem(
                metric_id=f'news_pca_{i}',
                label=f'뉴스 PCA {i}',
                value='0.0',
                numeric_value=float(np.random.normal(0, 1)),
                trend=0.0,
                impact='중립'
            )
        )
    
    # 기후 지수 (3개)
    dummy_metrics.extend([
        dataschemas.MarketMetricItem(
            metric_id='pdsi',
            label='Palmer 가뭄 지수',
            value='0.0',
            numeric_value=float(np.random.uniform(-3, 3)),
            trend=0.0,
            impact='중립'
        ),
        dataschemas.MarketMetricItem(
            metric_id='spi30d',
            label='표준 강수 지수 (30일)',
            value='0.0',
            numeric_value=float(np.random.uniform(-1, 1)),
            trend=0.0,
            impact='중립'
        ),
        dataschemas.MarketMetricItem(
            metric_id='spi90d',
            label='표준 강수 지수 (90일)',
            value='0.0',
            numeric_value=float(np.random.uniform(-1, 1)),
            trend=0.0,
            impact='중립'
        )
    ])
    
    # Hawkes Intensity (2개)
    dummy_metrics.extend([
        dataschemas.MarketMetricItem(
            metric_id='lambda_price',
            label='Hawkes 가격 강도',
            value='0.0',
            numeric_value=float(np.random.uniform(0.1, 0.5)),
            trend=0.0,
            impact='중립'
        ),
        dataschemas.MarketMetricItem(
            metric_id='lambda_news',
            label='Hawkes 뉴스 강도',
            value='0.0',
            numeric_value=float(np.random.uniform(0.1, 0.5)),
            trend=0.0,
            impact='중립'
        )
    ])
    
    # 뉴스 카운트 (1개)
    dummy_metrics.append(
        dataschemas.MarketMetricItem(
            metric_id='news_count',
            label='뉴스 개수',
            value='0',
            numeric_value=float(np.random.randint(5, 15)),
            trend=0.0,
            impact='중립'
        )
    )
    
    return dummy_metrics


def _get_feature_label(feature_id: str) -> str:
    """Feature ID를 한글 라벨로 변환"""
    label_map = {
        'close': '종가',
        'open': '시가',
        'high': '고가',
        'low': '저가',
        'volume': '거래량',
        'EMA': '지수이동평균',
        '10Y_Yield': '미국 10년물 국채 금리',
        'USD_Index': '달러 인덱스',
        'pdsi': 'Palmer 가뭄 지수',
        'spi30d': '표준 강수 지수 (30일)',
        'spi90d': '표준 강수 지수 (90일)',
        'lambda_price': 'Hawkes 가격 강도',
        'lambda_news': 'Hawkes 뉴스 강도',
        'news_count': '뉴스 개수',
    }
    
    # 뉴스 PCA는 동적으로 처리
    if feature_id.startswith('news_pca_'):
        idx = feature_id.replace('news_pca_', '')
        return f'뉴스 PCA {idx}'
    
    return label_map.get(feature_id, feature_id)
