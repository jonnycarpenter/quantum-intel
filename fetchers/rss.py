"""
RSS Feed Fetcher
================

Async RSS feed fetcher for quantum computing news sources.
Supports tiered feeds with keyword filtering and date extraction.
"""

import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime

import feedparser

from models.article import RawArticle, SourceType
from utils.logger import get_logger

logger = get_logger(__name__)


class RSSFetcher:
    """
    Fetches articles from RSS feeds.

    Features:
    - Async feed fetching with concurrency control
    - Keyword filtering for Tier 4 (broad tech) feeds
    - Date extraction with confidence scoring
    - Content hashing for dedup support
    """

    def __init__(self, config=None):
        self.config = config
        self.max_article_age_days = 7 if config is None else config.max_article_age_days
        self.max_articles_per_feed = 20 if config is None else config.max_articles_per_feed

    async def fetch_all_feeds(self, feeds: List[Dict[str, Any]]) -> List[RawArticle]:
        """
        Fetch articles from all configured RSS feeds.

        Args:
            feeds: List of feed config dicts from config/rss_sources.py

        Returns:
            List of RawArticle objects
        """
        all_articles = []

        for feed in feeds:
            try:
                articles = await self.fetch_feed(feed)
                all_articles.extend(articles)
            except Exception as e:
                logger.warning(
                    f"[FETCHER] RSS error ({feed.get('name', 'unknown')}): {e}"
                )

        logger.info(f"[FETCHER] RSS total: {len(all_articles)} articles from {len(feeds)} feeds")
        return all_articles

    async def fetch_feed(
        self,
        feed_config: Dict[str, Any],
        days_back: Optional[int] = None,
    ) -> List[RawArticle]:
        """
        Fetch articles from a single RSS feed.

        Args:
            feed_config: Feed configuration dict
            days_back: Override max article age

        Returns:
            List of RawArticle objects
        """
        name = feed_config.get("name", "Unknown")
        url = feed_config.get("url", "")
        filter_keywords = feed_config.get("filter_keywords", [])
        max_age = days_back or self.max_article_age_days

        if not url:
            return []

        # Parse feed (feedparser is synchronous, run in thread)
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, feedparser.parse, url)

        if parsed.bozo and not parsed.entries:
            logger.warning(f"[FETCHER] RSS parse error for {name}: {parsed.bozo_exception}")
            return []

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age)

        for entry in parsed.entries[:self.max_articles_per_feed]:
            try:
                article = self._parse_entry(entry, feed_config, cutoff)
                if article is None:
                    continue

                # Apply keyword filter for Tier 4 feeds
                if filter_keywords and not self._matches_keywords(article, filter_keywords):
                    continue

                articles.append(article)

            except Exception as e:
                logger.debug(f"[FETCHER] Entry parse error in {name}: {e}")

        logger.info(f"[FETCHER] {name}: {len(articles)} articles")
        return articles

    def _parse_entry(
        self,
        entry: Any,
        feed_config: Dict[str, Any],
        cutoff: datetime,
    ) -> Optional[RawArticle]:
        """Parse a single RSS entry into a RawArticle."""
        # Extract URL
        url = entry.get("link", "")
        if not url:
            return None

        # Extract title
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Extract published date
        published_at, date_confidence = self._extract_date(entry)
        if published_at and published_at < cutoff:
            return None

        # Extract summary
        summary = ""
        if entry.get("summary"):
            summary = self._clean_html(entry.summary)
        elif entry.get("description"):
            summary = self._clean_html(entry.description)

        # Extract author
        author = entry.get("author")

        # Extract tags
        tags = []
        if entry.get("tags"):
            tags = [t.get("term", "") for t in entry.tags if t.get("term")]

        # Content hash for dedup
        content_for_hash = f"{title}|{summary[:200]}"
        content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()

        return RawArticle(
            url=url,
            title=title,
            source_name=feed_config.get("name", "Unknown RSS"),
            source_url=feed_config.get("url", ""),
            published_at=published_at or datetime.now(timezone.utc),
            summary=summary[:2000],
            author=author,
            tags=tags,
            date_confidence=date_confidence,
            content_hash=content_hash,
            metadata={
                "source_type": SourceType.RSS.value,
                "feed_tier": feed_config.get("tier", 0),
                "feed_category": feed_config.get("category", ""),
                "priority_boost": feed_config.get("priority_boost", 0.0),
            },
        )

    def _extract_date(self, entry: Any) -> tuple[Optional[datetime], str]:
        """
        Extract publication date from RSS entry.

        Returns:
            (datetime, confidence) tuple
        """
        # Try structured date fields
        for date_field in ["published_parsed", "updated_parsed"]:
            parsed_time = entry.get(date_field)
            if parsed_time:
                try:
                    dt = datetime(*parsed_time[:6], tzinfo=timezone.utc)
                    return dt, "exact"
                except (TypeError, ValueError):
                    pass

        # Try string date fields
        for date_str_field in ["published", "updated"]:
            date_str = entry.get(date_str_field)
            if date_str:
                try:
                    dt = parsedate_to_datetime(date_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt, "exact"
                except (TypeError, ValueError):
                    pass

        # Fallback to current time
        return None, "fetched"

    def _matches_keywords(self, article: RawArticle, keywords: List[str]) -> bool:
        """Check if article matches any filter keywords (case-insensitive)."""
        text = f"{article.title} {article.summary}".lower()
        return any(kw.lower() in text for kw in keywords)

    def _clean_html(self, text: str) -> str:
        """Basic HTML tag removal."""
        import re
        clean = re.sub(r"<[^>]+>", "", text)
        clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        clean = clean.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        return clean.strip()
