import logging
import xml.etree.ElementTree as ET
from typing import Optional, List

from src.config import MIN_PURCHASE_VALUE_USD, TARGET_TRANSACTION_CODE
from src.models import Form4Meta, InsiderTrade, TransactionItem

logger = logging.getLogger(__name__)

def _get_node_text(element: Optional[ET.Element], path: str, default: str = "") -> str:
    if element is None:
        return default
    node = element.find(path)
    if node is not None and node.text:
        return node.text.strip()
    # child <value> tag check
    if node is not None:
        val_node = node.find("value")
        if val_node is not None and val_node.text:
            return val_node.text.strip()
    return default

def _to_bool(val: str) -> bool:
    return val.strip().lower() in ("1", "true", "yes")

def _to_float(val: str, default: float = 0.0) -> float:
    try:
        clean_val = val.replace(",", "").replace("$", "").strip()
        return float(clean_val)
    except (ValueError, TypeError):
        return default

class Form4Parser:
    def __init__(self, min_purchase_value: float = MIN_PURCHASE_VALUE_USD):
        self.min_purchase_value = min_purchase_value

    def parse_and_filter(self, xml_content: str, meta: Form4Meta) -> Optional[InsiderTrade]:
        """
        Form 4 XML을 파싱하여 다음 조건을 충족하는 내부자 매수인지 검증:
        1. 경영진/이사/10% 지분권자 여부
        2. Transaction Code == 'P' (Open Market Purchase)
        3. 동일 보고서 내 유효 매수 금액 합계 >= min_purchase_value ($100,000)
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.debug(f"XML parse error for {meta.accession_number}: {e}")
            return None

        # 1. Issuer 정보
        issuer = root.find("issuer")
        ticker = _get_node_text(issuer, "issuerTradingSymbol", "N/A")
        issuer_name = _get_node_text(issuer, "issuerName", meta.title)

        # 2. Reporting Owner & Relationship 정보
        rpt_owner = root.find("reportingOwner")
        reporter_name = _get_node_text(rpt_owner, "reportingOwnerId/rptOwnerName", "Unknown")
        rel_elem = rpt_owner.find("reportingOwnerRelationship") if rpt_owner is not None else None

        is_officer = _to_bool(_get_node_text(rel_elem, "isOfficer", "0"))
        is_director = _to_bool(_get_node_text(rel_elem, "isDirector", "0"))
        is_ten_percent = _to_bool(_get_node_text(rel_elem, "isTenPercentOwner", "0"))
        role_title = _get_node_text(rel_elem, "officerTitle", "")

        # 내부자 자격 여부 필터 (Officer, Director, 10% Owner 중 하나여야 함)
        if not (is_officer or is_director or is_ten_percent):
            return None

        # 3. Non-Derivative Transactions 파싱 (주식 장내 매수)
        non_deriv_table = root.find("nonDerivativeTable")
        if non_deriv_table is None:
            return None

        valid_items: List[TransactionItem] = []
        total_shares = 0.0
        total_value = 0.0
        latest_shares_following = None
        transaction_date = meta.filing_date

        for tx in non_deriv_table.findall("nonDerivativeTransaction"):
            # 거래 코드 확인: 'P' (Open Market Purchase)
            tx_code = _get_node_text(tx, "transactionCoding/transactionCode")
            if tx_code != TARGET_TRANSACTION_CODE:
                continue

            # 취득(A)인지 확인
            acq_disp = _get_node_text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value")
            if not acq_disp:
                acq_disp = _get_node_text(tx, "transactionAmounts/transactionAcquiredDisposedCode")
            if acq_disp.upper() != "A":
                continue

            # 주식 수 및 단가
            shares_str = _get_node_text(tx, "transactionAmounts/transactionShares/value")
            price_str = _get_node_text(tx, "transactionAmounts/transactionPricePerShare/value")
            tx_date_str = _get_node_text(tx, "transactionDate/value", meta.filing_date)
            sec_title = _get_node_text(tx, "securityTitle/value", "Common Stock")

            shares = _to_float(shares_str)
            price = _to_float(price_str)
            subtotal = shares * price

            if shares <= 0:
                continue

            valid_items.append(TransactionItem(
                security_title=sec_title,
                transaction_date=tx_date_str,
                shares=shares,
                price_per_share=price,
                total_value=subtotal
            ))

            total_shares += shares
            total_value += subtotal
            transaction_date = tx_date_str

            # 거래 후 보유 주식 수
            following_str = _get_node_text(tx, "postTransactionAmounts/sharesOwnedFollowingTransaction/value")
            if following_str:
                latest_shares_following = _to_float(following_str)

        # 4. 금액 임계값 검증 ($100,000 이상)
        if total_value < self.min_purchase_value or total_shares <= 0:
            return None

        # 5. 통계 계산 (가중평균가, 지분 변화율)
        avg_price = total_value / total_shares if total_shares > 0 else 0.0
        shares_after = latest_shares_following if latest_shares_following is not None else 0.0
        
        pct_increase = None
        if shares_after > total_shares:
            prior_shares = shares_after - total_shares
            if prior_shares > 0:
                pct_increase = (total_shares / prior_shares) * 100.0

        return InsiderTrade(
            accession_number=meta.accession_number,
            ticker=ticker,
            issuer_name=issuer_name,
            reporter_name=reporter_name,
            role_title=role_title,
            is_officer=is_officer,
            is_director=is_director,
            is_ten_percent=is_ten_percent,
            total_shares=total_shares,
            avg_price=avg_price,
            total_value_usd=total_value,
            shares_owned_after=shares_after,
            pct_increase=pct_increase,
            transaction_date=transaction_date,
            sec_form4_url=meta.index_url,
            items=valid_items
        )
