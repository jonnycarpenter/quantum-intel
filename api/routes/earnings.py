"""
Earnings API Routes
===================

Endpoints for earnings call quotes.
Powers the Filings page (Earnings tab).
"""

from typing import Optional
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_all_quotes(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    quote_type: Optional[str] = Query(None, description="Filter by quote type"),
    confidence: Optional[str] = Query(None, description="Filter by confidence level"),
    limit: int = Query(50, description="Max results"),
):
    """
    Get earnings call quotes across all tickers (or filtered by ticker).
    Powers the Filings page Earnings tab.
    """
    storage = get_db()

    if ticker:
        quotes = await storage.get_quotes_by_ticker(ticker.upper(), limit=limit)
    else:
        # Get quotes for all tracked tickers
        try:
            from config.earnings_tickers import EARNINGS_COMPANIES
            tickers = [t["ticker"] for t in EARNINGS_COMPANIES]
        except ImportError:
            tickers = []

        quotes = []
        for t in tickers:
            ticker_quotes = await storage.get_quotes_by_ticker(t, limit=10)
            quotes.extend(ticker_quotes)

    # Apply filters
    results = []
    for q in quotes:
        qt = q.quote_type.value if hasattr(q.quote_type, "value") else str(q.quote_type)
        cl = q.confidence_level.value if hasattr(q.confidence_level, "value") else str(q.confidence_level)

        if quote_type and qt != quote_type:
            continue
        if confidence and cl != confidence:
            continue

        results.append({
            "quote_id": q.quote_id,
            "quote_text": q.quote_text,
            "speaker_name": q.speaker_name,
            "speaker_role": q.speaker_role.value if hasattr(q.speaker_role, "value") else str(q.speaker_role),
            "speaker_title": q.speaker_title,
            "ticker": q.ticker,
            "company_name": q.company_name,
            "year": q.year,
            "quarter": q.quarter,
            "quote_type": qt,
            "confidence_level": cl,
            "sentiment": q.sentiment,
            "section": q.section.value if hasattr(q.section, "value") else str(q.section),
            "themes": q.themes,
            "relevance_score": q.relevance_score,
            "is_quotable": q.is_quotable,
            "companies_mentioned": q.companies_mentioned,
            "technologies_mentioned": q.technologies_mentioned,
            "competitors_mentioned": q.competitors_mentioned,
        })

    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return {"quotes": results, "count": len(results)}


@router.get("/tickers")
async def get_earnings_tickers():
    """Get all tickers with earnings data."""
    try:
        from config.earnings_tickers import ALL_EARNINGS_TICKERS
        return {"tickers": ALL_EARNINGS_TICKERS}
    except ImportError:
        return {"tickers": []}
