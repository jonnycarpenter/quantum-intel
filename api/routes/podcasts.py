"""
Podcast API Routes
==================

Endpoints for podcast quotes.
Powers the Explore page Voice Quotes tab.
"""

from typing import Optional
from fastapi import APIRouter, Query

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_podcast_quotes(
    domain: Optional[str] = Query(None, description="Filter by domain: quantum or ai"),
    quote_type: Optional[str] = Query(None, description="Filter by quote type"),
    speaker: Optional[str] = Query(None, description="Filter by speaker name"),
    podcast: Optional[str] = Query(None, description="Filter by podcast_id"),
    search: Optional[str] = Query(None, description="Text search query"),
    limit: int = Query(50, description="Max results"),
):
    """
    Get podcast quotes with optional filters.
    Powers the Explore page Voice Quotes tab.
    """
    storage = get_db()

    if search:
        quotes = await storage.search_podcast_quotes(search, limit=limit)
    elif podcast:
        quotes = await storage.get_podcast_quotes(podcast_id=podcast, limit=limit)
    else:
        quotes = await storage.get_podcast_quotes(limit=limit)

    # Apply client-side filters (domain, quote_type, speaker)
    results = []
    for q in quotes:
        if quote_type and q.quote_type != quote_type:
            continue
        if speaker and speaker.lower() not in q.speaker_name.lower():
            continue
        # Domain filtering: check podcast_id prefix or themes for domain relevance
        # Podcast quotes don't have a domain field directly, so we skip domain filter
        # unless we add domain awareness to the storage query in the future.
        results.append(_quote_to_dict(q))

    return {"quotes": results, "count": len(results)}


def _quote_to_dict(q) -> dict:
    """Convert PodcastQuote to API response dict."""
    return {
        "quote_id": q.quote_id,
        "transcript_id": q.transcript_id,
        "episode_id": q.episode_id,
        "quote_text": q.quote_text,
        "context_before": q.context_before,
        "context_after": q.context_after,
        "speaker_name": q.speaker_name,
        "speaker_role": q.speaker_role,
        "speaker_title": q.speaker_title,
        "speaker_company": q.speaker_company,
        "quote_type": q.quote_type,
        "themes": q.themes,
        "sentiment": q.sentiment,
        "companies_mentioned": q.companies_mentioned,
        "technologies_mentioned": q.technologies_mentioned,
        "people_mentioned": q.people_mentioned,
        "relevance_score": q.relevance_score,
        "is_quotable": q.is_quotable,
        "quotability_reason": q.quotability_reason,
        "podcast_id": q.podcast_id,
        "podcast_name": q.podcast_name,
        "episode_title": q.episode_title,
        "published_at": q.published_at,
        "extracted_at": q.extracted_at.isoformat() if hasattr(q.extracted_at, 'isoformat') else str(q.extracted_at),
        "extraction_confidence": q.extraction_confidence,
    }
