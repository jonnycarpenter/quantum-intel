"""
ArXiv Search Tool
=================

Searches the stored ArXiv papers corpus by keyword matching on
title and abstract. Returns paper metadata including relevance
scores and commercial readiness assessments.
"""

import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ArXivSearchTool:
    """Search ArXiv papers in the quantum computing corpus."""

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
        days: int = 30,
        limit: int = 10,
    ) -> str:
        """
        Search ArXiv papers and return results as JSON string.

        Args:
            query: Search query
            days: Look back window in days
            limit: Maximum number of results

        Returns:
            JSON string with paper results
        """
        self._ensure_initialized()
        logger.info(f"[TOOL] arxiv_search: query='{query}' days={days}")

        try:
            papers = await self._storage.get_recent_papers(days=days, limit=200)
        except Exception as e:
            logger.error(f"[TOOL] arxiv_search error: {e}")
            return json.dumps({
                "results": [],
                "total_found": 0,
                "query": query,
                "error": f"Failed to search papers: {e}",
            })

        if not papers:
            return json.dumps({
                "results": [],
                "total_found": 0,
                "query": query,
                "message": (
                    "No ArXiv papers found in the corpus. "
                    "Run ingestion with --sources arxiv first."
                ),
            })

        # Keyword filter on title + abstract
        query_terms = query.lower().split()
        matched = []
        for paper in papers:
            searchable = f"{paper.title} {paper.abstract}".lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                matched.append((score, paper))

        # Sort by match score, then by relevance_score
        matched.sort(
            key=lambda x: (x[0], x[1].relevance_score or 0),
            reverse=True,
        )

        results: List[Dict[str, Any]] = []
        for _, paper in matched[:limit]:
            published = (
                paper.published_at.strftime("%Y-%m-%d")
                if paper.published_at else None
            )
            results.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors[:5] if paper.authors else [],
                "abstract": (paper.abstract[:400] + "...") if len(paper.abstract) > 400 else paper.abstract,
                "categories": paper.categories,
                "published_at": published,
                "relevance_score": paper.relevance_score,
                "paper_type": paper.paper_type,
                "commercial_readiness": paper.commercial_readiness,
                "significance_summary": paper.significance_summary,
                "pdf_url": paper.pdf_url,
                "abs_url": paper.abs_url,
            })

        logger.info(f"[TOOL] arxiv_search: found {len(results)} papers matching '{query}'")
        return json.dumps({
            "results": results,
            "total_found": len(results),
            "query": query,
        })
