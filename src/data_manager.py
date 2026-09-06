import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.models import InsiderTrade
from src.config import get_realtime_usd_krw_rate

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

def save_trades(new_trades: List[InsiderTrade], file_path: str = DEFAULT_DATA_PATH, usd_to_krw_rate: float = None) -> int:
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
    total_buy_volume = sum(t.get("total_value_usd", 0.0) for t in merged_trades if t.get("trade_type") == "BUY" and t.get("category", "INSIDER") == "INSIDER")
    total_sell_volume = sum(t.get("total_value_usd", 0.0) for t in merged_trades if t.get("trade_type") == "SELL")
    
    current_rate = usd_to_krw_rate if usd_to_krw_rate is not None else get_realtime_usd_krw_rate()

    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "usd_to_krw_rate": round(current_rate, 2),
        "total_count": len(merged_trades),
        "total_volume_usd": round(total_volume, 2),
        "total_buy_volume_usd": round(total_buy_volume, 2),
        "total_sell_volume_usd": round(total_sell_volume, 2),
        "trades": merged_trades
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Saved {len(merged_trades)} trades to {file_path} (New added: {added_count})")
    
    # Supabase 클라우드 데이터베이스 동기화 시도
    sync_trades_to_supabase(merged_trades)
    
    return added_count

def sync_trades_to_supabase(trades: List[Dict[str, Any]]) -> bool:
    """Supabase REST API를 통해 trades 테이블에 벌크 Upsert (on_conflict=accession_number)"""
    import urllib.request
    from src.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
    
    if not SUPABASE_URL:
        return False
        
    api_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
    if not api_key:
        return False
        
    endpoint = f"{SUPABASE_URL.rstrip('/')}/rest/v1/trades?on_conflict=accession_number"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }
    
    payload = []
    for t in trades:
        acc_no = t.get("accession_number")
        if not acc_no:
            continue
        record = {
            "accession_number": acc_no,
            "ticker": t.get("ticker", "N/A"),
            "issuer_name": t.get("issuer_name"),
            "reporter_name": t.get("reporter_name"),
            "role_title": t.get("role_title"),
            "role_summary": t.get("role_summary"),
            "is_officer": bool(t.get("is_officer", False)),
            "is_director": bool(t.get("is_director", False)),
            "is_ten_percent": bool(t.get("is_ten_percent", False)),
            "total_shares": t.get("total_shares"),
            "avg_price": t.get("avg_price"),
            "total_value_usd": t.get("total_value_usd"),
            "shares_owned_after": t.get("shares_owned_after"),
            "pct_increase": t.get("pct_increase"),
            "transaction_date": t.get("transaction_date"),
            "sec_form4_url": t.get("sec_form4_url"),
            "trade_type": t.get("trade_type", "BUY"),
            "category": t.get("category", "INSIDER"),
            "percent_of_class": t.get("percent_of_class"),
            "investor_type": t.get("investor_type"),
            "is_amendment": bool(t.get("is_amendment", False)),
            "items": t.get("items", [])
        }
        payload.append(record)
            
    if not payload:
        return True
        
    try:
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201, 204):
                logger.info(f"Successfully synced {len(payload)} trades to Supabase DB.")
                return True
    except Exception as e:
        logger.debug(f"Supabase sync notice: {e} (로컬 trades.json에 안전 저장됨)")
        return False

