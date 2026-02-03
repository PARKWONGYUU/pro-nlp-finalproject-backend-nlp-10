# pro-nlp-finalproject-backend-nlp-10

## 📋 주요 구현 기능 (Features)

### 1. 📈 가격 예측 데이터 조회 (Price Prediction)
- **과거 데이터 차트:** 특정 품목의 과거 30일(기본) 예측 가격 및 실제 가격 제공
- **최신 예측:** 메인 대시보드용 금일 기준 향후 30일의 최신 예측 데이터 제공.
- **영향 요인 분석:** 가격 변동에 영향을 준 요인 및 영향도 수치 제공.

### 2. 📝 AI 시장 분석 리포트 (AI Explanation)
- **날짜별 상세 분석:** 특정 날짜의 예측 결과에 대해 LLM이 생성한 텍스트 리포트 제공.
- **RESTful 조회:** 날짜를 Key로 하여 예측 데이터와 매핑된 설명 조회.

### 3. 📰 뉴스 의미 기반 검색 (Vector Search) - 해야함
- **유사도 검색:** 단순 키워드 매칭이 아닌, 문맥적 의미가 유사한 뉴스 검색 (Vector Embedding).
- **PostgreSQL + pgvector:** 벡터 검색 구현.

---

## 🛠 기술 스택 (Tech Stack)

- **Language:** Python 3.9+
- **Framework:** FastAPI
- **Database:** PostgreSQL (with pgvector extension)
- **ORM:** SQLAlchemy
- **Data Validation:** Pydantic
- **Server:** Uvicorn, AWS EC2

---

## 📂 프로젝트 구조 (Project Structure)

```bash
pro-nlp-finalproject-backend-nlp-10/
├── app/
│   ├── __init__.py
│   ├── main.py            # 앱 진입점 (Entry Point)
│   ├── database.py        # DB 연결 세션 관리
│   ├── crud.py            # DB 쿼리 함수 모음
│   ├── datatable.py       # SQLAlchemy 모델 (DB 테이블 정의)
│   ├── dataschemas.py     # Pydantic 스키마 (데이터 검증/직렬화)
│   └── routers/           # API 라우터 폴더
│       ├── predictions.py # 예측 및 설명 관련 API
│       └── newsdb.py        # 뉴스 벡터 검색 API
├── requirements.txt       # 의존성 패키지 목록
└── README.md

+ 추가: api_client.py      # 외부 클라이언트에서 해당 endpoint로 요청 전송 예시
