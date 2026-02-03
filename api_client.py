import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://127.0.0.1:5432" #   <-- 아이피 주소 변경 필수

def send_prediction(data: dict, base_url: str = DEFAULT_API_URL) -> bool:
    endpoint = f"{base_url}/api/predictions"
    
    try:
        response = requests.post(endpoint, json=data, timeout=5)
        response.raise_for_status()
        
        logger.info(f"[Prediction 저장 성공] 응답: {response.json()}")
        return True

    except Exception as e:
        logger.error(f"[Prediction 저장 실패] {e}")
        return False

def send_explanation(data: dict, base_url: str = DEFAULT_API_URL) -> bool:
    endpoint = f"{base_url}/api/explanations"
    
    try:
        response = requests.post(endpoint, json=data, timeout=5)
        response.raise_for_status()
        
        logger.info(f"[Explanation 저장 성공] 응답: {response.json()}")
        return True

    except Exception as e:
        logger.error(f"[Explanation 저장 실패] {e}")
        return False
    
def send_news(data: dict, base_url: str = DEFAULT_API_URL) -> bool:
    endpoint = f"{base_url}/api/newsdb"
    
    try:
        response = requests.post(endpoint, json=data, timeout=5)
        response.raise_for_status()
        
        logger.info(f"[News 저장 성공] 응답: {response.json()}")
        return True

    except Exception as e:
        logger.error(f"[News 저장 실패] {e}")
        return False

"""
    입력 데이터 형식 예시

    dummy_pred = {
        "target_date": "2026-06-01",
        "commodity": "Corn",
        "price_pred": 500.5,
        "conf_lower": 490.0,
        "conf_upper": 510.0,
        "top1_factor": "Test Factor",
        "top1_impact": 10.0,
        "top2_factor": "None",
        "top2_impact": 0,
        "top3_factor": "None",
        "top3_impact": 0,
        "top4_factor": "None",
        "top4_impact": 0,
        "top5_factor": "None",
        "top5_impact": 0
    }
    
    dummy_exp = {
        "pred_id": int
        "content": str
        "llm_model": str
    }

    news_data = {
    "content": "금값 폭등...",
    "source_url": "http://...",
    "embedding": [0.1, 0.2, 0.3] # 1536차원 리스트
}

    각각의 함수 호출로 구분해서 전송
    예측 데이터 전송
    send_prediction(dummy_pred)

    설명 데이터 전송
    send_explanation(dummy_exp)

    뉴스 데이터 전송
    send_news(news_data)
"""