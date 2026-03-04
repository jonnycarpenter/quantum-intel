"""
Ad-Hoc SEC Filing Fetcher Tool
==============================

Allows the Intelligence Agent to pull an SEC filing on-demand for a specific company,
automatically injecting it into the platform's core BigQuery storage pipeline.
"""

import json
import logging
from typing import Optional

from fetchers.sec import SecFetcher
from storage import get_storage
from processing.quote_extractor import QuoteExtractor
from config.settings import SecConfig

logger = logging.getLogger(__name__)


class AdHocSecTool:
    """Tool for ad-hoc SEC filing retrieval."""

    def __init__(self):
        self.fetcher = SecFetcher()
        self.storage = get_storage()
        
        # We need the quote extractor to fully process the pipeline 
        # so it saves to the BigQuery analytics tables
        config = SecConfig()
        self.extractor = QuoteExtractor(config=config)

    async def execute(
        self,
        ticker: str,
        filing_type: str = "10-K",
    ) -> str:
        """
        Fetch an SEC filing, extract quotes, save to BigQuery, and return a snippet.

        Args:
            ticker: Stock ticker symbol
            filing_type: "10-K", "10-Q", or "8-K"

        Returns:
            JSON string with operation success and an executive summary snippet.
        """
        logger.info(f"[TOOL] adhoc_sec: ticker='{ticker}', type='{filing_type}'")

        try:
            # 1. Fetch metadata
            filings = self.fetcher.get_company_filings(
                ticker=ticker,
                filing_types=[filing_type],
                max_filings=1
            )

            if not filings:
                return json.dumps({
                    "status": "error",
                    "message": f"Could not find any {filing_type} filings for {ticker}."
                })

            target_filing = filings[0]
            
            # Check if we already have it in the DB to avoid redundant extraction cost
            exists = await self.storage.filing_exists(
                target_filing.ticker, 
                target_filing.filing_type,
                target_filing.fiscal_year, 
                target_filing.fiscal_quarter
            )

            if exists:
                logger.info(f"[ADHOC SEC] Filing already exists in DB: {target_filing.unique_key}")
                return json.dumps({
                    "status": "success",
                    "message": f"The {filing_type} for {ticker} is already in the platform database. You can query it using the corpus_search tool."
                })

            # 2. Fetch full content
            full_filing = self.fetcher.fetch_filing_content(target_filing)
            if not full_filing or not full_filing.raw_content:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to download the text content for {ticker} {filing_type}."
                })

            # 3. Save raw filing to BQ
            await self.storage.save_filings([full_filing])

            # 4. Extract Quotes (Regulatory Voice Pipeline)
            logger.info(f"[ADHOC SEC] Extracting quotes for {full_filing.unique_key}")
            quotes, err = await self.extractor.extract_quotes(full_filing)
            
            if quotes:
                await self.storage.save_quotes(quotes)
                logger.info(f"[ADHOC SEC] Saved {len(quotes)} quotes to BQ.")

            # Return success to the agent with a small snippet
            summary = full_filing.raw_content[:1500] + "\n\n...[TRUNCATED]"
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully fetched and ingested the {filing_type} for {ticker} into the BigQuery database.",
                "filing_date": str(full_filing.filing_date),
                "url": full_filing.filing_url,
                "extracted_quotes_count": len(quotes) if quotes else 0,
                "content_preview": summary
            })

        except Exception as e:
            logger.error(f"[TOOL] adhoc_sec error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Ad-Hoc SEC fetch failed: {type(e).__name__}: {e}"
            })
