"""
SEC Pipeline Runner
===================

Standalone script to run the SEC filing pipeline.
Fetches filings → extracts nuggets → stores results.

Usage:
    python scripts/run_sec.py
    python scripts/run_sec.py --domain ai --tickers PLTR,NVDA --types 10-K,10-Q
    python scripts/run_sec.py --tickers IONQ,QBTS --types 10-K,10-Q
"""

import asyncio
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import SecConfig
from config.earnings_tickers import (
    ALL_EARNINGS_TICKERS as QUANTUM_ALL_TICKERS,
    CORE_TICKERS as QUANTUM_CORE_TICKERS,
)
from config.ai_earnings_tickers import (
    AI_ALL_EARNINGS_TICKERS as AI_ALL_TICKERS,
    AI_CORE_TICKERS,
)
from fetchers.sec import SecFetcher
from processing.nugget_extractor import NuggetExtractor
from storage import get_storage
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_sec_pipeline(
    tickers: list[str],
    filing_types: list[str] | None = None,
    skip_extraction: bool = False,
    re_extract: bool = False,
    max_filings: int = 1,
    db_path: str = "data/quantum_intel.db",
    domain: str = "quantum",
):
    """
    Run the complete SEC filing pipeline.

    1. Fetch new filings from EDGAR
    2. Extract nuggets using Claude Sonnet
    3. Store in storage backend (SQLite or BigQuery)
    """
    config = SecConfig()
    storage = get_storage(db_path=db_path)
    fetcher = SecFetcher(config)
    extractor = NuggetExtractor(config)

    if re_extract:
        # Re-extraction mode: extract nuggets for filings that have none
        logger.info("[SEC_PIPELINE] Re-extract mode: finding filings without nuggets...")
        filings_to_process = await storage.get_filings_without_nuggets(
            tickers=tickers if tickers else None
        )
        if not filings_to_process:
            logger.info("[SEC_PIPELINE] All filings already have nuggets")
            await storage.close()
            return
        logger.info(f"[SEC_PIPELINE] Found {len(filings_to_process)} filings without nuggets")
    else:
        # Step 1: Fetch new filings
        logger.info(f"[SEC_PIPELINE] Fetching filings for {len(tickers)} tickers...")
        filings_to_process = await fetcher.fetch_new_filings(
            storage=storage,
            tickers=tickers,
            filing_types=filing_types,
            fetch_content=True,
            max_filings=max_filings,
        )

        if not filings_to_process:
            logger.info("[SEC_PIPELINE] No new filings to process")
            await storage.close()
            return

        logger.info(f"[SEC_PIPELINE] Found {len(filings_to_process)} new filings")

    # Step 2: Save filings and extract nuggets
    total_nuggets = 0
    for filing in filings_to_process:
        if not re_extract:
            # Save filing (only needed in normal fetch mode)
            await storage.save_filing(filing)

        if skip_extraction:
            logger.info(f"[SEC_PIPELINE] Skipping extraction for {filing.unique_key}")
            continue

        # Extract nuggets
        result = await extractor.extract_nuggets(filing, domain=domain)

        if result.nuggets:
            saved = await storage.save_nuggets(result.nuggets)
            total_nuggets += saved
            logger.info(
                f"[SEC_PIPELINE] {filing.unique_key}: "
                f"{saved} nuggets saved"
            )
        else:
            logger.warning(
                f"[SEC_PIPELINE] No nuggets extracted from {filing.unique_key}"
            )

    logger.info(
        f"[SEC_PIPELINE] Complete! "
        f"Filings: {len(filings_to_process)}, Nuggets: {total_nuggets}"
    )

    await storage.close()


def main():
    parser = argparse.ArgumentParser(description="Run the SEC Filings pipeline")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated tickers (default: all tracked)",
    )
    parser.add_argument(
        "--types",
        type=str,
        default=None,
        help="Comma-separated filing types (default: 10-K,10-Q,8-K)",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only process core tickers for the selected domain",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="quantum",
        choices=["quantum", "ai"],
        help="Domain: quantum or ai (default: quantum)",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Fetch filings only, skip LLM extraction",
    )
    parser.add_argument(
        "--re-extract",
        action="store_true",
        help="Re-run extraction on saved filings that have no nuggets",
    )
    parser.add_argument(
        "--max-filings",
        type=int,
        default=1,
        help="Max filings per ticker (default: 1 = most recent only)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/quantum_intel.db",
        help="SQLite database path",
    )

    args = parser.parse_args()

    # Select ticker list based on domain
    if args.domain == "ai":
        all_tickers = AI_ALL_TICKERS
        core_tickers = AI_CORE_TICKERS
    else:
        all_tickers = QUANTUM_ALL_TICKERS
        core_tickers = QUANTUM_CORE_TICKERS

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif args.core_only:
        tickers = core_tickers
    else:
        tickers = all_tickers

    filing_types = None
    if args.types:
        filing_types = [t.strip() for t in args.types.split(",")]

    asyncio.run(
        run_sec_pipeline(
            tickers=tickers,
            filing_types=filing_types,
            skip_extraction=args.skip_extraction,
            re_extract=args.re_extract,
            max_filings=args.max_filings,
            db_path=args.db_path,
            domain=args.domain,
        )
    )


if __name__ == "__main__":
    main()
