# 로컬 모델 사용 가이드

## 📁 파일 구조

```
pro-nlp-finalproject-backend-nlp-10/
├── temp/
│   ├── 60d_20260206.onnx              # ONNX 모델 파일
│   └── 60d_preprocessing_20260206.pkl  # 전처리 정보 (스케일러 등)
├── .env
└── ...
```

---

## ⚙️ 설정 방법

### 1. .env 파일 설정

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# 모델 로딩 모드
MODEL_LOAD_MODE=local

# 로컬 모델 경로
LOCAL_MODEL_PATH=./temp
```

### 2. 모델 파일 준비

`temp/` 폴더에 다음 파일들을 배치:

- **ONNX 모델**: `*.onnx` (예: `60d_20260206.onnx`)
- **전처리 정보**: `*.pkl` (예: `60d_preprocessing_20260206.pkl`)

**Note:** 
- 여러 파일이 있으면 가장 최신 파일(파일명 정렬 기준)을 자동으로 사용
- pkl 파일은 선택사항 (없어도 동작하지만 전처리가 적용되지 않음)

---

## 🔍 전처리 정보 (pkl) 구조

pkl 파일에는 다음 정보가 포함되어야 합니다:

```python
{
    'scaler': StandardScaler(),  # 또는 다른 스케일러
    'feature_names': [
        'us_10y_yield',
        'dxy',
        'pdsi',
        'spi_30d',
        'spi_90d'
    ]
}
```

### pkl 파일 생성 예시

```python
import pickle
from sklearn.preprocessing import StandardScaler

# 스케일러 학습
scaler = StandardScaler()
scaler.fit(training_data)

# 전처리 정보 저장
preprocessing_info = {
    'scaler': scaler,
    'feature_names': ['us_10y_yield', 'dxy', 'pdsi', 'spi_30d', 'spi_90d']
}

with open('temp/60d_preprocessing_20260206.pkl', 'wb') as f:
    pickle.dump(preprocessing_info, f)
```

---

## 🚀 서버 실행

```bash
# 가상환경 활성화
source venv/bin/activate  # Windows: venv\Scripts\activate

# 서버 시작
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 로그 확인

서버 시작 시 다음 로그가 표시되어야 합니다:

```
INFO:     모델 로더 초기화: mode=local, path=temp
INFO:     로컬 모델 파일 발견: 60d_20260206.onnx
INFO:     전처리 정보 파일 발견: 60d_preprocessing_20260206.pkl
INFO:     ✅ ONNX 세션 생성 완료: 60d_20260206.onnx
INFO:     ✅ 전처리 정보 로드 완료: 60d_preprocessing_20260206.pkl
```

---

## 🧪 테스트

### 1. 시뮬레이션 API 테스트

```bash
curl -X POST "http://localhost:8000/api/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "commodity": "Corn",
    "base_date": "2026-02-10",
    "feature_overrides": {
      "US_10Y_YIELD": 4.5,
      "DXY": 105.0,
      "PDSI": -2.0,
      "SPI_30D": 0.5,
      "SPI_90D": 1.0
    }
  }'
```

### 2. Python으로 테스트

```python
import requests

response = requests.post(
    "http://localhost:8000/api/simulate",
    json={
        "commodity": "Corn",
        "base_date": "2026-02-10",
        "feature_overrides": {
            "US_10Y_YIELD": 4.5,
            "DXY": 105.0,
            "PDSI": -2.0,
            "SPI_30D": 0.5,
            "SPI_90D": 1.0
        }
    }
)

print(response.json())
```

---

## 🔄 모델 업데이트

### 새 모델 배포 방법

1. 새 ONNX 모델을 `temp/` 폴더에 복사
   ```bash
   cp new_model.onnx temp/60d_20260207.onnx
   cp new_preprocessing.pkl temp/60d_preprocessing_20260207.pkl
   ```

2. 서버 재시작 (또는 핫 리로드 대기)
   ```bash
   # Ctrl+C로 중지 후 재시작
   uvicorn main:app --reload
   ```

3. 자동으로 최신 파일 사용

### 기존 모델 삭제

```bash
# 오래된 모델 파일 삭제
rm temp/60d_20260206.onnx
rm temp/60d_preprocessing_20260206.pkl
```

---

## ⚠️ 주의사항

1. **파일명 규칙**
   - 파일명에 날짜가 포함되면 자동으로 최신 버전 선택
   - 알파벳 정렬 기준이므로 `YYYYMMDD` 형식 권장

2. **전처리 정보**
   - pkl 파일이 없으면 스케일링 없이 원시 값 사용
   - Feature 순서가 중요: pkl의 `feature_names` 순서대로 입력 배열 생성

3. **메모리 캐싱**
   - 모델은 메모리에 캐싱되어 재사용
   - 새 모델로 변경하려면 서버 재시작 필요

4. **commodity 파라미터**
   - 로컬 모드에서는 commodity 값 무시
   - 하나의 통합 모델만 사용

---

## 🔧 문제 해결

### "ONNX 모델 파일을 찾을 수 없습니다"

- `temp/` 폴더 존재 확인
- `.onnx` 파일이 폴더 내에 있는지 확인
- `LOCAL_MODEL_PATH` 환경 변수 확인

### "전처리 정보 파일이 없습니다"

- 경고 메시지이며 동작은 가능
- 전처리가 필요하면 `.pkl` 파일 추가

### 예측 결과가 이상함

1. pkl 파일의 스케일러가 학습 시 사용한 것과 동일한지 확인
2. Feature 순서가 올바른지 확인
3. 로그에서 "입력 features" 확인

---

## 📊 로깅

### 추론 시 로그 예시

```
INFO:     입력 features: {'US_10Y_YIELD': 4.5, 'DXY': 105.0, ...}
INFO:     전처리 적용 중 - scaler: StandardScaler
INFO:     스케일링 적용 완료
INFO:     추론 실행 - 입력 shape: (1, 5), dtype: float32
INFO:     예측 결과: 452.75
```

---

## 🚀 S3 모드로 전환

나중에 S3 사용이 필요하면 `.env` 수정:

```bash
MODEL_LOAD_MODE=s3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
MODEL_S3_BUCKET=your-bucket
```

코드 변경 없이 환경 변수만 수정하면 됩니다!
