"""
AI Earnings Ticker Config
==========================

Ticker-to-CIK mapping and configuration for the AI domain
Earnings Call + SEC Filing pipelines.
CIK numbers are required for SEC EDGAR lookups.
"""

from typing import Dict, List, Any


# =============================================================================
# Ticker → CIK Mapping (SEC Central Index Key)
# =============================================================================

AI_TICKER_CIK_MAP: Dict[str, str] = {
    # AI-Native Pure Plays
    "PLTR": "1321655",
    "AI": "1577526",
    "PATH": "1734722",
    "SOUN": "1840856",
    "BBAI": "1836981",
    "APP": "1751008",
    "CRWV": "1769628",
    "ARM": "1973239",
    # AI Infrastructure & Silicon
    "NVDA": "1045810",
    "AMD": "2488",
    "AVGO": "1730168",
    "MRVL": "1835632",
    "TSM": "1046179",
    "SMCI": "1375365",
    # Hyperscaler & Cloud AI
    "GOOGL": "1652044",
    "MSFT": "789019",
    "AMZN": "1018724",
    "META": "1326801",
    "SNOW": "1640147",
    "NOW": "1373715",
}


# =============================================================================
# Company Info
# =============================================================================

AI_EARNINGS_COMPANIES: List[Dict[str, Any]] = [
    # AI-Native Pure Plays — extract all AI-relevant content
    {"ticker": "PLTR", "company": "Palantir Technologies", "tier": "core", "cik": "1321655"},
    {"ticker": "AI", "company": "C3.ai", "tier": "core", "cik": "1577526"},
    {"ticker": "PATH", "company": "UiPath", "tier": "core", "cik": "1734722"},
    {"ticker": "SOUN", "company": "SoundHound AI", "tier": "core", "cik": "1840856"},
    {"ticker": "BBAI", "company": "BigBear.ai", "tier": "core", "cik": "1836981"},
    {"ticker": "APP", "company": "AppLovin", "tier": "core", "cik": "1751008"},
    {"ticker": "CRWV", "company": "CoreWeave", "tier": "core", "cik": "1769628"},
    {"ticker": "ARM", "company": "ARM Holdings", "tier": "core", "cik": "1973239"},
    # AI Infrastructure & Silicon — extract AI-specific sections
    {"ticker": "NVDA", "company": "NVIDIA", "tier": "secondary", "cik": "1045810"},
    {"ticker": "AMD", "company": "Advanced Micro Devices", "tier": "secondary", "cik": "2488"},
    {"ticker": "AVGO", "company": "Broadcom", "tier": "secondary", "cik": "1730168"},
    {"ticker": "MRVL", "company": "Marvell Technology", "tier": "secondary", "cik": "1835632"},
    {"ticker": "TSM", "company": "TSMC", "tier": "secondary", "cik": "1046179"},
    {"ticker": "SMCI", "company": "Super Micro Computer", "tier": "secondary", "cik": "1375365"},
    # Hyperscaler & Cloud AI — extract AI capex, AI revenue, model launches
    {"ticker": "GOOGL", "company": "Alphabet (Google)", "tier": "secondary", "cik": "1652044"},
    {"ticker": "MSFT", "company": "Microsoft", "tier": "secondary", "cik": "789019"},
    {"ticker": "AMZN", "company": "Amazon", "tier": "secondary", "cik": "1018724"},
    {"ticker": "META", "company": "Meta Platforms", "tier": "secondary", "cik": "1326801"},
    {"ticker": "SNOW", "company": "Snowflake", "tier": "secondary", "cik": "1640147"},
    {"ticker": "NOW", "company": "ServiceNow", "tier": "secondary", "cik": "1373715"},
]


# =============================================================================
# Convenience accessors
# =============================================================================

AI_CORE_TICKERS: List[str] = [c["ticker"] for c in AI_EARNINGS_COMPANIES if c["tier"] == "core"]
AI_SECONDARY_TICKERS: List[str] = [c["ticker"] for c in AI_EARNINGS_COMPANIES if c["tier"] == "secondary"]
AI_ALL_EARNINGS_TICKERS: List[str] = [c["ticker"] for c in AI_EARNINGS_COMPANIES]

def get_ai_company_name(ticker: str) -> str:
    """Get company name by ticker."""
    for c in AI_EARNINGS_COMPANIES:
        if c["ticker"] == ticker:
            return c["company"]
    return ticker

def get_ai_cik(ticker: str) -> str:
    """Get CIK number by ticker."""
    return AI_TICKER_CIK_MAP.get(ticker, "")
