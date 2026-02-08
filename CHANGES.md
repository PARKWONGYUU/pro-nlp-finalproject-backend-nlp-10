# 변경 사항 요약

## 2026-02-08: 데이터 정규화 개선

### 🎯 목적
TFT 모델의 예측 정확도와 안정성을 개선하기 위해 동적 데이터 정규화를 추가했습니다.

### 📝 주요 변경사항

#### 1. `app/ml/prediction_service.py` 개선

**추가된 기능**:
- ✅ 동적 정규화 파라미터 계산 (`_compute_normalization_params`)
- ✅ Z-score 정규화 적용 (`_normalize_features`)
- ✅ 동적 target_scale 계산 (`_get_target_scale` 개선)

**변경 내용**:
```python
# 이전: 하드코딩된 값
DEFAULT_TARGET_CENTER = 450.0
DEFAULT_TARGET_SCALE = 10.0

# 개선 후: 데이터 기반 동적 계산
center = normalization_params['close']['mean']  # 예: 452.0
scale = normalization_params['close']['std']    # 예: 1.41
```

#### 2. 정규화 방식
- **방법**: StandardScaler (Z-score normalization)
- **공식**: `(x - mean) / std`
- **적용**: 46개 features (가격, 뉴스, 기후, 경제 지표 등)
- **제외**: 6개 features (시간, static features)

#### 3. 처리 흐름
```
과거 데이터 로드 
  → Feature override 적용 
  → 정규화 파라미터 계산 (encoder 60일 기반)
  → 정규화 적용 
  → 모델 입력 생성 
  → 추론
```

### ✅ 검증 완료

- ✅ 정규화 파라미터 계산 정확성
- ✅ 정규화 적용 (mean≈0, std≈1)
- ✅ 역정규화 가능성
- ✅ Feature override 호환성
- ✅ Linter 통과

### 📚 추가 문서

1. **`docs/NORMALIZATION_GUIDE.md`**: 상세 가이드
2. **`NORMALIZATION_IMPROVEMENT_SUMMARY.md`**: 개선 보고서
3. **`test_normalization_pure.py`**: 검증 스크립트

### 🎁 기대 효과

- 📈 예측 정확도 개선
- 🔄 데이터 분포 변화 적응
- 🎯 Feature 간 스케일 통일
- 💪 학습 안정성 향상

---

**작성자**: AI Assistant  
**날짜**: 2026-02-08
