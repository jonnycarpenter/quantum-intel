"""
Web Search Tool
===============

Real-time web search for quantum computing information using Exa.
Includes quantum-domain filtering with broad search fallback.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)

# Prioritized domains for quantum computing news
QUANTUM_DOMAINS = [
    "thequantuminsider.com",
    "quantumcomputingreport.com",
    "insidequantumtechnology.com",
    "quantumzeitgeist.com",
    "nature.com",
    "sciencedaily.com",
    "techcrunch.com",
    "arstechnica.com",
    "reuters.com",
    "bloomberg.com",
    "sifted.eu",
]


class WebSearchTool:
    """Real-time web search via Exa API."""

    def __init__(self):
        self._client = None

    def _ensure_client(self) -> None:
        """Lazy-initialize Exa client."""
        if self._client is None:
            api_key = os.getenv("EXA_API_KEY", "")
            if not api_key:
                raise ValueError("EXA_API_KEY not set")
            from exa_py import Exa
            self._client = Exa(api_key=api_key)

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        days: Optional[int] = 7,
    ) -> str:
        """
        Search the web and return results as JSON string.

        Args:
            query: Search query
            max_results: Maximum number of results
            days: Limit to last N days

        Returns:
            JSON string with search results
        """
        logger.info(f"[TOOL] web_search: query='{query}' max_results={max_results}")

        try:
            self._ensure_client()
        except ValueError as e:
            return json.dumps({
                "results": [],
                "total_found": 0,
                "query": query,
                "error": str(e),
            })

        try:
            results = await self._search(
                query=query,
                max_results=max_results,
                days=days,
            )

            if not results:
                return json.dumps({
                    "results": [],
                    "total_found": 0,
                    "query": query,
                    "message": "No web results found for this query.",
                })

            logger.info(f"[TOOL] web_search: found {len(results)} results")
            return json.dumps({
                "results": results,
                "total_found": len(results),
                "query": query,
            })

        except Exception as e:
            logger.error(f"[TOOL] web_search error: {e}")
            return json.dumps({
                "results": [],
                "total_found": 0,
                "query": query,
                "error": f"Web search failed: {type(e).__name__}",
            })

    async def _search(
        self,
        query: str,
        max_results: int,
        days: Optional[int],
    ) -> List[dict]:
        """Execute search with domain filtering and fallback."""
        import asyncio

        search_kwargs = {
            "query": query,
            "num_results": max_results,
            "type": "auto",
            "text": {"max_characters": 500},
        }
        if days:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            search_kwargs["start_published_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            search_kwargs["end_published_date"] = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # First try with quantum domain filtering
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.search_and_contents(
                    include_domains=QUANTUM_DOMAINS,
                    **search_kwargs,
                ),
            )
            results = self._parse_results(response)
            if len(results) >= 2:
                return results
        except Exception:
            pass

        # Fallback: broad search without domain filter
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.search_and_contents(**search_kwargs),
        )
        return self._parse_results(response)

    def _parse_results(self, response) -> List[dict]:
        """Parse Exa response into result dicts."""
        results = []
        for item in (response.results if hasattr(response, "results") else []):
            url = getattr(item, "url", "")
            results.append({
                "title": getattr(item, "title", "") or "",
                "url": url,
                "content": ((getattr(item, "text", "") or "")[:500]),
                "published_date": getattr(item, "published_date", "") or "",
                "source": url.split("/")[2] if url and "/" in url else "",
            })
        return results
