-- 마이그레이션: tft_pred 테이블에 top6~top20 컬럼 추가
-- 작성일: 2026-02-04
-- 설명: 예측 모델의 영향 요인을 5개에서 20개로 확장

-- top6~top20 factor와 impact 컬럼 추가
ALTER TABLE tft_pred 
ADD COLUMN top6_factor VARCHAR(255),
ADD COLUMN top6_impact FLOAT,
ADD COLUMN top7_factor VARCHAR(255),
ADD COLUMN top7_impact FLOAT,
ADD COLUMN top8_factor VARCHAR(255),
ADD COLUMN top8_impact FLOAT,
ADD COLUMN top9_factor VARCHAR(255),
ADD COLUMN top9_impact FLOAT,
ADD COLUMN top10_factor VARCHAR(255),
ADD COLUMN top10_impact FLOAT,
ADD COLUMN top11_factor VARCHAR(255),
ADD COLUMN top11_impact FLOAT,
ADD COLUMN top12_factor VARCHAR(255),
ADD COLUMN top12_impact FLOAT,
ADD COLUMN top13_factor VARCHAR(255),
ADD COLUMN top13_impact FLOAT,
ADD COLUMN top14_factor VARCHAR(255),
ADD COLUMN top14_impact FLOAT,
ADD COLUMN top15_factor VARCHAR(255),
ADD COLUMN top15_impact FLOAT,
ADD COLUMN top16_factor VARCHAR(255),
ADD COLUMN top16_impact FLOAT,
ADD COLUMN top17_factor VARCHAR(255),
ADD COLUMN top17_impact FLOAT,
ADD COLUMN top18_factor VARCHAR(255),
ADD COLUMN top18_impact FLOAT,
ADD COLUMN top19_factor VARCHAR(255),
ADD COLUMN top19_impact FLOAT,
ADD COLUMN top20_factor VARCHAR(255),
ADD COLUMN top20_impact FLOAT;

-- 컬럼 추가 확인
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'tft_pred' 
  AND column_name LIKE 'top%'
ORDER BY column_name;

-- 완료 메시지
SELECT 'tft_pred 테이블에 top6~top20 컬럼 추가 완료' AS status;
