#!/usr/bin/env python3
"""
Whale Radar: trades.json -> Supabase PostgreSQL 1회성 마이그레이션 스크립트
기존 docs/data/trades.json에 저장된 모든 공시 데이터를 Supabase trades 테이블로 일괄 전송(Upsert)합니다.
"""

import sys
import os
import json
import logging

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
from src.data_manager import DEFAULT_DATA_PATH, sync_trades_to_supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MigrateToSupabase")

def migrate():
    logger.info("==========================================================")
    logger.info("🚀 Whale Radar: Supabase Database Migration Tool")
    logger.info("==========================================================")
    logger.info(f"Supabase Endpoint: {SUPABASE_URL}")
    
    if not os.path.exists(DEFAULT_DATA_PATH):
        logger.error(f"Data file not found: {DEFAULT_DATA_PATH}")
        return False

    with open(DEFAULT_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    trades = data.get("trades", [])
    logger.info(f"Loaded {len(trades)} trades from {DEFAULT_DATA_PATH}")

    if not trades:
        logger.warning("No trades found to migrate.")
        return True

    success = sync_trades_to_supabase(trades)
    if success:
        logger.info(f"✅ Successfully migrated {len(trades)} trades to Supabase PostgreSQL!")
        logger.info("Now the web dashboard can query these trades on-demand.")
        return True
    else:
        logger.error("❌ Migration failed.")
        logger.error("Please verify that the 'trades' table exists in your Supabase SQL Editor:")
        logger.error("Execute the contents of 'supabase_schema.sql' in Supabase SQL Editor first.")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
