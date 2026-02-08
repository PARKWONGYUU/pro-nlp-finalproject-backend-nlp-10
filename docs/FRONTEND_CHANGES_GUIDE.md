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
      "name": "기사",
      "category": "외부 이벤트 (External Events)",
      "impact": 0.2119,
      "ratio": 0.106
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

## 🎨 UI/UX 개선 제안

### 1. Executive Summary 섹션

기존 `content` 필드를 Executive Summary로 표시합니다.

```tsx
<section className="executive-summary">
  <h3>📊 예측 요약</h3>
  <p className="summary-text">{explanation.content}</p>
  <span className="llm-badge">{explanation.llm_model}</span>
</section>
```

**디자인 제안:**
- 카드 형태로 상단에 배치
- 배경색: 연한 회색 또는 흰색
- 폰트: 가독성 좋은 본문 폰트 (16-18px)

---

### 2. 상위 영향 요인 (Top Factors) 섹션 ✨ 새로 추가

`top_factors` 데이터를 시각화합니다.

```tsx
<section className="top-factors">
  <h3>🎯 주요 영향 요인</h3>
  <div className="factors-list">
    {explanation.top_factors?.map((factor, index) => (
      <div key={index} className="factor-item">
        <div className="factor-rank">#{index + 1}</div>
        <div className="factor-info">
          <h4>{factor.name}</h4>
          <span className="category-badge">{factor.category}</span>
        </div>
        <div className="factor-impact">
          <div className="impact-bar" style={{ width: `${factor.ratio * 100}%` }}>
            <span>{(factor.ratio * 100).toFixed(1)}%</span>
          </div>
          <span className="impact-value">영향도: {factor.impact.toFixed(3)}</span>
        </div>
      </div>
    ))}
  </div>
</section>
```

**디자인 제안:**
- 순위 표시 (1, 2, 3...)
- 진행률 바 (Horizontal Bar Chart)
- 카테고리 뱃지 (색상 구분)
  - 시장 구조: 파란색
  - 기술적 지표: 초록색
  - 외부 이벤트: 주황색
  - 기후 요인: 하늘색
  - 거시 경제: 보라색

**예시 CSS:**
```css
.factor-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
  gap: 16px;
}

.factor-rank {
  font-size: 20px;
  font-weight: bold;
  color: #666;
  min-width: 40px;
}

.impact-bar {
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  height: 24px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.category-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  background-color: #e3f2fd;
  color: #1976d2;
}
```

---

### 3. 카테고리별 영향도 (Category Summary) 섹션 ✨ 새로 추가

`category_summary` 데이터를 파이 차트 또는 도넛 차트로 시각화합니다.

```tsx
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const CATEGORY_COLORS = {
  '시장 구조 (Market Structure)': '#2196F3',
  '기술적 지표 (Technical Indicators)': '#4CAF50',
  '외부 이벤트 (External Events)': '#FF9800',
  '기후 요인 (Climate)': '#00BCD4',
  '거시 경제 (Macroeconomics)': '#9C27B0',
};

<section className="category-summary">
  <h3>📈 카테고리별 영향도</h3>
  <ResponsiveContainer width="100%" height={300}>
    <PieChart>
      <Pie
        data={explanation.category_summary}
        dataKey="ratio"
        nameKey="category"
        cx="50%"
        cy="50%"
        outerRadius={100}
        label={({ category, ratio }) => `${(ratio * 100).toFixed(1)}%`}
      >
        {explanation.category_summary?.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.category] || '#999'} />
        ))}
      </Pie>
      <Tooltip 
        formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
      />
      <Legend />
    </PieChart>
  </ResponsiveContainer>
  
  <div className="category-details">
    {explanation.category_summary?.map((cat, index) => (
      <div key={index} className="category-item">
        <div 
          className="category-color" 
          style={{ backgroundColor: CATEGORY_COLORS[cat.category] }}
        />
        <span className="category-name">{cat.category}</span>
        <span className="category-impact">
          총 영향도: {cat.impact_sum.toFixed(3)} ({(cat.ratio * 100).toFixed(1)}%)
        </span>
      </div>
    ))}
  </div>
</section>
```

**디자인 제안:**
- 파이 차트 또는 도넛 차트
- 각 카테고리별 색상 구분
- 범례 포함
- 마우스 오버 시 상세 정보 표시

---

### 4. 영향 뉴스 (Impact News) 섹션 ⚠️ 구조 변경

`impact_news` 구조가 변경되었습니다.

**기존 코드 (AS-IS):**
```tsx
// ❌ 더 이상 작동하지 않음
{explanation.impact_news?.map((news, index) => (
  <div key={index}>
    <h4>{news.title}</h4>
    <p>출처: {news.source}</p>
    <p>영향도: {news.impact_score}/10</p>
    <p>{news.analysis}</p>
  </div>
))}
```

**새로운 코드 (TO-BE):**
```tsx
// ✅ 새로운 구조에 맞춤
<section className="impact-news">
  <h3>📰 영향력 있는 뉴스</h3>
  {explanation.impact_news?.map((news, index) => (
    <div key={index} className="news-item">
      <div className="news-rank">#{news.rank}</div>
      <div className="news-content">
        <h4>{news.title}</h4>
        <div className="news-impact">
          <div className="impact-bar" style={{ width: `${news.impact * 100}%` }}>
            <span>영향도: {(news.impact * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </div>
  ))}
</section>
```

**주요 변경점:**
- `source` 필드 제거 → 제목에 날짜 포함됨
- `impact_score` (1-10) → `impact` (0-1)로 변경
- `analysis` 필드 제거
- `rank` 필드 추가

---

## 📱 반응형 레이아웃 제안

```tsx
<div className="explanation-container">
  {/* 상단: Executive Summary */}
  <div className="summary-section">
    <ExecutiveSummary content={explanation.content} llmModel={explanation.llm_model} />
  </div>
  
  <div className="content-grid">
    {/* 좌측: 상위 영향 요인 + 뉴스 */}
    <div className="left-column">
      <TopFactors factors={explanation.top_factors} />
      <ImpactNews news={explanation.impact_news} />
    </div>
    
    {/* 우측: 카테고리별 영향도 */}
    <div className="right-column">
      <CategorySummary summary={explanation.category_summary} />
    </div>
  </div>
</div>
```

**CSS Grid 예시:**
```css
.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-top: 24px;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
```

---

## 🔧 마이그레이션 체크리스트

### 1. 타입 정의 업데이트
- [ ] `types/api.ts` 또는 `types/explanation.ts` 파일에 새로운 인터페이스 추가
- [ ] 기존 `Explanation` 인터페이스 업데이트
- [ ] `TopFactorItem`, `HighImpactNewsItem`, `CategoryImpactItem` 추가

### 2. API 호출 및 상태 관리
- [ ] `explanation` API 응답 타입 업데이트
- [ ] Redux/Zustand/Context 상태 타입 업데이트
- [ ] API 에러 핸들링 확인

### 3. UI 컴포넌트
- [ ] `ExecutiveSummary.tsx` 컴포넌트 생성/수정
- [ ] `TopFactors.tsx` 컴포넌트 생성 ✨
- [ ] `CategorySummary.tsx` 컴포넌트 생성 ✨
- [ ] `ImpactNews.tsx` 컴포넌트 수정 ⚠️
- [ ] 차트 라이브러리 추가 (recharts, chart.js 등)

### 4. 스타일링
- [ ] 카테고리별 색상 정의
- [ ] 진행률 바 스타일
- [ ] 반응형 레이아웃
- [ ] 다크 모드 대응 (선택)

### 5. 데이터 핸들링
- [ ] `null` 값 처리 (top_factors, category_summary, impact_news 모두 optional)
- [ ] 빈 배열 처리
- [ ] 로딩 상태 처리

### 6. 테스트
- [ ] 새로운 API 응답 형식 테스트
- [ ] 컴포넌트 단위 테스트
- [ ] 통합 테스트
- [ ] E2E 테스트

---

## 🧪 테스트 시나리오

### 시나리오 1: 모든 데이터가 있는 경우
```json
{
  "top_factors": [...],
  "category_summary": [...],
  "impact_news": [...]
}
```
→ 모든 섹션이 정상적으로 표시되어야 함

### 시나리오 2: 일부 데이터가 null인 경우
```json
{
  "top_factors": null,
  "category_summary": [...],
  "impact_news": null
}
```
→ 해당 섹션을 숨기거나 "데이터 없음" 메시지 표시

### 시나리오 3: 빈 배열인 경우
```json
{
  "top_factors": [],
  "category_summary": [],
  "impact_news": []
}
```
→ "영향 요인 없음" 또는 Placeholder 표시

---

## 📦 추천 라이브러리

### 차트 시각화
```bash
npm install recharts
# 또는
npm install chart.js react-chartjs-2
```

### 프로그레스 바
```bash
npm install @mui/material @emotion/react @emotion/styled
# LinearProgress 컴포넌트 사용
```

### 아이콘
```bash
npm install @mui/icons-material
# 또는
npm install react-icons
```

---

## 💡 추가 개선 아이디어

### 1. 인터랙티브 차트
- 클릭 시 해당 카테고리의 상세 요인 표시
- 마우스 오버 시 툴팁으로 추가 정보 표시

### 2. 비교 기능
- 여러 날짜의 예측 설명 비교
- 영향 요인 변화 추이 시각화

### 3. 필터링
- 카테고리별 필터링
- 영향도 임계값 설정

### 4. 내보내기
- PDF 리포트 생성
- 이미지 캡처 기능

---

## 🔗 참고 문서

- **Backend API Guide**: `docs/BATCH_API_GUIDE.md`
- **Database Schema**: `docs/DATABASE_SCHEMA.md`
- **Migration Guide**: `docs/MIGRATION_GUIDE_EXP_PRED.md`

## 📞 문의사항

API 응답 구조나 데이터 형식에 대한 문의는 백엔드 팀에 연락하세요.
