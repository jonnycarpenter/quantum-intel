"""
Test RSS Feeds
==============

Verify that configured RSS feeds are accessible and returning entries.

Usage:
    python scripts/test_feeds.py
    python scripts/test_feeds.py --tier 1
"""

import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
from config.rss_sources import RSS_FEEDS


async def test_feeds(tier_filter: int = 0):
    """Test all configured RSS feeds."""
    feeds = RSS_FEEDS
    if tier_filter:
        feeds = [f for f in feeds if f.get("tier") == tier_filter]

    print(f"Testing {len(feeds)} RSS feeds...")
    print("-" * 70)

    success = 0
    failed = 0

    for feed in feeds:
        name = feed["name"]
        url = feed["url"]
        tier = feed.get("tier", "?")

        try:
            parsed = feedparser.parse(url)
            entry_count = len(parsed.entries)

            if parsed.bozo and not parsed.entries:
                print(f"  FAIL  | T{tier} | {name:30s} | Error: {parsed.bozo_exception}")
                failed += 1
            elif entry_count == 0:
                print(f"  WARN  | T{tier} | {name:30s} | 0 entries (feed may be empty)")
                failed += 1
            else:
                latest = "?"
                if parsed.entries[0].get("published"):
                    latest = parsed.entries[0]["published"][:25]
                print(f"  OK    | T{tier} | {name:30s} | {entry_count:3d} entries | Latest: {latest}")
                success += 1

        except Exception as e:
            print(f"  FAIL  | T{tier} | {name:30s} | {type(e).__name__}: {e}")
            failed += 1

    print("-" * 70)
    print(f"Results: {success} OK, {failed} failed out of {len(feeds)} feeds")


def main():
    parser = argparse.ArgumentParser(description="Test RSS feeds")
    parser.add_argument("--tier", type=int, default=0, help="Filter by tier (1-4)")
    args = parser.parse_args()

    asyncio.run(test_feeds(args.tier))


if __name__ == "__main__":
    main()
