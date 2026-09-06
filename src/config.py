import os

# SEC EDGAR API Headers (SEC 규정에 따라 User-Agent 필수: AppName ContactEmail)
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "WhaleRadar/1.0 (contact: admin@whaleradar.com)")

# SEC EDGAR Endpoints
SEC_ATOM_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&start=0&count={count}&output=atom"
SEC_13D_G_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=SC&company=&dateb=&owner=include&start=0&count={count}&output=atom"
SEC_ARCHIVE_BASE_URL = "https://www.sec.gov/Archives/edgar/data"

# Filtering Rules
MIN_PURCHASE_VALUE_USD = float(os.getenv("MIN_PURCHASE_VALUE_USD", "100000.0"))  # 최소 거래 금액 $100,000
MIN_INSTITUTION_PERCENT = float(os.getenv("MIN_INSTITUTION_PERCENT", "5.0"))    # 기관 최소 지분율 5.0%
TARGET_TRANSACTION_CODES = {
    "P": "BUY",   # Open Market Purchase (장내 매수)
    "S": "SELL"   # Open Market Sale (장내 매도)
}

# Network & Rate Limiting
REQUEST_DELAY_SECONDS = 0.15  # SEC Rate limit: 초당 10회 미만 (안전하게 0.15초 대기)
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_FEED_COUNT = 80  # 최신 공시 조회 건수
