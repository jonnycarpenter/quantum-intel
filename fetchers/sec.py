"""
SEC Filing Fetcher (sec-api.io)
===============================

Fetches SEC filings using sec-api.io paid API.
Part of the Regulatory Voice pipeline — runs as a standalone process.

Two endpoints used:
  - Full-Text Search: https://api.sec-api.io — query filings by ticker/type
  - Section Extractor: https://api.sec-api.io/extractor — clean section text
    (supports 10-K, 10-Q, and 8-K with filing-type-specific item codes)

Rate Limit: 500ms between requests, retry with backoff on 429.
"""

import re
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx

from models.sec_filing import SecFiling
from config.settings import SecConfig
from config.earnings_tickers import TICKER_CIK_MAP, EARNINGS_COMPANIES
from config.ai_earnings_tickers import AI_TICKER_CIK_MAP, AI_EARNINGS_COMPANIES
from utils.logger import get_logger

logger = get_logger(__name__)

# Merged CIK map and company list across both domains
_MERGED_CIK_MAP: Dict[str, str] = {**TICKER_CIK_MAP, **AI_TICKER_CIK_MAP}
_MERGED_COMPANIES: List[Dict[str, Any]] = EARNINGS_COMPANIES + [
    c for c in AI_EARNINGS_COMPANIES if c["ticker"] not in {e["ticker"] for e in EARNINGS_COMPANIES}
]


def get_cik(ticker: str) -> str:
    """Get CIK from merged quantum + AI map."""
    return _MERGED_CIK_MAP.get(ticker, "")


def get_company_name(ticker: str) -> str:
    """Get company name from merged quantum + AI list."""
    for c in _MERGED_COMPANIES:
        if c["ticker"] == ticker:
            return c["company"]
    return ticker

# sec-api.io section IDs → human-readable names, keyed by filing type
# 10-K: numeric item codes
SECTIONS_10K: Dict[str, str] = {
    "1": "business",
    "1A": "risk_factors",
    "7": "mda",
    "7A": "market_risk_disclosures",
}

# 10-Q: part/item codes (different from 10-K)
SECTIONS_10Q: Dict[str, str] = {
    "part1item2": "mda",
    "part1item3": "market_risk_disclosures",
    "part2item1": "legal_proceedings",
    "part2item1a": "risk_factors",
}

# 8-K: event item codes — sec-api.io uses dash notation (1-1, 2-2, not 1.01, 2.02)
# 2-2 = financial results (earnings), 1-1 = material agreement,
# 5-2 = leadership change, 7-1 = Reg FD, 8-1 = other events
SECTIONS_8K: Dict[str, str] = {
    "2-2": "financial_results",
    "1-1": "material_agreement",
    "5-2": "leadership_change",
    "7-1": "regulation_fd",
    "8-1": "other_events",
}


class SecFetcher:
    """
    Fetches SEC filings using sec-api.io.

    Uses the paid API for reliable filing search and clean section extraction.
    Falls back to free EDGAR JSON API for metadata if needed.
    """

    MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests

    def __init__(self, config: Optional[SecConfig] = None):
        self.config = config or SecConfig()
        self.api_key = self.config.sec_api_key
        self.query_url = self.config.sec_api_query_url
        self.extractor_url = self.config.sec_api_extractor_url
        self._last_call_time = 0.0

        if not self.api_key:
            logger.warning("[SEC] No SECIO_API_KEY set — sec-api.io calls will fail")

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_call_time = time.time()

    def _api_request(
        self,
        method: str,
        url: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> Optional[httpx.Response]:
        """Make an authenticated request to sec-api.io with retry."""
        self._rate_limit()

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    if method == "POST":
                        resp = client.post(url, headers=headers, json=json_body)
                    else:
                        resp = client.get(url, headers=headers, params=params)

                    if resp.status_code == 429:
                        delay = 2 * (2 ** attempt)
                        logger.warning(
                            f"[SEC] Rate limited (attempt {attempt + 1}/{max_retries}), "
                            f"backing off {delay}s"
                        )
                        time.sleep(delay)
                        continue

                    resp.raise_for_status()
                    return resp

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"[SEC] HTTP {e.response.status_code} for {url} | "
                    f"body: {e.response.text[:200]}"
                )
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    time.sleep(2 * (2 ** attempt))
                    continue
                return None
            except Exception as e:
                logger.error(f"[SEC] Request error: {e}")
                return None

        return None

    # =========================================================================
    # Filing Search (Full-Text Search API)
    # =========================================================================

    def get_company_filings(
        self,
        ticker: str,
        filing_types: Optional[List[str]] = None,
        max_filings: int = 10,
    ) -> List[SecFiling]:
        """
        Search for filings via sec-api.io Full-Text Search.

        Args:
            ticker: Stock ticker (e.g., 'IONQ')
            filing_types: Filter to these types (default: config.filing_types)
            max_filings: Maximum filings to return

        Returns:
            List of SecFiling objects (metadata only, no content)
        """
        cik = get_cik(ticker)
        company_name = get_company_name(ticker)

        if not cik:
            logger.warning(f"[SEC] No CIK for ticker: {ticker}")
            return []

        types = filing_types or self.config.filing_types
        type_clause = " OR ".join(f'"{t}"' for t in types)
        query = f'ticker:{ticker} AND formType:({type_clause})'

        payload = {
            "query": {"query_string": {"query": query}},
            "from": "0",
            "size": str(max_filings),
            "sort": [{"filedAt": {"order": "desc"}}],
        }

        logger.info(f"[SEC] Searching filings for {ticker}: {types}")
        resp = self._api_request("POST", self.query_url, json_body=payload)
        if not resp:
            return []

        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"[SEC] Failed to parse search response: {e}")
            return []

        hits = data.get("filings", [])
        if not hits:
            logger.info(f"[SEC] No filings found for {ticker}")
            return []

        filings = []
        for hit in hits:
            try:
                # Parse filing date
                filed_at = hit.get("filedAt", "")
                try:
                    filing_date = datetime.fromisoformat(
                        filed_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    filing_date = datetime.now(timezone.utc)

                form_type = hit.get("formType", "")
                accession = hit.get("accessionNo", "")
                filing_url = hit.get("linkToFilingDetails", "")

                # Determine fiscal year/quarter
                fiscal_year = filing_date.year
                fiscal_quarter = None

                if form_type == "10-Q":
                    month = filing_date.month
                    if month <= 3:
                        fiscal_quarter = 4
                        fiscal_year -= 1
                    elif month <= 6:
                        fiscal_quarter = 1
                    elif month <= 9:
                        fiscal_quarter = 2
                    else:
                        fiscal_quarter = 3
                elif form_type == "10-K":
                    if filing_date.month <= 4:
                        fiscal_year -= 1

                filing = SecFiling(
                    ticker=ticker,
                    company_name=hit.get("companyName", company_name),
                    cik=str(cik),
                    accession_number=accession,
                    filing_type=form_type,
                    filing_date=filing_date,
                    fiscal_year=fiscal_year,
                    fiscal_quarter=fiscal_quarter,
                    primary_document=hit.get("documentFormatFiles", [{}])[0].get(
                        "documentUrl", ""
                    ) if hit.get("documentFormatFiles") else "",
                    filing_url=filing_url,
                )
                filings.append(filing)

            except Exception as e:
                logger.warning(f"[SEC] Error parsing filing hit: {e}")
                continue

        logger.info(f"[SEC] Found {len(filings)} filings for {ticker}")
        return filings

    # =========================================================================
    # Section Extraction (Extractor API)
    # =========================================================================

    def _extract_section(self, filing_url: str, section_id: str) -> Optional[str]:
        """
        Extract a single section from a filing via sec-api.io Extractor.

        Works for 10-K, 10-Q, and 8-K with filing-type-specific item codes:
          - 10-K: "1", "1A", "7", "7A"
          - 10-Q: "part1item2", "part2item1a", etc.
          - 8-K: "1.01", "2.02", "5.02", "7.01", "8.01"

        Args:
            filing_url: URL to the filing (linkToFilingDetails)
            section_id: Section identifier (type-specific code)

        Returns:
            Clean text content of the section, or None
        """
        params = {
            "url": filing_url,
            "item": section_id,
            "type": "text",
            "token": self.api_key,
        }

        resp = self._api_request("GET", self.extractor_url, params=params, timeout=120.0)
        if not resp:
            return None

        text = resp.text.strip()
        # sec-api.io returns empty string or error message for missing sections
        if not text or len(text) < 50 or text.startswith("{"):
            return None

        return text

    def fetch_filing_content(self, filing: SecFiling) -> Optional[SecFiling]:
        """
        Download and parse the filing content using sec-api.io Extractor.

        Uses filing-type-specific section item codes:
          - 10-K: business, risk_factors, mda, market_risk
          - 10-Q: mda, market_risk, legal_proceedings, risk_factors
          - 8-K: financial_results, material_agreement, leadership_change, etc.

        Args:
            filing: SecFiling with filing_url set

        Returns:
            SecFiling with raw_content and sections populated
        """
        if not filing.filing_url:
            logger.warning(f"[SEC] No filing URL for {filing.unique_key}")
            return None

        logger.info(f"[SEC] Fetching content for {filing.unique_key}")

        # Select the right section map for this filing type
        if filing.filing_type == "10-K":
            section_map = SECTIONS_10K
            extract_url = filing.filing_url
        elif filing.filing_type == "10-Q":
            section_map = SECTIONS_10Q
            extract_url = filing.filing_url
        elif filing.filing_type == "8-K":
            section_map = SECTIONS_8K
            # 8-K extractor needs the raw document URL, not the iXBRL viewer wrapper.
            # EDGAR often returns URLs like: https://www.sec.gov/ix?doc=/Archives/...
            # Strip the iXBRL wrapper to get the real .htm document path.
            doc_url = filing.primary_document or filing.filing_url
            if "ix?doc=" in doc_url:
                # e.g. https://www.sec.gov/ix?doc=/Archives/... → https://www.sec.gov/Archives/...
                doc_path = doc_url.split("ix?doc=", 1)[1]
                if doc_path.startswith("/"):
                    doc_url = "https://www.sec.gov" + doc_path
            extract_url = doc_url
        else:
            logger.warning(f"[SEC] Unsupported filing type: {filing.filing_type}")
            return None

        logger.info(f"[SEC] Extracting {filing.filing_type} from URL: {extract_url}")

        sections = {}
        for section_id, section_name in section_map.items():
            text = self._extract_section(extract_url, section_id)
            if text:
                sections[section_name] = text
                logger.debug(
                    f"[SEC] Extracted {section_name}: {len(text):,} chars"
                )

        if not sections:
            logger.warning(f"[SEC] No sections extracted for {filing.unique_key}")
            return None

        # Build raw_content from sections
        raw_parts = []
        for name, content in sections.items():
            raw_parts.append(f"--- {name.upper()} ---\n\n{content}")
        raw_content = "\n\n".join(raw_parts)

        filing.raw_content = raw_content
        filing.sections = sections
        filing.char_count = len(raw_content)

        # Truncate if too large
        max_chars = self.config.max_filing_chars
        if filing.char_count > max_chars:
            logger.info(
                f"[SEC] Truncating from {filing.char_count:,} to {max_chars:,} chars"
            )
            filing.raw_content = filing.raw_content[:max_chars]
            filing.char_count = max_chars

        logger.info(
            f"[SEC] Fetched {filing.unique_key}: {filing.char_count:,} chars, "
            f"{len(filing.sections)} sections"
        )
        return filing

    # =========================================================================
    # Pipeline Integration
    # =========================================================================

    async def fetch_new_filings(
        self,
        storage,
        tickers: Optional[List[str]] = None,
        filing_types: Optional[List[str]] = None,
        fetch_content: bool = True,
        max_filings: int = 1,
    ) -> List[SecFiling]:
        """
        Fetch only filings that aren't already in storage.

        Searches per filing type to guarantee max_filings of each type
        regardless of how frequently a company files other types.

        Args:
            storage: StorageBackend instance
            tickers: Tickers to check
            filing_types: Filing types to include
            fetch_content: Whether to download full content
            max_filings: Max filings per ticker PER TYPE

        Returns:
            List of new SecFiling objects
        """
        tickers = tickers or list(_MERGED_CIK_MAP.keys())
        types = filing_types or self.config.filing_types
        new_filings: List[SecFiling] = []

        for ticker in tickers:
            # Search per type so max_filings applies per-type, not combined
            for filing_type in types:
                filings = self.get_company_filings(
                    ticker,
                    filing_types=[filing_type],
                    max_filings=max_filings,
                )

                for filing in filings:
                    # Skip if already stored
                    exists = await storage.filing_exists(
                        filing.ticker, filing.filing_type,
                        filing.fiscal_year, filing.fiscal_quarter,
                    )
                    if exists:
                        logger.debug(f"[SEC] Already stored: {filing.unique_key}")
                        continue

                    if fetch_content:
                        filing = self.fetch_filing_content(filing)
                        if filing and filing.raw_content:
                            new_filings.append(filing)
                    else:
                        new_filings.append(filing)

        logger.info(f"[SEC] New filings fetched: {len(new_filings)}")
        return new_filings
