# 프론트엔드 변경 가이드 - exp_pred 구조 변경

## 📋 변경 개요

`exp_pred` 테이블에 구조화된 설명 데이터가 추가되어, 프론트엔드에서 더 풍부한 예측 설명 UI를 제공할 수 있습니다.

## 🔄 API 응답 변경사항

### 영향받는 API

```
GET /api/explanations/{target_date}?commodity={commodity}
```

### 기존 응답 구조 (AS-IS)

```typescript
interface Explanation {
  id: number;
  pred_id: number;
  content: string;  // 전체 설명 텍스트
  llm_model: string;
  impact_news: Array<{
    source: string;
    title: string;
    impact_score: number;
    analysis: string;
  }>;
  created_at: string;
}
```

### 새로운 응답 구조 (TO-BE)

```typescript
interface TopFactorItem {
  name: string;          // 요인명 (예: "예측 경과 시점")
  category: string;      // 카테고리 (예: "시장 구조 (Market Structure)")
  impact: number;        // 영향도 (0~1)
  ratio: number;         // 비율 (0~1)
}

interface HighImpactNewsItem {
  title: string;         // 뉴스 제목 (날짜 포함)
  impact: number;        // 영향도 (0~1)
  rank: number;          // 순위
}

interface CategoryImpactItem {
  category: string;      // 카테고리명
  impact_sum: number;    // 카테고리별 총 영향도
  ratio: number;         // 전체 대비 비율
}

interface Explanation {
  id: number;
  pred_id: number;
  content: string;                              // Executive Summary (요약문)
  llm_model: string | null;
  impact_news: HighImpactNewsItem[] | null;     // ⚠️ 구조 변경
  top_factors: TopFactorItem[] | null;          // ✨ 새로 추가
  category_summary: CategoryImpactItem[] | null; // ✨ 새로 추가
  created_at: string;
}
```

### 응답 예시

```json
{
  "id": 1,
  "pred_id": 1,
  "content": "이번 옥수수 선물 가격 전망은 342.03으로 설정되었으며, 변동 범위는 335.12에서 350.15로 예상됩니다...",
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
    },
    {
      "name": "뉴스 주성분 5",
      "category": "외부 이벤트 (External Events)",
      "impact": 0.2119,
      "ratio": 0.106
    },
    {
      "name": "전체 시계열의 장기적 흐름",
      "category": "시장 구조 (Market Structure)",
      "impact": 0.176,
      "ratio": 0.088
    },
    {
      "name": "연중 시기",
      "category": "시장 구조 (Market Structure)",
      "impact": 0.1514,
      "ratio": 0.0757
    },
    {
      "name": "Palmer 가뭄 지수",
      "category": "기후 요인 (Climate)",
      "impact": 0.0391,
      "ratio": 0.0196
    },
    {
      "name": "미국 10년물 국채 금리",
      "category": "거시 경제 (Macroeconomics)",
      "impact": 0.0285,
      "ratio": 0.0143
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
    },
    {
      "category": "외부 이벤트 (External Events)",
      "impact_sum": 0.2119,
      "ratio": 0.106
    }
  ],
  "created_at": "2026-02-06T12:00:00"
}
```

## 📊 Market Metrics DB 구조

### 저장되는 Feature (46개)

`market_metrics` 테이블에는 TFT 모델의 입력 feature들이 날짜별로 저장됩니다.

| 카테고리 | Feature (metric_id) | 개수 | 설명 |
|----------|-------------------|------|------|
| **가격/거래량** | `close`, `open`, `high`, `low`, `volume`, `EMA` | 6 | 옥수수 선물 가격 및 거래량 |
| **뉴스 PCA** | `news_pca_0` ~ `news_pca_31` | 32 | 뉴스 임베딩을 PCA로 차원 축소한 feature |
| **기후 지수** | `pdsi`, `spi30d`, `spi90d` | 3 | Palmer 가뭄 지수, 30일/90일 강수량 지수 |
| **거시경제** | `10Y_Yield`, `USD_Index` | 2 | 미국 10년물 국채 금리, 달러 인덱스 |
| **Hawkes Intensity** | `lambda_price`, `lambda_news` | 2 | 가격/뉴스 이벤트 강도 |
| **기타** | `news_count` | 1 | 일일 뉴스 개수 |

### Feature → Factor Name 매핑 (전체 46개)

`top_factors`의 `name` 필드는 `market_metrics` DB의 feature를 사람이 이해하기 쉽게 변환한 것입니다.

```typescript
// Feature 한글명 매핑 (전체 46개 + 모델 내부 생성 feature)
const FEATURE_LABELS: Record<string, string> = {
  // === 가격/거래량 (6개) ===
  'close': '종가',
  'open': '시가',
  'high': '고가',
  'low': '저가',
  'volume': '거래량',
  'EMA': '지수 이동 평균',
  
  // === 뉴스 PCA (32개) ===
  'news_pca_0': '뉴스 주성분 1',
  'news_pca_1': '뉴스 주성분 2',
  'news_pca_2': '뉴스 주성분 3',
  'news_pca_3': '뉴스 주성분 4',
  'news_pca_4': '뉴스 주성분 5',
  'news_pca_5': '뉴스 주성분 6',
  'news_pca_6': '뉴스 주성분 7',
  'news_pca_7': '뉴스 주성분 8',
  'news_pca_8': '뉴스 주성분 9',
  'news_pca_9': '뉴스 주성분 10',
  'news_pca_10': '뉴스 주성분 11',
  'news_pca_11': '뉴스 주성분 12',
  'news_pca_12': '뉴스 주성분 13',
  'news_pca_13': '뉴스 주성분 14',
  'news_pca_14': '뉴스 주성분 15',
  'news_pca_15': '뉴스 주성분 16',
  'news_pca_16': '뉴스 주성분 17',
  'news_pca_17': '뉴스 주성분 18',
  'news_pca_18': '뉴스 주성분 19',
  'news_pca_19': '뉴스 주성분 20',
  'news_pca_20': '뉴스 주성분 21',
  'news_pca_21': '뉴스 주성분 22',
  'news_pca_22': '뉴스 주성분 23',
  'news_pca_23': '뉴스 주성분 24',
  'news_pca_24': '뉴스 주성분 25',
  'news_pca_25': '뉴스 주성분 26',
  'news_pca_26': '뉴스 주성분 27',
  'news_pca_27': '뉴스 주성분 28',
  'news_pca_28': '뉴스 주성분 29',
  'news_pca_29': '뉴스 주성분 30',
  'news_pca_30': '뉴스 주성분 31',
  'news_pca_31': '뉴스 주성분 32',
  
  // === 기후 지수 (3개) ===
  'pdsi': 'Palmer 가뭄 지수',
  'spi30d': '30일 강수량 지수',
  'spi90d': '90일 강수량 지수',
  
  // === 거시경제 (2개) ===
  '10Y_Yield': '미국 10년물 국채 금리',
  'USD_Index': '달러 인덱스',
  
  // === Hawkes Intensity (2개) ===
  'lambda_price': '가격 이벤트 강도',
  'lambda_news': '뉴스 이벤트 강도',
  
  // === 기타 (1개) ===
  'news_count': '뉴스 개수',
  
  // === 모델 내부 생성 feature (DB에 저장 안 됨) ===
  // 이 feature들은 백엔드에서 동적으로 생성됨
  'time_idx': '예측 경과 시점',
  'day_of_year': '연중 시기',
  'relative_time_idx': '상대적 시간 위치',
  'encoder_length': '입력 시계열 길이',
  'close_center': '종가 중심값',
  'close_scale': '종가 스케일',
};
```

**참고:**
- **DB 저장 feature**: 46개 (`market_metrics` 테이블)
- **동적 생성 feature**: 6개 (백엔드에서 실시간 계산)
- **총 feature**: 52개 (TFT 모델 입력)

### Category 분류

| Category | 포함되는 Feature |
|----------|-----------------|
| **시장 구조 (Market Structure)** | 시계열 구조적 요인 (예: 예측 경과 시점, 시간 흐름) |
| **기술적 지표 (Technical Indicators)** | `close`, `open`, `high`, `low`, `volume`, `EMA` |
| **외부 이벤트 (External Events)** | `news_pca_*`, `news_count`, `lambda_news` |
| **기후 요인 (Climate)** | `pdsi`, `spi30d`, `spi90d` |
| **거시 경제 (Macroeconomics)** | `10Y_Yield`, `USD_Index` |

---

## 🎨 UI/UX 개선 제안

### 1. Executive Summary 섹션

`content` 필드를 Executive Summary로 표시합니다.

**디자인 요구사항:**
- Executive Summary 전문 표시
- LLM 모델 뱃지 표시 (gpt-4 등)
- 카드 형태 레이아웃

---

### 2. 상위 영향 요인 (Top Factors) 섹션 ✨ 새로 추가

`top_factors` 데이터를 순위별로 시각화합니다.

**필수 표시 정보:**
- 순위 (1, 2, 3...)
- 요인명 (`name`): 예) "고가", "Palmer 가뭄 지수"
- 카테고리 (`category`): 예) "기술적 지표", "기후 요인"
- 영향 비율 (`ratio`): 진행률 바로 표시 (0~1 → 0%~100%)
- 영향도 (`impact`): 수치로 표시

**디자인 요구사항:**
- 진행률 바 (Horizontal Bar Chart)
- 카테고리별 색상 구분
- 상위 5~10개 표시 권장

---

### 3. 카테고리별 영향도 (Category Summary) 섹션 ✨ 새로 추가

`category_summary` 데이터를 차트로 시각화합니다.

**필수 표시 정보:**
- 카테고리명 (`category`)
- 카테고리별 총 영향도 (`impact_sum`)
- 전체 대비 비율 (`ratio`): 0~1 → 0%~100%

**디자인 요구사항:**
- 파이 차트 또는 도넛 차트
- 각 카테고리별 색상 구분 (위 Category 색상 참고)
- 범례 포함
- 비율 표시 (퍼센트)

**카테고리 색상 가이드:**
```typescript
const CATEGORY_COLORS = {
  '시장 구조 (Market Structure)': '#2196F3',      // 파란색
  '기술적 지표 (Technical Indicators)': '#4CAF50', // 초록색
  '외부 이벤트 (External Events)': '#FF9800',      // 주황색
  '기후 요인 (Climate)': '#00BCD4',                // 하늘색
  '거시 경제 (Macroeconomics)': '#9C27B0',         // 보라색
};
```

---

### 4. 영향 뉴스 (Impact News) 섹션 ⚠️ 구조 변경

`impact_news` 구조가 변경되었습니다.

**주요 변경점:**
- ❌ 제거된 필드: `source`, `impact_score` (1-10), `analysis`
- ✅ 새로운 필드: `rank`, `impact` (0-1)
- 제목에 날짜 포함: `[YYYY-MM-DD] 뉴스 제목`

**필수 표시 정보:**
- 순위 (`rank`)
- 제목 (`title`): 날짜 포함
- 영향도 (`impact`): 0~1 → 0%~100%

---

## 🔗 Market Metrics API 활용

### 시뮬레이션에서 Market Metrics 사용

시뮬레이션 기능에서 조정 가능한 5개 feature의 현재 값을 가져올 때 사용합니다.

**API:**
```
GET /api/market-metrics?commodity={commodity}&date={date}
```

**응답 예시:**
```json
{
  "commodity": "corn",
  "date": "2026-02-06",
  "metrics": [
    {
      "metric_id": "10Y_Yield",
      "label": "미국 10년물 국채 금리",
      "value": "4.2%",
      "numeric_value": 4.2,
      "trend": 0.1,
      "impact": "neutral"
    },
    {
      "metric_id": "USD_Index",
      "label": "달러 인덱스",
      "value": "103.5",
      "numeric_value": 103.5,
      "trend": -0.5,
      "impact": "positive"
    },
    {
      "metric_id": "pdsi",
      "label": "Palmer 가뭄 지수",
      "value": "-1.0",
      "numeric_value": -1.0,
      "trend": -0.2,
      "impact": "negative"
    },
    {
      "metric_id": "spi30d",
      "label": "30일 강수량 지수",
      "value": "0.5",
      "numeric_value": 0.5,
      "trend": 0.1,
      "impact": "neutral"
    },
    {
      "metric_id": "spi90d",
      "label": "90일 강수량 지수",
      "value": "-0.3",
      "numeric_value": -0.3,
      "trend": -0.1,
      "impact": "negative"
    }
  ]
}
```

### 시뮬레이션 조정 가능 Feature (5개)

| Feature | 한글명 | 설명 | 일반 범위 |
|---------|--------|------|-----------|
| `10Y_Yield` | 미국 10년물 국채 금리 | 미국 국채 금리 (%) | 0 ~ 10 |
| `USD_Index` | 달러 인덱스 | 달러 강도 지수 | 80 ~ 120 |
| `pdsi` | Palmer 가뭄 지수 | 토양 수분 상태 | -6 ~ 6 |
| `spi30d` | 30일 강수량 지수 | 최근 30일 강수량 | -3 ~ 3 |
| `spi90d` | 90일 강수량 지수 | 최근 90일 강수량 | -3 ~ 3 |

**사용 예시:**
```typescript
// 1. 현재 값 조회
const metrics = await fetchMarketMetrics('corn', '2026-02-06');
const currentValues = {
  '10Y_Yield': metrics.find(m => m.metric_id === '10Y_Yield')?.numeric_value || 0,
  'USD_Index': metrics.find(m => m.metric_id === 'USD_Index')?.numeric_value || 0,
  'pdsi': metrics.find(m => m.metric_id === 'pdsi')?.numeric_value || 0,
  'spi30d': metrics.find(m => m.metric_id === 'spi30d')?.numeric_value || 0,
  'spi90d': metrics.find(m => m.metric_id === 'spi90d')?.numeric_value || 0,
};

// 2. 시뮬레이션 실행 (사용자가 조정한 값)
const simulationResult = await simulatePrediction({
  commodity: 'corn',
  base_date: '2026-02-06',
  feature_overrides: {
    '10Y_Yield': 4.5,     // 4.2 → 4.5로 조정
    'USD_Index': 105.0,   // 103.5 → 105.0으로 조정
    'pdsi': -2.0,         // -1.0 → -2.0으로 조정
  }
});
```

---

## 📊 데이터 흐름

### 배치 서버 → DB
1. 뉴스 크롤링 → `doc_embeddings`
2. 시장 지표 수집 → `market_metrics` (46개 feature)
3. 실제 가격 수집 → `historical_prices`
4. TFT 모델 예측 → `tft_pred` (20개 top factors)
5. LLM 설명 생성 → `exp_pred` (top_factors, category_summary, impact_news)

### 프론트엔드 ← 백엔드
1. `GET /api/predictions` → 예측 목록 + 과거 30일 가격
2. `GET /api/explanations/{date}` → 예측 설명 (구조화된 데이터)
3. `GET /api/market-metrics` → 시장 지표 (시뮬레이션용)
4. `POST /api/simulate` → What-If 시뮬레이션 (60일 예측)
