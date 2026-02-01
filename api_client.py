import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://127.0.0.1:5432"

def send_prediction(data: dict, base_url: str = DEFAULT_API_URL) -> bool:
    endpoint = f"{base_url}/api/predictions/create"
    
    try:
        response = requests.post(endpoint, json=data, timeout=5)
        
        response.raise_for_status()
        
        logger.info(f"전송 ID: {response.json().get('id')}")
        return True

    except requests.exceptions.ConnectionError:
        logger.error(f"연결 실패: {base_url}")
        return False
    except requests.exceptions.HTTPError as err:
        logger.error(f"전송 실패 (HTTP 에러): {err}")
        return False
    except Exception as e:
        logger.error(f"알 수 없는 에러: {e}")
        return False