"""
Ingestion Pipeline Orchestrator
===============================

Coordinates the full ingestion pipeline:
1. Fetch articles (RSS, Exa, ArXiv, StockNews)
2. Filter blocked sources
3. Deduplicate (URL + title similarity)
4. Classify (Claude)
5. Persist (SQLite)
6. Index embeddings (ChromaDB)

Usage:
    from orchestrator import IngestionOrchestrator

    orchestrator = IngestionOrchestrator()
    await orchestrator.initialize()
    stats = await orchestrator.run(sources=["rss"])
"""

import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from config.settings import IngestionConfig, BLOCKED_SOURCES, BLOCKED_DOMAINS
from config.rss_sources import RSS_FEEDS
from config.exa_queries import EXA_QUERIES
from config.ai_rss_sources import AI_RSS_FEEDS
from config.arxiv_queries import ARXIV_QUERIES, ARXIV_GENERAL_QUERY
from config.ai_arxiv_queries import AI_ARXIV_QUERIES, AI_ARXIV_GENERAL_QUERY
from config.tickers import ALL_TICKERS
from config.settings import StockNewsConfig
from fetchers.rss import RSSFetcher
from fetchers.exa import ExaFetcher
from fetchers.arxiv import ArXivFetcher
from fetchers.stocks import StockFetcher
from fetchers.stocknews import StockNewsFetcher
from processing.classifier import ContentClassifier
from processing.deduplication import DeduplicationService, ArticleAggregator
from models.article import RawArticle, ClassificationResult, SourceType
from storage import get_storage, get_embeddings_store
from storage.base import ClassifiedArticle
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IngestionStats:
    """Statistics from an ingestion run."""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # Fetch stats
    rss_fetched: int = 0
    exa_fetched: int = 0
    arxiv_fetched: int = 0
    stocks_fetched: int = 0
    stocknews_fetched: int = 0
    papers_saved: int = 0
    total_fetched: int = 0

    # Blocklist stats
    blocked_by_source: int = 0
    blocked_by_domain: int = 0
    total_blocked: int = 0

    # Dedup stats
    duplicates_url: int = 0
    duplicates_title: int = 0
    duplicates_content: int = 0
    after_dedup: int = 0

    # Classification stats
    classified: int = 0
    critical_priority: int = 0
    high_priority: int = 0
    medium_priority: int = 0
    low_priority: int = 0
    avg_relevance: float = 0.0

    # Storage stats
    saved: int = 0
    embedded: int = 0
    save_errors: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "rss_fetched": self.rss_fetched,
            "exa_fetched": self.exa_fetched,
            "arxiv_fetched": self.arxiv_fetched,
            "stocks_fetched": self.stocks_fetched,
            "stocknews_fetched": self.stocknews_fetched,
            "papers_saved": self.papers_saved,
            "total_fetched": self.total_fetched,
            "total_blocked": self.total_blocked,
            "duplicates_url": self.duplicates_url,
            "duplicates_title": self.duplicates_title,
            "after_dedup": self.after_dedup,
            "classified": self.classified,
            "critical_priority": self.critical_priority,
            "high_priority": self.high_priority,
            "medium_priority": self.medium_priority,
            "low_priority": self.low_priority,
            "avg_relevance": round(self.avg_relevance, 3),
            "saved": self.saved,
            "embedded": self.embedded,
            "save_errors": self.save_errors,
        }


class IngestionOrchestrator:
    """
    Main orchestrator for the Intelligence Hub ingestion pipeline.

    Coordinates:
    - RSS feed fetching (Phase 1)
    - Exa search (Phase 2)
    - ArXiv paper fetching (Phase 2)
    - Deduplication
    - Claude classification
    - SQLite/BigQuery persistence
    - ChromaDB embedding indexing

    Supports both quantum and AI domains via the domain parameter.
    """

    def __init__(self, config: Optional[IngestionConfig] = None, domain: str = "quantum"):
        self.config = config or IngestionConfig()
        self.domain = domain

        # Components (initialized in initialize())
        self.rss_fetcher: Optional[RSSFetcher] = None
        self.exa_fetcher: Optional[ExaFetcher] = None
        self.arxiv_fetcher: Optional[ArXivFetcher] = None
        self.stock_fetcher: Optional[StockFetcher] = None
        self.stocknews_fetcher: Optional[StockNewsFetcher] = None
        self.classifier: Optional[ContentClassifier] = None
        self.dedup_service: Optional[DeduplicationService] = None
        self.storage = None
        self.embeddings_store = None

        self._exa_themes: Optional[List[str]] = None
        self._initialized = False

    async def initialize(self):
        """Initialize all pipeline components."""
        if self._initialized:
            return

        logger.info("[ORCHESTRATOR] Initializing pipeline components...")

        # Storage
        self.storage = get_storage()
        logger.info(f"[ORCHESTRATOR] Storage: {type(self.storage).__name__}")

        # Dedup
        self.dedup_service = DeduplicationService(storage=self.storage)
        await self.dedup_service.initialize()
        await self.dedup_service.load_recent_cache(hours=168)
        logger.info(f"[ORCHESTRATOR] Dedup cache: {self.dedup_service.cache_stats}")

        # Select domain-specific feeds and queries
        if self.domain == "ai":
            self._rss_feeds = AI_RSS_FEEDS
        else:
            self._rss_feeds = RSS_FEEDS

        # RSS
        self.rss_fetcher = RSSFetcher(self.config)
        logger.info(f"[ORCHESTRATOR] [{self.domain.upper()}] RSS feeds: {len(self._rss_feeds)}")

        # Exa (conditional on API key)
        if self.config.exa_api_key:
            try:
                self.exa_fetcher = ExaFetcher(self.config)
                exa_queries = self._get_exa_queries()
                logger.info(f"[ORCHESTRATOR] [{self.domain.upper()}] Exa: {len(exa_queries)} queries configured")
            except ValueError as e:
                logger.warning(f"[ORCHESTRATOR] Exa disabled: {e}")
        else:
            logger.info("[ORCHESTRATOR] Exa: disabled (no API key)")

        # ArXiv (domain-aware)
        if self.domain == "ai":
            arxiv_queries = AI_ARXIV_QUERIES
            arxiv_general = AI_ARXIV_GENERAL_QUERY
        else:
            arxiv_queries = ARXIV_QUERIES
            arxiv_general = ARXIV_GENERAL_QUERY
        self.arxiv_fetcher = ArXivFetcher(
            self.config, queries=arxiv_queries, general_query=arxiv_general
        )
        logger.info(
            f"[ORCHESTRATOR] [{self.domain.upper()}] ArXiv: {len(arxiv_queries)} queries configured"
        )

        # Stocks
        self.stock_fetcher = StockFetcher(self.config)
        logger.info(f"[ORCHESTRATOR] Stocks: {len(ALL_TICKERS)} tickers configured")

        # StockNews (conditional on API key)
        stocknews_config = StockNewsConfig()
        if stocknews_config.api_key:
            self.stocknews_fetcher = StockNewsFetcher(stocknews_config)
            logger.info("[ORCHESTRATOR] StockNews: enabled")
        else:
            logger.info("[ORCHESTRATOR] StockNews: disabled (no STOCKNEWS_API_KEY)")

        # Classifier (domain-aware)
        self.classifier = ContentClassifier(self.config, domain=self.domain)
        logger.info(f"[ORCHESTRATOR] [{self.domain.upper()}] Classifier: {self.config.classifier_model}")

        # Embeddings
        try:
            self.embeddings_store = get_embeddings_store()
            logger.info("[ORCHESTRATOR] Embeddings store: loaded")
        except ImportError as e:
            logger.warning(f"[ORCHESTRATOR] Embeddings disabled (missing deps): {e}")
            self.embeddings_store = None

        self._initialized = True
        logger.info("[ORCHESTRATOR] Initialization complete")

    async def run(
        self,
        sources: Optional[List[str]] = None,
        max_classify: Optional[int] = None,
        save_results: bool = True,
        exa_themes: Optional[List[str]] = None,
    ) -> IngestionStats:
        """
        Run the ingestion pipeline.

        Args:
            sources: List of sources to run ("rss", "exa", "arxiv", "stocks", "stocknews").
                    If None, runs all enabled sources.
            max_classify: Limit classification count (for testing/cost control)
            save_results: Whether to persist to storage

        Returns:
            IngestionStats with run metrics
        """
        if not self._initialized:
            await self.initialize()

        stats = IngestionStats()
        self._exa_themes = exa_themes
        run_sources = set(s.lower() for s in sources) if sources else {"rss"}
        logger.info(f"[ORCHESTRATOR] [{self.domain.upper()}] Starting ingestion (sources: {', '.join(sorted(run_sources))})")

        # =====================================================================
        # Step 1: Fetch articles
        # =====================================================================
        all_articles: List[RawArticle] = []

        if "rss" in run_sources:
            rss_articles = await self.rss_fetcher.fetch_all_feeds(self._rss_feeds)
            stats.rss_fetched = len(rss_articles)
            all_articles.extend(rss_articles)

        if "exa" in run_sources and self.exa_fetcher:
            try:
                # For AI domain, pass AI-specific queries directly
                if self.domain == "ai":
                    ai_queries = self._get_exa_queries()
                    if self._exa_themes:
                        from config.exa_ai_queries import get_ai_queries_by_theme
                        ai_queries = []
                        for theme in self._exa_themes:
                            ai_queries.extend(get_ai_queries_by_theme(theme))
                    exa_articles = await self.exa_fetcher.fetch_all_queries(
                        queries=ai_queries,
                    )
                else:
                    exa_articles = await self.exa_fetcher.fetch_all_queries(
                        themes=self._exa_themes,
                    )
                stats.exa_fetched = len(exa_articles)
                all_articles.extend(exa_articles)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Exa fetch error: {e}")

        if "arxiv" in run_sources and self.arxiv_fetcher:
            try:
                arxiv_articles, arxiv_papers = await self.arxiv_fetcher.fetch_all_queries()
                stats.arxiv_fetched = len(arxiv_articles)
                all_articles.extend(arxiv_articles)

                # Save papers to papers table (separate from article pipeline)
                if save_results and arxiv_papers:
                    try:
                        paper_count = await self.storage.save_papers(arxiv_papers)
                        stats.papers_saved = paper_count
                        logger.info(f"[ORCHESTRATOR] Saved {paper_count} papers to papers table")
                    except Exception as e:
                        logger.warning(f"[ORCHESTRATOR] Paper save error (non-fatal): {e}")
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] ArXiv fetch error: {e}")

        if "stocknews" in run_sources and self.stocknews_fetcher:
            try:
                sn_articles = self.stocknews_fetcher.fetch_news()
                stats.stocknews_fetched = len(sn_articles)
                all_articles.extend(sn_articles)
                logger.info(f"[ORCHESTRATOR] StockNews: {len(sn_articles)} articles")
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] StockNews fetch error: {e}")

        stats.total_fetched = len(all_articles)
        logger.info(f"[ORCHESTRATOR] Fetched {stats.total_fetched} articles")

        # Inject domain into all fetched articles
        for article in all_articles:
            article.metadata["domain"] = self.domain

        # Article pipeline (steps 2-5) — skip if no articles fetched
        has_articles = bool(all_articles)

        if not has_articles and "stocks" not in run_sources:
            logger.warning("[ORCHESTRATOR] No articles fetched — aborting")
            stats.completed_at = datetime.now(timezone.utc)
            return stats

        if has_articles:
            # =====================================================================
            # Step 2: Filter blocked sources
            # =====================================================================
            stage_start = time.time()
            filtered = self._filter_blocked(all_articles, stats)
            if stats.total_blocked > 0:
                logger.info(
                    f"[ORCHESTRATOR] Filtered: {stats.total_blocked} blocked "
                    f"(source: {stats.blocked_by_source}, domain: {stats.blocked_by_domain}) "
                    f"| {time.time() - stage_start:.1f}s"
                )

            # =====================================================================
            # Step 3: Deduplicate
            # =====================================================================
            if filtered:
                stage_start = time.time()
                unique_articles = await self._deduplicate(filtered, stats)
                stats.after_dedup = len(unique_articles)
                logger.info(
                    f"[ORCHESTRATOR] Dedup: {len(filtered)} -> {stats.after_dedup} unique "
                    f"(URL: {stats.duplicates_url}, title: {stats.duplicates_title}) "
                    f"| {time.time() - stage_start:.1f}s"
                )
            else:
                unique_articles = []

            # =================================================================
            # Step 4: Classify
            # =================================================================
            if unique_articles:
                stage_start = time.time()
                articles_to_classify = unique_articles
                if max_classify and len(articles_to_classify) > max_classify:
                    articles_to_classify = articles_to_classify[:max_classify]
                    logger.info(f"[ORCHESTRATOR] Limiting classification to {max_classify} articles")

                classified = await self._classify(articles_to_classify, stats)
                logger.info(
                    f"[ORCHESTRATOR] Classified: {stats.classified} articles "
                    f"(critical: {stats.critical_priority}, high: {stats.high_priority}, "
                    f"med: {stats.medium_priority}, low: {stats.low_priority}) "
                    f"| avg relevance: {stats.avg_relevance:.2f} "
                    f"| {time.time() - stage_start:.1f}s"
                )

                # =============================================================
                # Step 5: Persist
                # =============================================================
                if save_results and classified:
                    stage_start = time.time()
                    saved_articles = await self._persist(classified, stats)
                    logger.info(
                        f"[ORCHESTRATOR] Saved: {stats.saved} articles, "
                        f"{stats.save_errors} errors | {time.time() - stage_start:.1f}s"
                    )

                    # Index embeddings
                    if self.embeddings_store and saved_articles:
                        try:
                            indexed = await self.embeddings_store.index_articles(saved_articles)
                            stats.embedded = indexed
                            logger.info(f"[ORCHESTRATOR] Embedded: {indexed} articles")
                        except Exception as e:
                            logger.warning(f"[ORCHESTRATOR] Embedding error (non-fatal): {e}")
            else:
                logger.info("[ORCHESTRATOR] No unique articles to classify")

        # =====================================================================
        # Step 6: Stock data (separate pipeline, no classification)
        # =====================================================================
        if "stocks" in run_sources and self.stock_fetcher:
            stage_start = time.time()
            try:
                stock_days = getattr(self.config, "stock_fetch_days", 60)
                stock_snapshots = await self.stock_fetcher.fetch_all(days_back=stock_days)
                if save_results and stock_snapshots:
                    stock_count = await self.storage.save_stock_data(stock_snapshots)
                    stats.stocks_fetched = stock_count
                    logger.info(
                        f"[ORCHESTRATOR] Stocks: {stock_count} snapshots saved "
                        f"| {time.time() - stage_start:.1f}s"
                    )
                else:
                    stats.stocks_fetched = len(stock_snapshots)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Stock fetch error: {e}")

        stats.completed_at = datetime.now(timezone.utc)
        logger.info(f"[ORCHESTRATOR] Run complete in {stats.duration_seconds:.1f}s")
        return stats

    def _filter_blocked(
        self, articles: List[RawArticle], stats: IngestionStats
    ) -> List[RawArticle]:
        """Filter out articles from blocked sources/domains."""
        if not BLOCKED_SOURCES and not BLOCKED_DOMAINS:
            return articles

        blocked_sources_lower = [s.lower() for s in BLOCKED_SOURCES]
        blocked_domains_lower = [d.lower() for d in BLOCKED_DOMAINS]

        filtered = []
        for article in articles:
            source_name = (article.source_name or "").lower()
            if source_name and any(b in source_name for b in blocked_sources_lower):
                stats.blocked_by_source += 1
                stats.total_blocked += 1
                continue

            url = (article.url or "").lower()
            if url and any(d in url for d in blocked_domains_lower):
                stats.blocked_by_domain += 1
                stats.total_blocked += 1
                continue

            filtered.append(article)

        return filtered

    async def _deduplicate(
        self, articles: List[RawArticle], stats: IngestionStats
    ) -> List[RawArticle]:
        """Deduplicate articles using URL + title similarity."""
        new_articles = []

        for article in articles:
            is_dup, _, match_type = await self.dedup_service.check_duplicate(article)
            if is_dup:
                if match_type == "url":
                    stats.duplicates_url += 1
                elif match_type == "title":
                    stats.duplicates_title += 1
                elif match_type == "content":
                    stats.duplicates_content += 1
            else:
                new_articles.append(article)

        # Aggregate similar new articles
        if len(new_articles) > 1:
            aggregator = ArticleAggregator()
            article_map = {}
            for article in new_articles:
                key = id(article)
                aggregator.add_article({
                    "url": article.url,
                    "title": article.title,
                    "source_name": article.source_name,
                    "summary": article.summary,
                    "_key": key,
                })
                article_map[key] = article

            aggregated = aggregator.get_aggregated_articles()
            result = []
            for agg in aggregated:
                key = agg.get("_key")
                if key and key in article_map:
                    article = article_map[key]
                    article.metadata["coverage_count"] = agg.get("coverage_count", 1)
                    article.metadata["duplicate_urls"] = agg.get("all_urls", [])
                    result.append(article)

            return result

        return new_articles

    async def _classify(
        self,
        articles: List[RawArticle],
        stats: IngestionStats,
    ) -> List[tuple]:
        """Classify articles with Claude."""
        results = []
        relevance_sum = 0.0

        for i, article in enumerate(articles, 1):
            try:
                result = await self.classifier.classify(article)
                if result is None:
                    continue

                results.append((article, result))
                stats.classified += 1
                relevance_sum += result.relevance_score

                priority_val = (
                    result.priority.value
                    if hasattr(result.priority, "value")
                    else str(result.priority)
                )
                if priority_val == "critical":
                    stats.critical_priority += 1
                elif priority_val == "high":
                    stats.high_priority += 1
                elif priority_val == "medium":
                    stats.medium_priority += 1
                else:
                    stats.low_priority += 1

                logger.debug(
                    f"[ORCHESTRATOR] [{i}/{len(articles)}] {article.title[:50]}... "
                    f"-> {result.primary_category} | {priority_val} | {result.relevance_score:.2f}"
                )

            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Classification error: {e}")

        if stats.classified > 0:
            stats.avg_relevance = relevance_sum / stats.classified

        return results

    async def _persist(
        self,
        classified: List[tuple],
        stats: IngestionStats,
    ) -> List[ClassifiedArticle]:
        """Persist classified articles to storage."""
        articles_to_save = []

        for raw, classification in classified:
            try:
                classified_article = ClassifiedArticle.from_raw_and_classification(
                    raw, classification
                )
                articles_to_save.append(classified_article)
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Error building article: {e}")
                stats.save_errors += 1

        if articles_to_save:
            try:
                saved = await self.storage.save_articles(articles_to_save)
                stats.saved = saved

                # Update dedup cache
                for article in articles_to_save:
                    self.dedup_service.add_to_cache(
                        article_id=article.id,
                        url=article.url,
                        title=article.title,
                        content_hash=article.content_hash or "",
                    )
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Storage error: {e}")
                stats.save_errors += len(articles_to_save)

        return articles_to_save

    def _get_exa_queries(self) -> list:
        """Get domain-appropriate Exa queries."""
        if self.domain == "ai":
            try:
                from config.exa_ai_queries import AI_EXA_QUERIES
                return AI_EXA_QUERIES
            except ImportError:
                logger.warning("[ORCHESTRATOR] AI Exa queries not yet configured")
                return []
        return EXA_QUERIES

    async def get_recent_articles(
        self, hours: int = 24, priority: Optional[str] = None, limit: int = 100
    ) -> List[ClassifiedArticle]:
        """Retrieve recent articles from storage."""
        if not self._initialized:
            await self.initialize()

        if priority:
            return await self.storage.get_articles_by_priority(priority, hours=hours, limit=limit)
        return await self.storage.get_recent_articles(hours=hours, limit=limit)

    async def close(self):
        """Close all connections."""
        if self.storage:
            await self.storage.close()
