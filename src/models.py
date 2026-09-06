from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Form4Meta:
    """SEC 피드에서 추출한 공시 메타데이터"""
    accession_number: str
    cik: str
    clean_acc_no: str
    filing_date: str
    title: str
    index_url: str

@dataclass
class TransactionItem:
    """개별 매수/매도 내역"""
    security_title: str
    transaction_date: str
    shares: float
    price_per_share: float
    total_value: float
    trade_type: str = "BUY"  # "BUY" or "SELL"

@dataclass
class InsiderTrade:
    """필터링을 통과한 유의미한 내부자 거래 신호"""
    accession_number: str
    ticker: str
    issuer_name: str
    reporter_name: str
    role_title: str
    is_officer: bool
    is_director: bool
    is_ten_percent: bool
    total_shares: float
    avg_price: float
    total_value_usd: float
    shares_owned_after: float
    pct_increase: Optional[float]
    transaction_date: str
    sec_form4_url: str
    trade_type: str = "BUY"  # "BUY" or "SELL"
    items: List[TransactionItem] = field(default_factory=list)

    @property
    def role_summary(self) -> str:
        roles = []
        if self.role_title:
            roles.append(self.role_title)
        elif self.is_officer:
            roles.append("Officer")
        if self.is_director:
            roles.append("Director")
        if self.is_ten_percent:
            roles.append("10% Owner")
        return ", ".join(roles) if roles else "Insider"
