# AI 배치 서버 요구사항 (Airflow)

> **역할 변경**: 실시간 추론 서버 → 배치 처리 서버

---

## 📌 AI 배치 서버 개요

### 역할 분리
- **백엔드 서버 (온라인 서버)**: 
  - 실시간 추론 (ONNX 모델)
  - `/api/simulate` 엔드포인트 제공
  - GET API 제공
  
- **AI 배치 서버 (Airflow)**:
  - 데이터 수집 및 저장
  - 예측 생성 및 DB 저장
  - LLM 분석 및 저장
  - 모델 학습 및 S3 배포

### 🔑 핵심 특징
- ✅ DB에 직접 접근 (SQLAlchemy)
- ✅ 백엔드와 **동일한 스키마 공유** (`app/datatable.py`)
- ✅ 스케줄 기반 배치 작업 (Airflow DAG)
- ✅ S3에 ONNX 모델 배포

---

## 🔄 AI 서버 워크플로우

```mermaid
graph TD
    A[스케줄러 시작] --> B[뉴스 데이터 수집]
    B --> C[뉴스 임베딩 생성]
    C --> D[DB에 직접 뉴스 저장]
    
    A --> E[시장 지표 수집]
    E --> F[DB에 직접 지표 저장]
    
    A --> G[TFT 예측 모델 실행]
    G --> H[예측 결과 생성]
    H --> I[DB에 직접 예측 저장]
    
    I --> J[LLM으로 설명 생성]
    J --> K[고영향 뉴스 분석]
    K --> L[DB에 직접 설명 저장]
    
    A --> M[과거 실제 가격 수집]
    M --> N[DB에 직접 가격 저장]
    
    O[백엔드] --> P[시뮬레이션 요청 프록시]
    P --> Q[AI 서버 FastAPI]
    Q --> R[TFT 모델 재실행]
    R --> S[시뮬레이션 결과 반환]
    S --> O
```

---

## 📋 AI 서버가 수행할 작업

### 1. 뉴스 데이터 수집 및 저장

#### 작업 흐름
```python
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.datatable import DocEmbeddings
from datetime import datetime

# 1. 외부 뉴스 API에서 데이터 수집
news_data = fetch_news_from_sources(commodity="Corn")

# 2. 임베딩 생성 (OpenAI, Sentence-BERT 등)
embedding = generate_embedding(news_data['content'])

# 3. DB 세션 생성 및 직접 저장
db = SessionLocal()
try:
    news_obj = DocEmbeddings(
        title="아르헨티나 항만 파업으로 곡물 선적 지연",
        content="아르헨티나 주요 항만에서...",
        source_url="https://www.wsj.com/...",
        created_at=datetime.now(),
        embedding=embedding.tolist()  # pgvector 형식
    )
    db.add(news_obj)
    db.commit()
    db.refresh(news_obj)
    print(f"뉴스 저장 완료: ID={news_obj.id}")
finally:
    db.close()
```

#### 데이터베이스 테이블
- **테이블**: `doc_embeddings`
- **모델**: `app.datatable.DocEmbeddings`

#### 실행 주기
- **일별 1회**: 매일 오전 8시 (KST)
- 또는 실시간 스트리밍

---

### 2. 시장 지표 수집 및 저장

#### 작업 흐름
```python
from app.database import SessionLocal
from app.datatable import MarketMetrics
from datetime import date

# 1. 시장 지표 데이터 수집 (예: Bloomberg API, Yahoo Finance)
metrics = fetch_market_metrics(commodity="Corn", date="2026-02-04")

# 2. DB에 직접 저장
db = SessionLocal()
try:
    for metric in metrics:
        metric_obj = MarketMetrics(
            commodity="Corn",
            date=date(2026, 2, 4),
            metric_id="net_long",
            label="Net Long (순매수)",
            value="15.4K",
            numeric_value=15400.0,
            trend=5.2,  # 전일 대비 변화율 (%)
            impact="High"  # High, Medium, Low
        )
        db.add(metric_obj)
    
    db.commit()
    print(f"시장 지표 {len(metrics)}개 저장 완료")
finally:
    db.close()
```

#### 데이터베이스 테이블
- **테이블**: `market_metrics`
- **모델**: `app.datatable.MarketMetrics`

#### 수집할 지표 예시
- `net_long`: Net Long (순매수)
- `open_interest`: Open Interest
- `wti_crude`: WTI Crude Oil
- `dxy_index`: Dollar Index
- `weather_index`: 날씨 지수
- `supply_estimate`: 공급 예측치

#### 실행 주기
- **일별 1회**: 장 마감 후 (예: 오후 6시)

---

### 3. TFT 예측 모델 실행 및 저장

#### 작업 흐름
```python
from app.database import SessionLocal
from app.datatable import TftPred
from datetime import date

# 1. 특징 데이터 준비 (시장 지표, 과거 가격 등)
features = prepare_features(commodity="Corn", target_date="2026-02-10")

# 2. TFT 모델로 예측 실행
prediction = tft_model.predict(features)

# 3. Top 5 영향 요인 추출
top_factors = extract_top_factors(prediction)

# 4. DB에 직접 저장
db = SessionLocal()
try:
    pred_obj = TftPred(
        target_date=date(2026, 2, 10),
        commodity="Corn",
        price_pred=452.30,
        conf_lower=440.00,
        conf_upper=465.00,
        top1_factor="WTI_Crude_Oil",
        top1_impact=3.6,
        top2_factor="Net_Long",
        top2_impact=2.1,
        top3_factor="Dollar_Index",
        top3_impact=1.8,
        top4_factor="Weather_Index",
        top4_impact=1.2,
        top5_factor="Supply_Estimate",
        top5_impact=0.9
    )
    db.add(pred_obj)
    db.commit()
    db.refresh(pred_obj)
    
    pred_id = pred_obj.id  # 저장된 예측 ID
    print(f"예측 저장 완료: ID={pred_id}")
    
    return pred_id  # 다음 단계에서 사용
finally:
    db.close()
```

#### 데이터베이스 테이블
- **테이블**: `tft_pred`
- **모델**: `app.datatable.TftPred`

#### 실행 주기
- **일별 1회**: 오전 9시 (모든 데이터 수집 후)
- 7일 후까지 예측 (target_date가 7개)

---

### 4. LLM 설명 생성 및 저장

#### 작업 흐름
```python
from app.database import SessionLocal
from app.datatable import TftPred, ExpPred, DocEmbeddings

# 1. 예측 데이터 가져오기 (방금 저장한 pred_id 사용)
db = SessionLocal()
try:
    prediction = db.query(TftPred).filter(TftPred.id == pred_id).first()
    
    # 2. 관련 뉴스 검색 (벡터 유사도 기반)
    # pgvector 사용: <=> 연산자로 코사인 거리 계산
    query_embedding = get_commodity_embedding("Corn")
    related_news = db.query(DocEmbeddings)\
        .order_by(DocEmbeddings.embedding.op('<=>')(query_embedding))\
        .limit(10)\
        .all()
    
    # 3. LLM으로 예측 설명 생성
    prompt = f"""
    다음 정보를 바탕으로 {prediction.commodity} 가격 예측을 설명해주세요:
    - 예측 가격: {prediction.price_pred}
    - 주요 영향 요인: {prediction.top1_factor} ({prediction.top1_impact}%)
    - 관련 뉴스: {[news.title for news in related_news]}
    """
    
    explanation = llm_call(prompt, model="gpt-4")
    
    # 4. 고영향 뉴스 분석
    impact_news = analyze_high_impact_news(related_news, prediction)
    
    # 5. DB에 직접 저장
    exp_obj = ExpPred(
        pred_id=pred_id,
        content=explanation,
        llm_model="gpt-4-turbo",
        impact_news=[
            {
                "source": "Bloomberg",
                "title": "미 중서부 기습 폭염 경보",
                "impact_score": 92,
                "analysis": "공급망 충격(Supply Shock) 우려로 가격 상승 압력 증가"
            },
            {
                "source": "Reuters",
                "title": "아르헨티나 항만 파업 장기화",
                "impact_score": 85,
                "analysis": "글로벌 공급 차질로 단기 가격 변동성 확대"
            }
        ]
    )
    db.add(exp_obj)
    db.commit()
    db.refresh(exp_obj)
    
    print(f"설명 저장 완료: ID={exp_obj.id}")
finally:
    db.close()
```

#### 데이터베이스 테이블
- **테이블**: `exp_pred`
- **모델**: `app.datatable.ExpPred`
- **관계**: `TftPred`와 1:1 관계 (Foreign Key: `pred_id`)

#### 실행 주기
- **예측 직후**: 각 예측이 저장된 직후 실행

---

### 5. 과거 실제 가격 수집 및 저장

#### 작업 흐름
```python
from app.database import SessionLocal
from app.datatable import HistoricalPrices
from datetime import date

# 1. 실제 가격 데이터 수집 (거래소, 마켓 데이터 API)
actual_price = fetch_actual_price(commodity="Corn", date="2026-02-04")

# 2. DB에 직접 저장
db = SessionLocal()
try:
    price_obj = HistoricalPrices(
        commodity="Corn",
        date=date(2026, 2, 4),
        actual_price=448.75
    )
    db.add(price_obj)
    db.commit()
    db.refresh(price_obj)
    
    print(f"실제 가격 저장 완료: ID={price_obj.id}")
finally:
    db.close()
```

#### 데이터베이스 테이블
- **테이블**: `historical_prices`
- **모델**: `app.datatable.HistoricalPrices`

#### 실행 주기
- **일별 1회**: 장 마감 후 (예: 오후 7시)

---

### 6. 시뮬레이션 API 제공 (중요!)

#### 역할
프론트엔드에서 사용자가 특정 변수를 조정했을 때, 예측이 어떻게 변하는지 실시간으로 계산

#### AI 서버 API 엔드포인트
```python
@app.post("/simulate")
def simulate_prediction(request: SimulationRequest):
    """
    특정 feature를 변경했을 때 예측 재계산
    """
    # 1. 원본 예측 데이터 로드
    base_features = load_features(request.commodity, request.base_date)
    
    # 2. feature_overrides 적용
    modified_features = base_features.copy()
    for feature_name, new_value in request.feature_overrides.items():
        modified_features[feature_name] = new_value
    
    # 3. TFT 모델로 재예측
    original_pred = tft_model.predict(base_features)
    simulated_pred = tft_model.predict(modified_features)
    
    # 4. 각 feature의 기여도 계산 (SHAP, Attention 등)
    feature_impacts = []
    for feature_name, new_value in request.feature_overrides.items():
        current_value = base_features[feature_name]
        contribution = calculate_contribution(
            feature_name, current_value, new_value, 
            original_pred, simulated_pred
        )
        
        feature_impacts.append({
            "feature": feature_name,
            "current_value": current_value,
            "new_value": new_value,
            "value_change": new_value - current_value,
            "contribution": contribution
        })
    
    # 5. 응답 반환
    return {
        "original_forecast": original_pred,
        "simulated_forecast": simulated_pred,
        "change": simulated_pred - original_pred,
        "change_percent": ((simulated_pred - original_pred) / original_pred) * 100,
        "feature_impacts": feature_impacts
    }
```

#### 백엔드 서버와의 연동
백엔드 서버의 `/api/simulate` 엔드포인트는 AI 서버로 요청을 프록시:

```python
# 백엔드 서버 (FastAPI)
@router.post("/simulate", response_model=SimulationResponse)
def simulate_prediction(request: SimulationRequest):
    # AI 서버로 요청 전달
    ai_server_url = os.getenv("AI_SERVER_URL")
    response = requests.post(
        f"{ai_server_url}/simulate",
        json=request.dict(),
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=500, detail="AI 서버 시뮬레이션 실패")
```

#### AI 서버 API
- **Endpoint**: `POST /simulate`
- **Request Body**:
```json
{
  "commodity": "Corn",
  "base_date": "2026-02-03",
  "feature_overrides": {
    "WTI": 80.0,
    "DXY": 105.5,
    "NET_LONG": 18000,
    "ETHANOL_PROD": 1.15
  }
}
```
- **Response**:
```json
{
  "original_forecast": 452.30,
  "simulated_forecast": 458.75,
  "change": 6.45,
  "change_percent": 1.43,
  "feature_impacts": [
    {
      "feature": "WTI",
      "current_value": 75.50,
      "new_value": 80.0,
      "value_change": 4.5,
      "contribution": 3.6
    }
  ]
}
```

#### 실행 주기
- **온디맨드**: 프론트엔드 사용자 요청 시 즉시 실행

---

## 🔧 AI 서버 기술 스택 제안

### 프레임워크
- **FastAPI**: 비동기 API 서버
- **Celery**: 백그라운드 작업 및 스케줄러
- **Redis**: 작업 큐 및 캐싱

### 모델/라이브러리
- **PyTorch Forecasting**: TFT 모델
- **Sentence-Transformers**: 뉴스 임베딩
- **OpenAI API**: GPT-4 for 설명 생성
- **SHAP**: Feature importance 분석

### 데이터 수집
- **yfinance**: Yahoo Finance 데이터
- **ccxt**: 암호화폐 거래소 데이터 (필요시)
- **NewsAPI**: 뉴스 데이터
- **BeautifulSoup**: 웹 스크래핑

---

## 📅 일일 실행 스케줄 (예시)

```
06:00 - 뉴스 데이터 수집 시작
07:00 - 시장 지표 데이터 수집
08:00 - 과거 실제 가격 수집
09:00 - TFT 예측 모델 실행
09:30 - LLM 설명 생성 및 저장
10:00 - 모든 작업 완료, 프론트엔드 알림
```

---

## 🔌 데이터베이스 직접 접근 방법

AI 서버는 백엔드 API를 호출하지 않고 **SQLAlchemy를 통해 DB에 직접 접근**합니다.

### AI 서버 프로젝트 구조

```
ai-server/
├── main.py                 # FastAPI 앱 (시뮬레이션 API만)
├── scheduler.py            # Celery 스케줄러
├── models/
│   ├── tft_model.py       # TFT 예측 모델
│   └── embedding.py       # 임베딩 생성
├── collectors/
│   ├── news_collector.py  # 뉴스 수집
│   ├── market_collector.py # 시장 지표 수집
│   └── price_collector.py # 실제 가격 수집
├── analyzers/
│   └── llm_analyzer.py    # LLM 분석
├── shared/                 # 백엔드와 공유하는 모듈
│   ├── database.py        # DB 연결 (백엔드와 동일)
│   ├── datatable.py       # 테이블 모델 (백엔드와 동일)
│   └── dataschemas.py     # Pydantic 스키마 (백엔드와 동일)
└── .env                    # DATABASE_URL 포함
```

### 백엔드 모듈 공유 방법

#### 옵션 1: 심볼릭 링크 (권장)
```bash
cd ai-server/shared/
ln -s ../../pro-nlp-finalproject-backend-nlp-10/app/database.py database.py
ln -s ../../pro-nlp-finalproject-backend-nlp-10/app/datatable.py datatable.py
ln -s ../../pro-nlp-finalproject-backend-nlp-10/app/dataschemas.py dataschemas.py
```

#### 옵션 2: Git Submodule
```bash
# 백엔드를 submodule로 추가
git submodule add <backend-repo-url> backend
```

#### 옵션 3: 패키지로 설치
```bash
# 백엔드를 로컬 패키지로 설치
pip install -e ../pro-nlp-finalproject-backend-nlp-10
```

### 사용 예시

```python
# AI 서버 코드에서
from shared.database import SessionLocal
from shared.datatable import TftPred, ExpPred, DocEmbeddings, MarketMetrics, HistoricalPrices

# DB 세션 생성
db = SessionLocal()

# 데이터 저장
prediction = TftPred(commodity="Corn", ...)
db.add(prediction)
db.commit()
```

---

## 🚨 에러 핸들링

### 재시도 로직
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def send_data_with_retry(data, endpoint):
    response = requests.post(endpoint, json=data)
    response.raise_for_status()
    return response.json()
```

### 실패 시 로깅
```python
import logging

logger = logging.getLogger(__name__)

try:
    send_prediction(data)
except Exception as e:
    logger.error(f"예측 데이터 전송 실패: {e}")
    # Slack/Discord 알림 전송
    notify_admin(f"AI 서버 에러: {e}")
```

---

## 📊 모니터링

### 체크리스트
- ✅ 일일 데이터 수집 완료 여부
- ✅ 예측 모델 실행 성공 여부
- ✅ 백엔드 서버 응답 시간
- ✅ 데이터 품질 (결측치, 이상치)
- ✅ LLM API 사용량 및 비용

### 대시보드 메트릭
- 일일 뉴스 수집 건수
- 예측 정확도 (RMSE, MAE)
- 백엔드 API 호출 성공률
- 시뮬레이션 응답 시간

---

## 🔐 환경 변수

```bash
# .env 파일
# 백엔드와 동일한 DB 연결 정보
DATABASE_URL=postgresql://user:password@host:5432/dbname

# API Keys
OPENAI_API_KEY=sk-...
NEWS_API_KEY=...
BLOOMBERG_API_KEY=...

# 모델 경로
TFT_MODEL_PATH=/models/tft_corn.pth
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# FastAPI 설정 (시뮬레이션 API용)
AI_SERVER_HOST=0.0.0.0
AI_SERVER_PORT=8001

# 스케줄러 설정
SCHEDULER_TIMEZONE=Asia/Seoul
```

---

## 📝 체크리스트

### AI 서버 개발 우선순위

1. **Phase 1 - 기본 데이터 파이프라인** ✅
   - [ ] 뉴스 수집 및 임베딩
   - [ ] 예측 모델 실행
   - [ ] 백엔드 API 연동

2. **Phase 2 - LLM 통합** 🔄
   - [ ] LLM 설명 생성
   - [ ] 고영향 뉴스 분석

3. **Phase 3 - 시뮬레이션** 🎯
   - [ ] 시뮬레이션 API 구현
   - [ ] Feature importance 계산
   - [ ] 백엔드 프록시 연동

4. **Phase 4 - 모니터링 & 최적화** 📈
   - [ ] 로깅 및 알림 시스템
   - [ ] 성능 모니터링
   - [ ] 자동 재시도 로직

---

## 🎯 다음 단계

1. ~~**AI 서버 저장소 생성**~~ → **동일 저장소 사용 (별도 디렉토리)**
2. **백엔드 모듈 공유 설정** (심볼릭 링크 또는 서브모듈)
3. **TFT 모델 학습 및 저장**
4. **데이터 수집 스크립트 작성**
5. **DB 직접 접근 테스트**
6. **시뮬레이션 API 구현**
7. **스케줄러 설정 및 배포**

---

## 📌 중요 참고사항

### DB 공유 시 주의사항
1. **스키마 변경 시**: 백엔드의 `datatable.py` 수정 후 AI 서버도 동기화
2. **마이그레이션**: 백엔드에서 마이그레이션 실행 후 AI 서버 재시작
3. **트랜잭션**: 데이터 저장 시 항상 `try-finally`로 DB 세션 관리
4. **동시성**: 같은 데이터를 동시에 수정하지 않도록 주의

### 권장 개발 순서
1. 백엔드 스키마 확정
2. AI 서버에서 백엔드 모듈 import 테스트
3. 간단한 데이터 저장/조회 테스트
4. 전체 파이프라인 구현

---

**작성일**: 2026-02-04  
**버전**: 2.0.0 (DB 직접 접근 방식)  
**담당**: AI 서버 개발팀
