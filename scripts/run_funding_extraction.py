#!/usr/bin/env python3
"""
Run Funding Extraction
======================

Backfills and continuously runs the funding extractor on articles
classified as `funding_ipo` to build the comprehensive funding database.
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.sqlite import SQLiteStorage
from processing.funding_extractor import FundingExtractor
from models.funding import FundingEvent
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Run VC Funding Extraction")
    parser.add_argument("--domain", type=str, choices=["quantum", "ai", "all"], default="all",
                        help="Domain to filter by")
    parser.add_argument("--hours", type=int, default=720,
                        help="Lookback window in hours (default: 720 / 30 days)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max articles to process")
    args = parser.parse_args()

    load_dotenv()
    
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)
        
    storage = SQLiteStorage()
    extractor = FundingExtractor(api_key=anthropic_api_key)

    domains = ["quantum", "ai"] if args.domain == "all" else [args.domain]
    
    total_extracted = 0
    total_cost = 0.0
    
    for domain in domains:
        logger.info(f"=== Fetching funding articles for domain: {domain} ===")
        # Get articles classified as funding_ipo
        articles = await storage.get_articles_by_category(
            category="funding_ipo",
            hours=args.hours,
            limit=args.limit,
            domain=domain
        )
        
        logger.info(f"Found {len(articles)} potential funding articles in the last {args.hours} hours.")
        
        # Filter out those we already processed
        to_process = []
        for article in articles:
            exists = await storage.funding_events_exist_for_article(article.id)
            if not exists:
                to_process.append(article)
                
        logger.info(f"Skipped {len(articles) - len(to_process)} already processed. Extracting from {len(to_process)} articles...")
        
        for article in to_process:
            logger.info(f"\nProcessing: {article.title}")
            logger.info(f"URL: {article.url}")
            
            result = await extractor.extract_funding_events(
                article_id=article.id,
                article_url=article.url,
                full_text=article.full_text,
                domain=domain
            )
            
            total_cost += result.extraction_cost_usd
            
            if result.success and result.funding_events:
                events_saved = await storage.save_funding_events(result.funding_events)
                total_extracted += events_saved
                for event in result.funding_events:
                    logger.info(f"  -> Extracted: {event.startup_name} | {event.funding_round} | {event.funding_amount}")
            elif not result.success:
                logger.warning(f"  -> Extraction failed: {result.error_message}")
            else:
                logger.info("  -> No valid funding events found in text.")

    await storage.close()
    
    logger.info("\n=== Extraction Summary ===")
    logger.info(f"Total New Funding Events Extracted: {total_extracted}")
    logger.info(f"Estimated Claude Run Cost: ${total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
