"""
Earnings Call Fetcher
======================

Fetches earnings call transcripts from API Ninjas.
Part of the Earnings Voice pipeline — runs as a standalone process.

API Docs: https://api-ninjas.com/api/earningstranscript
"""

import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx

from models.earnings import EarningsTranscript
from config.settings import EarningsConfig
from config.earnings_tickers import (
    EARNINGS_COMPANIES, ALL_EARNINGS_TICKERS,
)
from config.ai_earnings_tickers import AI_EARNINGS_COMPANIES
from utils.logger import get_logger

logger = get_logger(__name__)

# Merged company list across both domains
_MERGED_COMPANIES = EARNINGS_COMPANIES + [
    c for c in AI_EARNINGS_COMPANIES if c["ticker"] not in {e["ticker"] for e in EARNINGS_COMPANIES}
]


def get_company_name(ticker: str) -> str:
    """Get company name from merged quantum + AI list."""
    for c in _MERGED_COMPANIES:
        if c["ticker"] == ticker:
            return c["company"]
    return ticker


class EarningsFetcher:
    """Fetches earnings call transcripts from API Ninjas."""

    def __init__(self, config: Optional[EarningsConfig] = None):
        self.config = config or EarningsConfig()
        self.base_url = self.config.api_ninja_base_url
        self.api_key = self.config.api_ninja_api_key
        self._last_request_time = 0.0

        if not self.api_key:
            logger.warning("[EARNINGS] No API_NINJA_API_KEY set — fetcher will not work")

    def _rate_limit(self):
        """Enforce rate limit between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.api_ninja_rate_limit_seconds:
            time.sleep(self.config.api_ninja_rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def _estimate_call_date(year: int, quarter: int) -> datetime:
        """
        Estimate earnings call date from fiscal year/quarter.

        Earnings calls typically happen 4-6 weeks after quarter end:
          Q1 (Jan-Mar) → ~May 1    Q2 (Apr-Jun) → ~Aug 1
          Q3 (Jul-Sep) → ~Nov 1    Q4 (Oct-Dec) → ~Feb 1 next year
        """
        month_map = {1: 5, 2: 8, 3: 11, 4: 2}
        call_month = month_map[quarter]
        call_year = year + 1 if quarter == 4 else year
        return datetime(call_year, call_month, 1, tzinfo=timezone.utc)

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Make an authenticated API request."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "X-Api-Key": self.api_key,
        }

        self._rate_limit()
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[EARNINGS] API request failed: {e.response.status_code} - "
                f"{e.response.text[:200]}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"[EARNINGS] Network error: {e}")
            return None

    def fetch_transcript(
        self, ticker: str, year: int, quarter: int
    ) -> Optional[EarningsTranscript]:
        """
        Fetch a single earnings call transcript.

        Args:
            ticker: Stock ticker (e.g., 'IONQ')
            year: Fiscal year
            quarter: Fiscal quarter (1-4)

        Returns:
            EarningsTranscript if found, None otherwise
        """
        logger.info(f"[EARNINGS] Fetching transcript: {ticker} Q{quarter} {year}")

        data = self._make_request(
            "earningstranscript",
            {"ticker": ticker, "year": year, "quarter": quarter},
        )

        if not data:
            logger.warning(f"[EARNINGS] No transcript found: {ticker} Q{quarter} {year}")
            return None

        # API Ninjas returns a list — get the transcript content
        transcript_text = ""
        participants = []

        if isinstance(data, list):
            # Each item may be a segment of the transcript
            segments = []
            for item in data:
                if isinstance(item, dict):
                    text = item.get("transcript", item.get("text", ""))
                    if text:
                        segments.append(text)
                    # Extract participants if available
                    if "speakers" in item:
                        for speaker in item["speakers"]:
                            participants.append({
                                "name": speaker.get("name", ""),
                                "role": speaker.get("role", speaker.get("title", "")),
                            })
                elif isinstance(item, str):
                    segments.append(item)
            transcript_text = "\n\n".join(segments)
        elif isinstance(data, dict):
            transcript_text = data.get("transcript", data.get("text", str(data)))
            if "speakers" in data:
                for speaker in data["speakers"]:
                    participants.append({
                        "name": speaker.get("name", ""),
                        "role": speaker.get("role", speaker.get("title", "")),
                    })
        elif isinstance(data, str):
            transcript_text = data

        if not transcript_text or len(transcript_text) < 100:
            logger.warning(
                f"[EARNINGS] Transcript too short ({len(transcript_text)} chars): "
                f"{ticker} Q{quarter} {year}"
            )
            return None

        transcript = EarningsTranscript(
            ticker=ticker,
            company_name=get_company_name(ticker),
            year=year,
            quarter=quarter,
            transcript_text=transcript_text,
            participants=participants,
            fiscal_period=f"Q{quarter} {year}",
            call_date=self._estimate_call_date(year, quarter),
        )

        logger.info(
            f"[EARNINGS] Fetched {ticker} Q{quarter} {year}: "
            f"{transcript.char_count:,} chars"
        )
        return transcript

    def fetch_available_transcripts(
        self,
        tickers: Optional[List[str]] = None,
        max_quarters: Optional[int] = None,
    ) -> List[EarningsTranscript]:
        """
        Fetch transcripts for multiple tickers across recent quarters.

        Args:
            tickers: Tickers to fetch (defaults to ALL_EARNINGS_TICKERS)
            max_quarters: Max quarters to go back per ticker

        Returns:
            List of EarningsTranscript objects
        """
        tickers = tickers or ALL_EARNINGS_TICKERS
        max_q = max_quarters or self.config.max_quarters_to_fetch
        transcripts: List[EarningsTranscript] = []

        # Generate year/quarter pairs going back max_q quarters from now
        now = datetime.now(timezone.utc)
        current_year = now.year
        current_quarter = (now.month - 1) // 3 + 1

        quarters_to_check = []
        y, q = current_year, current_quarter
        for _ in range(max_q):
            quarters_to_check.append((y, q))
            q -= 1
            if q == 0:
                q = 4
                y -= 1

        for ticker in tickers:
            logger.info(f"[EARNINGS] Scanning {ticker} for last {max_q} quarters...")
            for year, quarter in quarters_to_check:
                transcript = self.fetch_transcript(ticker, year, quarter)
                if transcript:
                    transcripts.append(transcript)

        logger.info(f"[EARNINGS] Total transcripts fetched: {len(transcripts)}")
        return transcripts

    async def fetch_new_transcripts(
        self,
        storage,
        tickers: Optional[List[str]] = None,
        max_quarters: Optional[int] = None,
    ) -> List[EarningsTranscript]:
        """
        Fetch only transcripts that aren't already in storage.

        Args:
            storage: StorageBackend instance
            tickers: Tickers to fetch
            max_quarters: Max quarters per ticker

        Returns:
            List of newly fetched EarningsTranscript objects
        """
        tickers = tickers or ALL_EARNINGS_TICKERS
        max_q = max_quarters or self.config.max_quarters_to_fetch
        new_transcripts: List[EarningsTranscript] = []

        now = datetime.now(timezone.utc)
        current_year = now.year
        current_quarter = (now.month - 1) // 3 + 1

        quarters_to_check = []
        y, q = current_year, current_quarter
        for _ in range(max_q):
            quarters_to_check.append((y, q))
            q -= 1
            if q == 0:
                q = 4
                y -= 1

        for ticker in tickers:
            for year, quarter in quarters_to_check:
                # Skip if already in storage
                if await storage.transcript_exists(ticker, year, quarter):
                    logger.debug(
                        f"[EARNINGS] Already stored: {ticker} Q{quarter} {year}"
                    )
                    continue

                transcript = self.fetch_transcript(ticker, year, quarter)
                if transcript:
                    new_transcripts.append(transcript)

        logger.info(
            f"[EARNINGS] New transcripts fetched: {len(new_transcripts)} "
            f"(checked {len(tickers)} tickers × {max_q} quarters)"
        )
        return new_transcripts
