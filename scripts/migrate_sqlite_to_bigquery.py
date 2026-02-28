"""
SQLite → BigQuery Migration Script
====================================

One-time migration of all data from local SQLite to BigQuery.
Uses the storage backends directly (which handle dedup/upsert),
so re-running is safe.

Usage:
    python scripts/migrate_sqlite_to_bigquery.py
    python scripts/migrate_sqlite_to_bigquery.py --tables articles,papers --dry-run
    python scripts/migrate_sqlite_to_bigquery.py --db-path data/quantum_intel.db --batch-size 200
"""

import sys
import os
import asyncio
import argparse
import json
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.sqlite import SQLiteStorage
from storage.bigquery import BigQueryStorage
from storage.base import ClassifiedArticle
from models.paper import Paper
from models.stock import StockSnapshot
from models.article import Digest
from models.earnings import EarningsTranscript, ExtractedQuote
from models.sec_filing import SecFiling, SecNugget
from models.podcast import PodcastTranscript, PodcastQuote
from models.weekly_briefing import WeeklyBriefing
from models.case_study import CaseStudy
from utils.logger import get_logger

logger = get_logger(__name__)

# Tables in dependency order
ALL_TABLES = [
    "articles",
    "papers",
    "stocks",
    "digests",
    "earnings_transcripts",
    "earnings_quotes",
    "sec_filings",
    "sec_nuggets",
    "podcast_transcripts",
    "podcast_quotes",
    "weekly_briefings",
    "case_studies",
]


# =============================================================================
# Per-table migration functions
# =============================================================================

async def migrate_articles(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate articles table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM articles")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM articles ORDER BY fetched_at")
    rows = cursor.fetchall()
    migrated = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        articles = []
        for row in batch:
            try:
                articles.append(sqlite._row_to_article(row))
            except Exception as e:
                logger.warning(f"  Skipping bad article row: {e}")

        if articles:
            saved = await bq.save_articles(articles)
            migrated += saved
            logger.info(f"  Articles: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_papers(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate papers table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM papers")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM papers ORDER BY ingested_at")
    rows = cursor.fetchall()
    papers = []
    for row in rows:
        try:
            papers.append(sqlite._row_to_paper(row))
        except Exception as e:
            logger.warning(f"  Skipping bad paper row: {e}")

    migrated = 0
    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        saved = await bq.save_papers(batch)
        migrated += saved
        logger.info(f"  Papers: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_stocks(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate stocks table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM stocks")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM stocks ORDER BY date")
    rows = cursor.fetchall()
    snapshots = [StockSnapshot.from_dict(dict(r)) for r in rows]

    migrated = 0
    for i in range(0, len(snapshots), batch_size):
        batch = snapshots[i : i + batch_size]
        saved = await bq.save_stock_data(batch)
        migrated += saved
        logger.info(f"  Stocks: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_digests(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate digests table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM digests")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    digest = await sqlite.get_latest_digest()
    if digest:
        await bq.save_digest(digest)
        return 1
    return 0


async def migrate_earnings_transcripts(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate earnings_transcripts table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM earnings_transcripts")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM earnings_transcripts ORDER BY ticker, year, quarter")
    rows = cursor.fetchall()
    migrated = 0

    for row in rows:
        try:
            transcript = EarningsTranscript.from_dict(dict(row))
            await bq.save_transcript(transcript)
            migrated += 1
        except Exception as e:
            logger.warning(f"  Skipping bad transcript: {e}")

    return migrated


async def migrate_earnings_quotes(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate earnings_quotes table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM earnings_quotes")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM earnings_quotes ORDER BY ticker, year, quarter")
    rows = cursor.fetchall()
    quotes = []
    for row in rows:
        try:
            quotes.append(ExtractedQuote.from_dict(dict(row)))
        except Exception as e:
            logger.warning(f"  Skipping bad quote: {e}")

    migrated = 0
    for i in range(0, len(quotes), batch_size):
        batch = quotes[i : i + batch_size]
        saved = await bq.save_quotes(batch)
        migrated += saved
        logger.info(f"  Earnings quotes: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_sec_filings(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate sec_filings table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM sec_filings")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM sec_filings ORDER BY ticker, filing_date")
    rows = cursor.fetchall()
    migrated = 0

    for row in rows:
        try:
            filing = SecFiling.from_dict(dict(row))
            await bq.save_filing(filing)
            migrated += 1
        except Exception as e:
            logger.warning(f"  Skipping bad filing: {e}")

    return migrated


async def migrate_sec_nuggets(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate sec_nuggets table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM sec_nuggets")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM sec_nuggets ORDER BY ticker")
    rows = cursor.fetchall()
    nuggets = []
    for row in rows:
        try:
            nuggets.append(SecNugget.from_dict(dict(row)))
        except Exception as e:
            logger.warning(f"  Skipping bad nugget: {e}")

    migrated = 0
    for i in range(0, len(nuggets), batch_size):
        batch = nuggets[i : i + batch_size]
        saved = await bq.save_nuggets(batch)
        migrated += saved
        logger.info(f"  SEC nuggets: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_podcast_transcripts(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate podcast_transcripts table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM podcast_transcripts")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM podcast_transcripts ORDER BY podcast_name, episode_title")
    rows = cursor.fetchall()
    migrated = 0

    for row in rows:
        try:
            transcript = PodcastTranscript.from_dict(dict(row))
            await bq.save_podcast_transcript(transcript)
            migrated += 1
        except Exception as e:
            logger.warning(f"  Skipping bad podcast transcript: {e}")

    return migrated


async def migrate_podcast_quotes(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate podcast_quotes table."""
    conn = sqlite._conn
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM podcast_quotes")
    total = cursor.fetchone()["cnt"]
    if dry_run:
        return total

    cursor = conn.execute("SELECT * FROM podcast_quotes ORDER BY podcast_name")
    rows = cursor.fetchall()
    quotes = []
    for row in rows:
        try:
            quotes.append(PodcastQuote.from_dict(dict(row)))
        except Exception as e:
            logger.warning(f"  Skipping bad podcast quote: {e}")

    migrated = 0
    for i in range(0, len(quotes), batch_size):
        batch = quotes[i : i + batch_size]
        saved = await bq.save_podcast_quotes(batch)
        migrated += saved
        logger.info(f"  Podcast quotes: batch {i // batch_size + 1} — saved {saved}")

    return migrated


async def migrate_weekly_briefings(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate weekly_briefings table."""
    conn = sqlite._conn
    try:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM weekly_briefings")
        total = cursor.fetchone()["cnt"]
    except Exception:
        return 0  # Table may not exist in older DBs

    if dry_run:
        return total

    for domain in ["quantum", "ai"]:
        briefing = await sqlite.get_latest_weekly_briefing(domain=domain)
        if briefing:
            await bq.save_weekly_briefing(briefing)

    return total


async def migrate_case_studies(sqlite: SQLiteStorage, bq: BigQueryStorage, batch_size: int, dry_run: bool) -> int:
    """Migrate case_studies table."""
    conn = sqlite._conn
    try:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM case_studies")
        total = cursor.fetchone()["cnt"]
    except Exception:
        return 0  # Table may not exist

    if dry_run:
        return total

    case_studies = await sqlite.get_case_studies(limit=10000)
    if case_studies:
        saved = await bq.save_case_studies(case_studies)
        return saved
    return 0


# Dispatch table
MIGRATORS = {
    "articles": migrate_articles,
    "papers": migrate_papers,
    "stocks": migrate_stocks,
    "digests": migrate_digests,
    "earnings_transcripts": migrate_earnings_transcripts,
    "earnings_quotes": migrate_earnings_quotes,
    "sec_filings": migrate_sec_filings,
    "sec_nuggets": migrate_sec_nuggets,
    "podcast_transcripts": migrate_podcast_transcripts,
    "podcast_quotes": migrate_podcast_quotes,
    "weekly_briefings": migrate_weekly_briefings,
    "case_studies": migrate_case_studies,
}


# =============================================================================
# Main pipeline
# =============================================================================

async def run_migration(
    db_path: str = "data/quantum_intel.db",
    tables: list[str] = None,
    batch_size: int = 500,
    dry_run: bool = False,
):
    """Run the full SQLite → BigQuery migration."""
    tables = tables or ALL_TABLES

    # Validate tables
    invalid = set(tables) - set(ALL_TABLES)
    if invalid:
        logger.error(f"Unknown tables: {invalid}")
        logger.error(f"Valid tables: {ALL_TABLES}")
        return

    from dotenv import load_dotenv
    load_dotenv()

    gcp_project = os.getenv("GCP_PROJECT_ID")
    if not gcp_project and not dry_run:
        logger.error("GCP_PROJECT_ID not set. Cannot migrate to BigQuery.")
        logger.info("Set GCP_PROJECT_ID in .env or use --dry-run to preview row counts.")
        return

    # Init sources
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}SQLite → BigQuery Migration")
    logger.info(f"  Source: {db_path}")
    logger.info(f"  Tables: {', '.join(tables)}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info("")

    sqlite = SQLiteStorage(db_path=db_path)

    bq = None
    if not dry_run:
        bq = BigQueryStorage(
            project_id=gcp_project,
            dataset_id=os.getenv("BQ_DATASET_ID", "quantum_ai_hub"),
            location=os.getenv("GCP_REGION", "us-central1"),
        )

    # Run migrations
    results = {}
    total_migrated = 0
    start_time = datetime.now()

    for table in tables:
        migrator = MIGRATORS.get(table)
        if not migrator:
            logger.warning(f"No migrator for table: {table}")
            continue

        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating: {table}")
        try:
            count = await migrator(sqlite, bq, batch_size, dry_run)
            results[table] = count
            total_migrated += count
            label = "rows found" if dry_run else "rows migrated"
            logger.info(f"  ✓ {table}: {count} {label}")
        except Exception as e:
            results[table] = f"ERROR: {e}"
            logger.error(f"  ✗ {table}: {e}")

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migration Summary")
    logger.info("=" * 60)
    for table, count in results.items():
        logger.info(f"  {table:30s} {count}")
    logger.info(f"  {'-' * 40}")
    logger.info(f"  {'Total':30s} {total_migrated}")
    logger.info(f"  {'Elapsed':30s} {elapsed:.1f}s")
    logger.info("=" * 60)

    await sqlite.close()
    if bq:
        await bq.close()


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_sqlite_to_bigquery.py --dry-run
  python scripts/migrate_sqlite_to_bigquery.py --tables articles,papers
  python scripts/migrate_sqlite_to_bigquery.py --db-path data/quantum_intel.db --batch-size 200
        """,
    )
    parser.add_argument(
        "--db-path",
        default="data/quantum_intel.db",
        help="Path to SQLite database (default: data/quantum_intel.db)",
    )
    parser.add_argument(
        "--tables",
        default=None,
        help=f"Comma-separated list of tables to migrate (default: all). Options: {','.join(ALL_TABLES)}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for BQ inserts (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows per table without writing to BigQuery",
    )

    args = parser.parse_args()

    tables = args.tables.split(",") if args.tables else None

    asyncio.run(run_migration(
        db_path=args.db_path,
        tables=tables,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
