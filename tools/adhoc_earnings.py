"""
Ad-Hoc Earnings Fetcher Tool
============================

Allows the Intelligence Agent to pull an earnings call transcript on-demand
for a specific company and automatically ingest it into BigQuery.
"""

import json
import logging
from typing import Optional

from fetchers.earnings import EarningsFetcher
from storage import get_storage
from processing.podcast_quote_extractor import PodcastQuoteExtractor
from config.settings import AppConfig

logger = logging.getLogger(__name__)


class AdHocEarningsTool:
    """Tool for ad-hoc earnings call transcript retrieval."""

    def __init__(self):
        self.fetcher = EarningsFetcher()
        self.storage = get_storage()
        
        # We need the quote extractor to fully process the pipeline 
        # so it saves to the BigQuery analytics tables
        config = AppConfig()
        self.extractor = PodcastQuoteExtractor(config=config)

    async def execute(
        self,
        ticker: str,
        year: int,
        quarter: int,
    ) -> str:
        """
        Fetch an earnings call transcript, extract quotes, save to BigQuery, and return a snippet.

        Args:
            ticker: Stock ticker symbol (e.g. 'IONQ')
            year: Four-digit fiscal year
            quarter: Fiscal quarter (1-4)

        Returns:
            JSON string with operation success and an executive summary snippet.
        """
        logger.info(f"[TOOL] adhoc_earnings: ticker='{ticker}' Q{quarter} {year}")

        try:
            # 1. Check if we already have it in the DB to avoid redundant extraction cost
            exists = await self.storage.transcript_exists(
                ticker, year, quarter
            )

            if exists:
                logger.info(f"[ADHOC EARNINGS] Transcript already exists in DB: {ticker} Q{quarter} {year}")
                return json.dumps({
                    "status": "success",
                    "message": f"The Q{quarter} {year} earnings call transcript for {ticker} is already in the platform database. You can query it using the corpus_search tool."
                })

            # 2. Fetch full content
            transcript = self.fetcher.fetch_transcript(ticker, year, quarter)
            if not transcript or not transcript.transcript_text:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to download the earnings transcript for {ticker} Q{quarter} {year}."
                })

            # 3. Save raw transcript to BQ
            await self.storage.save_transcripts([transcript])

            # 4. Extract Quotes (Executive Voice Pipeline)
            logger.info(f"[ADHOC EARNINGS] Extracting quotes for {ticker} Q{quarter}")
            # The podcast quote extractor is natively equipped to handle earnings call text blocks
            # if we pass it through the unified pipeline hook
            from scripts.run_earnings_extraction import process_transcript
            
            # Use the existing pipeline logic to handle chunking, API limits, and Quote dataclasses
            quotes = await process_transcript(transcript, self.extractor)

            if quotes:
                await self.storage.save_quotes(quotes)
                logger.info(f"[ADHOC EARNINGS] Saved {len(quotes)} quotes to BQ.")

            # Return success to the agent with a small snippet
            summary = transcript.transcript_text[:1500] + "\n\n...[TRUNCATED]"
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully fetched and ingested the Q{quarter} {year} earnings call for {ticker} into the BigQuery database. You can now analyze it.",
                "call_date": str(transcript.call_date),
                "extracted_quotes_count": len(quotes) if quotes else 0,
                "content_preview": summary
            })

        except Exception as e:
            logger.error(f"[TOOL] adhoc_earnings error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Ad-Hoc Earnings fetch failed: {type(e).__name__}: {e}"
            })
