from contextlib import asynccontextmanager
from fastapi import FastAPI
from app import datatable
from app.database import engine
from app.routers import predictions, newsdb, market_metrics, simulation, batch
from app.ml.model_loader import start_model_update_scheduler
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)

origins = [
    "http://localhost:3000",  ## 아이피 갱신 필요 - 프론트 주소!
    "http://127.0.0.1:3000",    
    "*"
]

# 스케줄러 참조 (종료 시 정리용)
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 lifecycle"""
    global _scheduler
    
    # --- Startup ---
    logger.info("🚀 서버 시작 중...")
    _scheduler = start_model_update_scheduler()
    
    yield
    
    # --- Shutdown ---
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("📅 모델 업데이트 스케줄러 종료")
    logger.info("👋 서버 종료")


# DB에 테이블이 없으면 자동 생성 (CREATE TABLE IF NOT EXISTS)
datatable.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Commodity Price AI Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],   
    allow_headers=["*"],   
)

# 라우터 등록
app.include_router(predictions.router)
app.include_router(newsdb.router)
app.include_router(market_metrics.router)
app.include_router(simulation.router)
app.include_router(batch.router)

@app.get("/")
def read_root():
    return {"message": "Server is running with new structure! 🚀"}
