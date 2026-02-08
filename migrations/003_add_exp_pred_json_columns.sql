-- ===================================================================
-- 마이그레이션: exp_pred 테이블에 JSON 컬럼 추가
-- 작성일: 2026-02-08
-- 설명: 예측 설명에 구조화된 데이터 저장을 위한 컬럼 추가
--       - top_factors: 상위 영향 요인 및 비율
--       - category_summary: 카테고리별 영향도 요약
-- ===================================================================

-- 1. JSON 컬럼 추가
ALTER TABLE exp_pred 
ADD COLUMN IF NOT EXISTS top_factors JSON,
ADD COLUMN IF NOT EXISTS category_summary JSON;

-- 2. 컬럼 코멘트 추가 (PostgreSQL)
COMMENT ON COLUMN exp_pred.content IS 'Executive Summary (LLM 생성 요약문)';
COMMENT ON COLUMN exp_pred.impact_news IS 'high_impact_news: 영향력 있는 뉴스 목록';
COMMENT ON COLUMN exp_pred.top_factors IS 'top_factors_impact_ratio: 상위 영향 요인 및 비율';
COMMENT ON COLUMN exp_pred.category_summary IS 'category_impact_ratio: 카테고리별 영향도 요약';

-- 3. 확인 쿼리 (실행하지 않음, 참고용)
-- SELECT 
--     column_name, 
--     data_type, 
--     is_nullable,
--     column_default
-- FROM information_schema.columns 
-- WHERE table_name = 'exp_pred' 
-- ORDER BY ordinal_position;

-- ===================================================================
-- 롤백 (필요시 실행)
-- ===================================================================
-- ALTER TABLE exp_pred DROP COLUMN IF EXISTS category_summary;
-- ALTER TABLE exp_pred DROP COLUMN IF EXISTS top_factors;
