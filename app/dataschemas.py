from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional, List

#---------------------------------------------------------------------

class TftPredBase(BaseModel):
    target_date: date
    commodity: str
    price_pred: float
    conf_lower: float
    conf_upper: float
    
    top1_factor: Optional[str] = None
    top1_impact: Optional[float] = None
    top2_factor: Optional[str] = None
    top2_impact: Optional[float] = None
    top3_factor: Optional[str] = None
    top3_impact: Optional[float] = None
    top4_factor: Optional[str] = None
    top4_impact: Optional[float] = None
    top5_factor: Optional[str] = None
    top5_impact: Optional[float] = None
    top6_factor: Optional[str] = None
    top6_impact: Optional[float] = None
    top7_factor: Optional[str] = None
    top7_impact: Optional[float] = None
    top8_factor: Optional[str] = None
    top8_impact: Optional[float] = None
    top9_factor: Optional[str] = None
    top9_impact: Optional[float] = None
    top10_factor: Optional[str] = None
    top10_impact: Optional[float] = None
    top11_factor: Optional[str] = None
    top11_impact: Optional[float] = None
    top12_factor: Optional[str] = None
    top12_impact: Optional[float] = None
    top13_factor: Optional[str] = None
    top13_impact: Optional[float] = None
    top14_factor: Optional[str] = None
    top14_impact: Optional[float] = None
    top15_factor: Optional[str] = None
    top15_impact: Optional[float] = None
    top16_factor: Optional[str] = None
    top16_impact: Optional[float] = None
    top17_factor: Optional[str] = None
    top17_impact: Optional[float] = None
    top18_factor: Optional[str] = None
    top18_impact: Optional[float] = None
    top19_factor: Optional[str] = None
    top19_impact: Optional[float] = None
    top20_factor: Optional[str] = None
    top20_impact: Optional[float] = None

    model_type: str = "TFT"

class TftPredCreate(TftPredBase):
    pass

class TftPredResponse(TftPredBase):
    id: int
    created_at: Optional[datetime] = None

    @field_validator('model_type', mode='before')
    @classmethod
    def set_default_model_type(cls, v):
        """model_type이 None이면 'TFT'로 설정"""
        return v if v is not None else "TFT"

    class Config:
        from_attributes = True

#---------------------------------------------------------------------

class ImpactNews(BaseModel):
    source: str
    title: str
    impact_score: int
    analysis: str

class ExpPredCreate(BaseModel):
    pred_id: int
    content: str
    llm_model: str
    impact_news: Optional[List[dict]] = None

class ExpPredResponse(BaseModel):
    id: int
    pred_id: int
    content: str
    llm_model: str
    impact_news: Optional[List[ImpactNews]] = None
    created_at: datetime

    class Config:
        from_attributes = True

#---------------------------------------------------------------------

class DailySummaryCreate(BaseModel):
    target_date: date
    commodity: str
    score: float
    related_news_ids: List[int]

class DailySummaryResponse(DailySummaryCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

#---------------------------------------------------------------------

class NewsBase(BaseModel):
    title: str
    content: str
    source_url: Optional[str] = None
    created_at: datetime


class NewsCreate(NewsBase):
    embedding: List[float]

class NewsResponse(NewsBase):
    id: int
    
    class Config:
        from_attributes = True

class NewsResponseWithVector(NewsResponse):
    embedding: List[float]

#---------------------------------------------------------------------

class MarketMetricItem(BaseModel):
    metric_id: str
    label: str
    value: str
    numeric_value: float
    trend: float
    impact: str

class MarketMetricBase(BaseModel):
    commodity: str
    date: date
    metric_id: str
    label: str
    value: str
    numeric_value: float
    trend: float
    impact: str

class MarketMetricCreate(MarketMetricBase):
    pass

class MarketMetricResponse(MarketMetricBase):
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MarketMetricsResponse(BaseModel):
    commodity: str
    date: str
    metrics: List[MarketMetricItem]

#---------------------------------------------------------------------

class HistoricalPriceItem(BaseModel):
    date: str
    actual_price: float
    is_trading_day: bool = True  # False면 휴장일 (주말/공휴일)

class HistoricalPriceBase(BaseModel):
    commodity: str
    date: date
    actual_price: float

class HistoricalPriceCreate(HistoricalPriceBase):
    pass

class HistoricalPriceResponse(HistoricalPriceBase):
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class HistoricalPricesResponse(BaseModel):
    commodity: str
    prices: List[HistoricalPriceItem]

#---------------------------------------------------------------------

class PredictionsWithPricesResponse(BaseModel):
    predictions: List[TftPredResponse]
    historical_prices: List[HistoricalPriceItem]

#---------------------------------------------------------------------

class FeatureImpact(BaseModel):
    feature: str
    current_value: float
    new_value: float
    value_change: float
    contribution: float

class SimulationRequest(BaseModel):
    commodity: str
    base_date: date
    feature_overrides: dict

class SimulationResponse(BaseModel):
    original_forecast: float
    simulated_forecast: float
    change: float
    change_percent: float
    feature_impacts: List[FeatureImpact]

#---------------------------------------------------------------------
# 배치서버용 스키마 (Bulk / Upsert / Delete)
#---------------------------------------------------------------------

# --- TFT 예측 Bulk ---
class TftPredBulkCreate(BaseModel):
    predictions: List[TftPredCreate]

# --- 뉴스 Bulk ---
class NewsBulkCreate(BaseModel):
    news_list: List[NewsCreate]

# --- Market Metrics Bulk ---
class MarketMetricBulkCreate(BaseModel):
    commodity: str
    date: date
    metrics: List[MarketMetricItem]

class MarketMetricUpsert(BaseModel):
    commodity: str
    date: date
    metric_id: str
    label: str = ""
    value: str = ""
    numeric_value: float = 0.0
    trend: float = 0.0
    impact: str = "neutral"

class MarketMetricBulkUpsert(BaseModel):
    commodity: str
    date: date
    metrics: List[MarketMetricItem]

# --- Historical Prices Bulk ---
class HistoricalPriceBulkCreate(BaseModel):
    commodity: str
    prices: List[HistoricalPriceItem]

class HistoricalPriceUpsert(BaseModel):
    commodity: str
    date: date
    actual_price: float

class HistoricalPriceBulkUpsert(BaseModel):
    commodity: str
    prices: List[HistoricalPriceItem]

# --- 공통 삭제 조건 ---
class DeleteByDateRange(BaseModel):
    commodity: str
    start_date: date
    end_date: date

class DeleteByDate(BaseModel):
    commodity: str
    date: date

# --- 응답 ---
class BatchResult(BaseModel):
    success: bool
    message: str
    count: int = 0