-- ================================================================
-- Whale Radar (웨일 레이더) - Supabase Database Schema
-- 목적: 내부자 거래(Form 4) 및 기관 5%+ 대량 지분(Schedule 13D/13G) 영구 저장 및 온디맨드 검색
-- ================================================================

-- 1. trades 테이블 생성
CREATE TABLE IF NOT EXISTS public.trades (
    accession_number VARCHAR(64) PRIMARY KEY, -- SEC 고유 공시 접수 번호 (중복 방지 PK)
    ticker VARCHAR(16) NOT NULL,              -- 종목 티커 (예: NVDA, TSLA, ASPI)
    issuer_name TEXT,                         -- 발행 회사명
    reporter_name TEXT,                       -- 보고자 (내부자 임원 또는 대량보유 기관)
    role_title TEXT,                          -- 공식 직함
    role_summary TEXT,                        -- 직책 요약 (예: CEO, Director)
    is_officer BOOLEAN DEFAULT FALSE,         -- 임원 여부
    is_director BOOLEAN DEFAULT FALSE,        -- 이사 여부
    is_ten_percent BOOLEAN DEFAULT FALSE,     -- 10% 이상 대주주 여부
    total_shares NUMERIC,                     -- 거래/보유 주식 수
    avg_price NUMERIC,                        -- 평균 단가 (USD)
    total_value_usd NUMERIC,                  -- 총 거래 금액 (USD)
    shares_owned_after NUMERIC,               -- 거래 후 보유 주식 수
    pct_increase NUMERIC,                     -- 지분 변동률 (%)
    transaction_date VARCHAR(32),             -- 거래/공시 일자 (YYYY-MM-DD)
    sec_form4_url TEXT,                       -- SEC EDGAR 공시 원문 링크
    trade_type VARCHAR(16) DEFAULT 'BUY',     -- 거래 유형: 'BUY' (장내매수) 또는 'SELL' (장내매도)
    category VARCHAR(16) DEFAULT 'INSIDER',   -- 공시 구분: 'INSIDER' (Form 4), '13D' (경영참여), '13G' (단순투자)
    percent_of_class NUMERIC,                 -- 기관 지분율 (%) (Schedule 13D/13G 전용)
    investor_type TEXT,                       -- 기관 투자자 유형
    is_amendment BOOLEAN DEFAULT FALSE,       -- 정정 공시 여부 (/A)
    items JSONB DEFAULT '[]'::jsonb,          -- 분할 거래 상세 내역 (JSON 배열)
    created_at TIMESTAMPTZ DEFAULT NOW(),     -- DB 최초 적재 시각
    updated_at TIMESTAMPTZ DEFAULT NOW()      -- DB 갱신 시각
);

-- 2. 고속 검색 및 필터링을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON public.trades (ticker);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON public.trades (transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_category ON public.trades (category);
CREATE INDEX IF NOT EXISTS idx_trades_trade_type ON public.trades (trade_type);
CREATE INDEX IF NOT EXISTS idx_trades_total_value_usd ON public.trades (total_value_usd DESC);

-- 3. Row Level Security (RLS) 정책 활성화
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;

-- 모든 사용자(웹 대시보드 방문자)에게 SELECT(조회) 권한 부여
CREATE POLICY "Allow public read access" 
ON public.trades 
FOR SELECT 
USING (true);

-- 데이터 파이프라인 및 백엔드 스크래퍼에게 INSERT/UPDATE 권한 부여
CREATE POLICY "Allow insert/update for anon and authenticated" 
ON public.trades 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- 4. 업데이트 시각 자동 갱신 트리거 (선택사항)
CREATE OR REPLACE FUNCTION update_trades_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_trades_updated_at ON public.trades;
CREATE TRIGGER trg_trades_updated_at
BEFORE UPDATE ON public.trades
FOR EACH ROW
EXECUTE FUNCTION update_trades_updated_at();
