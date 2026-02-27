"""
Case Study Extraction Pipeline
===============================

Standalone script to extract structured case studies from already-ingested content.
Queries stored articles, SEC filings, earnings transcripts, podcast transcripts,
and ArXiv papers — then runs the domain+source-aware CaseStudyExtractor.

Usage:
    python scripts/run_case_studies.py --domain ai --sources articles
    python scripts/run_case_studies.py --domain quantum --sources sec,earnings --tickers IONQ,GOOGL
    python scripts/run_case_studies.py --domain ai --sources all --max-items 5
    python scripts/run_case_studies.py --domain ai --sources articles --re-extract
    python scripts/run_case_studies.py --domain quantum --sources all --dry-run
"""

import asyncio
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import CaseStudyConfig
from config.earnings_tickers import (
    EARNINGS_COMPANIES as QUANTUM_EARNINGS_COMPANIES,
    CORE_TICKERS as QUANTUM_CORE_TICKERS,
)
from config.ai_earnings_tickers import (
    AI_EARNINGS_COMPANIES,
    AI_CORE_TICKERS,
)
from models.earnings import EarningsTranscript
from models.sec_filing import SecFiling
from models.podcast import PodcastTranscript
from processing.case_study_extractor import CaseStudyExtractor
from storage import get_storage, get_embeddings_store
from utils.logger import get_logger

logger = get_logger(__name__)

VALID_SOURCES = {"articles", "sec", "earnings", "podcasts", "arxiv", "all"}


# =============================================================================
# Source-specific batch fetchers
# =============================================================================

async def fetch_articles(storage, domain: str, max_items: int):
    """Fetch stored articles for case study extraction."""
    articles = await storage.get_recent_articles(
        hours=24 * 90,  # Last 90 days
        limit=max_items * 3,  # Fetch extra to account for skips
        domain=domain,
    )
    return articles[:max_items * 3]


async def fetch_papers(storage, domain: str, max_items: int):
    """Fetch stored ArXiv papers for case study extraction."""
    papers = await storage.get_recent_papers(
        days=90,
        limit=max_items * 3,
    )
    return papers[:max_items * 3]


def _detect_backend(storage):
    """Detect which storage backend is in use."""
    return type(storage).__name__


async def fetch_earnings_transcripts(storage, domain: str, max_items: int, tickers=None):
    """Fetch stored earnings transcripts for case study extraction."""
    if not tickers:
        if domain == "ai":
            tickers = [c["ticker"] for c in AI_EARNINGS_COMPANIES]
        else:
            tickers = [c["ticker"] for c in QUANTUM_EARNINGS_COMPANIES]

    backend = _detect_backend(storage)

    if backend == "SQLiteStorage":
        placeholders = ",".join("?" * len(tickers))
        cursor = storage._conn.execute(
            f"""SELECT * FROM earnings_transcripts
                WHERE ticker IN ({placeholders})
                ORDER BY year DESC, quarter DESC
                LIMIT ?""",
            tickers + [max_items * 3],
        )
        return [EarningsTranscript.from_dict(dict(row)) for row in cursor.fetchall()]

    elif backend == "BigQueryStorage":
        sql = f"""
            SELECT * FROM `{storage.full_dataset}.earnings_transcripts`
            WHERE ticker IN UNNEST(@tickers)
            ORDER BY year DESC, quarter DESC
            LIMIT @lim
        """
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("tickers", "STRING", tickers),
                bigquery.ScalarQueryParameter("lim", "INT64", max_items * 3),
            ]
        )
        rows = list(storage.bq_client.query(sql, job_config=job_config).result())
        return [EarningsTranscript.from_dict(dict(row)) for row in rows]

    return []


async def fetch_sec_filings(storage, domain: str, max_items: int, tickers=None):
    """Fetch stored SEC filings for case study extraction."""
    if not tickers:
        if domain == "ai":
            tickers = [c["ticker"] for c in AI_EARNINGS_COMPANIES]
        else:
            tickers = [c["ticker"] for c in QUANTUM_EARNINGS_COMPANIES]

    backend = _detect_backend(storage)

    if backend == "SQLiteStorage":
        placeholders = ",".join("?" * len(tickers))
        cursor = storage._conn.execute(
            f"""SELECT * FROM sec_filings
                WHERE ticker IN ({placeholders})
                ORDER BY filing_date DESC
                LIMIT ?""",
            tickers + [max_items * 3],
        )
        return [SecFiling.from_dict(dict(row)) for row in cursor.fetchall()]

    elif backend == "BigQueryStorage":
        sql = f"""
            SELECT * FROM `{storage.full_dataset}.sec_filings`
            WHERE ticker IN UNNEST(@tickers)
            ORDER BY filing_date DESC
            LIMIT @lim
        """
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("tickers", "STRING", tickers),
                bigquery.ScalarQueryParameter("lim", "INT64", max_items * 3),
            ]
        )
        rows = list(storage.bq_client.query(sql, job_config=job_config).result())
        return [SecFiling.from_dict(dict(row)) for row in rows]

    return []


async def fetch_podcast_transcripts(storage, domain: str, max_items: int):
    """Fetch stored podcast transcripts for case study extraction."""
    backend = _detect_backend(storage)

    if backend == "SQLiteStorage":
        cursor = storage._conn.execute(
            """SELECT * FROM podcast_transcripts
               ORDER BY published_at DESC
               LIMIT ?""",
            (max_items * 3,),
        )
        return [PodcastTranscript.from_dict(dict(row)) for row in cursor.fetchall()]

    elif backend == "BigQueryStorage":
        sql = f"""
            SELECT * FROM `{storage.full_dataset}.podcast_transcripts`
            ORDER BY published_at DESC
            LIMIT @lim
        """
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("lim", "INT64", max_items * 3),
            ]
        )
        rows = list(storage.bq_client.query(sql, job_config=job_config).result())
        return [PodcastTranscript.from_dict(dict(row)) for row in rows]

    return []


def _get_ticker_tier(ticker: str, domain: str) -> str:
    """Look up tier (core/secondary) for a ticker in the given domain."""
    companies = AI_EARNINGS_COMPANIES if domain == "ai" else QUANTUM_EARNINGS_COMPANIES
    for c in companies:
        if c["ticker"] == ticker:
            return c.get("tier", "core")
    return "core"


# =============================================================================
# Main pipeline
# =============================================================================

async def run_case_study_pipeline(
    domain: str = "quantum",
    sources: list[str] = None,
    tickers: list[str] = None,
    max_items: int = 50,
    re_extract: bool = False,
    skip_embed: bool = False,
    dry_run: bool = False,
    db_path: str = "data/quantum_intel.db",
):
    """
    Run the case study extraction pipeline.

    1. Query stored content from selected sources
    2. Skip items that already have case studies (unless --re-extract)
    3. Extract case studies using domain+source-aware prompts
    4. Save to storage backend
    5. Index embeddings for semantic search
    """
    if sources is None:
        sources = ["all"]

    # Expand "all" to all source types
    if "all" in sources:
        sources = ["articles", "sec", "earnings", "podcasts", "arxiv"]

    config = CaseStudyConfig()
    storage = get_storage(db_path=db_path)
    extractor = CaseStudyExtractor(config)

    total_extracted = 0
    total_saved = 0
    total_cost = 0.0

    for source in sources:
        logger.info(f"[CASE_STUDY_PIPELINE] === Processing source: {source} (domain={domain}) ===")

        items = []
        extract_fn = None
        source_type_key = None

        if source == "articles":
            items = await fetch_articles(storage, domain, max_items)
            extract_fn = extractor.extract_from_article
            source_type_key = "article"
            id_fn = lambda item: item.id

        elif source == "arxiv":
            items = await fetch_papers(storage, domain, max_items)
            extract_fn = extractor.extract_from_arxiv
            source_type_key = "arxiv"
            id_fn = lambda item: item.arxiv_id

        elif source == "earnings":
            items = await fetch_earnings_transcripts(storage, domain, max_items, tickers)
            extract_fn = None  # handled separately for tier
            source_type_key = "earnings"
            id_fn = lambda item: item.transcript_id

        elif source == "sec":
            items = await fetch_sec_filings(storage, domain, max_items, tickers)
            extract_fn = None  # handled separately for tier
            source_type_key = "sec_filing"
            id_fn = lambda item: item.filing_id

        elif source == "podcasts":
            items = await fetch_podcast_transcripts(storage, domain, max_items)
            extract_fn = extractor.extract_from_podcast
            source_type_key = "podcast"
            id_fn = lambda item: item.transcript_id

        else:
            logger.warning(f"[CASE_STUDY_PIPELINE] Unknown source: {source}")
            continue

        if not items:
            logger.info(f"[CASE_STUDY_PIPELINE] No {source} items found in storage")
            continue

        logger.info(f"[CASE_STUDY_PIPELINE] Found {len(items)} {source} items to process")

        # Process each item
        processed = 0
        for item in items:
            if processed >= max_items:
                break

            item_id = id_fn(item)

            # Check if already extracted (unless re-extract mode)
            if not re_extract:
                exists = await storage.case_studies_exist_for_source(
                    source_type=source_type_key,
                    source_id=item_id,
                )
                if exists:
                    logger.debug(f"[CASE_STUDY_PIPELINE] Already extracted: {source_type_key}/{item_id}")
                    continue

            processed += 1

            # Dry-run: just log what would be processed
            if dry_run:
                label = _get_item_label(item, source)
                logger.info(f"[CASE_STUDY_PIPELINE] [DRY RUN] Would extract from: {label}")
                continue

            # Extract case studies
            try:
                if source in ("earnings", "sec"):
                    ticker = getattr(item, "ticker", "")
                    tier = _get_ticker_tier(ticker, domain)
                    if source == "earnings":
                        result = await extractor.extract_from_earnings(
                            item, domain=domain, tier=tier
                        )
                    else:
                        result = await extractor.extract_from_sec(
                            item, domain=domain, tier=tier
                        )
                else:
                    result = await extract_fn(item, domain=domain)
            except Exception as e:
                logger.error(f"[CASE_STUDY_PIPELINE] Extraction error for {item_id}: {e}")
                continue

            total_cost += result.extraction_cost_usd

            if not result.success or not result.case_studies:
                label = _get_item_label(item, source)
                logger.info(
                    f"[CASE_STUDY_PIPELINE] No case studies from {label}"
                    f"{f' — {result.error_message}' if result.error_message else ''}"
                )
                continue

            # Save case studies
            saved = await storage.save_case_studies(result.case_studies)
            total_saved += saved
            total_extracted += len(result.case_studies)

            label = _get_item_label(item, source)
            logger.info(
                f"[CASE_STUDY_PIPELINE] {label}: "
                f"{len(result.case_studies)} extracted, {saved} saved "
                f"(cost=${result.extraction_cost_usd:.4f})"
            )

            # Index embeddings
            if not skip_embed and saved > 0:
                try:
                    cs_embeddings = get_embeddings_store(content_type="case_studies")
                    embedded = await cs_embeddings.index_items(result.case_studies)
                    logger.info(
                        f"[CASE_STUDY_PIPELINE] {label}: {embedded} case studies embedded"
                    )
                except Exception as e:
                    logger.warning(f"[CASE_STUDY_PIPELINE] Embedding error (non-fatal): {e}")

        if dry_run:
            logger.info(
                f"[CASE_STUDY_PIPELINE] [DRY RUN] {source}: {processed} items would be processed"
            )
        else:
            logger.info(
                f"[CASE_STUDY_PIPELINE] {source}: {processed} items processed, "
                f"{total_extracted} case studies extracted"
            )

    # Final summary
    logger.info(
        f"[CASE_STUDY_PIPELINE] Complete! "
        f"Sources: {', '.join(sources)} | "
        f"Case studies: {total_extracted} extracted, {total_saved} saved | "
        f"Cost: ${total_cost:.4f}"
    )

    await storage.close()


def _get_item_label(item, source: str) -> str:
    """Build a human-readable label for a source item."""
    if source == "articles":
        title = getattr(item, "title", "")
        return f"Article: {title[:60]}" if title else f"Article: {item.id}"
    elif source == "arxiv":
        return f"ArXiv: {item.arxiv_id}"
    elif source == "earnings":
        return f"Earnings: {item.ticker} Q{item.quarter} {item.year}"
    elif source == "sec":
        return f"SEC: {item.ticker} {item.filing_type}"
    elif source == "podcasts":
        return f"Podcast: {getattr(item, 'episode_title', item.transcript_id)}"
    return f"{source}: {getattr(item, 'id', '?')}"


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract structured case studies from stored content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_case_studies.py --domain ai --sources articles
  python scripts/run_case_studies.py --domain quantum --sources sec,earnings --tickers IONQ
  python scripts/run_case_studies.py --domain ai --sources all --max-items 5
  python scripts/run_case_studies.py --domain ai --sources articles --dry-run
  python scripts/run_case_studies.py --domain quantum --sources all --re-extract
        """,
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="quantum",
        choices=["quantum", "ai"],
        help="Domain: quantum or ai (default: quantum)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="all",
        help="Comma-separated source types: articles,sec,earnings,podcasts,arxiv,all (default: all)",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated tickers for SEC/earnings (default: all domain tickers)",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="Max items to process per source (default: 50)",
    )
    parser.add_argument(
        "--re-extract",
        action="store_true",
        help="Re-extract case studies even if they already exist for a source",
    )
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        help="Skip embedding indexing after extraction",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually extracting",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/quantum_intel.db",
        help="SQLite database path",
    )

    args = parser.parse_args()

    # Validate sources
    sources = [s.strip().lower() for s in args.sources.split(",")]
    invalid = set(sources) - VALID_SOURCES
    if invalid:
        parser.error(f"Invalid source(s): {invalid}. Valid: {VALID_SOURCES}")

    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]

    asyncio.run(
        run_case_study_pipeline(
            domain=args.domain,
            sources=sources,
            tickers=tickers,
            max_items=args.max_items,
            re_extract=args.re_extract,
            skip_embed=args.skip_embed,
            dry_run=args.dry_run,
            db_path=args.db_path,
        )
    )


if __name__ == "__main__":
    main()
