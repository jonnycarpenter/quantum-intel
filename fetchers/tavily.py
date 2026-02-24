"""
Tavily Web Search Fetcher
=========================

Async Tavily search client for quantum computing use-case intelligence.
Runs the 52 queries from config/tavily_queries.py across 9 strategic themes.
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

from tavily import TavilyClient

from config.settings import IngestionConfig
from config.tavily_queries import TAVILY_QUERIES, get_queries_by_theme, THEMES
from models.article import RawArticle, SourceType
from utils.logger import get_logger

logger = get_logger(__name__)


class TavilyFetcher:
    """
    Fetches articles via Tavily web search.

    Features:
    - 52 pre-configured queries across 9 strategic themes
    - Theme-based filtering for cost control
    - Cross-query URL deduplication
    - Rate limiting between queries
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        api_key = self.config.tavily_api_key
        if not api_key:
            raise ValueError("TAVILY_API_KEY not set — cannot initialize TavilyFetcher")
        self.client = TavilyClient(api_key=api_key)
        self.max_article_age_days = self.config.max_article_age_days
        self.search_depth = getattr(self.config, "tavily_search_depth", "advanced")
        self.max_results_per_query = getattr(self.config, "tavily_max_results_per_query", 10)

    async def fetch_all_queries(
        self,
        queries: Optional[List[Dict[str, Any]]] = None,
        themes: Optional[List[str]] = None,
    ) -> List[RawArticle]:
        """
        Run Tavily search queries and return articles.

        Args:
            queries: Override query list (defaults to all 52 from config)
            themes: Optional list of theme names to filter queries

        Returns:
            Deduplicated list of RawArticle objects
        """
        if queries is None:
            if themes:
                queries = []
                for theme in themes:
                    queries.extend(get_queries_by_theme(theme))
                logger.info(f"[FETCHER] Tavily: running {len(queries)} queries (themes: {', '.join(themes)})")
            else:
                queries = TAVILY_QUERIES
                logger.info(f"[FETCHER] Tavily: running all {len(queries)} queries")

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
                    f"[FETCHER] Tavily [{i}/{len(queries)}] "
                    f"'{query_config['query'][:40]}...' -> {len(articles)} results"
                )
            except Exception as e:
                error_count += 1
                logger.warning(
                    f"[FETCHER] Tavily query error ({query_config.get('query', '?')[:40]}): {e}"
                )

            # Rate limiting between queries
            if i < len(queries):
                await asyncio.sleep(0.5)

        logger.info(
            f"[FETCHER] Tavily total: {len(all_articles)} unique articles "
            f"from {success_count} queries ({error_count} errors, "
            f"{len(seen_urls) - len(all_articles)} cross-query dupes removed)"
        )
        return all_articles

    async def _fetch_query(self, query_config: Dict[str, Any]) -> List[RawArticle]:
        """
        Execute a single Tavily search query.

        Args:
            query_config: Dict with query, theme, id keys

        Returns:
            List of RawArticle objects from this query
        """
        query_str = query_config["query"]

        # TavilyClient.search() is synchronous, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.search(
                query=query_str,
                max_results=self.max_results_per_query,
                search_depth=self.search_depth,
                include_answer=False,
            ),
        )

        results = response.get("results", [])
        articles = []

        for result in results:
            article = self._parse_result(result, query_config)
            if article is not None:
                articles.append(article)

        return articles

    def _parse_result(
        self, result: Dict[str, Any], query_config: Dict[str, Any]
    ) -> Optional[RawArticle]:
        """
        Parse a single Tavily search result into a RawArticle.

        Args:
            result: Tavily result dict with url, title, content, published_date, score
            query_config: The query config that produced this result
        """
        url = result.get("url", "")
        title = result.get("title", "").strip()

        if not url or not title:
            return None

        # Parse published date
        published_at = None
        date_confidence = "fetched"
        raw_date = result.get("published_date")
        if raw_date:
            try:
                # Tavily returns dates in various formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d",
                    "%a, %d %b %Y %H:%M:%S %z",
                ]:
                    try:
                        published_at = datetime.strptime(raw_date, fmt)
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                        date_confidence = "exact"
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        if published_at is None:
            published_at = datetime.now(timezone.utc)

        # Extract content/snippet
        content = result.get("content", "")

        # Content hash for dedup
        content_for_hash = f"{title}|{content[:200]}"
        content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()

        return RawArticle(
            url=url,
            title=title,
            source_name="Tavily Search",
            source_url=url,
            published_at=published_at,
            summary=content[:2000],
            date_confidence=date_confidence,
            content_hash=content_hash,
            metadata={
                "source_type": SourceType.TAVILY.value,
                "theme": query_config.get("theme", ""),
                "query_id": query_config.get("id", 0),
                "query_text": query_config.get("query", ""),
                "tavily_score": result.get("score", 0.0),
            },
        )
