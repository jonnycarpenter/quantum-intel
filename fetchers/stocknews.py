"""
StockNews Fetcher
==================

Fetches company stock news from StockNews API.
Articles flow into the existing article classification pipeline.

API Docs: https://stocknewsapi.com/documentation
"""

import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx

from models.article import RawArticle
from config.settings import StockNewsConfig
from config.earnings_tickers import ALL_EARNINGS_TICKERS
from utils.logger import get_logger

logger = get_logger(__name__)


class StockNewsFetcher:
    """Fetches stock news articles from StockNews API."""

    def __init__(self, config: Optional[StockNewsConfig] = None):
        self.config = config or StockNewsConfig()
        self.base_url = self.config.base_url
        self.api_key = self.config.api_key
        self._last_request_time = 0.0

        if not self.api_key:
            logger.warning("[STOCKNEWS] No STOCKNEWS_API_KEY set — fetcher will not work")

    def _rate_limit(self):
        """Enforce rate limit between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_seconds:
            time.sleep(self.config.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    def fetch_news(
        self,
        tickers: Optional[List[str]] = None,
        items: Optional[int] = None,
    ) -> List[RawArticle]:
        """
        Fetch stock news articles for given tickers.

        Args:
            tickers: Stock tickers (defaults to ALL_EARNINGS_TICKERS)
            items: Number of items to request (defaults to config max)

        Returns:
            List of RawArticle objects ready for classification pipeline
        """
        tickers = tickers or ALL_EARNINGS_TICKERS
        items = items or self.config.max_items_per_request
        all_articles: List[RawArticle] = []

        # StockNews API accepts comma-separated tickers
        ticker_str = ",".join(tickers)
        logger.info(f"[STOCKNEWS] Fetching news for {len(tickers)} tickers")

        self._rate_limit()
        try:
            response = httpx.get(
                self.base_url,
                params={
                    "tickers": ticker_str,
                    "items": items,
                    "token": self.api_key,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[STOCKNEWS] API error: {e.response.status_code} - "
                f"{e.response.text[:200]}"
            )
            return []
        except httpx.RequestError as e:
            logger.error(f"[STOCKNEWS] Network error: {e}")
            return []

        # Parse response into RawArticle objects
        articles_data = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(articles_data, list):
            logger.warning(f"[STOCKNEWS] Unexpected response format: {type(articles_data)}")
            return []

        for item in articles_data:
            if not isinstance(item, dict):
                continue

            # Map StockNews fields to RawArticle
            url = item.get("news_url", item.get("url", ""))
            title = item.get("title", "")

            if not url or not title:
                continue

            # Parse date
            published_at = None
            date_str = item.get("date", item.get("published_at", ""))
            if date_str:
                try:
                    published_at = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    try:
                        # Try common formats
                        for fmt in ["%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S"]:
                            try:
                                published_at = datetime.strptime(date_str, fmt).replace(
                                    tzinfo=timezone.utc
                                )
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

            article = RawArticle(
                url=url,
                title=title,
                source_name=item.get("source_name", "StockNews"),
                source_url=item.get("source_url", ""),
                published_at=published_at,
                summary=item.get("text", item.get("description", "")),
                full_text=item.get("text", ""),
                author=item.get("author", ""),
                tags=item.get("tickers", []),
            )
            all_articles.append(article)

        logger.info(f"[STOCKNEWS] Fetched {len(all_articles)} articles")
        return all_articles
