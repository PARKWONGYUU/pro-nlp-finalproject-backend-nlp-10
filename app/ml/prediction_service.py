import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .model_loader import get_model_loader
from app.config import settings

logger = logging.getLogger(__name__)


class TFTFeatureConfig:
    """TFT 모델의 Feature 구성 정보"""
    
    # Feature 순서 정의 (총 52개)
    FEATURE_ORDER = [
        # Unknown Time-Varying (46개)
        'close', 'open', 'high', 'low', 'volume', 'EMA',  # 가격/거래량 6개
        *[f'news_pca_{i}' for i in range(32)],  # 뉴스 PCA 32개
        'pdsi', 'spi30d', 'spi90d',  # 기후 지수 3개
        '10Y_Yield', 'USD_Index',  # 거시경제 2개
        'lambda_price', 'lambda_news',  # Hawkes Intensity 2개
        'news_count',  # 뉴스 개수 1개
        # Known Time-Varying (3개)
        'time_idx', 'day_of_year', 'relative_time_idx',
        # Static (3개)
        'encoder_length', 'close_center', 'close_scale'
    ]
    
    # 시계열 관련 Feature (동적 생성 필요)
    TIME_FEATURES = {'time_idx', 'day_of_year', 'relative_time_idx'}
    
    # Static Feature (모든 시점에서 동일)
    STATIC_FEATURES = {'encoder_length', 'close_center', 'close_scale'}
    
    # Known Future Features (미래 시점에도 알 수 있는 Feature)
    KNOWN_FEATURES = TIME_FEATURES | STATIC_FEATURES
    
    # Encoder/Decoder 길이
    ENCODER_LENGTH = 60
    DECODER_LENGTH = 7
    
    # 기본값
    DEFAULT_CLOSE_VALUE = 450.0
    DEFAULT_SCALE_VALUE = 1.0
    DEFAULT_TARGET_CENTER = 450.0
    DEFAULT_TARGET_SCALE = 10.0


class ONNXPredictionService:
    """ONNX 기반 TFT 모델 예측 서비스"""
    
    def __init__(self):
        self.model_loader = get_model_loader()
        self.feature_config = TFTFeatureConfig()
        logger.info("TFT 예측 서비스 초기화 완료")
    
    def predict_tft(
        self, 
        commodity: str, 
        historical_data: Dict[str, any], 
        feature_overrides: Optional[Dict[str, float]] = None
    ) -> Dict[str, List[float]]:
        """
        TFT 모델로 실시간 예측 수행
        
        Args:
            commodity: 품목명 (예: "corn")
            historical_data: 과거 데이터
                {
                    'dates': ['2024-01-01', '2024-01-02', ...],
                    'features': {
                        'close': [450.0, 451.0, ...],
                        'open': [449.0, 450.0, ...],
                        ...
                    }
                }
            feature_overrides: 사용자 변경 Feature (선택사항)
                {
                    "10Y_Yield": 4.5,
                    "USD_Index": 105.0,
                    ...
                }
        
        Returns:
            예측 결과
            {
                'predictions': [가격1, 가격2, ..., 가격7],  # 7일 예측 (중앙값)
                'lower_bounds': [...],  # 하한
                'upper_bounds': [...]   # 상한
            }
        """
        # ONNX 세션 로드
        session = self.model_loader.load_session(commodity)
        
        # TFT 입력 형식으로 변환
        model_inputs = self._prepare_model_inputs(historical_data, feature_overrides)
        
        # 로깅
        self._log_inference_info(model_inputs)
        
        # 추론 실행
        outputs = session.run(None, model_inputs)
        
        # 결과 파싱
        result = self._parse_predictions(outputs)
        
        logger.info(f"예측 완료 - 7일 예측: {result['predictions']}")
        
        return result
    
    def _prepare_model_inputs(
        self, 
        historical_data: Dict[str, any],
        feature_overrides: Optional[Dict[str, float]] = None
    ) -> Dict[str, np.ndarray]:
        """
        과거 데이터를 TFT 모델 입력 형식으로 변환
        
        TFT 입력 구조:
        - encoder_cat: [1, 60, 1] - 과거 60일의 범주형 (group_id)
        - encoder_cont: [1, 60, 52] - 과거 60일의 52개 연속형 feature
        - encoder_lengths: [1] - 인코더 길이 (60)
        - decoder_cat: [1, 7, 1] - 미래 7일의 범주형
        - decoder_cont: [1, 7, 52] - 미래 7일의 52개 연속형 feature
        - decoder_lengths: [1] - 디코더 길이 (7)
        - target_scale: [1, 2] - 타겟 스케일 파라미터 (center, scale)
        
        Returns:
            ONNX 모델 입력 텐서 딕셔너리
        """
        features = historical_data['features'].copy()
        
        # Feature override 적용
        if feature_overrides:
            features = self._apply_feature_overrides(features, feature_overrides)
        
        # Encoder/Decoder 데이터 생성
        encoder_cont = self._build_encoder_features(features)
        decoder_cont = self._build_decoder_features(features)
        
        # 범주형 데이터 (group_id)
        encoder_cat = np.zeros([1, self.feature_config.ENCODER_LENGTH, 1], dtype=np.int64)
        decoder_cat = np.zeros([1, self.feature_config.DECODER_LENGTH, 1], dtype=np.int64)
        
        # Lengths
        encoder_lengths = np.array([self.feature_config.ENCODER_LENGTH], dtype=np.int64)
        decoder_lengths = np.array([self.feature_config.DECODER_LENGTH], dtype=np.int64)
        
        # Target scale
        target_scale = self._get_target_scale(features)
        
        return {
            'encoder_cat': encoder_cat,
            'encoder_cont': encoder_cont,
            'encoder_lengths': encoder_lengths,
            'decoder_cat': decoder_cat,
            'decoder_cont': decoder_cont,
            'decoder_lengths': decoder_lengths,
            'target_scale': target_scale
        }
    
    def _apply_feature_overrides(
        self, 
        features: Dict[str, List[float]], 
        overrides: Dict[str, float]
    ) -> Dict[str, List[float]]:
        """Feature override를 적용"""
        for key, value in overrides.items():
            if key in features:
                # 모든 시점에 동일한 값 적용
                features[key] = [value] * len(features[key])
        return features
    
    def _build_encoder_features(self, features: Dict[str, List[float]]) -> np.ndarray:
        """Encoder용 feature 배열 생성 (과거 60일)"""
        encoder_data = []
        
        for i in range(self.feature_config.ENCODER_LENGTH):
            feature_vector = self._get_feature_vector_at_index(features, i, is_encoder=True)
            encoder_data.append(feature_vector)
        
        return np.array([encoder_data], dtype=np.float32)  # [1, 60, 52]
    
    def _build_decoder_features(self, features: Dict[str, List[float]]) -> np.ndarray:
        """Decoder용 feature 배열 생성 (미래 7일)"""
        decoder_data = []
        
        for i in range(self.feature_config.DECODER_LENGTH):
            feature_vector = self._get_feature_vector_at_index(
                features, 
                self.feature_config.ENCODER_LENGTH + i, 
                is_encoder=False
            )
            decoder_data.append(feature_vector)
        
        return np.array([decoder_data], dtype=np.float32)  # [1, 7, 52]
    
    def _get_feature_vector_at_index(
        self, 
        features: Dict[str, List[float]], 
        time_idx: int, 
        is_encoder: bool
    ) -> List[float]:
        """특정 시점의 feature 벡터 생성"""
        feature_vector = []
        
        for fname in self.feature_config.FEATURE_ORDER:
            value = self._get_feature_value(features, fname, time_idx, is_encoder)
            feature_vector.append(value)
        
        return feature_vector
    
    def _get_feature_value(
        self, 
        features: Dict[str, List[float]], 
        feature_name: str, 
        time_idx: int, 
        is_encoder: bool
    ) -> float:
        """개별 feature 값 계산"""
        # Static Features
        if feature_name == 'encoder_length':
            return float(self.feature_config.ENCODER_LENGTH)
        elif feature_name == 'close_scale':
            return self.feature_config.DEFAULT_SCALE_VALUE
        elif feature_name == 'close_center':
            return self._get_close_value(features, time_idx)
        
        # Time Features
        elif feature_name == 'time_idx':
            return float(time_idx)
        elif feature_name == 'day_of_year':
            return self._get_day_of_year(time_idx, is_encoder)
        elif feature_name == 'relative_time_idx':
            total_length = self.feature_config.ENCODER_LENGTH + self.feature_config.DECODER_LENGTH
            return float(time_idx) / float(total_length)
        
        # Unknown Features (Decoder에서는 0)
        elif not is_encoder and feature_name not in self.feature_config.KNOWN_FEATURES:
            return 0.0
        
        # 일반 Features
        elif feature_name in features:
            if time_idx < len(features[feature_name]):
                return features[feature_name][time_idx]
            return 0.0
        
        # 기본값
        return 0.0
    
    def _get_close_value(self, features: Dict[str, List[float]], time_idx: int) -> float:
        """Close 가격 값 가져오기"""
        if 'close' in features and time_idx < len(features['close']):
            return features['close'][time_idx]
        return self.feature_config.DEFAULT_CLOSE_VALUE
    
    def _get_day_of_year(self, time_idx: int, is_encoder: bool) -> float:
        """연중 몇 번째 날인지 계산"""
        if is_encoder:
            # 과거 날짜
            days_ago = self.feature_config.ENCODER_LENGTH - time_idx
            target_date = datetime.now() - timedelta(days=days_ago)
        else:
            # 미래 날짜
            days_ahead = time_idx - self.feature_config.ENCODER_LENGTH
            target_date = datetime.now() + timedelta(days=days_ahead)
        
        return float(target_date.timetuple().tm_yday)
    
    def _get_target_scale(self, features: Dict[str, List[float]]) -> np.ndarray:
        """Target scale 파라미터 생성"""
        return np.array(
            [[self.feature_config.DEFAULT_TARGET_CENTER, self.feature_config.DEFAULT_TARGET_SCALE]], 
            dtype=np.float32
        )
    
    def _parse_predictions(self, outputs: List[np.ndarray]) -> Dict[str, List[float]]:
        """ONNX 출력을 파싱하여 예측 결과 반환"""
        predictions = outputs[0]  # shape: [1, 7, 3]
        
        return {
            'predictions': predictions[0, :, 0].tolist(),      # 중앙값
            'lower_bounds': predictions[0, :, 1].tolist(),     # 하한
            'upper_bounds': predictions[0, :, 2].tolist()      # 상한
        }
    
    def _log_inference_info(self, model_inputs: Dict[str, np.ndarray]):
        """추론 정보 로깅"""
        logger.info("TFT 추론 실행")
        for name, array in model_inputs.items():
            logger.info(f"  {name}: {array.shape}")


def get_prediction_service() -> ONNXPredictionService:
    """예측 서비스 인스턴스 반환"""
    return ONNXPredictionService()
