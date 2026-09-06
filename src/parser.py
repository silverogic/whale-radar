import logging
import xml.etree.ElementTree as ET
from typing import Optional, List

from src.config import MIN_PURCHASE_VALUE_USD, TARGET_TRANSACTION_CODES
from src.models import Form4Meta, InsiderTrade, TransactionItem

logger = logging.getLogger(__name__)

def _get_node_text(element: Optional[ET.Element], path: str, default: str = "") -> str:
    if element is None:
        return default
    node = element.find(path)
    if node is not None and node.text:
        return node.text.strip()
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
        Form 4 XML을 파싱하여 다음 조건을 충족하는 내부자 거래(매수/매도)인지 검증:
        1. 경영진/이사/10% 지분권자 여부
        2. Transaction Code == 'P' (장내 매수) 또는 'S' (장내 매도)
        3. 동일 보고서 내 유효 거래 금액 합계 >= min_purchase_value ($100,000)
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

        if not (is_officer or is_director or is_ten_percent):
            return None

        # 3. Non-Derivative Transactions 파싱 (주식 장내 매수/매도)
        non_deriv_table = root.find("nonDerivativeTable")
        if non_deriv_table is None:
            return None

        tx_buckets = {"BUY": [], "SELL": []}
        latest_shares_following = None
        transaction_date = meta.filing_date

        for tx in non_deriv_table.findall("nonDerivativeTransaction"):
            tx_code = _get_node_text(tx, "transactionCoding/transactionCode").upper()
            if tx_code not in TARGET_TRANSACTION_CODES:
                continue

            trade_type = TARGET_TRANSACTION_CODES[tx_code]  # "BUY" or "SELL"

            # 취득(A) 또는 처분(D) 검증
            acq_disp = _get_node_text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value")
            if not acq_disp:
                acq_disp = _get_node_text(tx, "transactionAmounts/transactionAcquiredDisposedCode")
            acq_disp = acq_disp.upper()

            if trade_type == "BUY" and acq_disp != "A":
                continue
            if trade_type == "SELL" and acq_disp != "D":
                continue

            shares_str = _get_node_text(tx, "transactionAmounts/transactionShares/value")
            price_str = _get_node_text(tx, "transactionAmounts/transactionPricePerShare/value")
            tx_date_str = _get_node_text(tx, "transactionDate/value", meta.filing_date)
            sec_title = _get_node_text(tx, "securityTitle/value", "Common Stock")

            shares = _to_float(shares_str)
            price = _to_float(price_str)
            subtotal = shares * price

            if shares <= 0:
                continue

            tx_buckets[trade_type].append(TransactionItem(
                security_title=sec_title,
                transaction_date=tx_date_str,
                shares=shares,
                price_per_share=price,
                total_value=subtotal,
                trade_type=trade_type
            ))
            transaction_date = tx_date_str

            following_str = _get_node_text(tx, "postTransactionAmounts/sharesOwnedFollowingTransaction/value")
            if following_str:
                latest_shares_following = _to_float(following_str)

        # 4. 금액 임계값 검증 ($100,000 이상인 거래 타입 선택)
        buy_total = sum(it.total_value for it in tx_buckets["BUY"])
        sell_total = sum(it.total_value for it in tx_buckets["SELL"])

        selected_type = None
        valid_items = []
        total_value = 0.0

        if buy_total >= self.min_purchase_value and buy_total >= sell_total:
            selected_type = "BUY"
            valid_items = tx_buckets["BUY"]
            total_value = buy_total
        elif sell_total >= self.min_purchase_value:
            selected_type = "SELL"
            valid_items = tx_buckets["SELL"]
            total_value = sell_total
        else:
            return None

        total_shares = sum(it.shares for it in valid_items)
        if total_shares <= 0:
            return None

        # 5. 통계 계산 (가중평균가, 지분 변화율)
        avg_price = total_value / total_shares if total_shares > 0 else 0.0
        shares_after = latest_shares_following if latest_shares_following is not None else 0.0
        
        pct_increase = None
        if selected_type == "BUY" and shares_after > total_shares:
            prior_shares = shares_after - total_shares
            if prior_shares > 0:
                pct_increase = (total_shares / prior_shares) * 100.0
        elif selected_type == "SELL":
            prior_shares = shares_after + total_shares
            if prior_shares > 0:
                pct_increase = - (total_shares / prior_shares) * 100.0

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
            trade_type=selected_type,
            items=valid_items
        )

