import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
import requests

from src.config import (
    SEC_USER_AGENT,
    SEC_ATOM_FEED_URL,
    SEC_13D_G_FEED_URL,
    SEC_ARCHIVE_BASE_URL,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    DEFAULT_FEED_COUNT,
)
from src.models import Form4Meta

logger = logging.getLogger(__name__)

class SECClient:
    def __init__(self, user_agent: str = SEC_USER_AGENT):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate"
        })
        self._last_request_time = 0.0

    def _rate_limit(self):
        """SEC EDGAR 초당 10회 요청 한도 준수 (최소 REQUEST_DELAY_SECONDS 대기)"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str) -> requests.Response:
        self._rate_limit()
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp

    def fetch_latest_form4_entries(self, count: int = DEFAULT_FEED_COUNT) -> List[Form4Meta]:
        """SEC 최신 공시 Atom 피드에서 Form 4 메타데이터 목록 수집 및 중복 제거"""
        url = SEC_ATOM_FEED_URL.format(count=count)
        logger.info(f"Fetching latest Form 4 entries from: {url}")
        resp = self._get(url)
        
        root = ET.fromstring(resp.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        entries: List[Form4Meta] = []
        seen_acc_nos = set()

        for entry in root.findall('atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            link_elem = entry.find('atom:link', ns)
            summary_elem = entry.find('atom:summary', ns)

            title = title_elem.text if title_elem is not None and title_elem.text else ""
            index_url = link_elem.attrib.get('href', '') if link_elem is not None else ""
            summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

            # summary에서 AccNo 추출: <b>AccNo:</b> 0001493152-26-041638
            acc_match = re.search(r"AccNo:\s*</b>\s*([0-9\-]+)", summary)
            if not acc_match:
                acc_match = re.search(r"([0-9]{10}-[0-9]{2}-[0-9]{6})", index_url)
            
            if not acc_match:
                continue

            acc_no = acc_match.group(1).strip()
            if acc_no in seen_acc_nos:
                continue
            seen_acc_nos.add(acc_no)

            # summary에서 Filed date 추출: <b>Filed:</b> 2026-09-04
            date_match = re.search(r"Filed:\s*</b>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", summary)
            filing_date = date_match.group(1) if date_match else ""

            # index_url에서 CIK와 clean_acc_no 추출
            # 예: https://www.sec.gov/Archives/edgar/data/2006392/000149315226041638/0001493152-26-041638-index.htm
            url_match = re.search(r"/data/([0-9]+)/([0-9]+)/", index_url)
            if url_match:
                cik = url_match.group(1)
                clean_acc_no = url_match.group(2)
            else:
                clean_acc_no = acc_no.replace("-", "")
                cik_match = re.search(r"\(([0-9]{10})\)", title)
                cik = cik_match.group(1) if cik_match else ""

            entries.append(Form4Meta(
                accession_number=acc_no,
                cik=cik,
                clean_acc_no=clean_acc_no,
                filing_date=filing_date,
                title=title,
                index_url=index_url
            ))

        logger.info(f"Retrieved {len(entries)} unique Form 4 submissions.")
        return entries

    def fetch_latest_13d_13g_entries(self, count: int = 50) -> List[Form4Meta]:
        """SEC 최신 Schedule 13D / 13G (기관 5%+ 지분 공시) 수집 및 중복 제거"""
        url = SEC_13D_G_FEED_URL.format(count=count)
        logger.info(f"Fetching latest Schedule 13D/G entries from: {url}")
        resp = self._get(url)

        root = ET.fromstring(resp.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        entries: List[Form4Meta] = []
        seen_acc_nos = set()

        for entry in root.findall('atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            link_elem = entry.find('atom:link', ns)
            summary_elem = entry.find('atom:summary', ns)

            title = title_elem.text if title_elem is not None and title_elem.text else ""
            index_url = link_elem.attrib.get('href', '') if link_elem is not None else ""
            summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

            # 13D 또는 13G 공시인지 필터링
            if "13D" not in title and "13G" not in title:
                continue

            acc_match = re.search(r"AccNo:\s*</b>\s*([0-9\-]+)", summary)
            if not acc_match:
                acc_match = re.search(r"([0-9]{10}-[0-9]{2}-[0-9]{6})", index_url)

            if not acc_match:
                continue

            acc_no = acc_match.group(1).strip()
            if acc_no in seen_acc_nos:
                continue
            seen_acc_nos.add(acc_no)

            date_match = re.search(r"Filed:\s*</b>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", summary)
            filing_date = date_match.group(1) if date_match else ""

            url_match = re.search(r"/data/([0-9]+)/([0-9]+)/", index_url)
            if url_match:
                cik = url_match.group(1)
                clean_acc_no = url_match.group(2)
            else:
                clean_acc_no = acc_no.replace("-", "")
                cik_match = re.search(r"\(([0-9]{10})\)", title)
                cik = cik_match.group(1) if cik_match else ""

            entries.append(Form4Meta(
                accession_number=acc_no,
                cik=cik,
                clean_acc_no=clean_acc_no,
                filing_date=filing_date,
                title=title,
                index_url=index_url
            ))

        logger.info(f"Retrieved {len(entries)} unique Schedule 13D/G submissions.")
        return entries

    def fetch_filings_by_ticker(self, ticker: str, count: int = 30) -> List[Form4Meta]:
        """특정 티커(예: TSLA, NVDA)의 최근 Form 4 및 Schedule 13D/13G 공시 목록 직접 조회"""
        from src.ticker_resolver import TickerResolver
        cik, title = TickerResolver.get_info_by_ticker(ticker)
        if not cik:
            logger.warning(f"Could not resolve CIK for ticker '{ticker}'")
            return []

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        logger.info(f"Fetching filings for ticker {ticker} (CIK: {cik}) from {url}")
        resp = self._get(url)
        data = resp.json()
        
        recent = data.get("filings", {}).get("recent", {})
        acc_nums = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        
        entries: List[Form4Meta] = []
        clean_cik = cik.lstrip("0")
        
        for i in range(len(forms)):
            form_type = forms[i]
            if form_type not in ("4", "4/A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"):
                continue
                
            acc_no = acc_nums[i]
            clean_acc_no = acc_no.replace("-", "")
            f_date = filing_dates[i]
            index_url = f"{SEC_ARCHIVE_BASE_URL}/{clean_cik}/{clean_acc_no}/{acc_no}-index.htm"
            
            entries.append(Form4Meta(
                accession_number=acc_no,
                cik=clean_cik,
                clean_acc_no=clean_acc_no,
                filing_date=f_date,
                title=f"{form_type} - {title or ticker}",
                index_url=index_url
            ))
            
            if len(entries) >= count:
                break
                
        logger.info(f"Retrieved {len(entries)} filings for {ticker}.")
        return entries

    def get_form4_xml_content(self, meta: Form4Meta) -> Optional[str]:
        """해당 submission의 원본 XML 다운로드 (Form 4 및 Schedule 13D/G 공용)"""
        if not meta.cik or not meta.clean_acc_no:
            return None

        directory_url = f"{SEC_ARCHIVE_BASE_URL}/{meta.cik}/{meta.clean_acc_no}/index.json"
        try:
            resp = self._get(directory_url)
            dir_data = resp.json()
            items = dir_data.get("directory", {}).get("item", [])
            
            xml_filename = None
            for item in items:
                name = item.get("name", "").lower()
                if name.endswith(".xml") and not name.startswith("xsl"):
                    # primary_doc.xml, doc4.xml, ownership.xml 또는 submission xml 우선순위
                    xml_filename = item.get("name")
                    if name == "primary_doc.xml" or "doc4" in name or "ownership" in name or "form4" in name:
                        break

            if not xml_filename:
                xml_filename = "primary_doc.xml"

            xml_url = f"{SEC_ARCHIVE_BASE_URL}/{meta.cik}/{meta.clean_acc_no}/{xml_filename}"
            xml_resp = self._get(xml_url)
            return xml_resp.text

        except Exception as e:
            logger.debug(f"Failed to fetch XML for {meta.accession_number}: {e}")
            return None

