import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.models import InsiderTrade

logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "data", "trades.json")

def trade_to_dict(trade: InsiderTrade) -> Dict[str, Any]:
    """InsiderTrade dataclass를 JSON 직렬화 가능한 딕셔너리로 변환"""
    return {
        "accession_number": trade.accession_number,
        "ticker": trade.ticker,
        "issuer_name": trade.issuer_name,
        "reporter_name": trade.reporter_name,
        "role_title": trade.role_title,
        "role_summary": trade.role_summary,
        "is_officer": trade.is_officer,
        "is_director": trade.is_director,
        "is_ten_percent": trade.is_ten_percent,
        "total_shares": trade.total_shares,
        "avg_price": round(trade.avg_price, 2),
        "total_value_usd": round(trade.total_value_usd, 2),
        "shares_owned_after": trade.shares_owned_after,
        "pct_increase": round(trade.pct_increase, 2) if trade.pct_increase is not None else None,
        "transaction_date": trade.transaction_date,
        "sec_form4_url": trade.sec_form4_url,
        "trade_type": trade.trade_type,
        "category": trade.category,
        "percent_of_class": round(trade.percent_of_class, 2) if trade.percent_of_class is not None else None,
        "investor_type": trade.investor_type,
        "is_amendment": trade.is_amendment,
        "items": [
            {
                "security_title": item.security_title,
                "transaction_date": item.transaction_date,
                "shares": item.shares,
                "price_per_share": round(item.price_per_share, 2),
                "total_value": round(item.total_value, 2),
                "trade_type": item.trade_type,
            }
            for item in trade.items
        ]
    }

def load_existing_trades(file_path: str = DEFAULT_DATA_PATH) -> Dict[str, Any]:
    """기존 trades.json 파일 로드 (없으면 기본 빈 구조 반환)"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read existing data file {file_path}: {e}")
    
    return {
        "last_updated": None,
        "total_count": 0,
        "total_volume_usd": 0.0,
        "trades": []
    }

def save_trades(new_trades: List[InsiderTrade], file_path: str = DEFAULT_DATA_PATH) -> int:
    """새로 감지된 거래를 기존 데이터와 중복 없이 병합(Merge)하여 JSON 저장"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    existing_data = load_existing_trades(file_path)
    existing_trades = existing_data.get("trades", [])
    
    # Accession Number 기준으로 중복 체크
    seen_accessions = {t["accession_number"]: t for t in existing_trades}
    added_count = 0
    
    for trade in new_trades:
        trade_dict = trade_to_dict(trade)
        if trade.accession_number not in seen_accessions:
            seen_accessions[trade.accession_number] = trade_dict
            added_count += 1
        else:
            # 기존 항목 업데이트 (필요한 경우)
            seen_accessions[trade.accession_number] = trade_dict

    merged_trades = list(seen_accessions.values())
    
    # 최신 거래일자 순으로 정렬 (transaction_date DESC)
    merged_trades.sort(key=lambda x: (x.get("transaction_date", ""), x.get("total_value_usd", 0)), reverse=True)
    
    total_volume = sum(t.get("total_value_usd", 0.0) for t in merged_trades)
    
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_count": len(merged_trades),
        "total_volume_usd": round(total_volume, 2),
        "trades": merged_trades
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Saved {len(merged_trades)} trades to {file_path} (New added: {added_count})")
    return added_count
