"""
Run Weekly Briefing Generation
===============================

CLI entry point for generating weekly intelligence briefings.
Two-agent pipeline: Research Agent (Sonnet) → Briefing Agent (Opus).

Usage:
    python scripts/run_weekly_briefing.py --domain quantum
    python scripts/run_weekly_briefing.py --domain ai --save
    python scripts/run_weekly_briefing.py --domain quantum --days 14 --json
"""

import sys
import os
import asyncio
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import WeeklyBriefingConfig
from processing.weekly_briefing import WeeklyBriefingPipeline
from storage import get_storage
from utils.logger import configure_root_logger


def _safe_print(text: str) -> None:
    """Print with safe encoding for Windows console."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def print_briefing(briefing) -> None:
    """Pretty-print a WeeklyBriefing to the console."""
    domain_label = briefing.domain.upper()
    print()
    print("=" * 70)
    print(f"  {domain_label} WEEKLY INTELLIGENCE BRIEFING")
    print(f"  Week of {briefing.week_of}")
    print(f"  {briefing.articles_analyzed} articles analyzed | "
          f"{briefing.sections_active}/{briefing.sections_total} sections active | "
          f"cost: ${briefing.generation_cost_usd:.4f}")
    print("=" * 70)

    # Active sections
    active_sections = [s for s in briefing.sections if s.has_content]
    inactive_tags = [
        f"{s.priority_tag}: {s.priority_label}"
        for s in briefing.sections if not s.has_content
    ]

    for section in active_sections:
        print()
        print(f"  [{section.priority_tag}] {section.header}")
        print("  " + "-" * 60)
        # Narrative
        for line in section.narrative.split("\n"):
            _safe_print(f"  {line}")

        # Voice quotes
        if section.voice_quotes:
            print()
            for vq in section.voice_quotes:
                source_tag = vq.source_type.upper() if vq.source_type else "QUOTE"
                _safe_print(f'  [{source_tag}] "{vq.text}"')
                speaker_line = f"    -- {vq.speaker}"
                if vq.role:
                    speaker_line += f", {vq.role}"
                if vq.company:
                    speaker_line += f" ({vq.company})"
                if vq.source_context:
                    speaker_line += f" | {vq.source_context}"
                _safe_print(speaker_line)

        # Citations
        if section.citations:
            print()
            print("  Sources:")
            for c in section.citations:
                source_info = f"  [{c.number}] {c.title}"
                if c.source_name:
                    source_info += f" — {c.source_name}"
                _safe_print(source_info)

    # Market movers
    if briefing.market_movers:
        print()
        print()
        print("  MARKET MOVERS (>5% weekly change)")
        print("  " + "-" * 60)
        print(f"  {'Ticker':<8} {'Close':>8} {'Change':>8}  Context")
        print(f"  {'------':<8} {'-----':>8} {'------':>8}  -------")
        for mm in briefing.market_movers:
            close_str = f"${mm.close:.2f}" if mm.close is not None else "N/A"
            sign = "+" if mm.change_pct >= 0 else ""
            _safe_print(
                f"  {mm.ticker:<8} {close_str:>8} {sign}{mm.change_pct:.1f}%"
                f"{'':>3}{mm.context_text}"
            )

    # Research papers
    if briefing.research_papers:
        print()
        print()
        print("  RESEARCH FRONTIER")
        print("  " + "-" * 60)
        for rp in briefing.research_papers:
            _safe_print(f"  {rp.title}")
            authors_str = ", ".join(rp.authors[:3])
            if len(rp.authors) > 3:
                authors_str += " et al."
            _safe_print(f"    Authors: {authors_str}")
            if rp.why_it_matters:
                _safe_print(f"    Why it matters: {rp.why_it_matters}")
            if rp.commercial_readiness:
                _safe_print(f"    Commercial readiness: {rp.commercial_readiness}")
            print()

    # Footer
    print()
    print("  " + "-" * 60)
    if inactive_tags:
        _safe_print(f"  Sections with no updates this week: {', '.join(inactive_tags)}")
    print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(
        description="Quantum+AI Intelligence Hub — Weekly Briefing Generator"
    )
    parser.add_argument(
        "--domain", type=str, default="quantum", choices=["quantum", "ai"],
        help="Domain to generate briefing for (default: quantum)",
    )
    parser.add_argument(
        "--days", type=int, default=14,
        help="Lookback window in days (default: 14)",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save briefing to storage",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of pretty-print",
    )
    parser.add_argument(
        "--db-path", type=str, default=None,
        help="Override SQLite database path",
    )

    args = parser.parse_args()
    configure_root_logger()

    domain_label = "AI" if args.domain == "ai" else "QUANTUM"
    print("=" * 60)
    print(f"{domain_label} INTELLIGENCE HUB — Weekly Briefing Generator")
    print(f"Domain: {args.domain}")
    print(f"Lookback: {args.days} days")
    print("=" * 60)

    storage = get_storage(db_path=args.db_path)

    try:
        config = WeeklyBriefingConfig()
        pipeline = WeeklyBriefingPipeline(config=config, storage=storage)

        print("\nRunning 2-agent pipeline...")
        print("  Step 1: Fetching articles")
        print("  Step 2: Research Agent (Sonnet) — batch analysis")
        print("  Step 3: Voice enrichment (earnings/SEC/podcasts)")
        print("  Step 4: Market mover detection")
        print("  Step 5: Research paper selection")
        print("  Step 6: Briefing Agent (Opus) — narrative synthesis")
        print()

        briefing = await pipeline.generate(domain=args.domain, days=args.days)

        # Save before printing so encoding errors don't prevent persistence
        if args.save:
            briefing_id = await storage.save_weekly_briefing(briefing)
            print(f"\nBriefing saved: {briefing_id}")

        if args.json:
            print(json.dumps(briefing.to_dict(), indent=2, default=str))
        else:
            print_briefing(briefing)

    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
