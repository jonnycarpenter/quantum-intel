"""
Papers API Routes
=================

Endpoints for ArXiv papers.
Powers the Research page.
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_papers(
    days: int = Query(30, description="Days to look back"),
    limit: int = Query(100, description="Max results"),
    paper_type: Optional[str] = Query(None, description="Filter: breakthrough, incremental, review, theoretical"),
    readiness: Optional[str] = Query(None, description="Filter: near_term, mid_term, long_term, theoretical"),
    search: Optional[str] = Query(None, description="Keyword search in title/abstract"),
):
    """
    Get ArXiv papers with optional filters.
    Powers the Research page.
    """
    storage = get_db()
    papers = await storage.get_recent_papers(days=days, limit=limit)

    results = []
    for p in papers:
        # Apply filters
        if paper_type and p.paper_type != paper_type:
            continue
        if readiness and p.commercial_readiness != readiness:
            continue
        if search:
            search_lower = search.lower()
            if search_lower not in (p.title or "").lower() and search_lower not in (p.abstract or "").lower():
                continue

        results.append({
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "authors": p.authors,
            "abstract": p.abstract,
            "categories": p.categories,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "pdf_url": p.pdf_url,
            "abs_url": p.abs_url,
            "relevance_score": p.relevance_score,
            "paper_type": p.paper_type,
            "commercial_readiness": p.commercial_readiness,
            "significance_summary": p.significance_summary,
        })

    # Sort by relevance
    results.sort(key=lambda x: x.get("relevance_score") or 0, reverse=True)

    return {"papers": results, "count": len(results)}
