"""
경량 스케일러 유틸리티

pytorch-forecasting 없이 JSON 파라미터만으로 스케일링을 수행합니다.
서빙 환경에서 무거운 라이브러리 설치 없이 사용 가능합니다.

Usage:
    from src.utils.lightweight_scaler import LightweightScaler
    
    scaler = LightweightScaler.from_json("checkpoints/scaler_params.json")
    scaled_value = scaler.transform(raw_value, group_id="Corn")
    original_value = scaler.inverse_transform(scaled_value, group_id="Corn")
"""

import json
import numpy as np
from typing import Union, Optional, Dict, Any
from pathlib import Path


class LightweightScaler:
    """
    경량 스케일러: JSON 파라미터만으로 스케일링 수행
    
    pytorch-forecasting의 GroupNormalizer 동작을 재현하지만,
    무거운 라이브러리 의존성 없이 numpy만으로 구현
    """
    
    def __init__(self, scaler_params: Dict[str, Any]):
        """
        Args:
            scaler_params: extract_scaler_params.py로 추출한 JSON 파라미터
        """
        self.params = scaler_params
        self.transformation = scaler_params['metadata'].get('transformation', 'softplus')
        self.groups = scaler_params['metadata'].get('groups', [])
        self.target = scaler_params['metadata'].get('target', 'close')
        
        self.normalizer_params = scaler_params.get('normalizer_params', {})
        self.center = self.normalizer_params.get('center')
        self.scale = self.normalizer_params.get('scale')
        self.group_statistics = self.normalizer_params.get('group_statistics', {})
        
        print(f"✅ LightweightScaler initialized")
        print(f"   Transformation: {self.transformation}")
        print(f"   Groups: {self.groups}")
        print(f"   Target: {self.target}")
    
    @classmethod
    def from_json(cls, json_path: str) -> 'LightweightScaler':
        """
        JSON 파일에서 스케일러 로드
        
        Args:
            json_path: scaler_params.json 파일 경로
            
        Returns:
            LightweightScaler 인스턴스
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            scaler_params = json.load(f)
        
        return cls(scaler_params)
    
    def softplus(self, x: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Softplus 변환: log(1 + exp(x))
        
        pytorch-forecasting의 GroupNormalizer에서 사용하는 변환
        """
        x = np.asarray(x)
        # 수치 안정성을 위해 큰 값은 linear approximation
        return np.where(x > 20, x, np.log1p(np.exp(x)))
    
    def inverse_softplus(self, y: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Softplus 역변환: log(exp(y) - 1)
        """
        y = np.asarray(y)
        # 수치 안정성
        return np.where(y > 20, y, np.log(np.expm1(y)))
    
    def transform(
        self, 
        value: Union[float, np.ndarray], 
        group_id: Optional[str] = None,
        use_center: bool = True,
        use_scale: bool = True
    ) -> Union[float, np.ndarray]:
        """
        원본 값을 스케일링된 값으로 변환
        
        Args:
            value: 원본 값
            group_id: 그룹 ID (GroupNormalizer 사용 시)
            use_center: 중심화 적용 여부
            use_scale: 스케일링 적용 여부
            
        Returns:
            스케일링된 값
        """
        value = np.asarray(value)
        
        # 1. Transformation 적용 (softplus 등)
        if self.transformation == 'softplus':
            value = self.softplus(value)
        elif self.transformation == 'log':
            value = np.log1p(value)
        elif self.transformation == 'log1p':
            value = np.log1p(value)
        # 'none'이나 None인 경우 변환 없음
        
        # 2. 정규화 (center & scale)
        if self.center is not None and use_center:
            if isinstance(self.center, (list, np.ndarray)) and len(self.center) > 0:
                center_val = self.center[0] if len(self.center) == 1 else self.center
                value = value - center_val
        
        if self.scale is not None and use_scale:
            if isinstance(self.scale, (list, np.ndarray)) and len(self.scale) > 0:
                scale_val = self.scale[0] if len(self.scale) == 1 else self.scale
                # 0으로 나누기 방지
                scale_val = np.where(np.abs(scale_val) < 1e-8, 1.0, scale_val)
                value = value / scale_val
        
        # 3. 그룹별 통계 적용 (있는 경우)
        if group_id and self.group_statistics:
            group_key = str(group_id)
            if group_key in self.group_statistics:
                group_stats = self.group_statistics[group_key]
                if 'mean' in group_stats:
                    value = value - group_stats['mean']
                if 'std' in group_stats:
                    std_val = group_stats['std']
                    std_val = std_val if abs(std_val) > 1e-8 else 1.0
                    value = value / std_val
        
        return value if isinstance(value, np.ndarray) else float(value)
    
    def inverse_transform(
        self,
        scaled_value: Union[float, np.ndarray],
        group_id: Optional[str] = None,
        use_center: bool = True,
        use_scale: bool = True
    ) -> Union[float, np.ndarray]:
        """
        스케일링된 값을 원본 값으로 역변환
        
        Args:
            scaled_value: 스케일링된 값
            group_id: 그룹 ID
            use_center: 중심화 역변환 여부
            use_scale: 스케일 역변환 여부
            
        Returns:
            원본 값
        """
        value = np.asarray(scaled_value)
        
        # 1. 그룹별 통계 역변환 (있는 경우)
        if group_id and self.group_statistics:
            group_key = str(group_id)
            if group_key in self.group_statistics:
                group_stats = self.group_statistics[group_key]
                if 'std' in group_stats:
                    value = value * group_stats['std']
                if 'mean' in group_stats:
                    value = value + group_stats['mean']
        
        # 2. 정규화 역변환 (scale & center)
        if self.scale is not None and use_scale:
            if isinstance(self.scale, (list, np.ndarray)) and len(self.scale) > 0:
                scale_val = self.scale[0] if len(self.scale) == 1 else self.scale
                value = value * scale_val
        
        if self.center is not None and use_center:
            if isinstance(self.center, (list, np.ndarray)) and len(self.center) > 0:
                center_val = self.center[0] if len(self.center) == 1 else self.center
                value = value + center_val
        
        # 3. Transformation 역변환
        if self.transformation == 'softplus':
            value = self.inverse_softplus(value)
        elif self.transformation in ['log', 'log1p']:
            value = np.expm1(value)
        
        return value if isinstance(value, np.ndarray) else float(value)
    
    def get_config(self) -> Dict[str, Any]:
        """
        스케일러 설정 정보 반환
        """
        return {
            'transformation': self.transformation,
            'groups': self.groups,
            'target': self.target,
            'has_center': self.center is not None,
            'has_scale': self.scale is not None,
            'num_groups': len(self.group_statistics),
            'feature_columns': self.params.get('feature_columns', {}),
            'dataset_config': self.params.get('dataset_config', {})
        }
    
    def summary(self):
        """
        스케일러 정보 출력
        """
        print("\n" + "=" * 60)
        print("📊 LightweightScaler Summary")
        print("=" * 60)
        
        config = self.get_config()
        print(f"Target: {config['target']}")
        print(f"Transformation: {config['transformation']}")
        print(f"Groups: {config['groups']}")
        print(f"Center: {'✓' if config['has_center'] else '✗'}")
        print(f"Scale: {'✓' if config['has_scale'] else '✗'}")
        print(f"Group Statistics: {config['num_groups']} groups")
        
        dataset_config = config.get('dataset_config', {})
        print(f"\nDataset Configuration:")
        print(f"  Max Encoder Length: {dataset_config.get('max_encoder_length')}")
        print(f"  Max Prediction Length: {dataset_config.get('max_prediction_length')}")
        
        feature_cols = config.get('feature_columns', {})
        print(f"\nFeature Columns:")
        print(f"  Time-varying Known Reals: {len(feature_cols.get('time_varying_known_reals', []))}")
        print(f"  Time-varying Unknown Reals: {len(feature_cols.get('time_varying_unknown_reals', []))}")
        print(f"  Static Categoricals: {len(feature_cols.get('static_categoricals', []))}")
        
        print("=" * 60 + "\n")


def example_usage():
    """
    사용 예시
    """
    print("=" * 60)
    print("🔧 LightweightScaler Usage Example")
    print("=" * 60 + "\n")
    
    # 1. JSON에서 로드
    json_path = "checkpoints/scaler_params.json"
    
    if not Path(json_path).exists():
        print(f"⚠️  Example file not found: {json_path}")
        print("   Please run extract_scaler_params.py first:")
        print("   python scripts/ops/extract_scaler_params.py --input checkpoints/enhanced_tft_v1_preprocessing.pkl --output checkpoints/scaler_params.json")
        return
    
    scaler = LightweightScaler.from_json(json_path)
    scaler.summary()
    
    # 2. 스케일링 테스트
    print("🧪 Transform Test:")
    raw_price = 450.5
    print(f"   Raw Price: {raw_price}")
    
    scaled = scaler.transform(raw_price, group_id="Corn")
    print(f"   Scaled: {scaled:.6f}")
    
    inverse = scaler.inverse_transform(scaled, group_id="Corn")
    print(f"   Inverse: {inverse:.6f}")
    
    error = abs(raw_price - inverse)
    print(f"   Reconstruction Error: {error:.8f}")
    
    if error < 1e-6:
        print("   ✅ Perfect reconstruction!")
    else:
        print("   ⚠️  Some numerical error (expected with transformations)")
    
    # 3. 배치 처리 테스트
    print("\n🧪 Batch Transform Test:")
    raw_prices = np.array([450.5, 455.0, 460.2, 448.3, 452.1])
    print(f"   Raw Prices: {raw_prices}")
    
    scaled_batch = scaler.transform(raw_prices, group_id="Corn")
    print(f"   Scaled: {scaled_batch}")
    
    inverse_batch = scaler.inverse_transform(scaled_batch, group_id="Corn")
    print(f"   Inverse: {inverse_batch}")
    
    batch_error = np.max(np.abs(raw_prices - inverse_batch))
    print(f"   Max Reconstruction Error: {batch_error:.8f}")
    

if __name__ == "__main__":
    example_usage()
