"""
Run Ingestion Pipeline
======================

CLI entry point for the Quantum Intelligence Hub ingestion pipeline.

Usage:
    python scripts/run_ingestion.py
    python scripts/run_ingestion.py --sources rss
    python scripts/run_ingestion.py --sources rss,exa,arxiv --max-classify 10
    python scripts/run_ingestion.py --sources exa --exa-themes cybersecurity_pqc,ai_ml_intersection
    python scripts/run_ingestion.py --sources stocks
"""

import sys
import os
import asyncio
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from orchestrator import IngestionOrchestrator
from utils.logger import configure_root_logger


async def main():
    parser = argparse.ArgumentParser(description="Intelligence Hub — Ingestion Pipeline")
    parser.add_argument(
        "--sources",
        type=str,
        default="rss",
        help="Comma-separated list of sources to run (rss, exa, arxiv, stocks). Default: rss",
    )
    parser.add_argument(
        "--max-classify",
        type=int,
        default=None,
        help="Limit number of articles to classify (for testing/cost control)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and dedup only, don't classify or save",
    )
    parser.add_argument(
        "--exa-themes",
        type=str,
        default=None,
        help="Comma-separated Exa themes to run (e.g. cybersecurity_pqc,ai_ml_intersection). Default: all",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="quantum",
        choices=["quantum", "ai"],
        help="Intelligence domain to ingest (default: quantum)",
    )

    args = parser.parse_args()
    sources = [s.strip() for s in args.sources.split(",")]
    exa_themes = (
        [t.strip() for t in args.exa_themes.split(",")]
        if args.exa_themes
        else None
    )

    configure_root_logger()

    domain_label = "AI" if args.domain == "ai" else "QUANTUM"
    print("=" * 60)
    print(f"{domain_label} INTELLIGENCE HUB — Ingestion Pipeline")
    print(f"Domain:  {args.domain}")
    print(f"Sources: {', '.join(sources)}")
    if args.max_classify:
        print(f"Max classify: {args.max_classify}")
    if exa_themes:
        print(f"Exa themes: {', '.join(exa_themes)}")
    if args.dry_run:
        print("Mode: DRY RUN (no classification or save)")
    print("=" * 60)

    orchestrator = IngestionOrchestrator(domain=args.domain)

    try:
        await orchestrator.initialize()

        stats = await orchestrator.run(
            sources=sources,
            max_classify=args.max_classify,
            save_results=not args.dry_run,
            exa_themes=exa_themes,
        )

        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"Duration: {stats.duration_seconds:.1f}s")
        print(
            f"Fetched:  {stats.total_fetched} "
            f"(RSS: {stats.rss_fetched}, Exa: {stats.exa_fetched}, "
            f"ArXiv: {stats.arxiv_fetched})"
        )
        print(f"Blocked:  {stats.total_blocked}")
        print(f"Deduped:  {stats.after_dedup} unique")
        print(f"Classified: {stats.classified}")
        print(f"  Critical: {stats.critical_priority}")
        print(f"  High:     {stats.high_priority}")
        print(f"  Medium:   {stats.medium_priority}")
        print(f"  Low:      {stats.low_priority}")
        print(f"Avg Relevance: {stats.avg_relevance:.2f}")
        print(f"Saved:    {stats.saved}")
        if stats.papers_saved:
            print(f"Papers:   {stats.papers_saved}")
        if stats.stocks_fetched:
            print(f"Stocks:   {stats.stocks_fetched} snapshots")
        print(f"Embedded: {stats.embedded}")
        if stats.save_errors:
            print(f"Errors:   {stats.save_errors}")
        print("=" * 60)

    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
