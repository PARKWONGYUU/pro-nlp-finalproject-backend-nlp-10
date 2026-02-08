# 배치 서버용 API 가이드

**Base URL**: `http://44.252.76.158:8000`

배치 서버(AI 서버)가 DB에 데이터를 저장/수정/삭제할 때 사용하는 Write API입니다.

---

## 기본 정보

| 항목 | 값 |
|------|-----|
| **Base URL** | `http://44.252.76.158:8000` |
| **Content-Type** | `application/json` |
| **날짜 형식** | `YYYY-MM-DD` |
| **Timestamp 형식** | ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) |
| **commodity** | `corn` (소문자 고정) |

---

## 공통 응답

### BatchResult (벌크/삭제 작업)

```json
{
  "success": true,
  "message": "3건 저장 완료",
  "count": 3
}
```

### 에러 응답

```json
{
  "detail": "에러 메시지"
}
```

---

## 엔드포인트 요약

| 메서드 | 경로 | 설명 | 응답 타입 |
|--------|------|------|-----------|
| POST | /api/predictions | 예측 단건 저장 | TftPredResponse |
| POST | /api/predictions/bulk | 예측 벌크 저장 | BatchResult |
| DELETE | /api/predictions | 예측 삭제 | BatchResult |
| POST | /api/explanations | 설명 저장 | ExpPredResponse |
| DELETE | /api/explanations/{pred_id} | 설명 삭제 | BatchResult |
| POST | /api/newsdb | 뉴스 단건 저장 | NewsResponse |
| POST | /api/newsdb/bulk | 뉴스 벌크 저장 | BatchResult |
| DELETE | /api/newsdb | 뉴스 삭제 | BatchResult |
| POST | /api/daily-summary | 일일 요약 저장 | DailySummaryResponse |
| DELETE | /api/daily-summary | 일일 요약 삭제 | BatchResult |
| POST | /api/market-metrics | 시장 지표 저장 | BatchResult |
| PUT | /api/market-metrics | 시장 지표 Upsert | BatchResult |
| DELETE | /api/market-metrics | 시장 지표 삭제 | BatchResult |
| POST | /api/historical-prices | 실제 가격 저장 | BatchResult |
| PUT | /api/historical-prices | 실제 가격 Upsert | BatchResult |
| DELETE | /api/historical-prices | 실제 가격 삭제 | BatchResult |

---

## 1. 예측 (Predictions)

DB 테이블: `tft_pred`

### POST /api/predictions

예측 단건 저장. 저장된 레코드를 반환합니다.

**Request Body:**

```json
{
  "target_date": "2026-02-07",
  "commodity": "corn",
  "price_pred": 450.50,
  "conf_lower": 445.20,
  "conf_upper": 455.80,
  "top1_factor": "close",
  "top1_impact": 0.25,
  "top2_factor": "USD_Index",
  "top2_impact": 0.18,
  "top3_factor": "10Y_Yield",
  "top3_impact": 0.15,
  "top4_factor": "volume",
  "top4_impact": 0.12,
  "top5_factor": "news_pca_0",
  "top5_impact": 0.10,
  "model_type": "TFT_v2"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| target_date | string | ✅ | 예측 대상 날짜 (YYYY-MM-DD) |
| commodity | string | ✅ | 품목명 |
| price_pred | float | ✅ | 예측 가격 |
| conf_lower | float | ✅ | 신뢰구간 하한 |
| conf_upper | float | ✅ | 신뢰구간 상한 |
| top1_factor ~ top20_factor | string | ❌ | 영향도 순위별 factor 이름 |
| top1_impact ~ top20_impact | float | ❌ | 영향도 순위별 impact 값 |
| model_type | string | ✅ | 모델 이름 (예: "TFT_v2") |

**Response:** 저장된 레코드 (id, created_at 포함)

```json
{
  "id": 1,
  "target_date": "2026-02-07",
  "commodity": "corn",
  "price_pred": 450.50,
  "conf_lower": 445.20,
  "conf_upper": 455.80,
  "top1_factor": "close",
  "top1_impact": 0.25,
  "model_type": "TFT_v2",
  "created_at": "2026-02-06T12:00:00"
}
```

---

### POST /api/predictions/bulk

예측 벌크 저장. 7일치 예측을 한 번에 저장할 때 사용합니다.

**Request Body:**

```json
{
  "predictions": [
    {
      "target_date": "2026-02-07",
      "commodity": "corn",
      "price_pred": 450.50,
      "conf_lower": 445.20,
      "conf_upper": 455.80,
      "top1_factor": "close",
      "top1_impact": 0.25,
      "model_type": "TFT_v2"
    },
    {
      "target_date": "2026-02-08",
      "commodity": "corn",
      "price_pred": 451.00,
      "conf_lower": 445.80,
      "conf_upper": 456.20,
      "top1_factor": "close",
      "top1_impact": 0.23,
      "model_type": "TFT_v2"
    }
  ]
}
```

**Response:** BatchResult

---

### DELETE /api/predictions

commodity + date 범위 기준으로 예측을 삭제합니다.

**Request Body:**

```json
{
  "commodity": "corn",
  "start_date": "2026-02-01",
  "end_date": "2026-02-07"
}
```

**Response:** BatchResult

---

## 2. 설명 (Explanations)

DB 테이블: `exp_pred` (FK: `tft_pred.id`)

### POST /api/explanations

예측 설명 저장. 반드시 해당 `pred_id`의 예측 레코드가 먼저 존재해야 합니다.

**Request Body:**

```json
{
  "pred_id": 1,
  "content": "이번 옥수수 선물 가격 전망은 342.03으로 설정되었으며, 변동 범위는 335.12에서 350.15로 예상됩니다. 핵심적으로, 최근 시장에서의 고가가 저항선 역할을 하며 가격 형성에 중요한 영향을 미치고 있습니다...",
  "llm_model": "gpt-4",
  "impact_news": [
    {
      "title": "[2026-02-02] A 3-step Grain Marketing Plan to Help Manage Risk in 2026 - Successful Farming",
      "impact": 0.2119,
      "rank": 3
    }
  ],
  "top_factors": [
    {
      "name": "예측 경과 시점",
      "category": "시장 구조 (Market Structure)",
      "impact": 0.6993,
      "ratio": 0.3497
    },
    {
      "name": "고가",
      "category": "기술적 지표 (Technical Indicators)",
      "impact": 0.4233,
      "ratio": 0.2117
    }
  ],
  "category_summary": [
    {
      "category": "시장 구조 (Market Structure)",
      "impact_sum": 1.0267,
      "ratio": 0.5134
    },
    {
      "category": "기술적 지표 (Technical Indicators)",
      "impact_sum": 0.6938,
      "ratio": 0.3469
    }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| pred_id | int | ✅ | tft_pred 테이블의 id (FK) |
| content | string | ✅ | Executive Summary (LLM이 생성한 요약문) |
| llm_model | string | ❌ | 사용된 LLM 모델명 (예: "gpt-4") |
| impact_news | array | ❌ | 영향력 있는 뉴스 목록 |
| impact_news[].title | string | ✅ | 뉴스 제목 (날짜 포함) |
| impact_news[].impact | float | ✅ | 영향도 (0~1) |
| impact_news[].rank | int | ✅ | 순위 |
| top_factors | array | ❌ | 상위 영향 요인 및 비율 |
| top_factors[].name | string | ✅ | 요인명 |
| top_factors[].category | string | ✅ | 카테고리 |
| top_factors[].impact | float | ✅ | 영향도 |
| top_factors[].ratio | float | ✅ | 비율 |
| category_summary | array | ❌ | 카테고리별 영향도 요약 |
| category_summary[].category | string | ✅ | 카테고리명 |
| category_summary[].impact_sum | float | ✅ | 카테고리별 총 영향도 |
| category_summary[].ratio | float | ✅ | 전체 대비 비율 |

**Response:** 저장된 레코드 (id, created_at 포함)

---

### DELETE /api/explanations/{pred_id}

특정 예측(pred_id)에 연결된 설명을 삭제합니다.

**Path Parameters:**

| 이름 | 타입 | 설명 |
|------|------|------|
| pred_id | int | tft_pred 테이블의 id |

**Response:** BatchResult

---

## 3. 뉴스 (News)

DB 테이블: `doc_embeddings`

### POST /api/newsdb

뉴스 단건 저장. embedding 벡터(1536차원)를 함께 저장합니다.

**Request Body:**

```json
{
  "title": "중국, 옥수수 수입량 증가 전망",
  "content": "중국의 축산업 성장으로 옥수수 수요가 증가하고 있습니다...",
  "source_url": "https://reuters.com/article/...",
  "created_at": "2026-02-06T10:30:00",
  "embedding": [0.012, -0.034, 0.056, ...]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | ✅ | 뉴스 제목 |
| content | string | ✅ | 뉴스 본문 |
| source_url | string | ❌ | 원문 URL |
| created_at | string | ✅ | 뉴스 수집 시각 (ISO 8601) |
| embedding | float[] | ✅ | 임베딩 벡터 (1536차원) |

**Response:** 저장된 레코드 (id 포함, embedding 제외)

---

### POST /api/newsdb/bulk

뉴스 벌크 저장.

**Request Body:**

```json
{
  "news_list": [
    {
      "title": "뉴스 제목 1",
      "content": "뉴스 본문 1...",
      "source_url": "https://...",
      "created_at": "2026-02-06T10:30:00",
      "embedding": [0.012, -0.034, ...]
    },
    {
      "title": "뉴스 제목 2",
      "content": "뉴스 본문 2...",
      "source_url": "https://...",
      "created_at": "2026-02-06T11:00:00",
      "embedding": [0.023, -0.045, ...]
    }
  ]
}
```

**Response:** BatchResult

---

### DELETE /api/newsdb

특정 날짜 **이전**의 모든 뉴스를 삭제합니다.

**Request Body:**

```json
{
  "commodity": "corn",
  "date": "2026-01-01"
}
```

> `date`(2026-01-01) 이전에 생성된 뉴스가 모두 삭제됩니다.

**Response:** BatchResult

---

## 4. 일일 요약 (Daily Summary)

DB 테이블: `daily_summary`

### POST /api/daily-summary

일일 요약 저장.

**Request Body:**

```json
{
  "target_date": "2026-02-06",
  "commodity": "corn",
  "score": 0.7523,
  "related_news_ids": [1, 5, 12, 23]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| target_date | string | ✅ | 요약 대상 날짜 |
| commodity | string | ✅ | 품목명 |
| score | float | ✅ | 일일 점수 (0~1) |
| related_news_ids | int[] | ✅ | 관련 뉴스 id 배열 (doc_embeddings.id) |

**Response:** 저장된 레코드 (id, created_at 포함)

```json
{
  "id": 1,
  "target_date": "2026-02-06",
  "commodity": "corn",
  "score": 0.7523,
  "related_news_ids": [1, 5, 12, 23],
  "created_at": "2026-02-06T12:00:00"
}
```

---

### DELETE /api/daily-summary

commodity + date 범위 기준으로 일일 요약을 삭제합니다.

**Request Body:**

```json
{
  "commodity": "corn",
  "start_date": "2026-02-01",
  "end_date": "2026-02-07"
}
```

**Response:** BatchResult

---

## 5. 시장 지표 (Market Metrics)

DB 테이블: `market_metrics`

TFT 모델의 입력 feature들을 날짜별로 저장합니다. 하루에 46개의 feature를 `metric_id`로 구분하여 저장합니다.

### metric_id 목록 (46개)

| 카테고리 | metric_id | 개수 |
|----------|-----------|------|
| 가격/거래량 | `close`, `open`, `high`, `low`, `volume`, `EMA` | 6 |
| 뉴스 PCA | `news_pca_0` ~ `news_pca_31` | 32 |
| 기후 지수 | `pdsi`, `spi30d`, `spi90d` | 3 |
| 거시경제 | `10Y_Yield`, `USD_Index` | 2 |
| Hawkes Intensity | `lambda_price`, `lambda_news` | 2 |
| 기타 | `news_count` | 1 |

---

### POST /api/market-metrics

시장 지표 벌크 저장 (하루치 전체 feature 저장).

**Request Body:**

```json
{
  "commodity": "corn",
  "date": "2026-02-06",
  "metrics": [
    {
      "metric_id": "close",
      "label": "종가",
      "value": "450.5",
      "numeric_value": 450.5,
      "trend": 0.5,
      "impact": "positive"
    },
    {
      "metric_id": "open",
      "label": "시가",
      "value": "448.0",
      "numeric_value": 448.0,
      "trend": 0.3,
      "impact": "neutral"
    },
    {
      "metric_id": "10Y_Yield",
      "label": "미국 10년물 국채 금리",
      "value": "4.2%",
      "numeric_value": 4.2,
      "trend": 0.1,
      "impact": "neutral"
    },
    {
      "metric_id": "pdsi",
      "label": "Palmer Drought Severity Index",
      "value": "-1.0",
      "numeric_value": -1.0,
      "trend": -0.2,
      "impact": "negative"
    }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| commodity | string | ✅ | 품목명 |
| date | string | ✅ | 날짜 (YYYY-MM-DD) |
| metrics | array | ✅ | 지표 배열 |
| metrics[].metric_id | string | ✅ | 지표 식별자 (위 표 참고) |
| metrics[].label | string | ✅ | 지표 라벨 (한글명) |
| metrics[].value | string | ✅ | 표시용 값 (단위 포함) |
| metrics[].numeric_value | float | ✅ | 수치 값 (모델 입력용) |
| metrics[].trend | float | ✅ | 전일 대비 변화량 |
| metrics[].impact | string | ✅ | 영향 방향 (`positive` / `negative` / `neutral`) |

**Response:** BatchResult

---

### PUT /api/market-metrics

시장 지표 Upsert. `commodity + date + metric_id` 기준으로 이미 존재하면 Update, 없으면 Insert합니다.

**Request Body:** POST와 동일

**Response:** BatchResult

> 매일 배치 작업에서 기존 데이터 유무와 관계없이 안전하게 호출할 수 있습니다.

---

### DELETE /api/market-metrics

commodity + date 범위 기준으로 시장 지표를 삭제합니다.

**Request Body:**

```json
{
  "commodity": "corn",
  "start_date": "2026-02-01",
  "end_date": "2026-02-07"
}
```

**Response:** BatchResult

---

## 6. 실제 가격 (Historical Prices)

DB 테이블: `historical_prices`

### POST /api/historical-prices

실제 가격 벌크 저장.

**Request Body:**

```json
{
  "commodity": "corn",
  "prices": [
    {
      "date": "2026-02-05",
      "actual_price": 448.25
    },
    {
      "date": "2026-02-06",
      "actual_price": 450.50
    }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| commodity | string | ✅ | 품목명 |
| prices | array | ✅ | 가격 배열 |
| prices[].date | string | ✅ | 날짜 (YYYY-MM-DD) |
| prices[].actual_price | float | ✅ | 실제 거래 가격 |

**Response:** BatchResult

---

### PUT /api/historical-prices

실제 가격 Upsert. `commodity + date` 기준으로 이미 존재하면 Update, 없으면 Insert합니다.

**Request Body:** POST와 동일

**Response:** BatchResult

---

### DELETE /api/historical-prices

commodity + date 범위 기준으로 실제 가격을 삭제합니다.

**Request Body:**

```json
{
  "commodity": "corn",
  "start_date": "2026-02-01",
  "end_date": "2026-02-07"
}
```

**Response:** BatchResult

---

## DB 스키마 참조

### tft_pred

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | serial (PK) | 자동 생성 |
| target_date | date | 예측 대상 날짜 |
| commodity | varchar(50) | 품목명 |
| price_pred | numeric(10,2) | 예측 가격 |
| conf_lower | numeric(10,2) | 신뢰구간 하한 |
| conf_upper | numeric(10,2) | 신뢰구간 상한 |
| top1_factor ~ top20_factor | varchar(255) | 영향 factor 이름 |
| top1_impact ~ top20_impact | float | 영향 impact 값 |
| model_type | varchar(255) | 모델명 |
| created_at | timestamp | 자동 생성 |

### exp_pred

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | serial (PK) | 자동 생성 |
| pred_id | int (FK) | tft_pred.id |
| content | text | 설명 내용 |
| llm_model | varchar(50) | LLM 모델명 |
| impact_news | json | 영향 뉴스 목록 |
| created_at | timestamp | 자동 생성 |

### doc_embeddings

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | bigserial (PK) | 자동 생성 |
| title | varchar(255) | 뉴스 제목 |
| content | text | 뉴스 본문 |
| source_url | varchar(255) | 원문 URL |
| created_at | timestamp | 수집 시각 |
| embedding | vector(1536) | 임베딩 벡터 |

### daily_summary

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | serial (PK) | 자동 생성 |
| target_date | date | 대상 날짜 |
| commodity | varchar(50) | 품목명 |
| score | numeric(5,4) | 일일 점수 |
| related_news_ids | bigint[] | 관련 뉴스 id 배열 |
| created_at | timestamp | 자동 생성 |

### market_metrics

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | serial (PK) | 자동 생성 |
| commodity | varchar(50) | 품목명 |
| date | date | 날짜 |
| metric_id | varchar(50) | 지표 식별자 |
| label | varchar(255) | 지표 라벨 |
| value | varchar(50) | 표시용 값 |
| numeric_value | float | 수치 값 |
| trend | float | 전일 대비 변화량 |
| impact | varchar(20) | 영향 방향 |
| created_at | timestamp | 자동 생성 |

### historical_prices

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | serial (PK) | 자동 생성 |
| commodity | varchar(50) | 품목명 |
| date | date | 날짜 |
| actual_price | numeric(10,2) | 실제 가격 |
| created_at | timestamp | 자동 생성 |

---

## 배치 작업 순서 (권장)

매일 배치 실행 시 아래 순서를 권장합니다:

1. **뉴스 수집 및 임베딩 저장** → `POST /api/newsdb/bulk`
2. **시장 지표 저장** → `PUT /api/market-metrics` (Upsert 권장)
3. **실제 가격 저장** → `PUT /api/historical-prices` (Upsert 권장)
4. **TFT 모델 예측 실행 및 저장** → `POST /api/predictions/bulk`
5. **LLM 설명 생성 및 저장** → `POST /api/explanations`
6. **일일 요약 저장** → `POST /api/daily-summary`

> Upsert(PUT)는 멱등성이 보장되므로, 재실행 시에도 안전합니다.

---

## Swagger UI

서버 실행 후 아래 URL에서 API를 직접 테스트할 수 있습니다:

```
http://44.252.76.158:8000/docs
```

`Batch Write` 태그로 배치 API들이 그룹화되어 있습니다.
