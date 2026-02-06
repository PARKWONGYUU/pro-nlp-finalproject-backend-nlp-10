from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, dataschemas, database

router = APIRouter(
    prefix="/api/newsdb",
    tags=["News Data"]
)

# URL: GET /api/newsdb?skip=0&limit=10
# embedding 제외 목록 조회, skip ~ limit까지만 조회
@router.get("", response_model=List[dataschemas.NewsResponse])
def get_news_list(
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(database.get_db)
):
    return crud.get_doc_embeddings_light(db, skip, limit)

"""
# URL: GET /api/newsdb/어케하지?
# keyword의 벡터 기반 뉴스데이터 검색 (top_k)
@router.get("/{keyword_vector}", response_model=Union[dataschemas.NewsResponseWithVector, dataschemas.NewsResponse])
def get_news_detail(
    keyword_vector: int,
    top_k: int,
    db: Session = Depends(database.get_db)
):
    results = crud.search_similar_docs(db, keyword_vector, top_k=5)
    
    if not results:
        raise HTTPException(status_code=404, detail="News not found")
    return results
"""