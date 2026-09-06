import argparse
import logging
import sys
from typing import List

# Windows 콘솔 인코딩 대응 (UTF-8)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config import (
    DEFAULT_FEED_COUNT,
    MIN_PURCHASE_VALUE_USD,
    MIN_INSTITUTION_PERCENT,
)
from src.models import InsiderTrade
from src.sec_client import SECClient
from src.parser import Form4Parser
from src.schedule13_parser import Schedule13Parser
from src.data_manager import save_trades

USD_TO_KRW = 1350.0  # 원화 환산 참고 환율

def format_krw(usd_val: float) -> str:
    krw = usd_val * USD_TO_KRW
    if krw >= 100_000_000:
        return f"{krw / 100_000_000:.1f}억 원"
    elif krw >= 10_000:
        return f"{krw / 10_000:,.0f}만 원"
    return f"{krw:,.0f}원"

def display_trade(trade: InsiderTrade, index: int, total: int):
    if trade.category in ("13D", "13G"):
        icon = "🟣" if trade.category == "13D" else "🔵"
        cat_name = "행동주의/경영참여 (13D)" if trade.category == "13D" else "대형기관단순투자 (13G)"
        print("\n" + "=" * 65)
        print(f" {icon} [{index}/{total}] [{trade.category}] {trade.ticker} ({trade.issuer_name}) - {cat_name} 5%+ 포착!")
        print("=" * 65)
        print(f" • 투자 주체 (기관) : {trade.reporter_name}")
        print(f" • 기관 유형 분류   : {trade.investor_type or trade.role_title}")
        print(f" • 총 보유 지분율   : {trade.percent_of_class:.1f}%")
        print(f" • 보유 주식 수     : {trade.total_shares:,.0f}주")
        print(f" • 공시 기준 일자   : {trade.transaction_date}")
        print(f" • SEC 공시 원문    : {trade.sec_form4_url}")
        print("=" * 65)
        return

    is_buy = trade.trade_type == "BUY"
    icon = "🟢" if is_buy else "🔴"
    type_label = "매수" if is_buy else "매도"
    
    print("\n" + "=" * 65)
    print(f" {icon} [{index}/{total}] [{trade.trade_type}] {trade.ticker} ({trade.issuer_name}) - 경영진 장내 {type_label} 포착!")
    print("=" * 65)
    print(f" • 거래자 (내부자)  : {trade.reporter_name} ({trade.role_summary})")
    print(f" • 총 {type_label} 규모     : {trade.total_shares:,.0f}주 (${trade.total_value_usd:,.2f} / 약 {format_krw(trade.total_value_usd)})")
    print(f" • 가중 평균 {type_label}가 : ${trade.avg_price:.2f}")
    
    if trade.pct_increase is not None:
        print(f" • 보유 지분 변동   : {trade.pct_increase:+.2f}%")
        
    print(f" • 거래 후 보유 주식: {trade.shares_owned_after:,.0f}주")
    print(f" • 거래 일자        : {trade.transaction_date}")
    
    if len(trade.items) > 1:
        print(f" • 세부 분할 {type_label} ({len(trade.items)}회):")
        for idx, item in enumerate(trade.items, 1):
            print(f"    - {idx}) {item.shares:,.0f}주 @ ${item.price_per_share:.2f} (${item.total_value:,.2f}) [{item.transaction_date}]")
            
    print(f" • SEC Form 4 원문 : {trade.sec_form4_url}")
    print("=" * 65)

def run_pipeline(count: int, min_val: float, min_inst_pct: float = MIN_INSTITUTION_PERCENT, save_to_json: bool = True) -> List[InsiderTrade]:
    print(f"📡 [Insider Radar] SEC EDGAR 통합 스캔 시작...")
    print(f"   1) Form 4 내부자 거래 (최근 {count}건, ${min_val:,.0f}+)")
    print(f"   2) Schedule 13D/13G 기관 5%+ 대량 지분 (최근 {count//2}건, {min_inst_pct}%+)")
    
    client = SECClient()
    form4_parser = Form4Parser(min_purchase_value=min_val)
    sc13_parser = Schedule13Parser(min_percent=min_inst_pct)
    
    detected_trades: List[InsiderTrade] = []

    # --- 1. Form 4 수집 & 분석 ---
    form4_entries = client.fetch_latest_form4_entries(count=count)
    print(f"📥 수집된 Form 4 공시: {len(form4_entries)}건")
    for i, meta in enumerate(form4_entries, 1):
        print(f"\r🔍 [Form 4 {i}/{len(form4_entries)}] 분석 중: {meta.accession_number}...", end="", flush=True)
        xml_content = client.get_form4_xml_content(meta)
        if not xml_content:
            continue
        trade = form4_parser.parse_and_filter(xml_content, meta)
        if trade:
            detected_trades.append(trade)

    # --- 2. Schedule 13D / 13G 수집 & 분석 ---
    print(f"\n📥 수집된 Schedule 13D/13G 공시 탐색 중...")
    sc13_entries = client.fetch_latest_13d_13g_entries(count=max(20, count // 2))
    print(f"📥 수집된 Schedule 13D/G 공시: {len(sc13_entries)}건")
    for i, meta in enumerate(sc13_entries, 1):
        print(f"\r🔍 [13D/G {i}/{len(sc13_entries)}] 분석 중: {meta.accession_number}...", end="", flush=True)
        xml_content = client.get_form4_xml_content(meta)
        if not xml_content:
            continue
        trade = sc13_parser.parse_and_filter(xml_content, meta)
        if trade:
            detected_trades.append(trade)

    print("\n" + "-" * 65)
    print(f"✅ 전체 스캔 완료! 총 {len(detected_trades)}건의 유의미한 내부자/기관 거래 신호 포착.")
    
    for idx, trade in enumerate(detected_trades, 1):
        display_trade(trade, idx, len(detected_trades))
        
    if save_to_json and detected_trades:
        added = save_trades(detected_trades)
        print(f"💾 [저장 완료] docs/data/trades.json 에 {len(detected_trades)}건 반영 (신규: {added}건)")
    elif save_to_json:
        save_trades([])

    return detected_trades

def main():
    arg_parser = argparse.ArgumentParser(description="SEC Form 4 Insider Buying Radar Engine")
    arg_parser.add_argument("--count", type=int, default=DEFAULT_FEED_COUNT, help="조회할 최신 공시 건수 (기본 80)")
    arg_parser.add_argument("--min-value", type=float, default=MIN_PURCHASE_VALUE_USD, help="최소 매수 금액 USD (기본 100,000)")
    arg_parser.add_argument("--no-save", action="store_true", help="JSON 파일 저장 건너뛰기")
    arg_parser.add_argument("--debug", action="store_true", help="디버그 로그 출력")
    
    args = arg_parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")
    
    run_pipeline(count=args.count, min_val=args.min_value, save_to_json=not args.no_save)

if __name__ == "__main__":
    main()
