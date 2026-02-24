"""
Corpus Search Tool
==================

Searches the classified article corpus using both semantic similarity
(ChromaDB) and keyword matching (SQLite). Merges and deduplicates results.
"""

import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class CorpusSearchTool:
    """Search the quantum computing intelligence corpus."""

    def __init__(self):
        self._storage = None
        self._embeddings = None

    def _ensure_initialized(self) -> None:
        """Lazy-initialize storage and embeddings singletons."""
        if self._storage is None:
            from storage import get_storage
            self._storage = get_storage()
        if self._embeddings is None:
            try:
                from storage import get_embeddings_store
                self._embeddings = get_embeddings_store()
            except Exception as e:
                logger.warning(f"[TOOL] ChromaDB not available: {e}")
                self._embeddings = None

    async def execute(
        self,
        query: str,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        hours: int = 168,
        limit: int = 10,
        domain: Optional[str] = None,
    ) -> str:
        """
        Search the corpus and return results as JSON string.

        Args:
            query: Search query
            category: Optional category filter
            priority: Optional priority filter
            hours: Look back window in hours
            limit: Maximum results
            domain: Optional domain filter ("quantum" or "ai")

        Returns:
            JSON string with search results
        """
        self._ensure_initialized()
        logger.info(
            f"[TOOL] corpus_search: query='{query}' category={category} "
            f"priority={priority} domain={domain}"
        )

        seen_urls: set = set()
        merged: List[Dict[str, Any]] = []

        # 1. Semantic search via ChromaDB
        if self._embeddings is not None:
            try:
                filters: Optional[Dict[str, Any]] = None
                if category or priority:
                    filter_conditions = []
                    if category:
                        filter_conditions.append({"primary_category": category})
                    if priority:
                        filter_conditions.append({"priority": priority})
                    if len(filter_conditions) == 1:
                        filters = filter_conditions[0]
                    else:
                        filters = {"$and": filter_conditions}

                search_results = await self._embeddings.search(
                    query=query,
                    n_results=limit * 2,
                    filters=filters,
                )

                for r in search_results.results:
                    if r.url and r.url not in seen_urls:
                        seen_urls.add(r.url)
                        merged.append({
                            "title": r.title,
                            "url": r.url,
                            "source": r.metadata.get("source_name", ""),
                            "summary": r.summary[:300] if r.summary else "",
                            "category": r.metadata.get("primary_category", ""),
                            "priority": r.metadata.get("priority", ""),
                            "relevance_score": round(r.score, 3),
                            "published_at": r.metadata.get("published_at", ""),
                            "search_type": "semantic",
                        })
            except Exception as e:
                logger.warning(f"[TOOL] Semantic search error: {e}")

        # 2. SQL text search (domain-filtered)
        try:
            if category:
                sql_results = await self._storage.get_articles_by_category(
                    category=category, hours=hours, limit=limit * 2,
                    domain=domain,
                )
            elif priority:
                sql_results = await self._storage.get_articles_by_priority(
                    priority=priority, hours=hours, limit=limit * 2,
                    domain=domain,
                )
            else:
                sql_results = await self._storage.search_articles(
                    query=query, hours=hours, limit=limit * 2,
                    domain=domain,
                )

            for article in sql_results:
                url = article.url
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    published = (
                        article.published_at.strftime("%Y-%m-%d")
                        if article.published_at else None
                    )
                    merged.append({
                        "title": article.title,
                        "url": url,
                        "source": article.source_name,
                        "summary": (article.ai_summary or article.summary or "")[:300],
                        "category": article.primary_category,
                        "priority": article.priority,
                        "relevance_score": round(article.relevance_score, 3),
                        "published_at": published,
                        "companies": article.companies_mentioned[:5] if article.companies_mentioned else [],
                        "technologies": article.technologies_mentioned[:5] if article.technologies_mentioned else [],
                        "search_type": "sql",
                    })
        except Exception as e:
            logger.warning(f"[TOOL] SQL search error: {e}")

        # 3. Sort by relevance and limit
        merged.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        results = merged[:limit]

        if not results:
            return json.dumps({
                "results": [],
                "total_found": 0,
                "query": query,
                "message": "No articles found matching your query. The corpus may be empty — try running ingestion first.",
            })

        logger.info(f"[TOOL] corpus_search: found {len(results)} results")
        return json.dumps({
            "results": results,
            "total_found": len(results),
            "query": query,
        })
