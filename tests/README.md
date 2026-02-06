# 🧪 테스트

이 폴더에는 프로젝트의 모든 테스트 파일이 포함되어 있습니다.

## 📁 파일 구조

### 주요 테스트
- **test_tft_model.py** - TFT 모델 테스트 (권장)
  - 기본 예측 테스트
  - Feature override 테스트
  - 시나리오별 테스트
  - Mock 데이터 생성

- **test_model.py** - 기본 모델 테스트
  - 모델 로딩 테스트
  - 입력/출력 검증
  - 다양한 데이터 길이 테스트

- **test_simulation_api.py** - 시뮬레이션 API 테스트
  - API 엔드포인트 테스트
  - 요청/응답 검증

### 검증 도구
- **check_files.py** - 모델 파일 검증
- **check_onnx.py** - ONNX 모델 구조 검증
- **inspect_pkl.py** - PKL 전처리 정보 확인

## 🚀 테스트 실행 방법

### 1. 전체 TFT 모델 테스트
```bash
python tests/test_tft_model.py
```

### 2. 기본 모델 테스트
```bash
python tests/test_model.py
```

### 3. API 테스트 (서버 실행 필요)
```bash
# 터미널 1: 서버 실행
uvicorn main:app --reload

# 터미널 2: 테스트 실행
python tests/test_simulation_api.py
```

### 4. 파일 검증
```bash
# 모델 파일 확인
python tests/check_files.py

# ONNX 구조 확인
python tests/check_onnx.py

# PKL 정보 확인
python tests/inspect_pkl.py
```

## ✅ 테스트 결과 예시

```
🎉 모든 테스트 통과!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 기본 예측 테스트: 성공
✅ Feature Override 테스트: 성공
✅ 데이터 길이 테스트: 성공
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 📝 참고사항

- 테스트 실행 전에 `temp/` 폴더에 ONNX 및 PKL 파일이 있어야 합니다
- 가상환경 활성화 필요: `source venv/bin/activate`
- 필요한 패키지: `pip install -r requirements.txt`
