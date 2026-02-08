# exp_pred 테이블 마이그레이션 가이드

## 개요

`exp_pred` 테이블에 구조화된 예측 설명 데이터를 저장하기 위한 JSON 컬럼 2개를 추가합니다.

## 변경 사항

### 추가된 컬럼
- `top_factors` (JSON): 상위 영향 요인 및 비율
- `category_summary` (JSON): 카테고리별 영향도 요약

### 기존 데이터 영향
- 기존 데이터는 영향을 받지 않습니다.
- 새 컬럼은 `NULL` 허용으로 추가됩니다.
- 기존 예측 설명은 그대로 유지됩니다.

## 마이그레이션 실행

### 방법 1: PostgreSQL 직접 실행 (권장)

```bash
# 1. PostgreSQL 접속
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME>

# 2. 마이그레이션 SQL 실행
\i migrations/003_add_exp_pred_json_columns.sql
```

### 방법 2: psql 명령어로 직접 실행

```bash
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f migrations/003_add_exp_pred_json_columns.sql
```

### 방법 3: SQL만 실행

```sql
ALTER TABLE exp_pred 
ADD COLUMN IF NOT EXISTS top_factors JSON,
ADD COLUMN IF NOT EXISTS category_summary JSON;

COMMENT ON COLUMN exp_pred.content IS 'Executive Summary (LLM 생성 요약문)';
COMMENT ON COLUMN exp_pred.impact_news IS 'high_impact_news: 영향력 있는 뉴스 목록';
COMMENT ON COLUMN exp_pred.top_factors IS 'top_factors_impact_ratio: 상위 영향 요인 및 비율';
COMMENT ON COLUMN exp_pred.category_summary IS 'category_impact_ratio: 카테고리별 영향도 요약';
```

## 마이그레이션 확인

```sql
-- 1. 스키마 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'exp_pred' 
ORDER BY ordinal_position;

-- 2. 기존 데이터 확인
SELECT id, pred_id, 
       top_factors IS NULL as top_factors_is_null, 
       category_summary IS NULL as category_summary_is_null
FROM exp_pred 
LIMIT 5;
```

**예상 결과:**
- `top_factors`와 `category_summary` 컬럼이 추가되어야 합니다.
- 기존 레코드의 해당 컬럼 값은 `NULL`이어야 합니다.

## 배치 서버에서의 사용

### 새로운 데이터 구조

```json
{
  "pred_id": 1,
  "content": "Executive Summary 텍스트...",
  "llm_model": "gpt-4",
  "impact_news": [
    {
      "title": "[2026-02-02] 뉴스 제목",
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
    }
  ],
  "category_summary": [
    {
      "category": "시장 구조 (Market Structure)",
      "impact_sum": 1.0267,
      "ratio": 0.5134
    }
  ]
}
```

### API 호출 예시

```bash
curl -X POST "http://44.252.76.158:8000/api/explanations" \
  -H "Content-Type: application/json" \
  -d '{
    "pred_id": 1,
    "content": "이번 옥수수 선물 가격 전망은...",
    "llm_model": "gpt-4",
    "impact_news": [...],
    "top_factors": [...],
    "category_summary": [...]
  }'
```

## 롤백 (필요시)

```sql
-- 컬럼 삭제 (주의: 데이터 손실 발생)
ALTER TABLE exp_pred DROP COLUMN IF EXISTS category_summary;
ALTER TABLE exp_pred DROP COLUMN IF EXISTS top_factors;
```

## 문서 참고

- **DB 스키마**: `docs/DATABASE_SCHEMA.md` - `exp_pred` 테이블 섹션 참고
- **Batch API**: `docs/BATCH_API_GUIDE.md` - "2. 예측 설명 (Explanations)" 섹션 참고
- **코드**: 
  - `app/datatable.py` - ORM 모델
  - `app/dataschemas.py` - Pydantic 스키마
  - `app/crud.py` - CRUD 함수 (수정 불필요)

## 주의사항

1. **외래키 제약**: `pred_id`는 반드시 `tft_pred.id`에 존재해야 합니다.
2. **JSON 유효성**: 잘못된 JSON 형식은 에러를 발생시킵니다.
3. **NULL 허용**: 새 컬럼들은 선택적(Optional)이므로 `NULL` 값이 허용됩니다.
4. **기존 데이터**: 마이그레이션 후 기존 데이터는 영향을 받지 않으며, 새 컬럼은 `NULL`입니다.

## 타임라인

- **마이그레이션 실행**: 배치 서버 배포 전
- **API 업데이트**: 마이그레이션 완료 후 배치 서버 코드 배포
- **데이터 전환**: 새로운 구조로 예측 설명 생성 시작
