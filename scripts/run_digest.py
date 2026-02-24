"""
Run Digest Generation
=====================

CLI entry point for generating a Quantum Intelligence Digest.

Usage:
    python scripts/run_digest.py
    python scripts/run_digest.py --hours 24
    python scripts/run_digest.py --hours 72 --use-llm
"""

import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from orchestrator import IngestionOrchestrator
from processing.digest_generator import DigestGenerator
from storage import get_storage
from utils.logger import configure_root_logger


async def main():
    parser = argparse.ArgumentParser(description="Intelligence Hub — Digest Generator")
    parser.add_argument(
        "--domain", type=str, default="quantum", choices=["quantum", "ai"],
        help="Domain to generate digest for (default: quantum)",
    )
    parser.add_argument(
        "--hours", type=int, default=72,
        help="Time window in hours (default: 72)",
    )
    parser.add_argument(
        "--use-llm", action="store_true",
        help="Use Claude for executive summary generation",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save digest to storage",
    )

    args = parser.parse_args()
    configure_root_logger()

    domain_label = "AI" if args.domain == "ai" else "QUANTUM"
    print("=" * 60)
    print(f"{domain_label} INTELLIGENCE HUB — Digest Generator")
    print(f"Domain: {args.domain}")
    print(f"Time window: {args.hours} hours")
    print(f"LLM summary: {'Yes' if args.use_llm else 'No (template mode)'}")
    print("=" * 60)

    storage = get_storage()

    try:
        # Get recent articles filtered by domain
        articles = await storage.get_recent_articles(hours=args.hours, domain=args.domain)
        print(f"\nFound {len(articles)} {args.domain} articles in last {args.hours} hours")

        if not articles:
            print("No articles found. Run ingestion first:")
            print(f"  python scripts/run_ingestion.py --domain {args.domain} --sources rss")
            return

        # Generate digest
        generator = DigestGenerator()
        digest = await generator.generate(
            articles=articles,
            hours=args.hours,
            use_llm=args.use_llm,
            domain=args.domain,
        )

        # Print digest (encode safely for Windows console)
        print("\n" + "=" * 60)
        summary = digest.executive_summary
        try:
            print(summary)
        except UnicodeEncodeError:
            print(summary.encode("utf-8", errors="replace").decode("utf-8"))
        print("=" * 60)
        print(f"\nTotal items: {digest.total_items}")
        print(f"  Critical: {digest.critical_count}")
        print(f"  High:     {digest.high_count}")
        print(f"  Medium:   {digest.medium_count}")
        print(f"  Low:      {digest.low_count}")

        # Save if requested
        if args.save:
            digest_id = await storage.save_digest(digest)
            print(f"\nDigest saved: {digest_id}")

    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
