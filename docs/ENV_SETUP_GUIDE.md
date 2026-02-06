# 환경 설정 가이드

## 📝 .env 파일 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# ===========================================
# 데이터베이스 설정
# ===========================================
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# 예시:
# DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/commodity_db

# ===========================================
# AWS S3 설정 (ONNX 모델 저장소)
# ===========================================
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=ap-northeast-2
MODEL_S3_BUCKET=your-model-bucket-name

# 예시:
# AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
# AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# AWS_REGION=ap-northeast-2
# MODEL_S3_BUCKET=commodity-ml-models

# ===========================================
# 모델 업데이트 설정
# ===========================================
# 모델 업데이트 확인 시간 (KST, 24시간 형식)
MODEL_UPDATE_CHECK_TIME=03:00

# 설명:
# - 매일 이 시간에 S3의 모델 변경사항을 확인합니다
# - 새 모델이 감지되면 자동으로 다운로드 및 재로드합니다
# - 기본값: 03:00 (새벽 3시)
```

---

## 🔧 AWS S3 설정

### 1. S3 버킷 생성

1. AWS Management Console에서 S3 서비스로 이동
2. "버킷 만들기" 클릭
3. 버킷 이름 입력 (예: `commodity-ml-models`)
4. 리전 선택: `ap-northeast-2` (서울)
5. 버킷 생성

### 2. IAM 사용자 생성 및 권한 부여

1. IAM 서비스로 이동
2. "사용자" → "사용자 추가"
3. 액세스 유형: "프로그래밍 방식 액세스" 선택
4. 권한 설정:
   - "기존 정책 직접 연결"
   - `AmazonS3ReadOnlyAccess` 정책 연결 (읽기 전용)
   - 또는 커스텀 정책 사용 (아래 참고)

#### 커스텀 IAM 정책 (최소 권한)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:HeadObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-model-bucket-name",
                "arn:aws:s3:::your-model-bucket-name/*"
            ]
        }
    ]
}
```

5. 액세스 키 ID와 시크릿 키를 `.env` 파일에 저장

### 3. S3 모델 디렉토리 구조

```
s3://your-model-bucket-name/models/
├── Corn/
│   ├── v1/
│   │   └── model.onnx
│   ├── v2/
│   │   └── model.onnx
│   └── latest/
│       └── model.onnx  ← 백엔드 서버가 사용
├── Wheat/
│   ├── v1/
│   │   └── model.onnx
│   └── latest/
│       └── model.onnx
└── Soybean/
    └── latest/
        └── model.onnx
```

---

## 🐘 PostgreSQL 설정

### 로컬 개발 환경

1. PostgreSQL 설치 (macOS):
```bash
brew install postgresql
brew services start postgresql
```

2. 데이터베이스 생성:
```bash
createdb commodity_db
```

3. pgvector 확장 설치:
```bash
psql commodity_db
CREATE EXTENSION vector;
\q
```

4. `.env` 파일 업데이트:
```bash
DATABASE_URL=postgresql://postgres@localhost:5432/commodity_db
```

### AWS RDS (프로덕션)

1. RDS PostgreSQL 인스턴스 생성
2. pgvector 지원 버전 선택 (PostgreSQL 15+)
3. 퍼블릭 액세스 활성화 (또는 VPC 설정)
4. 보안 그룹 인바운드 규칙: 5432 포트 허용
5. 엔드포인트 주소로 `.env` 업데이트:
```bash
DATABASE_URL=postgresql://username:password@your-rds-endpoint.amazonaws.com:5432/commodity_db
```

---

## 🚀 서버 실행 전 체크리스트

- [ ] `.env` 파일 생성 및 모든 변수 설정 완료
- [ ] AWS S3 버킷 생성 및 IAM 권한 설정 완료
- [ ] S3에 최소 1개 품목의 `latest/model.onnx` 업로드 완료
- [ ] PostgreSQL 설치 및 데이터베이스 생성 완료
- [ ] pgvector 확장 설치 완료
- [ ] `requirements.txt` 패키지 설치 완료

---

## 🧪 설정 테스트

### 1. 데이터베이스 연결 테스트

```python
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.fetchone())
```

### 2. S3 연결 테스트

```python
import boto3
from app.config import settings

s3 = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)

# 버킷 목록 조회
buckets = s3.list_buckets()
print("Buckets:", [b['Name'] for b in buckets['Buckets']])

# 모델 파일 존재 여부 확인
try:
    s3.head_object(
        Bucket=settings.model_s3_bucket,
        Key="models/Corn/latest/model.onnx"
    )
    print("✅ 모델 파일 존재")
except:
    print("❌ 모델 파일 없음")
```

### 3. 서버 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

로그에서 다음을 확인:
- `모델 업데이트 확인 스케줄러 시작: 매일 03:00`
- 에러 메시지 없음

---

## ⚠️ 주의사항

1. **AWS 자격증명 보안**
   - `.env` 파일을 `.gitignore`에 추가
   - 절대 Git에 커밋하지 않기
   - 프로덕션에서는 AWS IAM Role 사용 권장

2. **모델 파일 크기**
   - ONNX 모델은 수백 MB가 될 수 있음
   - 첫 실행 시 다운로드 시간 고려
   - `./models/` 디렉토리를 `.gitignore`에 추가

3. **타임존 설정**
   - `MODEL_UPDATE_CHECK_TIME`은 서버의 로컬 시간 기준
   - AWS EC2의 경우 UTC 기준일 수 있으므로 확인 필요

4. **데이터베이스 마이그레이션**
   - 기존 DB가 있는 경우 `MIGRATION_GUIDE.md` 참고
   - 새 스키마로 마이그레이션 필요
