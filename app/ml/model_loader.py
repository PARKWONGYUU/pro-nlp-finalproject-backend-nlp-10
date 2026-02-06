import onnxruntime as ort
import pickle
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ONNXModelLoader:
    def __init__(self):
        self.mode = settings.model_load_mode
        self.local_path = Path(settings.local_model_path)
        
        # 모델 세션 캐시
        self.sessions = {}
        # 전처리 정보 캐시
        self.preprocessing_info = {}
        
        logger.info(f"모델 로더 초기화: mode={self.mode}, path={self.local_path}")
    
    def _find_local_model_files(self):
        """로컬 경로에서 ONNX 및 pkl 파일 찾기"""
        onnx_files = list(self.local_path.glob("*.onnx"))
        pkl_files = list(self.local_path.glob("*.pkl"))
        
        if not onnx_files:
            raise FileNotFoundError(f"ONNX 모델 파일을 찾을 수 없습니다: {self.local_path}")
        
        # 가장 최신 파일 사용 (파일명 날짜 기준)
        onnx_file = sorted(onnx_files)[-1]
        pkl_file = sorted(pkl_files)[-1] if pkl_files else None
        
        logger.info(f"로컬 모델 파일 발견: {onnx_file.name}")
        if pkl_file:
            logger.info(f"전처리 정보 파일 발견: {pkl_file.name}")
        
        return onnx_file, pkl_file
    
    def load_session(self, commodity: str = None):
        """ONNX 세션 로드 (캐싱)"""
        # 로컬 모드에서는 commodity 무시하고 temp/ 폴더의 모델 사용
        cache_key = "default"
        
        if cache_key not in self.sessions:
            logger.info(f"ONNX 세션 생성 중...")
            
            onnx_file, pkl_file = self._find_local_model_files()
            
            # ONNX 세션 생성
            self.sessions[cache_key] = ort.InferenceSession(
                str(onnx_file),
                providers=['CPUExecutionProvider']
            )
            logger.info(f"✅ ONNX 세션 생성 완료: {onnx_file.name}")
            
            # 전처리 정보 로드
            if pkl_file and pkl_file.exists():
                with open(pkl_file, 'rb') as f:
                    self.preprocessing_info[cache_key] = pickle.load(f)
                logger.info(f"✅ 전처리 정보 로드 완료: {pkl_file.name}")
            else:
                logger.warning("⚠️ 전처리 정보 파일이 없습니다")
        
        return self.sessions[cache_key]
    
    def get_preprocessing_info(self, commodity: str = None):
        """전처리 정보 가져오기"""
        cache_key = "default"
        
        # 세션이 로드되지 않았으면 먼저 로드
        if cache_key not in self.sessions:
            self.load_session(commodity)
        
        return self.preprocessing_info.get(cache_key, {})

# 싱글톤 인스턴스
_model_loader = None

def get_model_loader():
    global _model_loader
    if _model_loader is None:
        _model_loader = ONNXModelLoader()
    return _model_loader
