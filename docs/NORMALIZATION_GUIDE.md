# 데이터 정규화 가이드

## 📊 개요

TFT 모델의 예측 정확도를 높이기 위해 입력 데이터에 대한 정규화(Normalization)를 적용합니다.

## 🔧 구현 방식

### 정규화 우선순위

**1순위: GroupNormalizer** (pytorch-forecasting)
- Softplus transformation + Group normalization
- LightweightScaler 사용
- Target feature (close)에 적용

**2순위: StandardScaler** (sklearn)
- Z-score normalization
- PKL 파일에서 로드
- 모든 features에 적용

**3순위: Dynamic** (fallback)
- Encoder 데이터 기반 Z-score
- PKL 로드 실패 시 사용

### 1. Z-Score Normalization (StandardScaler)

각 feature에 대해 다음 공식을 적용합니다:

```
normalized_value = (value - mean) / std
```

여기서:
- `mean`: 해당 feature의 평균값
- `std`: 해당 feature의 표준편차

### 2. 정규화 파라미터 소스

**우선순위 1: PKL 파일의 Scaler (권장)**

학습 시 사용한 동일한 정규화 파라미터를 사용합니다:

```python
# PKL 파일에서 로드
scaler = preprocessing_info['scaler']  # 또는 'feature_scaler', 'x_scaler'
mean = scaler.mean_   # 전체 학습 데이터의 평균
std = scaler.scale_   # 전체 학습 데이터의 표준편차
```

**우선순위 2: 동적 계산 (Fallback)**

PKL 로드 실패 시, Encoder 구간(과거 60일)으로 동적 계산:

```python
# app/ml/prediction_service.py의 _compute_normalization_params()
encoder_values = features[feature_name][:60]  # 과거 60일
mean_val = np.mean(encoder_values)
std_val = np.std(encoder_values)
```

### 3. 로드 프로세스

```python
def _load_or_compute_normalization_params(features):
    # 1. PKL 파일에서 scaler 로드 시도
    if _load_normalization_params_from_pkl():
        logger.info("✅ PKL 파일의 scaler 사용 (학습 시와 동일)")
        return
    
    # 2. 로드 실패 시 동적 계산
    logger.warning("⚠️ PKL scaler 로드 실패, encoder 데이터로 동적 계산")
    _compute_normalization_params(features)
```

### 3. 적용 대상

**정규화 적용**:
- 가격 관련: `close`, `open`, `high`, `low`, `volume`, `EMA`
- 뉴스 PCA: `news_pca_0` ~ `news_pca_31` (32개)
- 기후 지수: `pdsi`, `spi30d`, `spi90d`
- 거시경제: `10Y_Yield`, `USD_Index`
- Hawkes Intensity: `lambda_price`, `lambda_news`
- 뉴스 개수: `news_count`

**정규화 제외**:
- 시간 관련: `time_idx`, `day_of_year`, `relative_time_idx`
- Static features: `encoder_length`, `close_center`, `close_scale`

## 📝 주요 함수

### `_load_or_compute_normalization_params(features)`

정규화 파라미터를 로드하거나 계산합니다.

1. PKL 파일의 scaler 로드 시도
2. 실패 시 encoder 데이터로 동적 계산

### `_load_normalization_params_from_pkl()`

PKL 파일에서 StandardScaler를 로드합니다.

```python
# 지원하는 PKL 키
- 'scaler'
- 'feature_scaler'
- 'x_scaler'
- 'normalizer'

# 필수 속성
- scaler.mean_: 각 feature의 평균값 배열
- scaler.scale_: 각 feature의 표준편차 배열
- scaler.feature_names_in_: feature 이름 배열 (선택)
```

### `_compute_normalization_params(features)`

Encoder 데이터(과거 60일)를 기반으로 각 feature의 mean과 std를 계산합니다 (Fallback).

```python
# 예시 출력
{
    'close': {'mean': 452.00, 'std': 1.41},
    '10Y_Yield': {'mean': 4.58, 'std': 0.07},
    'USD_Index': {'mean': 105.40, 'std': 0.37},
    ...
}
```

### `_normalize_features(features)`

계산된 파라미터를 사용하여 모든 feature 값을 정규화합니다.

```python
# 정규화 적용
normalized_value = (value - mean) / std

# 예시: close = 450.0
# mean = 452.0, std = 1.41
# normalized = (450.0 - 452.0) / 1.41 = -1.42
```

### `_get_target_scale(features)`

Target scale 파라미터를 동적으로 계산합니다.

```python
# close feature의 정규화 파라미터 사용
center = normalization_params['close']['mean']  # 452.0
scale = normalization_params['close']['std']    # 1.41

return np.array([[center, scale]], dtype=np.float32)
```

## 🔄 처리 흐름

```
1. 과거 데이터 로드 (60일)
   ↓
2. Feature override 적용 (선택사항)
   ↓
3. 정규화 파라미터 계산 (encoder 60일 기반)
   ↓
4. Feature 정규화 적용 (Z-score)
   ↓
5. Encoder/Decoder 입력 생성
   ↓
6. ONNX 모델 추론
   ↓
7. 예측 결과 반환 (이미 역정규화된 가격)
```

## 🎯 Feature Override와 정규화

Feature override 시에도 정규화가 올바르게 적용됩니다:

```python
# 1. Override 적용
features['10Y_Yield'] = [5.0] * 60  # 모든 시점에 5.0 적용

# 2. 정규화 파라미터 계산 (override된 값 기반)
mean = 5.0  # 모든 값이 5.0이므로
std = 0.0 → 1.0  # 0이면 1.0으로 대체

# 3. 정규화 적용
normalized = (5.0 - 5.0) / 1.0 = 0.0
```

## ✅ 검증 결과

`test_normalization_pure.py` 실행 결과:

```
✅ 정규화 파라미터 계산: 성공
✅ Z-score 정규화 적용: 성공 (mean≈0, std≈1)
✅ 역정규화 검증: 성공
✅ Feature override 정규화: 성공
✅ Target scale 계산: 성공
```

## 🆚 이전 vs 개선 후

### 이전 (정규화 없음)

```python
# 하드코딩된 고정값 사용
DEFAULT_TARGET_CENTER = 450.0
DEFAULT_TARGET_SCALE = 10.0

# Feature 값을 raw 상태로 사용
feature_value = features['close'][i]  # 예: 452.0
```

**문제점**:
- 데이터 범위가 다른 경우 모델 성능 저하
- 학습 시와 추론 시 데이터 분포 불일치
- Feature 간 스케일 차이로 인한 학습 불균형

### 개선 후 (PKL Scaler 사용)

```python
# 1순위: PKL 파일의 scaler 사용 (학습 시와 동일)
scaler = preprocessing_info['scaler']
mean = scaler.mean_[feature_idx]   # 전체 학습 데이터의 평균
std = scaler.scale_[feature_idx]   # 전체 학습 데이터의 표준편차

# 2순위: 동적 계산 (fallback)
mean = np.mean(encoder_values)
std = np.std(encoder_values)

# 정규화 적용
normalized_value = (value - mean) / std
```

**장점**:
- ✅ **학습 시와 동일한 정규화** (PKL scaler 사용)
- ✅ Feature 간 스케일 통일 (mean≈0, std≈1)
- ✅ 모델 학습 안정성 향상
- ✅ 예측 정확도 개선
- ✅ PKL 로드 실패 시 자동 fallback

## 📚 참고

- **StandardScaler**: Scikit-learn의 표준 정규화 방식
- **Z-score**: 통계학에서 널리 사용되는 정규화 기법
- **Rolling Window**: 매 예측마다 최근 60일 데이터로 정규화 파라미터 재계산

## 🔍 디버깅

정규화 관련 로그 확인:

```bash
# PKL scaler 로드 성공
✅ PKL 파일의 scaler 사용 (학습 시와 동일한 정규화)
✅ PKL scaler 로드 성공: 46개 feature
   예시: close = mean:452.00, std:1.41

# 또는 동적 계산 (fallback)
⚠️ PKL scaler 로드 실패, encoder 데이터로 동적 계산
📊 정규화 파라미터 동적 계산 완료: 46개 feature
   예시: close = mean:452.00, std:1.41

# Feature 정규화 적용
✅ Feature 정규화 완료: 46개 정규화됨

# Target scale
📊 Target scale: center=452.00, scale=1.41 (데이터 기반)
```

## ⚠️ 주의사항

1. **PKL Scaler 우선**: 가능하면 항상 PKL 파일의 scaler를 사용 (학습 시와 동일)
2. **std = 0인 경우**: 자동으로 1.0으로 대체하여 division by zero 방지
3. **정규화 제외 feature**: 시간 관련 및 static feature는 정규화하지 않음
4. **Feature 이름 매핑**: PKL에 feature_names가 없으면 FEATURE_ORDER 순서로 매핑
5. **동적 계산 fallback**: PKL 로드 실패 시에만 encoder 데이터로 계산

## 🚀 성능 영향

- **계산 오버헤드**: 미미함 (60개 값의 mean/std 계산)
- **메모리 사용**: 증가 없음 (캐시에 파라미터만 저장)
- **예측 정확도**: 개선 예상 (데이터 분포 정규화)
