# 📂 프로젝트 구조 가이드

**최종 업데이트**: 2026-02-06

---

## 🎯 폴더 구조 개요

```
pro-nlp-finalproject-backend-nlp-10/
├── 📁 app/                 # 메인 애플리케이션 코드
├── 📁 docs/                # 프로젝트 문서
├── 📁 tests/               # 테스트 파일
├── 📁 scripts/             # 유틸리티 스크립트
├── 📁 migrations/          # DB 마이그레이션
├── 📁 temp/                # 임시/모델 파일 (gitignore)
├── 📁 venv/                # Python 가상환경 (gitignore)
├── 📄 main.py              # 애플리케이션 진입점
├── 📄 requirements.txt     # Python 패키지 의존성
├── 📄 .env                 # 환경 변수 (gitignore)
└── 📄 README.md            # 프로젝트 메인 문서
```

---

## 📁 상세 폴더 구조

### 1. **app/** - 메인 애플리케이션
```
app/
├── __init__.py
├── config.py               # 설정 관리 (Pydantic Settings)
├── database.py             # DB 세션 관리
├── crud.py                 # CRUD 함수 (타입 힌팅 완비)
├── datatable.py            # SQLAlchemy 모델
├── dataschemas.py          # Pydantic 스키마
├── ml/                     # 머신러닝 모듈
│   ├── __init__.py
│   ├── model_loader.py           # ONNX 모델 로더
│   └── prediction_service.py     # TFT 예측 서비스
└── routers/                # FastAPI 라우터
    ├── __init__.py
    ├── predictions.py            # 예측 및 설명 API
    ├── newsdb.py                 # 뉴스 API
    ├── historical_prices.py      # 가격 API
    ├── market_metrics.py         # 지표 API
    └── simulation.py             # 시뮬레이션 API
```

**역할:**
- FastAPI 애플리케이션의 핵심 코드
- 비즈니스 로직, DB 처리, API 엔드포인트
- ML 모델 로딩 및 예측 서비스

---

### 2. **docs/** - 프로젝트 문서 (9개 파일)
```
docs/
├── README.md                           # 문서 가이드
├── plan.md                            # 프로젝트 초기 계획
├── TFT_IMPLEMENTATION_SUMMARY.md      # TFT 구현 상세
├── REFACTORING_SUMMARY.md             # 리팩토링 내역
├── GIT_COMMIT_SUMMARY.md              # Git 히스토리
├── IMPLEMENTATION_SUMMARY.md          # 전체 구현 요약
├── AI_SERVER_REQUIREMENTS.md          # AI 서버 요구사항
├── ENV_SETUP_GUIDE.md                 # 환경 설정 가이드
└── LOCAL_MODEL_GUIDE.md               # 로컬 모델 가이드
```

**읽는 순서 (권장):**
1. `plan.md` - 프로젝트 이해
2. `ENV_SETUP_GUIDE.md` - 환경 설정
3. `TFT_IMPLEMENTATION_SUMMARY.md` - 핵심 기능
4. `IMPLEMENTATION_SUMMARY.md` - 전체 구조
5. `LOCAL_MODEL_GUIDE.md` - 모델 사용
6. `REFACTORING_SUMMARY.md` - 코드 품질
7. `GIT_COMMIT_SUMMARY.md` - 개발 히스토리

**빠른 링크:**
- 🚀 **시작하기** → `ENV_SETUP_GUIDE.md`
- 🤖 **TFT 모델** → `TFT_IMPLEMENTATION_SUMMARY.md`
- 🔧 **리팩토링** → `REFACTORING_SUMMARY.md`

---

### 3. **tests/** - 테스트 (7개 파일)
```
tests/
├── README.md                    # 테스트 가이드
├── test_tft_model.py           # TFT 모델 테스트 ⭐ 권장
├── test_model.py               # 기본 모델 테스트
├── test_simulation_api.py      # API 테스트
├── check_files.py              # 파일 검증
├── check_onnx.py               # ONNX 검증
└── inspect_pkl.py              # PKL 검증
```

**실행 방법:**
```bash
# 주요 테스트
python tests/test_tft_model.py

# 기본 테스트
python tests/test_model.py

# 파일 검증
python tests/check_files.py
python tests/check_onnx.py
python tests/inspect_pkl.py
```

**테스트 커버리지:**
- ✅ 모델 로딩 및 추론
- ✅ Feature override
- ✅ 데이터 검증
- ✅ 에러 핸들링
- ✅ API 엔드포인트

---

### 4. **scripts/** - 유틸리티 (3개 파일)
```
scripts/
├── README.md                    # 스크립트 가이드
├── inspect_onnx_inputs.py      # ONNX 구조 분석
└── inspect_pkl.py              # PKL 정보 확인
```

**사용 시나리오:**
```bash
# 1. 새 모델 파일 받았을 때
python scripts/inspect_onnx_inputs.py
python scripts/inspect_pkl.py

# 2. Feature 개수 불일치 에러
python scripts/inspect_onnx_inputs.py  # 기대하는 feature 수
python scripts/inspect_pkl.py          # 실제 feature 수

# 3. 모델 업데이트 후 검증
python scripts/inspect_onnx_inputs.py
python scripts/inspect_pkl.py
```

---

### 5. **migrations/** - DB 마이그레이션
```
migrations/
├── 001_add_top6_to_top20_factors.sql
└── 002_refactor.sql
```

**실행 방법:**
```bash
psql -U username -d dbname -f migrations/001_add_top6_to_top20_factors.sql
psql -U username -d dbname -f migrations/002_refactor.sql
```

---

### 6. **temp/** - 임시/모델 파일 (.gitignore)
```
temp/
├── 60d_20260206.onnx              # ONNX 모델 파일
└── 60d_preprocessing_20260206.pkl # 전처리 정보
```

**주의사항:**
- Git에 추적되지 않음 (.gitignore)
- 로컬 모드 사용 시 필수
- 파일명 형식: `{length}d_{date}.{ext}`

---

## 📊 통계

| 항목 | 개수 |
|------|------|
| **문서 파일** | 9개 (docs/) |
| **테스트 파일** | 7개 (tests/) |
| **스크립트** | 3개 (scripts/) |
| **API 라우터** | 5개 (app/routers/) |
| **ML 모듈** | 2개 (app/ml/) |
| **DB 마이그레이션** | 2개 (migrations/) |

---

## 🎯 주요 진입점

### 개발자용
1. **서버 시작**: `main.py`
2. **설정 관리**: `app/config.py`
3. **API 문서**: http://localhost:8000/docs

### 테스트용
1. **모델 테스트**: `tests/test_tft_model.py`
2. **파일 검증**: `tests/check_files.py`
3. **ONNX 분석**: `scripts/inspect_onnx_inputs.py`

### 문서용
1. **시작 가이드**: `docs/ENV_SETUP_GUIDE.md`
2. **구현 상세**: `docs/TFT_IMPLEMENTATION_SUMMARY.md`
3. **전체 README**: `README.md`

---

## 🔄 프로젝트 네비게이션

```
시작하기
  └─> README.md (루트)
      └─> docs/ENV_SETUP_GUIDE.md
          └─> 환경 설정 완료
              └─> tests/test_tft_model.py (테스트)
                  └─> main.py (서버 시작)
                      └─> http://localhost:8000/docs
```

---

## 📝 파일명 규칙

### Python 파일
- `test_*.py` - 테스트 파일
- `*_service.py` - 서비스 클래스
- `*_loader.py` - 로더 클래스
- `inspect_*.py` - 검사 스크립트
- `check_*.py` - 검증 스크립트

### 문서 파일
- `README.md` - 폴더/프로젝트 설명
- `*_SUMMARY.md` - 요약 문서
- `*_GUIDE.md` - 가이드 문서
- `*_REQUIREMENTS.md` - 요구사항 문서

### 마이그레이션
- `001_*.sql` - 순차 번호 포함
- 설명적인 이름 사용

---

## ✅ 폴더 정리 체크리스트

- [x] MD 문서 → `docs/`로 이동
- [x] 테스트 파일 → `tests/`로 통합
- [x] 검사 스크립트 → `scripts/`로 분리
- [x] test/ → tests/로 이름 변경
- [x] 각 폴더에 README.md 추가
- [x] 루트 README.md 업데이트
- [x] .gitignore 정리
- [x] Git 커밋 완료

---

**프로젝트 구조 정리 완료!** 🎉

모든 파일이 체계적으로 정리되어 가독성과 유지보수성이 대폭 향상되었습니다.
