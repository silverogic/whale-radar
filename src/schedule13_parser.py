import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any

from src.config import MIN_INSTITUTION_PERCENT
from src.models import Form4Meta, InsiderTrade
from src.ticker_resolver import TickerResolver

logger = logging.getLogger(__name__)

INVESTOR_TYPE_MAP = {
    "BD": "증권사 (Broker-Dealer)",
    "BK": "은행 (Bank)",
    "IC": "보험사 (Insurance Company)",
    "IV": "투자회사 (Investment Company)",
    "IA": "투자자문사/헤지펀드 (Investment Adviser)",
    "EP": "직원퇴직연금 (Employee Benefit Plan)",
    "HC": "지주회사 (Parent Holding Company)",
    "SA": "저축조합 (Savings Association)",
    "CP": "교회연금 (Church Plan)",
    "CO": "일반법인 (Corporation)",
    "PN": "파트너십/펀드 (Partnership)",
    "IN": "개인 대주주 (Individual)",
    "OO": "기타 기관 (Other)"
}

def _local_tag(elem: ET.Element) -> str:
    """XML 네임스페이스 접두사 제거한 순수 로컬 태그명 반환"""
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

def _find_child_by_local_name(parent: Optional[ET.Element], local_name: str) -> Optional[ET.Element]:
    if parent is None:
        return None
    for child in parent:
        if _local_tag(child).lower() == local_name.lower():
            return child
    return None

def _find_all_children_by_local_name(parent: Optional[ET.Element], local_name: str) -> List[ET.Element]:
    if parent is None:
        return []
    return [child for child in parent if _local_tag(child).lower() == local_name.lower()]

def _get_text(parent: Optional[ET.Element], path_parts: List[str], default: str = "") -> str:
    curr = parent
    for part in path_parts:
        curr = _find_child_by_local_name(curr, part)
        if curr is None:
            return default
    if curr is not None and curr.text:
        return curr.text.strip()
    return default

def _to_float(val: str, default: float = 0.0) -> float:
    try:
        clean = val.replace(",", "").replace("%", "").replace("$", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return default

class Schedule13Parser:
    """Schedule 13D / 13G (기관/증권사 5%+ 대량 지분 보고서) 전용 정밀 파서"""

    def __init__(self, min_percent: float = MIN_INSTITUTION_PERCENT):
        self.min_percent = min_percent

    def parse_and_filter(self, xml_content: str, meta: Form4Meta) -> Optional[InsiderTrade]:
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.debug(f"XML parse error in 13D/G ({meta.accession_number}): {e}")
            return None

        # 1. submissionType 확인
        header_data = _find_child_by_local_name(root, "headerData")
        sub_type = _get_text(header_data, ["submissionType"], meta.title).upper()

        if "13D" in sub_type:
            category = "13D"
        elif "13G" in sub_type:
            category = "13G"
        else:
            return None

        is_amendment = "/A" in sub_type

        # 2. Issuer(대상 기업) 정보 추출
        form_data = _find_child_by_local_name(root, "formData")
        cover_page = _find_child_by_local_name(form_data, "coverPageHeader")
        issuer_info = _find_child_by_local_name(cover_page, "issuerInfo")

        issuer_cik = _get_text(issuer_info, ["issuerCIK"])
        if not issuer_cik:
            issuer_cik = _get_text(issuer_info, ["issuerCik"])
            
        issuer_name = _get_text(issuer_info, ["issuerName"], meta.title)

        # CIK로 정확한 티커 및 회사명 획득
        ticker = None
        if issuer_cik:
            ticker, resolved_title = TickerResolver.get_ticker_and_title(issuer_cik)
            if resolved_title and not issuer_name:
                issuer_name = resolved_title

        if not ticker:
            ticker = "N/A"

        # 3. 기준 일자(Event Date) 추출
        event_date = _get_text(cover_page, ["dateOfEvent"])
        if not event_date:
            event_date = _get_text(cover_page, ["eventDateRequiresFilingThisStatement"])
        if not event_date:
            event_date = meta.filing_date

        # 4. Reporting Persons (보고 기관/투자자) 정보 추출 (13D 및 13G 스키마 모두 지원)
        rpt_person_list = []
        rpt_persons_container = _find_child_by_local_name(form_data, "reportingPersons")
        if rpt_persons_container is not None:
            rpt_person_list.extend(_find_all_children_by_local_name(rpt_persons_container, "reportingPersonInfo"))

        # 13G 전용 태그 지원 (coverPageHeaderReportingPersonDetails)
        if form_data is not None:
            for child in form_data:
                tag_name = _local_tag(child).lower()
                if "reportingperson" in tag_name and child not in rpt_person_list and child is not rpt_persons_container:
                    rpt_person_list.append(child)

        if not rpt_person_list:
            return None

        # 여러 reportingPersonInfo 중 가장 지분율이 높은 주요 기관 선택
        best_investor_name = "Unknown Institution"
        best_shares = 0.0
        best_percent = 0.0
        best_inv_type_code = ""

        for rpt in rpt_person_list:
            inv_name = _get_text(rpt, ["reportingPersonName"], "Unknown")
            
            # 주식 수 추출 (13D: aggregateAmountOwned, 13G: reportingPersonBeneficiallyOwnedAggregateNumberOfShares)
            shares_str = _get_text(rpt, ["aggregateAmountOwned"])
            if not shares_str:
                shares_str = _get_text(rpt, ["reportingPersonBeneficiallyOwnedAggregateNumberOfShares"])
                
            # 지분율 추출 (13D: percentOfClass, 13G: classPercent)
            pct_str = _get_text(rpt, ["percentOfClass"])
            if not pct_str:
                pct_str = _get_text(rpt, ["classPercent"])

            type_code = _get_text(rpt, ["typeOfReportingPerson"])

            shares = _to_float(shares_str)
            pct = _to_float(pct_str)

            if pct > best_percent or (best_percent == 0 and shares > best_shares):
                best_investor_name = inv_name
                best_shares = shares
                best_percent = pct
                best_inv_type_code = type_code

        # 지분율 5% 이상 필터링 검증
        if best_percent < self.min_percent and best_percent > 0:
            return None

        investor_type_desc = INVESTOR_TYPE_MAP.get(best_inv_type_code.upper(), best_inv_type_code)

        return InsiderTrade(
            accession_number=meta.accession_number,
            ticker=ticker,
            issuer_name=issuer_name,
            reporter_name=best_investor_name,
            role_title=investor_type_desc,
            is_officer=False,
            is_director=False,
            is_ten_percent=(best_percent >= 10.0),
            total_shares=best_shares,
            avg_price=0.0,
            total_value_usd=0.0,
            shares_owned_after=best_shares,
            pct_increase=best_percent,
            transaction_date=event_date,
            sec_form4_url=meta.index_url,
            trade_type="BUY",  # 지분 보유/취득
            category=category,  # "13D" or "13G"
            percent_of_class=best_percent,
            investor_type=investor_type_desc,
            is_amendment=is_amendment,
            items=[]
        )
