"""
Article API Routes
==================

Endpoints for browsing, filtering, and searching articles.
Powers the Explore page.
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_articles(
    hours: int = Query(168, description="Time window in hours"),
    limit: int = Query(100, description="Max results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Text search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """
    Get articles with optional filters.
    Main endpoint for the Explore page.
    """
    storage = get_db()

    if search:
        articles = await storage.search_articles(search, hours=hours, limit=limit, domain=domain)
    elif category:
        articles = await storage.get_articles_by_category(category, hours=hours, limit=limit, domain=domain)
    elif priority:
        articles = await storage.get_articles_by_priority(priority, hours=hours, limit=limit, domain=domain)
    else:
        articles = await storage.get_recent_articles(hours=hours, limit=limit, domain=domain)

    # Apply additional filters on the result set
    results = []
    for a in articles:
        if source_type and a.source_type != source_type:
            continue
        results.append(_article_to_dict(a))

    return {"articles": results, "count": len(results)}


@router.get("/categories")
async def get_category_counts(
    hours: int = Query(168, description="Time window in hours"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """Get article counts by category for the filter sidebar."""
    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    counts = {}
    for a in articles:
        cat = a.primary_category
        counts[cat] = counts.get(cat, 0) + 1

    return {"categories": counts, "total": len(articles)}


@router.get("/priorities")
async def get_priority_counts(
    hours: int = Query(168, description="Time window in hours"),
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
):
    """Get article counts by priority level."""
    storage = get_db()
    articles = await storage.get_recent_articles(hours=hours, limit=5000, domain=domain)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in articles:
        p = a.priority
        if p in counts:
            counts[p] += 1

    return {"priorities": counts, "total": len(articles)}


@router.get("/{article_id}")
async def get_article_by_url(article_id: str):
    """Get a single article by URL (URL-encoded)."""
    from urllib.parse import unquote
    url = unquote(article_id)
    storage = get_db()
    article = await storage.get_article_by_url(url)
    if not article:
        return {"error": "Article not found"}, 404
    return _article_to_dict(article)


def _article_to_dict(article) -> dict:
    """Convert ClassifiedArticle to API response dict."""
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "source_name": article.source_name,
        "source_type": article.source_type,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "summary": article.ai_summary or article.summary,
        "key_takeaway": article.key_takeaway,
        "category": article.primary_category,
        "priority": article.priority,
        "relevance_score": article.relevance_score,
        "sentiment": article.sentiment,
        "companies_mentioned": article.companies_mentioned,
        "technologies_mentioned": article.technologies_mentioned,
        "people_mentioned": article.people_mentioned,
        "use_case_domains": article.use_case_domains,
        "confidence": article.confidence,
        "domain": article.domain,
    }
