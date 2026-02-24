"""
Podcast Search Tool
===================

Searches podcast transcripts and extracted quotes for quantum computing
intelligence. Queries both quote-level data and full transcript text.
"""

import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class PodcastSearchTool:
    """Search podcast quotes and transcripts."""

    def __init__(self):
        self._storage = None

    def _ensure_initialized(self) -> None:
        """Lazy-initialize storage singleton."""
        if self._storage is None:
            from storage import get_storage
            self._storage = get_storage()

    async def execute(
        self,
        query: str,
        podcast_id: Optional[str] = None,
        limit: int = 15,
    ) -> str:
        """
        Search podcast quotes and transcripts.

        Args:
            query: Search query (searches quote text, speakers, themes,
                   companies, technologies)
            podcast_id: Optional podcast ID filter
            limit: Maximum results

        Returns:
            JSON string with search results
        """
        self._ensure_initialized()
        logger.info(
            f"[TOOL] podcast_search: query='{query}' "
            f"podcast_id={podcast_id} limit={limit}"
        )

        results: List[Dict[str, Any]] = []

        try:
            # Search quotes
            quotes = await self._storage.search_podcast_quotes(
                query=query, limit=limit
            )

            # If podcast_id filter, also get quotes for that podcast
            if podcast_id and not quotes:
                quotes = await self._storage.get_podcast_quotes(
                    podcast_id=podcast_id, limit=limit
                )

            for q in quotes:
                data = q.to_dict()
                results.append({
                    "type": "podcast_quote",
                    "quote_text": data.get("quote_text", ""),
                    "speaker_name": data.get("speaker_name", ""),
                    "speaker_role": data.get("speaker_role", ""),
                    "speaker_title": data.get("speaker_title", ""),
                    "speaker_company": data.get("speaker_company", ""),
                    "quote_type": data.get("quote_type", ""),
                    "themes": data.get("themes", ""),
                    "sentiment": data.get("sentiment", ""),
                    "relevance_score": data.get("relevance_score", 0.0),
                    "podcast_name": data.get("podcast_name", ""),
                    "episode_title": data.get("episode_title", ""),
                    "published_at": data.get("published_at", ""),
                    "companies_mentioned": data.get("companies_mentioned", ""),
                    "technologies_mentioned": data.get("technologies_mentioned", ""),
                    "is_quotable": data.get("is_quotable", False),
                })

        except Exception as e:
            logger.error(f"[TOOL] podcast_search error: {e}")
            return json.dumps({
                "status": "error",
                "message": str(e),
                "query": query,
                "results": [],
            })

        return json.dumps({
            "status": "ok",
            "query": query,
            "podcast_id": podcast_id,
            "count": len(results),
            "results": results,
        })
