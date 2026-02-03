from pydantic import BaseModel
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

class TftPredCreate(TftPredBase):
    pass

class TftPredResponse(TftPredBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

#---------------------------------------------------------------------

class ExpPredCreate(BaseModel):
    pred_id: int
    content: str
    llm_model: str

class ExpPredResponse(BaseModel):
    id: int
    pred_id: int
    content: str
    llm_model: str
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