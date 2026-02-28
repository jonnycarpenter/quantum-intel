"""
Deduplication Service
=====================

URL + fuzzy title matching for cross-source deduplication.
Prevents duplicate articles from RSS + Exa overlap.
"""

import hashlib
import re
from typing import List, Optional, Dict, Any, Set, Tuple

from models.article import RawArticle
from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_title(title: str) -> str:
    """Normalize a title for fuzzy matching."""
    # Lowercase, remove punctuation, collapse whitespace
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def title_similarity(title1: str, title2: str) -> float:
    """
    Simple word-overlap similarity between two titles.
    Returns 0.0-1.0.
    """
    words1 = set(normalize_title(title1).split())
    words2 = set(normalize_title(title2).split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


class DeduplicationService:
    """
    Deduplication service using URL matching + fuzzy title similarity.

    Caches known URLs and titles from storage to avoid re-ingesting
    articles across runs.
    """

    def __init__(self, storage=None, title_threshold: float = 0.85):
        """
        Args:
            storage: StorageBackend instance for loading known articles
            title_threshold: Minimum title similarity to consider duplicate (0-1)
        """
        self.storage = storage
        self.title_threshold = title_threshold

        # In-memory caches
        self._url_cache: Set[str] = set()
        self._title_cache: Dict[str, str] = {}  # normalized_title -> url
        self._hash_cache: Set[str] = set()

    @property
    def cache_stats(self) -> Dict[str, int]:
        return {
            "urls": len(self._url_cache),
            "titles": len(self._title_cache),
            "hashes": len(self._hash_cache),
        }

    async def initialize(self):
        """Initialize the service (placeholder for future setup)."""
        pass

    async def load_recent_cache(self, hours: int = 168):
        """
        Load recent articles from storage into dedup caches.

        Args:
            hours: Time window to load (default 7 days)
        """
        if not self.storage:
            return

        try:
            articles = await self.storage.get_recent_articles_for_dedup(hours=hours)
            for article in articles:
                url = article.get("url", "")
                title = article.get("title", "")
                content_hash = article.get("content_hash", "")

                if url:
                    self._url_cache.add(url)
                if title:
                    self._title_cache[normalize_title(title)] = url
                if content_hash:
                    self._hash_cache.add(content_hash)

            logger.info(
                f"[DEDUP] Cache loaded: {len(self._url_cache)} URLs, "
                f"{len(self._title_cache)} titles, {len(self._hash_cache)} hashes"
            )
        except Exception as e:
            logger.warning(f"[DEDUP] Failed to load cache: {e}")

    async def check_duplicate(
        self, article: RawArticle
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if an article is a duplicate.

        Args:
            article: RawArticle to check

        Returns:
            (is_duplicate, original_id_or_url, match_type)
            match_type is one of: "url", "title", "content", None
        """
        # 1. Exact URL match
        if article.url in self._url_cache:
            return True, article.url, "url"

        # 2. Content hash match
        if article.content_hash and article.content_hash in self._hash_cache:
            return True, None, "content"

        # 3. Fuzzy title match
        norm_title = normalize_title(article.title)
        if norm_title in self._title_cache:
            return True, self._title_cache[norm_title], "title"

        # Check similarity against cached titles
        for cached_title, cached_url in self._title_cache.items():
            sim = title_similarity(article.title, cached_title)
            if sim >= self.title_threshold:
                return True, cached_url, "title"

        return False, None, None

    def add_to_cache(
        self,
        article_id: str = "",
        url: str = "",
        title: str = "",
        content_hash: str = "",
    ):
        """Add an article to the dedup caches after saving."""
        if url:
            self._url_cache.add(url)
        if title:
            self._title_cache[normalize_title(title)] = url
        if content_hash:
            self._hash_cache.add(content_hash)


class ArticleAggregator:
    """
    Aggregates similar articles from the same ingestion batch.

    Groups articles about the same story from different sources,
    keeping the best source and tracking coverage count.
    """

    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold
        self._groups: List[List[Dict[str, Any]]] = []

    def add_article(self, article_data: Dict[str, Any]):
        """Add an article, grouping with similar ones."""
        title = article_data.get("title", "")

        # Try to find an existing group
        for group in self._groups:
            representative = group[0]
            rep_title = representative.get("title", "")
            if title_similarity(title, rep_title) >= self.threshold:
                group.append(article_data)
                return

        # New group
        self._groups.append([article_data])

    def get_aggregated_articles(self) -> List[Dict[str, Any]]:
        """
        Return one representative article per group with coverage metadata.
        """
        results = []
        for group in self._groups:
            # Pick the article with the most content as representative
            best = max(
                group,
                key=lambda a: len(a.get("summary", "") or a.get("full_text", "") or ""),
            )

            # Attach coverage metadata
            best["coverage_count"] = len(group)
            best["all_urls"] = [a.get("url", "") for a in group]
            best["duplicate_sources"] = [a.get("source_name", "") for a in group]

            results.append(best)

        return results
