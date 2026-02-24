"""
Stock API Routes
================

Endpoints for stock market data.
Powers the Markets page.
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from api.dependencies import get_db
from config.tickers import PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS, ALL_TICKERS

router = APIRouter()


@router.get("")
async def get_stock_overview():
    """
    Get latest stock data for all tracked tickers.
    Powers the Markets overview table.
    """
    storage = get_db()
    snapshots = await storage.get_latest_stock_data(ALL_TICKERS)

    # Build lookup for company info
    all_ticker_info = {t["ticker"]: t for t in PURE_PLAY_TICKERS + MAJOR_TECH_TICKERS + ETF_TICKERS}

    results = []
    for s in snapshots:
        info = all_ticker_info.get(s.ticker, {})
        results.append({
            "ticker": s.ticker,
            "company": info.get("company", s.ticker),
            "focus": info.get("focus", ""),
            "close": s.close,
            "change_percent": s.change_percent,
            "volume": s.volume,
            "sma_20": s.sma_20,
            "sma_50": s.sma_50,
            "market_cap": s.market_cap,
            "date": s.date,
        })

    # Sort by absolute change
    results.sort(key=lambda x: abs(x.get("change_percent") or 0), reverse=True)

    return {
        "stocks": results,
        "groups": {
            "pure_play": [t["ticker"] for t in PURE_PLAY_TICKERS],
            "major_tech": [t["ticker"] for t in MAJOR_TECH_TICKERS],
            "etf": [t["ticker"] for t in ETF_TICKERS],
        },
    }


@router.get("/tickers")
async def get_ticker_list():
    """Get all tracked tickers with company info."""
    all_info = PURE_PLAY_TICKERS + MAJOR_TECH_TICKERS + ETF_TICKERS
    return {
        "tickers": all_info,
        "groups": {
            "pure_play": PURE_PLAY_TICKERS,
            "major_tech": MAJOR_TECH_TICKERS,
            "etf": ETF_TICKERS,
        },
    }


@router.get("/{ticker}")
async def get_ticker_detail(
    ticker: str,
    days: int = Query(30, description="Days of history"),
):
    """
    Get detailed stock data for a single ticker.
    Powers the Markets company deep-dive view.
    """
    ticker = ticker.upper()
    storage = get_db()

    # Historical data
    snapshots = await storage.get_stock_data(ticker, days=days)

    # Company info
    all_ticker_info = {t["ticker"]: t for t in PURE_PLAY_TICKERS + MAJOR_TECH_TICKERS + ETF_TICKERS}
    info = all_ticker_info.get(ticker, {"ticker": ticker, "company": ticker, "focus": ""})

    # Related articles (mentioning this company)
    articles = await storage.search_articles(info.get("company", ticker), hours=168, limit=10)

    # Earnings quotes
    quotes = await storage.get_quotes_by_ticker(ticker, limit=20)

    # SEC nuggets
    nuggets = await storage.get_nuggets_by_ticker(ticker, limit=20)

    return {
        "ticker": ticker,
        "company": info.get("company", ticker),
        "focus": info.get("focus", ""),
        "history": [
            {
                "date": s.date,
                "open": s.open,
                "high": s.high,
                "low": s.low,
                "close": s.close,
                "volume": s.volume,
                "change_percent": s.change_percent,
                "sma_20": s.sma_20,
                "sma_50": s.sma_50,
            }
            for s in snapshots
        ],
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source_name": a.source_name,
                "summary": a.ai_summary or a.summary,
                "category": a.primary_category,
                "priority": a.priority,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in articles[:5]
        ],
        "quotes": [
            {
                "quote_id": q.quote_id,
                "quote_text": q.quote_text,
                "speaker_name": q.speaker_name,
                "speaker_role": q.speaker_role.value if hasattr(q.speaker_role, "value") else str(q.speaker_role),
                "quote_type": q.quote_type.value if hasattr(q.quote_type, "value") else str(q.quote_type),
                "confidence_level": q.confidence_level.value if hasattr(q.confidence_level, "value") else str(q.confidence_level),
                "sentiment": q.sentiment,
                "year": q.year,
                "quarter": q.quarter,
                "section": q.section.value if hasattr(q.section, "value") else str(q.section),
                "relevance_score": q.relevance_score,
            }
            for q in quotes
        ],
        "nuggets": [
            n.to_display_dict() for n in nuggets
        ],
    }
