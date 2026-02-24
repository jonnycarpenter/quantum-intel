"""
Earnings Ticker Config
=======================

Ticker-to-CIK mapping and configuration for the Earnings Call pipeline.
CIK numbers are required for SEC EDGAR lookups.
"""

from typing import Dict, List, Any


# =============================================================================
# Ticker → CIK Mapping (SEC Central Index Key)
# =============================================================================

TICKER_CIK_MAP: Dict[str, str] = {
    # Pure-Play Quantum
    "IONQ": "1824920",
    "QBTS": "1907982",
    "RGTI": "1838359",
    "QUBT": "1758009",
    "ARQQ": "1859690",
    "QMCO": "709283",
    "LAES": "1951222",
    # Major Tech with Quantum Divisions
    "GOOGL": "1652044",
    "IBM": "51143",
    "MSFT": "789019",
    "AMZN": "1018724",
    "HON": "773840",
    "NVDA": "1045810",
}


# =============================================================================
# Company Info (matches tickers.py structure)
# =============================================================================

EARNINGS_COMPANIES: List[Dict[str, Any]] = [
    # Pure-play quantum — always fetch earnings
    {"ticker": "IONQ", "company": "IonQ Inc.", "tier": "core", "cik": "1824920"},
    {"ticker": "QBTS", "company": "D-Wave Quantum Inc.", "tier": "core", "cik": "1907982"},
    {"ticker": "RGTI", "company": "Rigetti Computing Inc.", "tier": "core", "cik": "1838359"},
    {"ticker": "QUBT", "company": "Quantum Computing Inc.", "tier": "core", "cik": "1758009"},
    {"ticker": "ARQQ", "company": "Arqit Quantum Inc.", "tier": "core", "cik": "1859690"},
    {"ticker": "QMCO", "company": "Quantum Corporation", "tier": "core", "cik": "709283"},
    {"ticker": "LAES", "company": "SealSQ Corp.", "tier": "core", "cik": "1951222"},
    # Major tech — extract only quantum-relevant nuggets
    {"ticker": "GOOGL", "company": "Alphabet (Google)", "tier": "secondary", "cik": "1652044"},
    {"ticker": "IBM", "company": "IBM", "tier": "secondary", "cik": "51143"},
    {"ticker": "MSFT", "company": "Microsoft", "tier": "secondary", "cik": "789019"},
    {"ticker": "AMZN", "company": "Amazon", "tier": "secondary", "cik": "1018724"},
    {"ticker": "HON", "company": "Honeywell", "tier": "secondary", "cik": "773840"},
    {"ticker": "NVDA", "company": "Nvidia", "tier": "secondary", "cik": "1045810"},
]


# =============================================================================
# Convenience accessors
# =============================================================================

CORE_TICKERS: List[str] = [c["ticker"] for c in EARNINGS_COMPANIES if c["tier"] == "core"]
SECONDARY_TICKERS: List[str] = [c["ticker"] for c in EARNINGS_COMPANIES if c["tier"] == "secondary"]
ALL_EARNINGS_TICKERS: List[str] = [c["ticker"] for c in EARNINGS_COMPANIES]

def get_company_name(ticker: str) -> str:
    """Get company name by ticker."""
    for c in EARNINGS_COMPANIES:
        if c["ticker"] == ticker:
            return c["company"]
    return ticker

def get_cik(ticker: str) -> str:
    """Get CIK number by ticker."""
    return TICKER_CIK_MAP.get(ticker, "")
