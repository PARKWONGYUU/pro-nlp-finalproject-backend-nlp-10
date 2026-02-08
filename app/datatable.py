from sqlalchemy import Column, Integer, BigInteger, String, Date, Numeric, Text, ForeignKey, ARRAY, TIMESTAMP, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import UserDefinedType
from .database import Base
from pgvector.sqlalchemy import Vector

class DocEmbeddings(Base):
    __tablename__ = "doc_embeddings"

    id = Column(BigInteger, primary_key=True, index=True) # bigserial
    title = Column(String(255))
    content = Column(Text)
    source_url = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())
    embedding = Column(Vector(1536))  # vector(1536)

class DailySummary(Base):
    __tablename__ = "daily_summary"

    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(Date, index=True)
    commodity = Column(String(50), index=True)
    score = Column(Numeric(5, 4))
    related_news_ids = Column(ARRAY(BigInteger))
    created_at = Column(TIMESTAMP, server_default=func.now())

class TftPred(Base):
    __tablename__ = "tft_pred"

    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(Date, index=True)
    commodity = Column(String(50), index=True)
    
    price_pred = Column(Numeric(10, 2))
    conf_lower = Column(Numeric(10, 2))
    conf_upper = Column(Numeric(10, 2))

    top1_factor = Column(String(255))
    top1_impact = Column(Float)
    top2_factor = Column(String(255))
    top2_impact = Column(Float)
    top3_factor = Column(String(255))
    top3_impact = Column(Float)
    top4_factor = Column(String(255))
    top4_impact = Column(Float)
    top5_factor = Column(String(255))
    top5_impact = Column(Float)
    top6_factor = Column(String(255))
    top6_impact = Column(Float)
    top7_factor = Column(String(255))
    top7_impact = Column(Float)
    top8_factor = Column(String(255))
    top8_impact = Column(Float)
    top9_factor = Column(String(255))
    top9_impact = Column(Float)
    top10_factor = Column(String(255))
    top10_impact = Column(Float)
    top11_factor = Column(String(255))
    top11_impact = Column(Float)
    top12_factor = Column(String(255))
    top12_impact = Column(Float)
    top13_factor = Column(String(255))
    top13_impact = Column(Float)
    top14_factor = Column(String(255))
    top14_impact = Column(Float)
    top15_factor = Column(String(255))
    top15_impact = Column(Float)
    top16_factor = Column(String(255))
    top16_impact = Column(Float)
    top17_factor = Column(String(255))
    top17_impact = Column(Float)
    top18_factor = Column(String(255))
    top18_impact = Column(Float)
    top19_factor = Column(String(255))
    top19_impact = Column(Float)
    top20_factor = Column(String(255))
    top20_impact = Column(Float)

    model_type = Column(String(255))

    created_at = Column(TIMESTAMP, server_default=func.now())

    explanation = relationship("ExpPred", back_populates="prediction", uselist=False)

class ExpPred(Base):
    __tablename__ = "exp_pred"

    id = Column(Integer, primary_key=True, index=True)
    pred_id = Column(Integer, ForeignKey("tft_pred.id"))
    content = Column(Text)  # Executive Summary
    llm_model = Column(String(50))
    impact_news = Column(JSON)  # high_impact_news
    top_factors = Column(JSON)  # top_factors_impact_ratio
    category_summary = Column(JSON)  # category_impact_ratio
    created_at = Column(TIMESTAMP, server_default=func.now())

    prediction = relationship("TftPred", back_populates="explanation")

class MarketMetrics(Base):
    __tablename__ = "market_metrics"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(50), index=True)
    date = Column(Date, index=True)
    metric_id = Column(String(50))
    label = Column(String(255))
    value = Column(String(50))
    numeric_value = Column(Float)
    trend = Column(Float)
    impact = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=func.now())

class HistoricalPrices(Base):
    __tablename__ = "historical_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(50), index=True)
    date = Column(Date, index=True)
    actual_price = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, server_default=func.now())