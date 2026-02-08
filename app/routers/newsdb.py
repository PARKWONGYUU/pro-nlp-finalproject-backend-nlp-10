from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from .. import crud, dataschemas, database
from ..dummy_data_generator import get_generator

logger = logging.getLogger(__name__)

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
    """
    뉴스 목록 조회
    - DB에 있으면 실제 데이터 반환
    - 없으면 더미 데이터 생성하여 반환
    """
    # 1. DB에서 조회 시도
    news = crud.get_doc_embeddings_light(db, skip, limit)
    
    if news:
        logger.info(f"✅ DB에서 뉴스 조회 성공: {len(news)}개 (skip={skip}, limit={limit})")
        return news
    
    # 2. DB에 없으면 더미 데이터 생성
    logger.warning(f"⚠️ DB에 뉴스 없음, 더미 생성: skip={skip}, limit={limit}")
    
    try:
        generator = get_generator()
        
        # 전체 더미 뉴스 생성 (20개)
        all_dummy_news = generator.generate_news_list(n=20)
        
        # skip과 limit 적용
        dummy_news = all_dummy_news[skip:skip+limit]
        
        logger.info(f"✅ 더미 뉴스 생성 완료: {len(dummy_news)}개")
        return dummy_news
        
    except Exception as e:
        logger.error(f"❌ 더미 뉴스 생성 실패: {e}")
        # 빈 리스트 반환 (에러 대신)
        return []

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