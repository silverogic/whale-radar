import os
import json
import logging
from typing import Optional, Tuple, Dict
import requests

from src.config import SEC_USER_AGENT

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "company_tickers.json")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

class TickerResolver:
    """SEC CIK 번호를 티커(Ticker) 및 회사명으로 100% 오차 없이 매핑하는 캐시 리졸버"""
    
    _cik_to_ticker: Dict[str, Tuple[str, str]] = {}
    _ticker_to_info: Dict[str, Tuple[str, str]] = {}
    _loaded = False

    @classmethod
    def load(cls):
        if cls._loaded:
            return

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

        # 1. 로컬 캐시 확인
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._populate(data)
                    cls._loaded = True
                    logger.info(f"Loaded {len(cls._cik_to_ticker)} ticker mappings from local cache.")
                    return
            except Exception as e:
                logger.warning(f"Failed to read local ticker cache: {e}")

        # 2. 캐시가 없으면 SEC 공식 서버에서 다운로드
        try:
            logger.info("Downloading company_tickers.json from SEC EDGAR...")
            headers = {"User-Agent": SEC_USER_AGENT}
            resp = requests.get(SEC_TICKERS_URL, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                with open(CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                cls._populate(data)
                cls._loaded = True
                logger.info(f"Successfully cached {len(cls._cik_to_ticker)} ticker mappings.")
        except Exception as e:
            logger.error(f"Failed to download company tickers from SEC: {e}")

    @classmethod
    def _populate(cls, data: dict):
        cls._cik_to_ticker.clear()
        cls._ticker_to_info.clear()
        for item in data.values():
            cik_int = item.get("cik_str")
            ticker = item.get("ticker", "").strip().upper()
            title = item.get("title", "").strip()
            if cik_int is not None and ticker:
                # 숫자, 0 패딩된 10자리, 일반 문자열 모두 매핑
                cls._cik_to_ticker[str(cik_int)] = (ticker, title)
                cls._cik_to_ticker[f"{cik_int:010d}"] = (ticker, title)
                cls._ticker_to_info[ticker] = (f"{cik_int:010d}", title)

    @classmethod
    def get_ticker_and_title(cls, cik: str) -> Tuple[Optional[str], Optional[str]]:
        """CIK로 (Ticker, CompanyName) 조회 (없으면 (None, None))"""
        cls.load()
        clean_cik = cik.lstrip("0")
        padded_cik = cik.zfill(10)
        
        if cik in cls._cik_to_ticker:
            return cls._cik_to_ticker[cik]
        if clean_cik in cls._cik_to_ticker:
            return cls._cik_to_ticker[clean_cik]
        if padded_cik in cls._cik_to_ticker:
            return cls._cik_to_ticker[padded_cik]

        return None, None

    @classmethod
    def get_info_by_ticker(cls, ticker: str) -> Tuple[Optional[str], Optional[str]]:
        """티커(예: 'NVDA', 'TSLA')로 (10자리 CIK, 회사명) 조회"""
        cls.load()
        return cls._ticker_to_info.get(ticker.strip().upper(), (None, None))
