"""
Earnings Pipeline Runner
========================

Standalone script to run the earnings call pipeline.
Fetches transcripts → extracts quotes → stores results.

Usage:
    python scripts/run_earnings.py
    python scripts/run_earnings.py --domain ai --tickers PLTR,NVDA --quarters 2
    python scripts/run_earnings.py --tickers IONQ,QBTS --quarters 2
"""

import asyncio
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import EarningsConfig
from config.earnings_tickers import (
    ALL_EARNINGS_TICKERS as QUANTUM_ALL_TICKERS,
    CORE_TICKERS as QUANTUM_CORE_TICKERS,
)
from config.ai_earnings_tickers import (
    AI_ALL_EARNINGS_TICKERS as AI_ALL_TICKERS,
    AI_CORE_TICKERS,
)
from fetchers.earnings import EarningsFetcher
from processing.quote_extractor import QuoteExtractor
from storage import get_storage
from storage import get_embeddings_store
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_earnings_pipeline(
    tickers: list[str],
    max_quarters: int = 4,
    skip_extraction: bool = False,
    re_extract: bool = False,
    db_path: str = "data/quantum_intel.db",
    domain: str = "quantum",
):
    """
    Run the complete earnings pipeline.

    1. Fetch new transcripts from API Ninjas
    2. Extract quotes using Claude Sonnet
    3. Store in storage backend (SQLite or BigQuery)
    """
    config = EarningsConfig()
    storage = get_storage(db_path=db_path)
    fetcher = EarningsFetcher(config)
    extractor = QuoteExtractor(config)

    if re_extract:
        # Re-extraction mode: extract quotes for transcripts that have none
        logger.info(f"[EARNINGS_PIPELINE] Re-extract mode: finding transcripts without quotes...")
        transcripts_to_process = await storage.get_transcripts_without_quotes(
            tickers=tickers if tickers else None
        )
        if not transcripts_to_process:
            logger.info("[EARNINGS_PIPELINE] All transcripts already have quotes")
            await storage.close()
            return
        logger.info(f"[EARNINGS_PIPELINE] Found {len(transcripts_to_process)} transcripts without quotes")
    else:
        # Step 1: Fetch new transcripts
        logger.info(f"[EARNINGS_PIPELINE] Fetching transcripts for {len(tickers)} tickers...")
        transcripts_to_process = await fetcher.fetch_new_transcripts(
            storage=storage,
            tickers=tickers,
            max_quarters=max_quarters,
        )

        if not transcripts_to_process:
            logger.info("[EARNINGS_PIPELINE] No new transcripts to process")
            await storage.close()
            return

        logger.info(f"[EARNINGS_PIPELINE] Found {len(transcripts_to_process)} new transcripts")

    # Step 2: Save transcripts and extract quotes
    total_quotes = 0
    for transcript in transcripts_to_process:
        transcript.domain = domain
        if not re_extract:
            # Save transcript (only needed in normal fetch mode)
            await storage.save_transcript(transcript)

        if skip_extraction:
            logger.info(f"[EARNINGS_PIPELINE] Skipping extraction for {transcript.unique_key}")
            continue

        # Extract quotes
        result = await extractor.extract_quotes(transcript, domain=domain)

        if result.quotes:
            saved = await storage.save_quotes(result.quotes)
            total_quotes += saved
            logger.info(
                f"[EARNINGS_PIPELINE] {transcript.unique_key}: "
                f"{saved} quotes saved"
            )

            # Index embeddings for semantic search
            try:
                earnings_embeddings = get_embeddings_store(content_type="earnings_quotes")
                embedded = await earnings_embeddings.index_items(result.quotes)
                logger.info(f"[EARNINGS_PIPELINE] {transcript.unique_key}: {embedded} quotes embedded")
            except Exception as e:
                logger.warning(f"[EARNINGS_PIPELINE] Embedding error (non-fatal): {e}")
        else:
            logger.warning(
                f"[EARNINGS_PIPELINE] No quotes extracted from {transcript.unique_key}"
            )

    logger.info(
        f"[EARNINGS_PIPELINE] Complete! "
        f"Transcripts: {len(transcripts_to_process)}, Quotes: {total_quotes}"
    )

    await storage.close()


def main():
    parser = argparse.ArgumentParser(description="Run the Earnings Call pipeline")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated tickers (default: all tracked)",
    )
    parser.add_argument(
        "--quarters",
        type=int,
        default=4,
        help="Number of quarters to go back (default: 4)",
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
        help="Fetch transcripts only, skip LLM extraction",
    )
    parser.add_argument(
        "--re-extract",
        action="store_true",
        help="Re-run extraction on saved transcripts that have no quotes (uses fixed max_tokens)",
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

    asyncio.run(
        run_earnings_pipeline(
            tickers=tickers,
            max_quarters=args.quarters,
            skip_extraction=args.skip_extraction,
            re_extract=args.re_extract,
            db_path=args.db_path,
            domain=args.domain,
        )
    )


if __name__ == "__main__":
    main()
