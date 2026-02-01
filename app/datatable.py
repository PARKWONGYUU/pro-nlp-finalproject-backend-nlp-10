from sqlalchemy import Column, Integer, BigInteger, String, Date, Numeric, Text, ForeignKey, ARRAY, TIMESTAMP, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import UserDefinedType
from .database import Base

class DocEmbeddings(Base):
    __tablename__ = "doc_embeddings"

    id = Column(BigInteger, primary_key=True, index=True) # bigserial
    content = Column(Text)
    source_url = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())
    embedding = Column("vector(1536)")  # vector(1536)

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

    created_at = Column(TIMESTAMP, server_default=func.now())

    explanation = relationship("ExpPred", back_populates="prediction", uselist=False)

class ExpPred(Base):
    __tablename__ = "exp_pred"

    id = Column(Integer, primary_key=True, index=True)
    pred_id = Column(Integer, ForeignKey("tft_pred.id"))
    content = Column(Text)
    llm_model = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())

    prediction = relationship("TftPred", back_populates="explanation")