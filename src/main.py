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
)
from src.models import InsiderTrade
from src.sec_client import SECClient
from src.parser import Form4Parser
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
    print("\n" + "=" * 65)
    print(f" 🟢 [{index}/{total}] {trade.ticker} ({trade.issuer_name}) - 경영진 장내 매수 포착!")
    print("=" * 65)
    print(f" • 매수자 (내부자)  : {trade.reporter_name} ({trade.role_summary})")
    print(f" • 총 매수 규모     : {trade.total_shares:,.0f}주 (${trade.total_value_usd:,.2f} / 약 {format_krw(trade.total_value_usd)})")
    print(f" • 가중 평균 매수가 : ${trade.avg_price:.2f}")
    
    if trade.pct_increase is not None:
        print(f" • 보유 지분 변동   : {trade.shares_owned_after - trade.total_shares:,.0f}주 ➡️ {trade.shares_owned_after:,.0f}주 (+{trade.pct_increase:.2f}%)")
    else:
        print(f" • 매수 후 보유 주식: {trade.shares_owned_after:,.0f}주")
        
    print(f" • 거래 일자        : {trade.transaction_date}")
    
    if len(trade.items) > 1:
        print(f" • 세부 분할 매수 ({len(trade.items)}회):")
        for idx, item in enumerate(trade.items, 1):
            print(f"    - {idx}) {item.shares:,.0f}주 @ ${item.price_per_share:.2f} (${item.total_value:,.2f}) [{item.transaction_date}]")
            
    print(f" • SEC Form 4 원문 : {trade.sec_form4_url}")
    print("=" * 65)

def run_pipeline(count: int, min_val: float, save_to_json: bool = True) -> List[InsiderTrade]:
    print(f"📡 [Insider Radar] SEC EDGAR 최신 Form 4 스캔 시작 (최근 {count}건 조회, 필터 기준: ${min_val:,.0f}+)...")
    
    client = SECClient()
    parser = Form4Parser(min_purchase_value=min_val)
    
    entries = client.fetch_latest_form4_entries(count=count)
    print(f"📥 수집된 고유 Form 4 제출 공시: {len(entries)}건")
    
    detected_trades: List[InsiderTrade] = []
    
    for i, meta in enumerate(entries, 1):
        print(f"\r🔍 [{i}/{len(entries)}] 분석 중: AccNo {meta.accession_number}...", end="", flush=True)
        
        xml_content = client.get_form4_xml_content(meta)
        if not xml_content:
            continue
            
        trade = parser.parse_and_filter(xml_content, meta)
        if trade:
            detected_trades.append(trade)

    print("\n" + "-" * 65)
    print(f"✅ 스캔 완료! 총 {len(entries)}건의 Form 4 중 {len(detected_trades)}건의 유의미한 내부자 매수 신호 포착.")
    
    for idx, trade in enumerate(detected_trades, 1):
        display_trade(trade, idx, len(detected_trades))
        
    if save_to_json and detected_trades:
        added = save_trades(detected_trades)
        print(f"💾 [저장 완료] docs/data/trades.json 에 {len(detected_trades)}건 반영 (신규: {added}건)")
    elif save_to_json:
        # 새로운 거래가 없더라도 마지막 갱신 시간 등을 업데이트할 수 있도록 빈 리스트로 호출
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
