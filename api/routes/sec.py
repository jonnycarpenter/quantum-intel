"""
SEC Filing API Routes
=====================

Endpoints for SEC filing nuggets.
Powers the Filings page (SEC tab).
"""

from typing import Optional
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_all_nuggets(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    nugget_type: Optional[str] = Query(None, description="Filter by nugget type"),
    signal_strength: Optional[str] = Query(None, description="Filter by signal strength"),
    new_only: bool = Query(False, description="Only new disclosures"),
    limit: int = Query(50, description="Max results"),
):
    """
    Get SEC filing nuggets across all tickers (or filtered).
    Powers the Filings page SEC tab.
    """
    storage = get_db()

    if ticker:
        nuggets = await storage.get_nuggets_by_ticker(ticker.upper(), limit=limit)
    else:
        # Get nuggets for all tracked tickers
        try:
            from config.earnings_tickers import EARNINGS_COMPANIES
            tickers = [t["ticker"] for t in EARNINGS_COMPANIES]
        except ImportError:
            tickers = []

        nuggets = []
        for t in tickers:
            ticker_nuggets = await storage.get_nuggets_by_ticker(t, limit=10)
            nuggets.extend(ticker_nuggets)

    # Apply filters
    results = []
    for n in nuggets:
        nt = n.nugget_type.value if hasattr(n.nugget_type, "value") else str(n.nugget_type)
        ss = n.signal_strength.value if hasattr(n.signal_strength, "value") else str(n.signal_strength)

        if nugget_type and nt != nugget_type:
            continue
        if signal_strength and ss != signal_strength:
            continue
        if new_only and not n.is_new_disclosure:
            continue

        results.append(n.to_display_dict())

    # Sort: new disclosures first, then by relevance
    results.sort(
        key=lambda x: (x.get("is_new_disclosure", False), x.get("relevance_score", 0)),
        reverse=True,
    )

    return {"nuggets": results, "count": len(results)}


@router.get("/filing-types")
async def get_filing_type_options():
    """Get available filing type filter options."""
    return {
        "filing_types": ["10-K", "10-Q", "8-K"],
        "nugget_types": [
            "competitive_disclosure",
            "risk_admission",
            "technology_investment",
            "ip_patent",
            "regulatory_compliance",
            "forward_guidance",
            "material_change",
            "quantum_readiness",
        ],
        "signal_strengths": ["explicit", "standard", "hedged", "buried", "new"],
    }
