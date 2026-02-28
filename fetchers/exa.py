"""
Exa Web Search Fetcher
=======================

Async Exa search client for quantum computing and AI use-case intelligence.
Replaces Tavily with better published_date reliability and ISO 8601 date filtering.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set

from exa_py import Exa

from config.settings import IngestionConfig
from config.exa_queries import EXA_QUERIES, get_queries_by_theme, THEMES
from models.article import RawArticle, SourceType
from utils.logger import get_logger

logger = get_logger(__name__)


class ExaFetcher:
    """
    Fetches articles via Exa web search.

    Features:
    - Pre-configured queries across strategic themes
    - Theme-based filtering for cost control
    - Cross-query URL deduplication
    - ISO 8601 date-range filtering
    - Rate limiting between queries
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        api_key = self.config.exa_api_key
        if not api_key:
            raise ValueError("EXA_API_KEY not set — cannot initialize ExaFetcher")
        self.client = Exa(api_key=api_key)
        self.max_article_age_days = self.config.max_article_age_days
        self.max_results_per_query = getattr(self.config, "exa_max_results_per_query", 10)
        self.max_characters = getattr(self.config, "exa_max_characters", 2000)

    async def fetch_all_queries(
        self,
        queries: Optional[List[Dict[str, Any]]] = None,
        themes: Optional[List[str]] = None,
    ) -> List[RawArticle]:
        """
        Run Exa search queries and return articles.

        Args:
            queries: Override query list (defaults to all from config)
            themes: Optional list of theme names to filter queries

        Returns:
            Deduplicated list of RawArticle objects
        """
        if queries is None:
            if themes:
                queries = []
                for theme in themes:
                    queries.extend(get_queries_by_theme(theme))
                logger.info(f"[FETCHER] Exa: running {len(queries)} queries (themes: {', '.join(themes)})")
            else:
                queries = EXA_QUERIES
                logger.info(f"[FETCHER] Exa: running all {len(queries)} queries")

        all_articles: List[RawArticle] = []
        seen_urls: Set[str] = set()
        success_count = 0
        error_count = 0

        for i, query_config in enumerate(queries, 1):
            try:
                articles = await self._fetch_query(query_config)
                for article in articles:
                    if article.url not in seen_urls:
                        seen_urls.add(article.url)
                        all_articles.append(article)
                success_count += 1

                logger.debug(
                    f"[FETCHER] Exa [{i}/{len(queries)}] "
                    f"'{query_config['query'][:40]}...' -> {len(articles)} results"
                )
            except Exception as e:
                error_count += 1
                logger.warning(
                    f"[FETCHER] Exa query error ({query_config.get('query', '?')[:40]}): {e}"
                )

            # Rate limiting between queries
            if i < len(queries):
                await asyncio.sleep(0.5)

        logger.info(
            f"[FETCHER] Exa total: {len(all_articles)} unique articles "
            f"from {success_count} queries ({error_count} errors, "
            f"{len(seen_urls) - len(all_articles)} cross-query dupes removed)"
        )
        return all_articles

    async def _fetch_query(self, query_config: Dict[str, Any]) -> List[RawArticle]:
        """
        Execute a single Exa search query.

        Args:
            query_config: Dict with query, theme, id keys

        Returns:
            List of RawArticle objects from this query
        """
        query_str = query_config["query"]

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.max_article_age_days)

        # Exa's search_and_contents() is synchronous, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.search_and_contents(
                query=query_str,
                type="auto",
                num_results=self.max_results_per_query,
                text={"max_characters": self.max_characters},
                start_published_date=start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                end_published_date=end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

        results = response.results if hasattr(response, "results") else []
        articles = []

        for result in results:
            article = self._parse_result(result, query_config)
            if article is not None:
                articles.append(article)

        return articles

    def _parse_result(
        self, result: Any, query_config: Dict[str, Any]
    ) -> Optional[RawArticle]:
        """
        Parse a single Exa search result into a RawArticle.

        Args:
            result: Exa result object with url, title, text, published_date attributes
            query_config: The query config that produced this result
        """
        url = getattr(result, "url", "")
        title = (getattr(result, "title", "") or "").strip()

        if not url or not title:
            return None

        # Parse published date — Exa returns ISO 8601
        published_at = None
        date_confidence = "fetched"
        raw_date = getattr(result, "published_date", None)
        if raw_date:
            try:
                # Exa uses ISO 8601: "2025-02-15T01:36:32.547Z"
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                date_confidence = "exact"
            except (ValueError, AttributeError):
                pass

        if published_at is None:
            published_at = datetime.now(timezone.utc)

        # Extract content/snippet
        content = getattr(result, "text", "") or ""

        # Content hash for dedup
        content_for_hash = f"{title}|{content[:200]}"
        content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()

        return RawArticle(
            url=url,
            title=title,
            source_name="Exa Search",
            source_url=url,
            published_at=published_at,
            summary=content[:2000],
            date_confidence=date_confidence,
            content_hash=content_hash,
            metadata={
                "source_type": SourceType.EXA.value,
                "theme": query_config.get("theme", ""),
                "query_id": query_config.get("id", 0),
                "query_text": query_config.get("query", ""),
            },
        )
