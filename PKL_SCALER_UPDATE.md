# PKL Scaler 사용으로 업데이트 완료

## 📋 문제 인식

이전 구현에서는 **매 추론마다 encoder 60일 데이터로 정규화 파라미터를 동적 계산**했습니다.

```python
# 이전: 동적 계산
encoder_values = features[feature_name][:60]  # 현재 입력의 60일
mean = np.mean(encoder_values)
std = np.std(encoder_values)
```

**문제점**:
- ❌ 학습 시 사용한 scaler와 다를 수 있음
- ❌ 입력 데이터마다 정규화 기준이 달라짐
- ❌ 예측 정확도 저하 가능성

---

## ✅ 해결 방법

### PKL 파일의 Scaler 우선 사용

학습 시 사용한 **동일한 정규화 파라미터**를 PKL 파일에서 로드하여 사용합니다.

```python
# 개선 후: PKL scaler 우선 사용
scaler = preprocessing_info['scaler']
mean = scaler.mean_   # 전체 학습 데이터의 평균
std = scaler.scale_   # 전체 학습 데이터의 표준편차
```

---

## 🔧 구현 내용

### 1. 우선순위 시스템

```python
def _load_or_compute_normalization_params(features):
    # 1순위: PKL 파일의 scaler 사용
    if _load_normalization_params_from_pkl():
        logger.info("✅ PKL 파일의 scaler 사용 (학습 시와 동일)")
        return
    
    # 2순위: 동적 계산 (fallback)
    logger.warning("⚠️ PKL scaler 로드 실패, encoder 데이터로 동적 계산")
    _compute_normalization_params(features)
```

### 2. PKL Scaler 로드 로직

```python
def _load_normalization_params_from_pkl():
    # 전처리 정보 가져오기
    preprocessing_info = self.model_loader.get_preprocessing_info()
    
    # Scaler 객체 찾기 (여러 가능한 키 확인)
    for key in ['scaler', 'feature_scaler', 'x_scaler', 'normalizer']:
        if key in preprocessing_info:
            scaler = preprocessing_info[key]
            break
    
    # StandardScaler 속성 확인
    if hasattr(scaler, 'mean_') and hasattr(scaler, 'scale_'):
        # Feature 이름 매핑
        if hasattr(scaler, 'feature_names_in_'):
            feature_names = scaler.feature_names_in_
        
        # 정규화 파라미터 생성
        for i, feature_name in enumerate(feature_names):
            params[feature_name] = {
                'mean': float(scaler.mean_[i]),
                'std': float(scaler.scale_[i])
            }
        
        return True
    
    return False
```

### 3. Feature 이름 매핑

**케이스 1: feature_names_in_ 있음**
```python
# Scaler에 저장된 feature 이름 사용
feature_names = scaler.feature_names_in_
for i, name in enumerate(feature_names):
    params[name] = {'mean': mean_[i], 'std': scale_[i]}
```

**케이스 2: feature_names 없음**
```python
# FEATURE_ORDER 순서로 매핑
for i, name in enumerate(FEATURE_ORDER):
    if name not in NORMALIZATION_EXCLUDE:
        params[name] = {'mean': mean_[idx], 'std': scale_[idx]}
        idx += 1
```

---

## 📊 비교

### 이전 (동적 계산)

| 항목 | 값 |
|------|-----|
| 데이터 소스 | 현재 입력의 encoder 60일 |
| 계산 시점 | 매 추론마다 |
| 일관성 | ❌ 입력마다 다름 |
| 학습 시 일치 | ❌ 다를 수 있음 |

**예시**:
```python
# 입력 A의 close 평균: 450.0
# 입력 B의 close 평균: 460.0  ← 다름!
```

### 개선 후 (PKL Scaler)

| 항목 | 값 |
|------|-----|
| 데이터 소스 | 전체 학습 데이터 |
| 계산 시점 | 학습 시 1회 |
| 일관성 | ✅ 항상 동일 |
| 학습 시 일치 | ✅ 완전 일치 |

**예시**:
```python
# 모든 입력에서 동일
# close 평균: 452.5 (학습 데이터 전체 평균)
# close 표준편차: 10.2 (학습 데이터 전체 표준편차)
```

---

## 🎯 기대 효과

### 1. 예측 정확도 향상
- ✅ 학습 시와 동일한 정규화 사용
- ✅ 데이터 분포 일관성 유지

### 2. 안정성 향상
- ✅ 입력 데이터 변화에 영향 없음
- ✅ 항상 동일한 정규화 기준

### 3. 신뢰성 향상
- ✅ 학습-추론 파이프라인 일치
- ✅ 재현 가능한 결과

---

## 🔍 로그 확인

### PKL Scaler 사용 시
```bash
✅ PKL 파일의 scaler 사용 (학습 시와 동일한 정규화)
✅ PKL scaler 로드 성공: 46개 feature
   예시: close = mean:452.50, std:10.20
```

### Fallback (동적 계산) 시
```bash
⚠️ PKL scaler 로드 실패, encoder 데이터로 동적 계산
📊 정규화 파라미터 동적 계산 완료: 46개 feature
   예시: close = mean:450.00, std:1.41
```

---

## ⚠️ 중요 사항

### PKL 파일 요구사항

PKL 파일에 다음 중 하나의 키로 StandardScaler가 저장되어 있어야 합니다:
- `scaler`
- `feature_scaler`
- `x_scaler`
- `normalizer`

StandardScaler 객체는 다음 속성을 가져야 합니다:
- `mean_`: 각 feature의 평균값 배열
- `scale_`: 각 feature의 표준편차 배열
- `feature_names_in_`: feature 이름 배열 (선택사항)

### Fallback 동작

PKL 로드가 실패하더라도 시스템은 정상 작동합니다:
1. PKL scaler 로드 시도
2. 실패 시 경고 로그 출력
3. Encoder 데이터로 동적 계산 (fallback)
4. 정상적으로 예측 수행

---

## 📁 변경된 파일

### 수정
- `app/ml/prediction_service.py`
  - `__init__()`: `pkl_scaler` 캐시 추가
  - `_load_or_compute_normalization_params()`: 신규 메서드
  - `_load_normalization_params_from_pkl()`: 신규 메서드
  - `_compute_normalization_params()`: fallback으로 변경

### 문서 업데이트
- `docs/NORMALIZATION_GUIDE.md`: PKL scaler 사용 설명 추가
- `PKL_SCALER_UPDATE.md`: 본 문서

---

## ✅ 체크리스트

- [x] PKL scaler 로드 로직 구현
- [x] Fallback 메커니즘 구현
- [x] Feature 이름 매핑 로직
- [x] 에러 처리 및 로깅
- [x] 문서 업데이트
- [x] Linter 통과

---

**작성일**: 2026-02-08  
**상태**: ✅ 완료
