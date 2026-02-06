# pro-nlp-finalproject-backend-nlp-10

## 📋 주요 구현 기능 (Features)

### 1. 📈 가격 예측 데이터 조회 (Price Prediction)
- **최신 예측 조회:** 각 target_date별 가장 최신 created_at 예측 반환 (과거 30일 ~ 미래 60일)
- **영향 요인 분석:** Top 20 영향 요인 및 영향도 수치 제공
- **실제 가격 비교:** 예측 가격과 실제 가격 비교 데이터 제공

### 2. 🤖 실시간 ONNX 모델 서빙 (Real-time Inference)
- **시뮬레이션 API:** 조건 변경 시 실시간 예측 재계산
- **AWS S3 모델 로딩:** S3에서 ONNX 모델 자동 다운로드 및 캐싱
- **자동 업데이트:** 설정 시간에 S3 모델 변경 감지 및 재로드
- **조정 가능 Features:** 미국 10년물 국채 금리, 달러 인덱스, PDSI, SPI 등

### 3. 📝 AI 시장 분석 리포트 (AI Explanation)
- **날짜별 상세 분석:** LLM이 생성한 예측 설명 제공
- **고영향 뉴스:** 가격 변동에 영향을 준 뉴스 목록 제공
- **RESTful 조회:** 날짜를 Key로 하여 예측 데이터와 매핑된 설명 조회

### 4. 📰 뉴스 및 시장 지표 조회
- **뉴스 데이터:** 뉴스 제목, 내용, 발행일 조회
- **시장 지표:** 특정 날짜의 시장 지표 데이터 조회
- **실제 가격:** 기간별 실제 가격 데이터 조회

---

## 🛠 기술 스택 (Tech Stack)

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (with pgvector extension)
- **ORM:** SQLAlchemy
- **Data Validation:** Pydantic
- **ML Inference:** ONNX Runtime
- **Cloud Storage:** AWS S3
- **Scheduling:** APScheduler
- **Server:** Uvicorn, AWS EC2

---

## 📂 프로젝트 구조 (Project Structure)

```bash
pro-nlp-finalproject-backend-nlp-10/
├── app/                        # 메인 애플리케이션
│   ├── __init__.py
│   ├── config.py              # 설정 관리 (AWS, Feature 목록)
│   ├── database.py            # DB 연결 세션 관리
│   ├── crud.py                # DB 쿼리 함수 모음
│   ├── datatable.py           # SQLAlchemy 모델 (DB 테이블 정의)
│   ├── dataschemas.py         # Pydantic 스키마 (데이터 검증/직렬화)
│   ├── ml/                    # 머신러닝 모듈
│   │   ├── __init__.py
│   │   ├── model_loader.py          # ONNX 모델 로더 (S3/로컬)
│   │   └── prediction_service.py    # TFT 예측 서비스
│   └── routers/               # API 라우터
│       ├── predictions.py           # 예측 및 설명 API
│       ├── newsdb.py                # 뉴스 조회 API
│       ├── historical_prices.py     # 실제 가격 API
│       ├── market_metrics.py        # 시장 지표 API
│       └── simulation.py            # 실시간 시뮬레이션 API
│
├── docs/                       # 📚 프로젝트 문서
│   ├── README.md                    # 문서 가이드
│   ├── plan.md                      # 프로젝트 계획
│   ├── TFT_IMPLEMENTATION_SUMMARY.md   # TFT 구현 상세
│   ├── REFACTORING_SUMMARY.md       # 리팩토링 내역
│   ├── GIT_COMMIT_SUMMARY.md        # Git 히스토리
│   ├── AI_SERVER_REQUIREMENTS.md    # AI 서버 요구사항
│   ├── ENV_SETUP_GUIDE.md           # 환경 설정 가이드
│   ├── IMPLEMENTATION_SUMMARY.md    # 구현 요약
│   └── LOCAL_MODEL_GUIDE.md         # 로컬 모델 가이드
│
├── tests/                      # 🧪 테스트
│   ├── README.md                    # 테스트 가이드
│   ├── test_tft_model.py            # TFT 모델 테스트 (권장)
│   ├── test_model.py                # 기본 모델 테스트
│   ├── test_simulation_api.py       # API 테스트
│   ├── check_files.py               # 파일 검증
│   ├── check_onnx.py                # ONNX 검증
│   └── inspect_pkl.py               # PKL 검증
│
├── scripts/                    # 🔧 유틸리티 스크립트
│   ├── README.md                    # 스크립트 가이드
│   ├── inspect_onnx_inputs.py       # ONNX 구조 분석
│   └── inspect_pkl.py               # PKL 정보 확인
│
├── migrations/                 # 📊 DB 마이그레이션
│   ├── 001_add_top6_to_top20_factors.sql
│   └── 002_refactor.sql
│
├── temp/                       # 🗂 임시 파일 (gitignore)
│   ├── *.onnx                       # ONNX 모델 파일
│   └── *.pkl                        # 전처리 정보 파일
│
├── main.py                     # 🚀 애플리케이션 진입점
├── requirements.txt            # 📦 Python 패키지 의존성
├── .env                        # 🔐 환경 변수 (gitignore)
├── .gitignore                  # Git 제외 파일 목록
└── README.md                   # 📖 프로젝트 메인 문서
```

---

## 🚀 시작하기 (Getting Started)

### 1. 환경 변수 설정

`.env` 파일 생성:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# 모델 로딩 모드 ("local" 또는 "s3")
MODEL_LOAD_MODE=local

# 로컬 모델 경로 (local 모드일 때)
LOCAL_MODEL_PATH=./temp

# AWS S3 설정 (s3 모드일 때만 필요)
# AWS_ACCESS_KEY_ID=your_access_key_id
# AWS_SECRET_ACCESS_KEY=your_secret_access_key
# AWS_REGION=ap-northeast-2
# MODEL_S3_BUCKET=your-model-bucket-name

# 모델 업데이트 확인 시간 (KST, 24시간 형식)
MODEL_UPDATE_CHECK_TIME=03:00
```

**로컬 모드 사용 시:**
- `temp/` 폴더에 `.onnx` 파일과 `.pkl` 파일 배치
- 파일명 예시: `60d_20260206.onnx`, `60d_preprocessing_20260206.pkl`
- 자동으로 가장 최신 파일 사용

### 2. 의존성 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. API 문서 접속

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🔄 서버 아키텍처

### 백엔드 서버 (온라인 서버)
- **역할:** 실시간 API 제공, ONNX 모델 서빙
- **엔드포인트:** GET 전용 (예측, 뉴스, 시장지표 조회)
- **시뮬레이션:** POST `/api/simulate` (실시간 예측 재계산)

### AI 배치 서버 (Airflow)
- **역할:** 데이터 수집, 예측 생성, LLM 분석
- **DB 접근:** SQLAlchemy로 직접 INSERT
- **모델 배포:** S3에 ONNX 모델 업로드 (`latest/model.onnx`)

---

## 📡 주요 API 엔드포인트

### 예측 관련
- `GET /api/predictions?commodity=corn` - 최신 예측 조회 (과거 30일 ~ 미래 60일)
- `GET /api/predictions/{target_date}?commodity=corn` - 특정 날짜 예측 조회
- `GET /api/explanations/{target_date}?commodity=corn` - 예측 설명 조회

### 시뮬레이션
- `POST /api/simulate` - 조건 변경 시 실시간 예측 재계산

### 데이터 조회
- `GET /api/newsdb?skip=0&limit=10` - 뉴스 목록 조회
- `GET /api/historical-prices?commodity=corn&start_date=2026-01-01&end_date=2026-01-31` - 실제 가격 조회
- `GET /api/market-metrics?commodity=corn&date=2026-02-03` - 시장 지표 조회

---

## 📦 배포 (Deployment)

### AWS EC2 배포

```bash
ssh -i "키페어.pem" ubuntu@ec2-아이피.compute.amazonaws.com