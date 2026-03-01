import json
import logging
import asyncio
from typing import Optional

from fetchers.exa import ExaFetcher

logger = logging.getLogger(__name__)


class FindSimilarTool:
    """Find similar articles using Exa's neural network capability."""

    def __init__(self):
        self._fetcher: Optional[ExaFetcher] = None
        self._lock = asyncio.Lock()

    async def _ensure_fetcher(self) -> None:
        """Lazy-initialize ExaFetcher."""
        if self._fetcher is None:
            async with self._lock:
                if self._fetcher is None:
                    # The fetcher automatically grabs the API key from config/env
                    self._fetcher = ExaFetcher()

    async def execute(
        self,
        url: str,
        num_results: int = 5,
        exclude_source_domain: bool = True,
    ) -> str:
        """
        Execute the find similar search.

        Args:
            url: Target URL to find lookalikes for
            num_results: Max results to return
            exclude_source_domain: Filter out original URL's domain

        Returns:
            JSON string containing similar article highlights
        """
        logger.info(f"[TOOL] find_similar: url='{url}' max_results={num_results}")

        try:
            await self._ensure_fetcher()
        except ValueError as e:
            return json.dumps({
                "results": [],
                "target_url": url,
                "error": str(e),
            })

        try:
            # We already attached _fetcher above
            articles = await self._fetcher.find_similar(
                url=url,
                num_results=num_results,
                exclude_source_domain=exclude_source_domain,
            )

            if not articles:
                return json.dumps({
                    "results": [],
                    "target_url": url,
                    "message": "No lookalike URLs found or Exa could not crawl the target URL context.",
                })

            results = []
            for a in articles:
                results.append({
                    "title": a.title,
                    "url": a.url,
                    "content": a.summary,
                    "published_date": a.published_at.strftime('%Y-%m-%d') if a.published_at else "",
                    "source": a.source_name,
                })

            logger.info(f"[TOOL] find_similar: returning {len(results)} matches")
            return json.dumps({
                "results": results,
                "target_url": url,
                "total_found": len(results),
            })

        except Exception as e:
            logger.error(f"[TOOL] find_similar error for {url}: {e}")
            return json.dumps({
                "results": [],
                "target_url": url,
                "error": f"Search failed: {type(e).__name__}",
            })
