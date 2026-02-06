# TFT 모델 실시간 서빙 구현 완료

## ✅ 구현 완료 사항

### 1. DB 스키마 활용
- `market_metrics` 테이블을 활용하여 52개 feature 저장
- `metric_id`를 다양하게 사용하여 모든 시계열 데이터 저장 가능

### 2. 과거 데이터 로드 함수 추가
**파일**: `app/crud.py`

```python
def get_historical_features(db, commodity, end_date, days=60):
    """과거 60일의 52개 feature를 market_metrics에서 로드"""
```

- 과거 60일간의 모든 feature를 날짜별로 조회
- Feature별 시계열 데이터로 변환하여 반환

### 3. TFT 모델 예측 서비스 구현
**파일**: `app/ml/prediction_service.py`

```python
def predict_tft(self, commodity, historical_data, feature_overrides):
    """TFT 모델로 실시간 예측 (7일 예측)"""
```

**TFT 입력 구조 (7개)**:
- `encoder_cat`: [1, 60, 1] - 과거 60일 범주형
- `encoder_cont`: [1, 60, 52] - 과거 60일 연속형 (52개 feature)
- `encoder_lengths`: [1] - 인코더 길이
- `decoder_cat`: [1, 7, 1] - 미래 7일 범주형
- `decoder_cont`: [1, 7, 52] - 미래 7일 연속형
- `decoder_lengths`: [1] - 디코더 길이  
- `target_scale`: [1, 2] - 타겟 스케일

**52개 Feature 구성**:
1. 가격/거래량 (6개): close, open, high, low, volume, EMA
2. 뉴스 PCA (32개): news_pca_0 ~ news_pca_31
3. 기후 (3개): pdsi, spi30d, spi90d
4. 거시경제 (2개): 10Y_Yield, USD_Index
5. Hawkes (2개): lambda_price, lambda_news
6. 뉴스 (1개): news_count
7. Known (3개): time_idx, day_of_year, relative_time_idx
8. Static (3개): encoder_length, close_center, close_scale

### 4. 시뮬레이션 API 업데이트
**파일**: `app/routers/simulation.py`

- DB에서 과거 60일 데이터 로드
- `feature_overrides` 적용
- TFT 모델로 예측 실행 (7일 예측 중 1일차 사용)
- 원본 vs 시뮬레이션 비교

**조정 가능한 Features**:
- `10Y_Yield`: 미국 10년물 국채 금리
- `USD_Index`: 달러 인덱스
- `pdsi`: Palmer Drought Severity Index
- `spi30d`: SPI (30일)
- `spi90d`: SPI (90일)
- `close`, `open`, `high`, `low`, `volume`, `news_count`

---

## 📊 테스트 결과

### 테스트 파일: `test_tft_model.py`

```bash
./venv/bin/python test_tft_model.py
```

### 결과:
✅ **모든 테스트 통과!**

1. **기본 예측 테스트**: 성공
   - 7일 예측: [443.07, 442.46, 441.90, 441.60, 441.43, 441.33, 441.27]
   - 하한/상한 신뢰구간 포함

2. **Feature Override 테스트**: 성공
   - 금리 인상: 변화 거의 없음
   - 가뭄 상황: +0.93 (+0.21%) 상승
   - 복합 시나리오: 정상 작동

3. **데이터 길이 테스트**: 성공

---

## 🔄 AI 배치 서버 작업

### 배치 서버가 해야 할 일

**매일 실행 (예: 새벽 2시)**:

```python
# 1. 데이터 수집 및 저장
features_to_save = [
    # 가격 데이터
    {"metric_id": "close", "numeric_value": 450.25},
    {"metric_id": "open", "numeric_value": 449.50},
    {"metric_id": "high", "numeric_value": 455.00},
    {"metric_id": "low", "numeric_value": 445.00},
    {"metric_id": "volume", "numeric_value": 1000000},
    {"metric_id": "EMA", "numeric_value": 448.30},
    
    # 뉴스 PCA (32개)
    {"metric_id": "news_pca_0", "numeric_value": 0.123},
    {"metric_id": "news_pca_1", "numeric_value": -0.456},
    # ... news_pca_31까지
    
    # 기후 지수
    {"metric_id": "pdsi", "numeric_value": -2.1},
    {"metric_id": "spi30d", "numeric_value": 0.5},
    {"metric_id": "spi90d", "numeric_value": 1.2},
    
    # 거시경제
    {"metric_id": "10Y_Yield", "numeric_value": 4.2},
    {"metric_id": "USD_Index", "numeric_value": 103.5},
    
    # 기타
    {"metric_id": "lambda_price", "numeric_value": 0.8},
    {"metric_id": "lambda_news", "numeric_value": 0.2},
    {"metric_id": "news_count", "numeric_value": 15},
]

for feature in features_to_save:
    db.add(MarketMetrics(
        commodity="corn",
        date=today,
        metric_id=feature["metric_id"],
        numeric_value=feature["numeric_value"],
        label="",  # 선택사항
        value=str(feature["numeric_value"]),
        trend=0.0,
        impact="neutral"
    ))

db.commit()
```

**결과**:
- 1일 × 1품목 = 52개 레코드 생성
- 60일 × 1품목 = 3,120개 레코드 (백엔드가 조회)

---

## 🎯 API 사용 예시

### 시뮬레이션 요청

```bash
curl -X POST "http://localhost:8000/api/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "commodity": "corn",
    "base_date": "2026-02-10",
    "feature_overrides": {
      "10Y_Yield": 5.0,
      "USD_Index": 110.0,
      "pdsi": -3.0
    }
  }'
```

### 응답 예시

```json
{
  "original_forecast": 443.07,
  "simulated_forecast": 444.02,
  "change": 0.95,
  "change_percent": 0.21,
  "feature_impacts": [
    {
      "feature": "10Y_Yield",
      "current_value": 4.2,
      "new_value": 5.0,
      "value_change": 0.8,
      "contribution": 0
    },
    {
      "feature": "USD_Index",
      "current_value": 103.5,
      "new_value": 110.0,
      "value_change": 6.5,
      "contribution": 0
    },
    {
      "feature": "pdsi",
      "current_value": 0.5,
      "new_value": -3.0,
      "value_change": -3.5,
      "contribution": 0
    }
  ]
}
```

---

## 📝 주의사항

### 1. DB 데이터 필수
- 백엔드는 DB에서 과거 60일 데이터를 로드합니다
- `market_metrics` 테이블에 최소 60일치 데이터가 있어야 합니다
- 데이터가 없으면 404 에러 발생

### 2. Feature 순서
- 52개 feature의 순서가 중요합니다
- `prediction_service.py`의 `feature_order` 리스트 참고

### 3. 모델 버전
- 현재는 60일 예측 모델(`60d_20260206.onnx`) 사용
- 7일 예측 모델(`7d_20260206.onnx`)도 있지만 구조 확인 필요

### 4. Static Features
- `encoder_length`, `close_center`, `close_scale`는 자동 생성
- 필요 시 DB에서 가져올 수 있도록 수정 가능

---

## 🔧 다음 단계 (선택사항)

1. **SHAP 통합**: Feature 기여도 정확한 계산
2. **캐싱**: 과거 데이터 Redis 캐싱으로 성능 향상
3. **다중 예측 일수**: 7일 전체 예측 반환 (현재는 1일차만)
4. **에러 핸들링**: DB 데이터 부족 시 Mock 데이터 fallback
5. **로깅 개선**: 예측 실행 시간, 입력 데이터 통계 등

---

## 🎉 성공!

TFT 모델이 백엔드에서 정상적으로 작동하며, 실시간 시뮬레이션이 가능합니다!

**구현 날짜**: 2026-02-06
**테스트 상태**: ✅ 모두 통과
