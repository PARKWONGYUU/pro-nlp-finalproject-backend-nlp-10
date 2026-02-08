import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .model_loader import get_model_loader
from .lightweight_scaler import LightweightScaler
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
    DECODER_LENGTH = 7  # 🔄 Temporarily reverted to 7 (current ONNX model limitation)
    
    # 기본값 (fallback)
    DEFAULT_CLOSE_VALUE = 450.0
    DEFAULT_SCALE_VALUE = 1.0
    DEFAULT_TARGET_CENTER = 450.0
    DEFAULT_TARGET_SCALE = 10.0
    
    # 정규화에서 제외할 Feature들 (이미 정규화되어 있거나 범위가 고정된 경우)
    NORMALIZATION_EXCLUDE = TIME_FEATURES | STATIC_FEATURES | {'relative_time_idx'}


class ONNXPredictionService:
    """ONNX 기반 TFT 모델 예측 서비스"""
    
    def __init__(self):
        self.model_loader = get_model_loader()
        self.feature_config = TFTFeatureConfig()
        # 정규화 파라미터 캐시 (commodity별로 저장)
        self.normalization_params = {}
        # PKL에서 로드한 scaler 캐시
        self.pkl_scaler = None
        # LightweightScaler 캐시 (GroupNormalizer용)
        self.lightweight_scaler = None
        # 사용 중인 정규화 방식
        self.normalization_method = None  # 'group_normalizer', 'standard_scaler', 'dynamic'
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
        # 🔥 중요: Deep copy를 해야 원본 데이터가 변경되지 않음!
        import copy
        features = copy.deepcopy(historical_data['features'])
        
        # 🔥 추가: 모델 입력용 로그 변환 (data_fetcher에서 제거했으므로 여기서 수행)
        # 가격 관련 변수는 log1p 변환하여 모델에 입력
        log_cols = ['close', 'open', 'high', 'low', 'volume', 'EMA']
        for col in log_cols:
            if col in features and features[col]:
                # 리스트를 numpy로 변환하여 벡터 연산 후 다시 리스트로
                arr = np.array(features[col], dtype=np.float64)
                # 이미 로그 변환된 값이 아닌 경우에만 변환 (값의 범위로 추정)
                # 옥수수 가격은 보통 400~600이므로 log값은 6.0~6.5
                # 만약 평균이 10 미만이라면 이미 로그 변환된 것으로 간주할 수도 있지만,
                # data_fetcher가 원본을 주도록 수정했으므로 무조건 변환
                features[col] = np.log1p(arr).tolist()
                logger.debug(f"   {col}: Log1p 변환 완료 (first={features[col][0]:.2f})")
        
        # Feature override 적용
        if feature_overrides:
            features = self._apply_feature_overrides(features, feature_overrides)
        
        # 🔥 정규화 파라미터 로드 또는 계산
        # 1순위: PKL 파일의 scaler 사용 (학습 시와 동일)
        # 2순위: 동적 계산 (encoder 데이터 기반)
        self._load_or_compute_normalization_params(features)
        
        # 🔥 Feature 정규화 적용
        normalized_features = self._normalize_features(features)
        
        # Encoder/Decoder 데이터 생성
        encoder_cont = self._build_encoder_features(normalized_features)
        decoder_cont = self._build_decoder_features(normalized_features)
        
        # 범주형 데이터 (group_id)
        encoder_cat = np.zeros([1, self.feature_config.ENCODER_LENGTH, 1], dtype=np.int64)
        decoder_cat = np.zeros([1, self.feature_config.DECODER_LENGTH, 1], dtype=np.int64)
        
        # Lengths
        encoder_lengths = np.array([self.feature_config.ENCODER_LENGTH], dtype=np.int64)
        decoder_lengths = np.array([self.feature_config.DECODER_LENGTH], dtype=np.int64)
        
        # Target scale (정규화된 close 값 기반)
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
    
    def _load_or_compute_normalization_params(self, features: Dict[str, List[float]]):
        """
        정규화 파라미터 로드 또는 계산
        
        우선순위:
        1. GroupNormalizer (pytorch-forecasting) - LightweightScaler 사용
        2. StandardScaler (sklearn) - PKL에서 mean_/scale_ 추출
        3. 동적 계산 (fallback) - Encoder 데이터로 계산
        """
        # 1순위: GroupNormalizer 시도
        if self._load_group_normalizer_from_pkl():
            logger.info("✅ GroupNormalizer 사용 (pytorch-forecasting 방식)")
            self.normalization_method = 'group_normalizer'
            return
        
        # 2순위: StandardScaler 시도
        if self._load_normalization_params_from_pkl():
            logger.info("✅ StandardScaler 사용 (sklearn 방식)")
            self.normalization_method = 'standard_scaler'
            return
        
        # 3순위: 동적 계산 (fallback)
        logger.warning("⚠️ PKL scaler 로드 실패, encoder 데이터로 동적 계산")
        self._compute_normalization_params(features)
        self.normalization_method = 'dynamic'
    
    def _load_group_normalizer_from_pkl(self) -> bool:
        """
        PKL 파일에서 GroupNormalizer 로드 (pytorch-forecasting)
        
        Returns:
            성공 여부
        """
        try:
            preprocessing_info = self.model_loader.get_preprocessing_info()
            
            if not preprocessing_info:
                logger.debug("전처리 정보가 없습니다")
                return False
            
            # GroupNormalizer 관련 키 찾기
            normalizer = None
            normalizer_key = None
            
            for key in ['target_normalizer', 'normalizer', 'target_scaler']:
                if key in preprocessing_info:
                    normalizer = preprocessing_info[key]
                    normalizer_key = key
                    break
            
            if normalizer is None:
                logger.debug("GroupNormalizer를 찾을 수 없습니다")
                return False
            
            # GroupNormalizer 타입 확인
            normalizer_type = type(normalizer).__name__
            if 'GroupNormalizer' not in normalizer_type:
                logger.debug(f"GroupNormalizer가 아님: {normalizer_type}")
                return False
            
            # LightweightScaler로 변환
            scaler_params = self._extract_group_normalizer_params(normalizer, preprocessing_info)
            
            if scaler_params is None:
                logger.warning("GroupNormalizer 파라미터 추출 실패")
                return False
            
            # LightweightScaler 생성
            self.lightweight_scaler = LightweightScaler(scaler_params)
            
            logger.info(f"✅ GroupNormalizer 로드 성공: {normalizer_key}")
            logger.info(f"   Transformation: {scaler_params['metadata'].get('transformation', 'none')}")
            logger.info(f"   Groups: {scaler_params['metadata'].get('groups', [])}")
            
            return True
            
        except Exception as e:
            logger.warning(f"GroupNormalizer 로드 중 오류: {e}")
            return False
    
    def _extract_group_normalizer_params(self, normalizer, preprocessing_info: dict) -> Optional[dict]:
        """
        GroupNormalizer에서 LightweightScaler용 파라미터 추출
        
        Args:
            normalizer: GroupNormalizer 객체
            preprocessing_info: 전처리 정보 딕셔너리
            
        Returns:
            LightweightScaler용 파라미터 딕셔너리
        """
        try:
            # 기본 메타데이터
            scaler_params = {
                'metadata': {
                    'source': 'pkl',
                    'target': preprocessing_info.get('target', 'close'),
                    'transformation': getattr(normalizer, 'transformation', 'none'),
                    'groups': preprocessing_info.get('group_ids', [])
                },
                'normalizer_params': {}
            }
            
            # Center & Scale 추출
            if hasattr(normalizer, 'center_'):
                center = normalizer.center_
                if hasattr(center, 'cpu'):
                    center = center.cpu().numpy()
                scaler_params['normalizer_params']['center'] = center.tolist() if hasattr(center, 'tolist') else [float(center)]
            
            if hasattr(normalizer, 'scale_'):
                scale = normalizer.scale_
                if hasattr(scale, 'cpu'):
                    scale = scale.cpu().numpy()
                scaler_params['normalizer_params']['scale'] = scale.tolist() if hasattr(scale, 'tolist') else [float(scale)]
            
            # 그룹별 통계 추출 (있는 경우)
            group_statistics = {}
            if hasattr(normalizer, 'group_centers_') and hasattr(normalizer, 'group_scales_'):
                group_centers = normalizer.group_centers_
                group_scales = normalizer.group_scales_
                
                groups = preprocessing_info.get('group_ids', [])
                for i, group in enumerate(groups):
                    if i < len(group_centers) and i < len(group_scales):
                        group_statistics[str(group)] = {
                            'mean': float(group_centers[i]) if hasattr(group_centers[i], 'item') else float(group_centers[i]),
                            'std': float(group_scales[i]) if hasattr(group_scales[i], 'item') else float(group_scales[i])
                        }
            
            if group_statistics:
                scaler_params['normalizer_params']['group_statistics'] = group_statistics
            
            return scaler_params
            
        except Exception as e:
            logger.error(f"GroupNormalizer 파라미터 추출 실패: {e}")
            return None
    
    def _load_normalization_params_from_pkl(self) -> bool:
        """
        PKL 파일에서 정규화 파라미터 로드
        
        Returns:
            성공 여부
        """
        try:
            # 전처리 정보 가져오기
            preprocessing_info = self.model_loader.get_preprocessing_info()
            
            if not preprocessing_info:
                logger.debug("전처리 정보가 없습니다")
                return False
            
            # Scaler 객체 찾기 (여러 가능한 키 확인)
            scaler = None
            for key in ['scaler', 'feature_scaler', 'x_scaler', 'normalizer']:
                if key in preprocessing_info:
                    scaler = preprocessing_info[key]
                    break
            
            if scaler is None:
                logger.debug("PKL에서 scaler를 찾을 수 없습니다")
                return False
            
            # StandardScaler의 mean_, scale_ 속성 확인
            if not (hasattr(scaler, 'mean_') and hasattr(scaler, 'scale_')):
                logger.warning(f"Scaler에 mean_/scale_ 속성이 없습니다: {type(scaler)}")
                return False
            
            # Feature 순서 확인 (PKL에 저장되어 있을 수 있음)
            feature_names = None
            if hasattr(scaler, 'feature_names_in_'):
                feature_names = scaler.feature_names_in_
            elif 'feature_names' in preprocessing_info:
                feature_names = preprocessing_info['feature_names']
            
            # 정규화 파라미터 생성
            params = {}
            mean_array = np.array(scaler.mean_)
            scale_array = np.array(scaler.scale_)
            
            if feature_names is not None:
                # Feature 이름이 있는 경우 매핑
                for i, feature_name in enumerate(feature_names):
                    if i < len(mean_array) and i < len(scale_array):
                        params[feature_name] = {
                            'mean': float(mean_array[i]),
                            'std': float(scale_array[i])
                        }
            else:
                # Feature 이름이 없는 경우, FEATURE_ORDER 순서대로 매핑
                logger.warning("Feature 이름이 없어 FEATURE_ORDER 순서로 매핑합니다")
                idx = 0
                for feature_name in self.feature_config.FEATURE_ORDER:
                    if feature_name in self.feature_config.NORMALIZATION_EXCLUDE:
                        continue
                    if idx < len(mean_array) and idx < len(scale_array):
                        params[feature_name] = {
                            'mean': float(mean_array[idx]),
                            'std': float(scale_array[idx])
                        }
                        idx += 1
            
            # 캐시에 저장
            self.normalization_params = params
            self.pkl_scaler = scaler
            
            logger.info(f"✅ PKL scaler 로드 성공: {len(params)}개 feature")
            logger.debug(f"   예시: close = mean:{params.get('close', {}).get('mean', 0):.2f}, "
                        f"std:{params.get('close', {}).get('std', 1):.2f}")
            return True
            
        except Exception as e:
            logger.warning(f"PKL scaler 로드 중 오류: {e}")
            return False
    
    def _compute_normalization_params(self, features: Dict[str, List[float]]):
        """
        Encoder 데이터를 기반으로 정규화 파라미터 계산 (StandardScaler 방식)
        
        Fallback: PKL 로드 실패 시 사용
        """
        params = {}
        
        for feature_name in self.feature_config.FEATURE_ORDER:
            # 정규화 제외 대상은 건너뛰기
            if feature_name in self.feature_config.NORMALIZATION_EXCLUDE:
                continue
            
            # feature가 존재하고 encoder 범위 내에 충분한 데이터가 있는 경우
            if feature_name in features and len(features[feature_name]) >= self.feature_config.ENCODER_LENGTH:
                # Encoder 구간만 사용 (과거 60일)
                encoder_values = features[feature_name][:self.feature_config.ENCODER_LENGTH]
                
                # numpy 배열로 변환
                values_array = np.array(encoder_values, dtype=np.float32)
                
                # mean과 std 계산
                mean_val = np.mean(values_array)
                std_val = np.std(values_array)
                
                # std가 0이면 1로 대체 (division by zero 방지)
                if std_val == 0 or np.isnan(std_val):
                    std_val = 1.0
                
                params[feature_name] = {
                    'mean': float(mean_val),
                    'std': float(std_val)
                }
        
        # 캐시에 저장
        self.normalization_params = params
        
        logger.info(f"📊 정규화 파라미터 동적 계산 완료: {len(params)}개 feature")
        logger.debug(f"   예시: close = mean:{params.get('close', {}).get('mean', 0):.2f}, "
                    f"std:{params.get('close', {}).get('std', 1):.2f}")
    
    def _normalize_features(self, features: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        Feature들을 정규화
        
        정규화 방식:
        - GroupNormalizer: LightweightScaler 사용 (softplus + group normalization)
        - StandardScaler: Z-score normalization ((x - mean) / std)
        - Dynamic: Encoder 데이터 기반 Z-score
        
        Returns:
            정규화된 features 딕셔너리
        """
        # GroupNormalizer 사용
        if self.normalization_method == 'group_normalizer':
            return self._normalize_with_group_normalizer(features)
        
        # StandardScaler 또는 Dynamic (동일한 Z-score 방식)
        normalized = {}
        
        for feature_name, values in features.items():
            # 정규화 제외 대상은 그대로 사용
            if feature_name in self.feature_config.NORMALIZATION_EXCLUDE:
                normalized[feature_name] = values
                continue
            
            # 정규화 파라미터가 있는 경우 적용
            if feature_name in self.normalization_params:
                params = self.normalization_params[feature_name]
                mean_val = params['mean']
                std_val = params['std']
                
                # 정규화 적용: (x - mean) / std
                normalized_values = [
                    (val - mean_val) / std_val 
                    for val in values
                ]
                normalized[feature_name] = normalized_values
                
                logger.debug(f"   {feature_name} 정규화: mean={mean_val:.2f}, std={std_val:.2f}")
            else:
                # 파라미터가 없으면 원본 사용
                normalized[feature_name] = values
        
        logger.info(f"✅ Feature 정규화 완료 ({self.normalization_method}): "
                   f"{len(self.normalization_params)}개 정규화됨")
        return normalized
    
    def _normalize_with_group_normalizer(self, features: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        GroupNormalizer 방식으로 정규화 (LightweightScaler 사용)
        
        Args:
            features: 원본 features
            
        Returns:
            정규화된 features
        """
        if self.lightweight_scaler is None:
            logger.error("LightweightScaler가 초기화되지 않았습니다")
            return features
        
        normalized = {}
        group_id = "corn"  # 기본값, 필요시 파라미터로 전달
        
        for feature_name, values in features.items():
            # 정규화 제외 대상
            if feature_name in self.feature_config.NORMALIZATION_EXCLUDE:
                normalized[feature_name] = values
                continue
            
            # Target feature (close)는 GroupNormalizer 적용
            if feature_name == 'close':
                try:
                    values_array = np.array(values, dtype=np.float32)
                    normalized_array = self.lightweight_scaler.transform(
                        values_array, 
                        group_id=group_id
                    )
                    normalized[feature_name] = normalized_array.tolist()
                    logger.debug(f"   {feature_name}: GroupNormalizer 적용")
                except Exception as e:
                    logger.warning(f"   {feature_name}: GroupNormalizer 적용 실패 ({e}), 원본 사용")
                    normalized[feature_name] = values
            else:
                # 다른 features는 일반 정규화 (있는 경우)
                if feature_name in self.normalization_params:
                    params = self.normalization_params[feature_name]
                    mean_val = params['mean']
                    std_val = params['std']
                    
                    normalized_values = [
                        (val - mean_val) / std_val 
                        for val in values
                    ]
                    normalized[feature_name] = normalized_values
                else:
                    normalized[feature_name] = values
        
        logger.info(f"✅ Feature 정규화 완료 (GroupNormalizer + StandardScaler)")
        return normalized
    
    def _apply_feature_overrides(
        self, 
        features: Dict[str, List[float]], 
        overrides: Dict[str, float]
    ) -> Dict[str, List[float]]:
        """Feature override를 적용 (원본은 수정하지 않음)"""
        print(f"\n{'='*80}")
        print(f"🔧 Feature override 적용 시작: {overrides}")
        logger.info(f"🔧 Feature override 적용 시작: {overrides}")
        
        # 이미 deep copy된 features를 받지만, 명확성을 위해 다시 한 번 확인
        for key, value in overrides.items():
            if key in features:
                original_value = features[key][-1] if features[key] else 0.0
                original_length = len(features[key])
                
                # 🔥 중요: 새로운 리스트 생성 (모든 시점에 동일한 값 적용)
                features[key] = [value] * original_length
                
                msg = f"  ✓ {key}: {original_value:.2f} → {value:.2f} (변화: {value - original_value:.2f}, {original_length}일)"
                print(msg)
                logger.info(msg)
            else:
                msg = f"  ⚠️  {key}: features에 없음 (무시됨)"
                print(msg)
                logger.warning(msg)
        
        msg = f"🔧 Feature override 적용 완료: {len(overrides)}개 feature 변경됨"
        print(msg)
        print(f"{'='*80}\n")
        logger.info(msg)
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
        """
        Target scale 파라미터 생성
        
        정규화 파라미터를 사용하여 동적으로 계산
        - center: close의 평균값
        - scale: close의 표준편차
        """
        # 1순위: GroupNormalizer (LightweightScaler) 사용
        if self.lightweight_scaler and 'close' in features:
            close_values = np.array(features['close'])
            center = float(np.mean(close_values))
            scale = float(np.std(close_values))
            
            logger.debug(f"📊 Target scale: center={center:.2f}, scale={scale:.2f} (GroupNormalizer)")
            return np.array([[center, scale]], dtype=np.float32)
        
        # 2순위: StandardScaler 파라미터 사용
        if 'close' in self.normalization_params:
            params = self.normalization_params['close']
            center = params['mean']
            scale = params['std']
            
            logger.debug(f"📊 Target scale: center={center:.2f}, scale={scale:.2f} (StandardScaler)")
            return np.array([[center, scale]], dtype=np.float32)
        
        # 3순위: 동적 계산 (현재 데이터 기반)
        if 'close' in features:
            close_values = np.array(features['close'])
            center = float(np.mean(close_values))
            scale = float(np.std(close_values))
            
            logger.debug(f"📊 Target scale: center={center:.2f}, scale={scale:.2f} (동적 계산)")
            return np.array([[center, scale]], dtype=np.float32)
        
        # 4순위 fallback: 기본값 사용
        center = self.feature_config.DEFAULT_TARGET_CENTER
        scale = self.feature_config.DEFAULT_TARGET_SCALE
        
        logger.warning(f"⚠️ Target scale: 기본값 사용 (center={center}, scale={scale})")
        return np.array([[center, scale]], dtype=np.float32)
    
    def _parse_predictions(self, outputs: List[np.ndarray]) -> Dict[str, List[float]]:
        """
        ONNX 출력을 파싱하여 예측 결과 반환
        
        GroupNormalizer를 사용한 경우 역변환 적용
        """
        predictions = outputs[0]  # shape: [1, 7, 3]
        
        # 기본 예측값
        pred_median = predictions[0, :, 0]  # 중앙값
        pred_lower = predictions[0, :, 1]   # 하한
        pred_upper = predictions[0, :, 2]   # 상한
        
        logger.info(f"🔍 예측값 (역변환 전): median[0]={pred_median[0]:.4f}, method={self.normalization_method}")
        
        # GroupNormalizer 역변환
        if self.normalization_method == 'group_normalizer' and self.lightweight_scaler is not None:
            try:
                group_id = "corn"  # 기본값
                
                # 역변환 적용
                pred_median = self.lightweight_scaler.inverse_transform(pred_median, group_id=group_id)
                pred_lower = self.lightweight_scaler.inverse_transform(pred_lower, group_id=group_id)
                pred_upper = self.lightweight_scaler.inverse_transform(pred_upper, group_id=group_id)
                
                logger.info(f"✅ GroupNormalizer 역변환 완료: median[0]={pred_median[0]:.4f}")
            except Exception as e:
                logger.warning(f"GroupNormalizer 역변환 실패: {e}, 원본 사용")
        else:
            logger.warning(f"⚠️ 역변환 미적용: method={self.normalization_method}, scaler={'있음' if self.lightweight_scaler else '없음'}")
        
        # 🔥 중요: log1p 역변환 (데이터가 log1p로 변환되었으므로)
        # 배치 서버의 predict.py에서도 log1p 변환을 하므로, 역변환 필요
        pred_median = np.expm1(pred_median)
        pred_lower = np.expm1(pred_lower)
        pred_upper = np.expm1(pred_upper)
        
        logger.info(f"✅ Log1p 역변환 완료: median[0]=${pred_median[0]:.2f}")
        
        return {
            'predictions': pred_median.tolist() if hasattr(pred_median, 'tolist') else list(pred_median),
            'lower_bounds': pred_lower.tolist() if hasattr(pred_lower, 'tolist') else list(pred_lower),
            'upper_bounds': pred_upper.tolist() if hasattr(pred_upper, 'tolist') else list(pred_upper)
        }
    
    def _log_inference_info(self, model_inputs: Dict[str, np.ndarray]):
        """추론 정보 로깅"""
        logger.info("TFT 추론 실행")
        for name, array in model_inputs.items():
            logger.info(f"  {name}: {array.shape}")


def get_prediction_service() -> ONNXPredictionService:
    """예측 서비스 인스턴스 반환"""
    return ONNXPredictionService()
