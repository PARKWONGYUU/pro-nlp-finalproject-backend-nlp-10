# 🔧 스크립트 및 유틸리티

이 폴더에는 개발 및 디버깅에 유용한 스크립트가 포함되어 있습니다.

## 📁 파일 목록

### 모델 검사 도구

#### **inspect_onnx_inputs.py**
ONNX 모델의 입력 구조를 분석하는 스크립트

**사용법:**
```bash
python scripts/inspect_onnx_inputs.py
```

**출력 정보:**
- 입력 텐서 이름 및 형태
- 예상되는 Feature 개수
- 데이터 타입 정보
- 모델 구조 요약

**예시 출력:**
```
모델 입력 구조:
  encoder_cont: [1, 60, 52]
  decoder_cont: [1, 7, 52]
  encoder_cat: [1, 60, 1]
  ...
```

---

#### **inspect_pkl.py**
PKL 전처리 정보 파일을 확인하는 스크립트

**사용법:**
```bash
python scripts/inspect_pkl.py
```

**출력 정보:**
- Scaler 정보 (StandardScaler 등)
- Feature 이름 목록
- 정규화 파라미터
- Encoder/Decoder 길이
- 타겟 정규화 정보

**예시 출력:**
```
전처리 정보:
  max_encoder_length: 60
  max_prediction_length: 7
  feature_names: ['close', 'open', ...]
  scalers: {...}
```

---

## 🚀 사용 시나리오

### 1. 새로운 모델 파일 받았을 때
```bash
# 모델 구조 확인
python scripts/inspect_onnx_inputs.py

# 전처리 정보 확인
python scripts/inspect_pkl.py
```

### 2. Feature 개수 불일치 에러 발생 시
```bash
# ONNX 모델이 기대하는 Feature 개수 확인
python scripts/inspect_onnx_inputs.py

# 실제 전처리 파일의 Feature 확인
python scripts/inspect_pkl.py
```

### 3. 모델 업데이트 후 검증
```bash
# 두 스크립트를 실행하여 일관성 확인
python scripts/inspect_onnx_inputs.py
python scripts/inspect_pkl.py
```

---

## 📝 참고사항

- 스크립트 실행 전에 `temp/` 폴더에 모델 파일이 있어야 합니다
- 필요한 패키지: `onnxruntime`, `numpy`
- 모델 파일 경로는 스크립트 내에서 수정 가능

---

## 🔍 트러블슈팅

### 문제: "File not found" 에러
**해결:** `temp/` 폴더에 `.onnx` 또는 `.pkl` 파일이 있는지 확인

### 문제: Feature 개수 불일치
**해결:** 
1. `inspect_onnx_inputs.py`로 모델 요구사항 확인
2. `inspect_pkl.py`로 전처리 정보 확인
3. 두 개가 일치하는지 검증

### 문제: Import 에러
**해결:**
```bash
pip install onnxruntime numpy pickle5
```
