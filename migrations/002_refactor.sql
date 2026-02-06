-- 1. 기존 테이블에 컬럼 추가
ALTER TABLE doc_embeddings ADD COLUMN title VARCHAR(255);
ALTER TABLE exp_pred ADD COLUMN impact_news JSON;

-- 2. 신규 테이블 생성
CREATE TABLE market_metrics (
    id SERIAL PRIMARY KEY,
    commodity VARCHAR(50),
    date DATE,
    metric_id VARCHAR(50),
    label VARCHAR(255),
    value VARCHAR(50),
    numeric_value FLOAT,
    trend FLOAT,
    impact VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_market_metrics_commodity ON market_metrics(commodity);
CREATE INDEX idx_market_metrics_date ON market_metrics(date);

CREATE TABLE historical_prices (
    id SERIAL PRIMARY KEY,
    commodity VARCHAR(50),
    date DATE,
    actual_price NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_historical_prices_commodity ON historical_prices(commodity);
CREATE INDEX idx_historical_prices_date ON historical_prices(date);