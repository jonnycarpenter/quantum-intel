"""
Digest API Routes
=================

Endpoints for the weekly briefing / digest.
Powers the Briefing page.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_latest_digest():
    """
    Get the most recent AI-generated digest.
    Used by the Briefing page's executive summary section.
    """
    storage = get_db()
    digest = await storage.get_latest_digest()

    if not digest:
        return {"digest": None}

    items = []
    for item in digest.items:
        items.append({
            "id": item.id,
            "title": item.title,
            "source_name": item.source_name,
            "url": item.url,
            "summary": item.summary,
            "category": item.category,
            "priority": item.priority.value if hasattr(item.priority, "value") else str(item.priority),
            "relevance_score": item.relevance_score,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "companies_mentioned": item.companies_mentioned,
            "technologies_mentioned": item.technologies_mentioned,
        })

    return {
        "digest": {
            "id": digest.id,
            "created_at": digest.created_at.isoformat(),
            "period_hours": digest.period_hours,
            "executive_summary": digest.executive_summary,
            "items": items,
            "total_items": digest.total_items,
            "critical_count": digest.critical_count,
            "high_count": digest.high_count,
            "medium_count": digest.medium_count,
            "low_count": digest.low_count,
        }
    }


@router.get("/briefing")
async def get_briefing_data(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """
    Composite endpoint for the Briefing page.
    Returns digest + top stories + market snapshot + exec voices + regulatory signals + papers
    all in one request so the frontend can render the full briefing page.
    """
    storage = get_db()

    # Fetch all data sources in parallel-ish (they're all async)
    digest = await storage.get_latest_digest()
    articles = await storage.get_recent_articles(hours=168, limit=200, domain=domain)
    stocks = await storage.get_latest_stock_data()
    papers = await storage.get_recent_papers(days=7, limit=5)

    # Earnings quotes (top 5 by relevance)
    quotes = []
    try:
        from config.earnings_tickers import EARNINGS_TICKERS
        for ticker_info in EARNINGS_TICKERS[:5]:
            ticker_quotes = await storage.get_quotes_by_ticker(ticker_info["ticker"], limit=3)
            quotes.extend(ticker_quotes)
    except Exception:
        pass

    # SEC nuggets (top 5 new/high-signal)
    nuggets = []
    try:
        from config.earnings_tickers import EARNINGS_TICKERS
        for ticker_info in EARNINGS_TICKERS[:5]:
            ticker_nuggets = await storage.get_nuggets_by_ticker(ticker_info["ticker"], limit=3)
            nuggets.extend(ticker_nuggets)
    except Exception:
        pass

    # Top stories: critical + high priority, sorted by relevance
    top_stories = sorted(
        [a for a in articles if a.priority in ("critical", "high")],
        key=lambda a: a.relevance_score,
        reverse=True,
    )[:7]

    # Priority counts
    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in articles:
        if a.priority in priority_counts:
            priority_counts[a.priority] += 1

    # Market pulse: format stock data
    market_data = []
    for s in stocks:
        market_data.append({
            "ticker": s.ticker,
            "close": s.close,
            "change_percent": s.change_percent,
            "volume": s.volume,
            "date": s.date,
        })

    # Sort by absolute change for "top movers"
    market_data.sort(key=lambda s: abs(s.get("change_percent") or 0), reverse=True)

    # Exec voices: sort by relevance, take top 5
    exec_voices = sorted(quotes, key=lambda q: q.relevance_score, reverse=True)[:5]

    # Regulatory: sort new disclosures first, then by relevance
    regulatory = sorted(
        nuggets,
        key=lambda n: (n.is_new_disclosure, n.relevance_score),
        reverse=True,
    )[:5]

    return {
        "digest": {
            "executive_summary": digest.executive_summary if digest else None,
            "created_at": digest.created_at.isoformat() if digest else None,
        },
        "priority_counts": priority_counts,
        "top_stories": [
            {
                "id": a.id,
                "title": a.title,
                "source_name": a.source_name,
                "url": a.url,
                "summary": a.ai_summary or a.summary,
                "category": a.primary_category,
                "priority": a.priority,
                "relevance_score": a.relevance_score,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in top_stories
        ],
        "market_pulse": market_data[:10],
        "exec_voices": [
            {
                "quote_text": q.quote_text,
                "speaker_name": q.speaker_name,
                "speaker_role": q.speaker_role.value if hasattr(q.speaker_role, "value") else str(q.speaker_role),
                "ticker": q.ticker,
                "company_name": q.company_name,
                "year": q.year,
                "quarter": q.quarter,
                "quote_type": q.quote_type.value if hasattr(q.quote_type, "value") else str(q.quote_type),
                "confidence_level": q.confidence_level.value if hasattr(q.confidence_level, "value") else str(q.confidence_level),
                "relevance_score": q.relevance_score,
            }
            for q in exec_voices
        ],
        "regulatory": [
            {
                "nugget_text": n.nugget_text,
                "ticker": n.ticker,
                "company_name": n.company_name,
                "filing_type": n.filing_type.value if hasattr(n.filing_type, "value") else str(n.filing_type),
                "section": n.section.value if hasattr(n.section, "value") else str(n.section),
                "nugget_type": n.nugget_type.value if hasattr(n.nugget_type, "value") else str(n.nugget_type),
                "signal_strength": n.signal_strength.value if hasattr(n.signal_strength, "value") else str(n.signal_strength),
                "is_new_disclosure": n.is_new_disclosure,
                "relevance_score": n.relevance_score,
                "fiscal_year": n.fiscal_year,
            }
            for n in regulatory
        ],
        "papers": [
            {
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors[:3],
                "relevance_score": p.relevance_score,
                "paper_type": p.paper_type,
                "commercial_readiness": p.commercial_readiness,
                "significance_summary": p.significance_summary,
                "abs_url": p.abs_url,
            }
            for p in papers
        ],
    }


@router.get("/weekly-briefing")
async def get_weekly_briefing(
    domain: str = Query("quantum", description="Domain: quantum or ai"),
    week: Optional[str] = Query(None, description="Week date (YYYY-MM-DD), defaults to latest"),
):
    """
    Get a synthesized weekly intelligence briefing.

    Returns the full briefing with narrative sections, market movers,
    and research papers. Each section includes voice enrichment and citations.
    """
    if domain not in ("quantum", "ai"):
        raise HTTPException(status_code=400, detail="Domain must be 'quantum' or 'ai'")

    storage = get_db()

    if week:
        briefing = await storage.get_weekly_briefing_by_week(domain=domain, week_of=week)
    else:
        briefing = await storage.get_latest_weekly_briefing(domain=domain)

    if not briefing:
        return {"briefing": None}

    return {"briefing": briefing.to_dict()}
