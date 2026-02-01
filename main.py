from fastapi import FastAPI
from app import datatable  # models -> datatable로 변경됨
from app.database import engine
from app.routers import predictions

# DB에 테이블이 없으면 자동 생성 (CREATE TABLE IF NOT EXISTS)
datatable.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Commodity Price AI Server")

# 라우터 등록
app.include_router(predictions.router)

@app.get("/")
def read_root():
    return {"message": "Server is running with new structure! 🚀"}