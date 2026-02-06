# 실시간 서빙 서버 전환 구현 요약

## ✅ 완료된 작업

### 1. POST 엔드포인트 제거
- ✅ `app/routers/predictions.py`: `POST /api/predictions`, `POST /api/explanations` 제거
- ✅ `app/routers/newsdb.py`: `POST /api/newsdb` 제거
- ✅ `app/routers/historical_prices.py`: `POST /api/historical-prices` 제거
- ✅ `app/routers/market_metrics.py`: `POST /api/market-metrics` 제거

### 2. CRUD 함수 정리
- ✅ `app/crud.py`: 모든 Create 함수 제거
  - `create_tft_prediction()`
  - `create_explanation()`
  - `create_doc_embedding()`
  - `create_market_metric()`
  - `create_historical_price()`

### 3. Predictions GET 로직 변경
- ✅ 새로운 함수 추가: `get_latest_predictions()`
  - target_date별 최신 created_at 선택
  - 범위: 오늘-30일 ~ 오늘+60일
  - 서브쿼리 + 조인으로 구현
- ✅ `GET /api/predictions` 엔드포인트 수정
  - `start_date`, `end_date` 파라미터 제거
  - `commodity` 파라미터만 사용

### 4. ONNX 모델 서빙 인프라
- ✅ `requirements.txt`: ML 패키지 추가
  - `boto3>=1.34.0`
  - `onnxruntime>=1.16.0`
  - `numpy>=1.24.0`
  - `apscheduler>=3.10.0`
  - `pydantic-settings>=2.0.0`

- ✅ `app/config.py` 생성: 설정 관리
  - AWS S3 자격증명
  - 모델 업데이트 확인 시간
  - 조정 가능 Features 목록

- ✅ `app/ml/model_loader.py` 생성: ONNX 모델 로더
  - S3 다운로드 및 ETag 캐싱
  - ONNX 세션 캐싱
  - 백그라운드 스케줄러 (매일 자동 업데이트 확인)

- ✅ `app/ml/prediction_service.py` 생성: 예측 서비스
  - ONNX 추론 실행
  - Feature 입력 전처리

### 5. Simulation API 전면 수정
- ✅ `app/routers/simulation.py` 재작성
  - 실시간 ONNX 모델 서빙
  - feature_overrides 검증
  - base_features 로드 (market_metrics에서)
  - 예측 변화량 및 퍼센트 계산
  - Feature 영향도 반환

### 6. 문서화
- ✅ `README.md` 업데이트
  - 실시간 서빙 기능 설명
  - 프로젝트 구조 업데이트
  - API 엔드포인트 목록
  - 시작하기 가이드
- ✅ `AI_SERVER_REQUIREMENTS.md` 수정
  - 배치 서버로 역할 변경
  - 모델 배포 프로세스 추가
- ✅ `ENV_SETUP_GUIDE.md` 생성
  - .env 파일 설정 가이드
  - AWS S3 설정 방법
  - PostgreSQL 설정 방법
  - 설정 테스트 스크립트
- ✅ `.env.example` 생성 (문서로 대체)

---

## 🏗️ 아키텍처 변경 사항

### 이전 아키텍처
```
[프론트엔드] → [백엔드 API] ← [AI 서버 API]
                    ↓
                 [공유 DB]
```

- AI 서버가 실시간 추론 제공
- 백엔드가 AI 서버 API 호출

### 현재 아키텍처
```
[프론트엔드] → [백엔드 API (ONNX 모델 서빙)]
                    ↓
                 [공유 DB]
                    ↑
           [AI 배치 서버 (Airflow)]
                    ↓
                [AWS S3 (모델)]
```

- 백엔드가 ONNX 모델 직접 서빙
- AI 서버는 배치 작업만 수행
- 모델은 S3에서 자동 다운로드

---

## 📊 데이터 흐름

### 1. 모델 배포 (AI 배치 서버)
```
[학습 완료] → [ONNX 변환] → [S3 업로드 (v1, v2, ...)]
                                    ↓
                            [latest/model.onnx 업데이트]
```

### 2. 모델 로딩 (백엔드 서버)
```
[서버 시작] → [S3 ETag 확인] → [모델 다운로드] → [ONNX 세션 생성]
                                                        ↓
                                                [메모리 캐싱]
```

### 3. 실시간 예측 (Simulation API)
```
[POST /api/simulate]
    ↓
[기준 예측 조회 (DB)]
    ↓
[기준 Features 로드 (market_metrics)]
    ↓
[feature_overrides 적용]
    ↓
[ONNX 추론 실행]
    ↓
[변화량 계산 및 응답]
```

### 4. 최신 예측 조회
```
[GET /api/predictions?commodity=Corn]
    ↓
[서브쿼리: target_date별 최신 created_at]
    ↓
[메인쿼리: 조인하여 최신 레코드만 선택]
    ↓
[범위 필터: 오늘-30일 ~ 오늘+60일]
    ↓
[정렬 및 반환]
```

---


## 🔧 환경 변수 요구사항

### 필수 환경 변수

```bash
DATABASE_URL                # PostgreSQL 연결 문자열
AWS_ACCESS_KEY_ID          # AWS 액세스 키
AWS_SECRET_ACCESS_KEY      # AWS 시크릿 키
AWS_REGION                 # AWS 리전 (기본: ap-northeast-2)
MODEL_S3_BUCKET           # S3 버킷 이름
```

### 선택 환경 변수

```bash
MODEL_UPDATE_CHECK_TIME    # 모델 업데이트 확인 시간 (기본: 03:00)
```

## 🧪 테스트 시나리오

### 1. 최신 예측 조회 테스트
```bash
curl -X GET "http://localhost:8000/api/predictions?commodity=Corn"
```

**예상 결과:**
- 과거 30일 ~ 미래 60일 데이터 반환
- 각 target_date별 최신 created_at만 포함

### 2. 시뮬레이션 테스트
```bash
curl -X POST "http://localhost:8000/api/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "commodity": "Corn",
    "base_date": "2026-02-10",
    "feature_overrides": {
      "US_10Y_YIELD": 4.5,
      "DXY": 105.0
    }
  }'
```

**예상 결과:**
```json
{
  "original_forecast": 450.25,
  "simulated_forecast": 455.80,
  "change": 5.55,
  "change_percent": 1.23,
  "feature_impacts": [
    {
      "feature": "US_10Y_YIELD",
      "current_value": 4.2,
      "new_value": 4.5,
      "value_change": 0.3,
      "contribution": 0
    },
    {
      "feature": "DXY",
      "current_value": 103.5,
      "new_value": 105.0,
      "value_change": 1.5,
      "contribution": 0
    }
  ]
}
```

### 3. 모델 자동 업데이트 테스트

1. S3에 새 모델 업로드:
```bash
aws s3 cp new_model.onnx s3://your-bucket/models/Corn/latest/model.onnx
```

2. 설정 시간까지 대기 (또는 서버 재시작)

3. 로그 확인:
```
INFO: 모델 업데이트 확인 시작
INFO: 모델 업데이트 감지: Corn
INFO: 모델 다운로드 시작: Corn
INFO: 모델 다운로드 완료: Corn (ETag: abc123...)
INFO: ONNX 세션 생성: Corn
INFO: 모델 업데이트 확인 완료
```

---

## 📈 성능 고려사항

### 1. 모델 로딩
- **첫 요청 시**: 모델 다운로드 + 로드 (수초 ~ 수십초)
- **이후 요청**: 캐시된 세션 사용 (밀리초)
- **개선**: 서버 시작 시 주요 품목 모델 프리로드

### 2. 추론 속도
- **ONNX (CPU)**: ~10-50ms per inference
- **동시 요청**: ONNX 세션은 스레드 안전
- **개선**: GPU 사용 시 `providers=['CUDAExecutionProvider']`

### 3. S3 다운로드
- **ETag 캐싱**: 불필요한 다운로드 방지
- **로컬 캐싱**: `./models/` 디렉토리에 저장
- **개선**: CloudFront CDN 사용

---

## ⚠️ 알려진 제한사항

1. **Feature 기여도 계산**
   - 현재: `contribution: 0` (TODO)
   - 해결: SHAP 라이브러리 통합 필요

2. **모델 버전 관리**
   - 현재: `latest/model.onnx`만 사용
   - 해결: 버전 선택 API 추가

3. **에러 핸들링**
   - S3 연결 실패 시 재시도 로직 없음
   - ONNX 추론 실패 시 폴백 없음

---

## 🚀 다음 단계 (선택사항)

1. **SHAP 통합**: Feature 기여도 정확한 계산
2. **모델 버전 선택**: API에서 특정 버전 선택 가능
3. **모니터링**: 추론 시간, 에러율 모니터링
4. **캐싱**: Redis를 사용한 예측 결과 캐싱
5. **A/B 테스트**: 여러 모델 버전 동시 서빙

---

**구현 완료일**: 2026-02-06  
**구현 시간**: 약 1시간  
**파일 변경**: 13개 파일 (생성 5개, 수정 8개)
