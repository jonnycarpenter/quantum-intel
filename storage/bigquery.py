"""
BigQuery Storage Backend
========================

GCP production storage using BigQuery.
Implements the StorageBackend ABC for articles, digests, papers, stocks,
earnings, SEC filings, podcasts, and weekly briefings.

Uses MERGE statements for upserts (BigQuery has no INSERT OR IGNORE).
Synchronous BigQuery client wrapped in run_in_executor for async interface.
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Set, Any

from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from .base import StorageBackend, ClassifiedArticle
from .bigquery_schemas import get_all_create_ddl
from models.article import Digest, DigestItem, Priority
from models.paper import Paper
from models.stock import StockSnapshot
from models.earnings import EarningsTranscript, ExtractedQuote
from models.sec_filing import SecFiling, SecNugget
from models.podcast import PodcastTranscript, PodcastQuote
from models.weekly_briefing import WeeklyBriefing, BriefingSection, MarketMover, ResearchPaper
from models.case_study import CaseStudy
from utils.logger import get_logger

logger = get_logger(__name__)


class BigQueryStorage(StorageBackend):
    """BigQuery storage backend for GCP production."""

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "quantum_ai_hub",
        location: str = "us-central1",
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.full_dataset = f"{project_id}.{dataset_id}"
        self.client = bigquery.Client(project=project_id)
        self._initialize_dataset()

    def _initialize_dataset(self) -> None:
        """Create dataset and tables if they don't exist."""
        dataset_ref = bigquery.Dataset(f"{self.project_id}.{self.dataset_id}")
        dataset_ref.location = self.location
        try:
            self.client.get_dataset(dataset_ref)
            logger.info(f"[STORAGE] BigQuery dataset exists: {self.dataset_id}")
        except NotFound:
            self.client.create_dataset(dataset_ref)
            logger.info(f"[STORAGE] Created BigQuery dataset: {self.dataset_id}")

        for ddl in get_all_create_ddl(self.full_dataset):
            self.client.query(ddl).result()

        logger.info(f"[STORAGE] BigQuery initialized: {self.full_dataset}")

    def _table(self, name: str) -> str:
        """Return fully-qualified table name."""
        return f"`{self.full_dataset}.{name}`"

    def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in the default executor."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # =========================================================================
    # Helpers
    # =========================================================================

    def _ensure_list(self, val: Any) -> list:
        """Ensure value is a list."""
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, list) else [val]
            except (json.JSONDecodeError, TypeError):
                return [val] if val else []
        return []

    def _dt_to_iso(self, dt: Any) -> Optional[str]:
        """Convert datetime to ISO string or return None."""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
        return None

    def _parse_dt(self, val: Any) -> Optional[datetime]:
        """Parse a value to datetime."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None

    def _row_to_article(self, row: dict) -> ClassifiedArticle:
        """Convert a BigQuery row dict to ClassifiedArticle."""
        data = dict(row)
        # ARRAY fields come back as lists natively from BigQuery
        for list_field in [
            "tags", "companies_mentioned", "technologies_mentioned",
            "people_mentioned", "use_case_domains", "duplicate_urls",
        ]:
            data[list_field] = self._ensure_list(data.get(list_field))

        # JSON metadata
        meta = data.get("metadata")
        if meta is None:
            data["metadata"] = {}
        elif isinstance(meta, str):
            try:
                data["metadata"] = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                data["metadata"] = {}

        # Booleans
        data["feed_eligible"] = bool(data.get("feed_eligible", True))

        # Datetimes — BigQuery returns native datetime objects
        for dt_field in ["published_at", "fetched_at", "classified_at"]:
            val = data.get(dt_field)
            if val and isinstance(val, str):
                try:
                    data[dt_field] = datetime.fromisoformat(val)
                except ValueError:
                    data[dt_field] = None

        return ClassifiedArticle.from_dict(data)

    def _cutoff_timestamp(self, hours: int) -> str:
        """Return ISO timestamp N hours ago."""
        return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    def _cutoff_days(self, days: int) -> str:
        """Return date string N days ago."""
        return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # =========================================================================
    # Article Operations
    # =========================================================================

    async def save_articles(self, articles: List[ClassifiedArticle]) -> int:
        """Save classified articles using MERGE for upsert on url."""
        if not articles:
            return 0

        saved = 0
        # Process in batches of 100 for BigQuery efficiency
        batch_size = 100
        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]
            rows = []
            for article in batch:
                rows.append({
                    "id": article.id,
                    "url": article.url,
                    "title": article.title,
                    "source_name": article.source_name,
                    "source_url": article.source_url,
                    "source_type": article.source_type,
                    "published_at": self._dt_to_iso(article.published_at),
                    "date_confidence": article.date_confidence,
                    "fetched_at": self._dt_to_iso(article.fetched_at),
                    "summary": article.summary,
                    "full_text": article.full_text,
                    "author": article.author,
                    "tags": self._ensure_list(article.tags),
                    "primary_category": article.primary_category,
                    "priority": article.priority,
                    "relevance_score": article.relevance_score,
                    "ai_summary": article.ai_summary,
                    "key_takeaway": article.key_takeaway,
                    "companies_mentioned": self._ensure_list(article.companies_mentioned),
                    "technologies_mentioned": self._ensure_list(article.technologies_mentioned),
                    "people_mentioned": self._ensure_list(article.people_mentioned),
                    "use_case_domains": self._ensure_list(article.use_case_domains),
                    "sentiment": article.sentiment,
                    "confidence": article.confidence,
                    "classifier_model": article.classifier_model,
                    "classified_at": self._dt_to_iso(article.classified_at),
                    "digest_priority": article.digest_priority,
                    "feed_eligible": bool(article.feed_eligible),
                    "content_hash": article.content_hash,
                    "coverage_count": article.coverage_count,
                    "duplicate_urls": self._ensure_list(article.duplicate_urls),
                    "metadata": json.dumps(article.metadata or {}),
                    "domain": article.domain,
                })

            count = await self._insert_if_not_exists("articles", rows, ["url"])
            saved += count

        return saved

    async def _insert_if_not_exists(
        self, table_name: str, rows: list[dict], dedup_keys: list[str],
    ) -> int:
        """Insert rows that don't already exist (checked by dedup_keys)."""
        if not rows:
            return 0

        saved = 0
        for row in rows:
            try:
                # Check existence
                where_parts = []
                params = []
                query_params = []
                for i, key in enumerate(dedup_keys):
                    val = row[key]
                    param_name = f"key_{i}"
                    if val is None:
                        where_parts.append(f"{key} IS NULL")
                    else:
                        where_parts.append(f"{key} = @{param_name}")
                        query_params.append(
                            bigquery.ScalarQueryParameter(param_name, "STRING", str(val))
                        )

                where_clause = " AND ".join(where_parts)
                check_query = f"SELECT 1 FROM {self._table(table_name)} WHERE {where_clause} LIMIT 1"

                job_config = bigquery.QueryJobConfig(query_parameters=query_params)
                result = await self._run_sync(
                    lambda q=check_query, c=job_config: list(self.client.query(q, job_config=c).result())
                )

                if result:
                    continue  # Already exists

                # Insert the row
                table_ref = f"{self.full_dataset}.{table_name}"
                errors = await self._run_sync(
                    lambda r=row, t=table_ref: self.client.insert_rows_json(t, [r])
                )
                if not errors:
                    saved += 1
                else:
                    logger.warning(f"[STORAGE] BQ insert error ({table_name}): {errors}")
            except Exception as e:
                logger.warning(f"[STORAGE] BQ save error ({table_name}): {e}")

        return saved

    async def _upsert_row(
        self, table_name: str, row: dict, dedup_keys: list[str],
    ) -> bool:
        """Insert or replace a single row. Returns True if successful."""
        try:
            # Delete existing if any
            where_parts = []
            query_params = []
            for i, key in enumerate(dedup_keys):
                val = row[key]
                param_name = f"key_{i}"
                if val is None:
                    where_parts.append(f"{key} IS NULL")
                else:
                    where_parts.append(f"{key} = @{param_name}")
                    query_params.append(
                        bigquery.ScalarQueryParameter(param_name, "STRING", str(val))
                    )

            where_clause = " AND ".join(where_parts)
            delete_query = f"DELETE FROM {self._table(table_name)} WHERE {where_clause}"
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            await self._run_sync(
                lambda q=delete_query, c=job_config: self.client.query(q, job_config=c).result()
            )

            # Insert new row
            table_ref = f"{self.full_dataset}.{table_name}"
            errors = await self._run_sync(
                lambda r=row, t=table_ref: self.client.insert_rows_json(t, [r])
            )
            if errors:
                logger.warning(f"[STORAGE] BQ upsert error ({table_name}): {errors}")
                return False
            return True
        except Exception as e:
            logger.warning(f"[STORAGE] BQ upsert error ({table_name}): {e}")
            return False

    async def get_article_by_url(self, url: str) -> Optional[ClassifiedArticle]:
        """Get a single article by URL."""
        query = f"SELECT * FROM {self._table('articles')} WHERE url = @url LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("url", "STRING", url)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return self._row_to_article(dict(rows[0])) if rows else None

    async def get_recent_articles(
        self, hours: int = 72, limit: int = 500, domain: Optional[str] = None,
    ) -> List[ClassifiedArticle]:
        """Get articles from the last N hours, newest first."""
        cutoff = self._cutoff_timestamp(hours)
        params = [bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff)]

        if domain:
            query = (
                f"SELECT * FROM {self._table('articles')} "
                f"WHERE fetched_at >= TIMESTAMP(@cutoff) AND domain = @domain "
                f"ORDER BY published_at DESC LIMIT @lim"
            )
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        else:
            query = (
                f"SELECT * FROM {self._table('articles')} "
                f"WHERE fetched_at >= TIMESTAMP(@cutoff) "
                f"ORDER BY published_at DESC LIMIT @lim"
            )
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [self._row_to_article(dict(r)) for r in rows]

    async def get_articles_by_category(
        self, category: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None,
    ) -> List[ClassifiedArticle]:
        cutoff = self._cutoff_timestamp(hours)
        params = [
            bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
            bigquery.ScalarQueryParameter("category", "STRING", category),
        ]
        where = "fetched_at >= TIMESTAMP(@cutoff) AND primary_category = @category"
        if domain:
            where += " AND domain = @domain"
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))

        query = (
            f"SELECT * FROM {self._table('articles')} "
            f"WHERE {where} ORDER BY published_at DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [self._row_to_article(dict(r)) for r in rows]

    async def get_articles_by_priority(
        self, priority: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None,
    ) -> List[ClassifiedArticle]:
        cutoff = self._cutoff_timestamp(hours)
        params = [
            bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
            bigquery.ScalarQueryParameter("priority", "STRING", priority),
        ]
        where = "fetched_at >= TIMESTAMP(@cutoff) AND priority = @priority"
        if domain:
            where += " AND domain = @domain"
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))

        query = (
            f"SELECT * FROM {self._table('articles')} "
            f"WHERE {where} ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [self._row_to_article(dict(r)) for r in rows]

    async def search_articles(
        self, query: str, hours: int = 168, limit: int = 50, domain: Optional[str] = None,
    ) -> List[ClassifiedArticle]:
        """Search articles using CONTAINS_SUBSTR."""
        cutoff = self._cutoff_timestamp(hours)
        params = [
            bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
            bigquery.ScalarQueryParameter("q", "STRING", query),
        ]
        # BigQuery CONTAINS_SUBSTR searches for substring match
        where = (
            "fetched_at >= TIMESTAMP(@cutoff) AND ("
            "CONTAINS_SUBSTR(title, @q) OR "
            "CONTAINS_SUBSTR(ai_summary, @q) OR "
            "CONTAINS_SUBSTR(ARRAY_TO_STRING(companies_mentioned, ','), @q)"
            ")"
        )
        if domain:
            where += " AND domain = @domain"
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))

        sql = (
            f"SELECT * FROM {self._table('articles')} "
            f"WHERE {where} ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(sql, job_config=job_config).result())
        )
        return [self._row_to_article(dict(r)) for r in rows]

    # =========================================================================
    # Deduplication Support
    # =========================================================================

    async def url_exists(self, url: str) -> bool:
        query = f"SELECT 1 FROM {self._table('articles')} WHERE url = @url LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("url", "STRING", url)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    async def get_recent_urls(self, hours: int = 168) -> Set[str]:
        cutoff = self._cutoff_timestamp(hours)
        query = (
            f"SELECT url FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff)"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return {r["url"] for r in rows}

    async def get_recent_titles(self, hours: int = 168) -> Dict[str, str]:
        cutoff = self._cutoff_timestamp(hours)
        query = (
            f"SELECT title, url FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff)"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return {r["title"]: r["url"] for r in rows}

    async def get_recent_articles_for_dedup(
        self, hours: int = 168, limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        cutoff = self._cutoff_timestamp(hours)
        query = (
            f"SELECT id, url, title, content_hash FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff) LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [dict(r) for r in rows]

    # =========================================================================
    # Digest Operations
    # =========================================================================

    async def save_digest(self, digest: Digest) -> str:
        row = {
            "id": digest.id,
            "created_at": self._dt_to_iso(digest.created_at),
            "period_hours": digest.period_hours,
            "executive_summary": digest.executive_summary,
            "content": json.dumps([
                {
                    "id": item.id, "title": item.title,
                    "source_name": item.source_name, "url": item.url,
                    "summary": item.summary, "category": item.category,
                    "priority": item.priority.value if isinstance(item.priority, Priority) else item.priority,
                    "relevance_score": item.relevance_score,
                }
                for item in digest.items
            ]),
            "total_items": digest.total_items,
            "critical_count": digest.critical_count,
            "high_count": digest.high_count,
            "medium_count": digest.medium_count,
            "low_count": digest.low_count,
        }
        await self._upsert_row("digests", row, dedup_keys=["id"])
        return digest.id

    async def get_latest_digest(self) -> Optional[Digest]:
        query = (
            f"SELECT * FROM {self._table('digests')} "
            f"ORDER BY created_at DESC LIMIT 1"
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query).result())
        )
        if not rows:
            return None

        data = dict(rows[0])
        content = data.get("content")
        if isinstance(content, str):
            items_data = json.loads(content)
        elif isinstance(content, list):
            items_data = content
        else:
            items_data = []
        items = [DigestItem(**item) for item in items_data]

        return Digest(
            id=data["id"],
            created_at=self._parse_dt(data["created_at"]) or datetime.now(timezone.utc),
            period_hours=data.get("period_hours", 72),
            executive_summary=data.get("executive_summary", ""),
            items=items,
            total_items=data.get("total_items", 0),
            critical_count=data.get("critical_count", 0),
            high_count=data.get("high_count", 0),
            medium_count=data.get("medium_count", 0),
            low_count=data.get("low_count", 0),
        )

    # =========================================================================
    # Paper Operations
    # =========================================================================

    def _row_to_paper(self, row: dict) -> Paper:
        data = dict(row)
        for list_field in ["authors", "categories"]:
            data[list_field] = self._ensure_list(data.get(list_field))
        for dt_field in ["published_at", "updated_at", "ingested_at"]:
            val = data.get(dt_field)
            if val and isinstance(val, str):
                try:
                    data[dt_field] = datetime.fromisoformat(val)
                except ValueError:
                    data[dt_field] = None
        return Paper.from_dict(data)

    async def save_papers(self, papers: List[Paper]) -> int:
        if not papers:
            return 0

        rows = []
        for paper in papers:
            rows.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": self._ensure_list(paper.authors),
                "abstract": paper.abstract,
                "categories": self._ensure_list(paper.categories),
                "published_at": self._dt_to_iso(paper.published_at),
                "updated_at": self._dt_to_iso(paper.updated_at),
                "ingested_at": self._dt_to_iso(paper.ingested_at),
                "pdf_url": paper.pdf_url,
                "relevance_score": paper.relevance_score,
                "paper_type": paper.paper_type,
                "use_case_category": paper.use_case_category,
                "commercial_readiness": paper.commercial_readiness,
                "significance_summary": paper.significance_summary,
            })

        return await self._insert_if_not_exists("papers", rows, ["arxiv_id"])

    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        query = f"SELECT * FROM {self._table('papers')} WHERE arxiv_id = @arxiv_id LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("arxiv_id", "STRING", arxiv_id)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return self._row_to_paper(dict(rows[0])) if rows else None

    async def get_recent_papers(self, days: int = 7, limit: int = 50) -> List[Paper]:
        cutoff = self._cutoff_timestamp(days * 24)
        query = (
            f"SELECT * FROM {self._table('papers')} "
            f"WHERE ingested_at >= TIMESTAMP(@cutoff) ORDER BY published_at DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [self._row_to_paper(dict(r)) for r in rows]

    async def arxiv_id_exists(self, arxiv_id: str) -> bool:
        query = f"SELECT 1 FROM {self._table('papers')} WHERE arxiv_id = @arxiv_id LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("arxiv_id", "STRING", arxiv_id)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    # =========================================================================
    # Stock Operations
    # =========================================================================

    async def save_stock_data(self, snapshots: List[StockSnapshot]) -> int:
        if not snapshots:
            return 0

        rows = []
        for s in snapshots:
            rows.append({
                "ticker": s.ticker,
                "date": s.date,
                "open": s.open,
                "high": s.high,
                "low": s.low,
                "close": s.close,
                "volume": s.volume,
                "change_percent": s.change_percent,
                "market_cap": s.market_cap,
                "sma_20": s.sma_20,
                "sma_50": s.sma_50,
            })

        # Stocks use upsert (INSERT OR REPLACE in SQLite)
        saved = 0
        for row in rows:
            ok = await self._upsert_row("stocks", row, dedup_keys=["ticker", "date"])
            if ok:
                saved += 1
        return saved

    async def get_stock_data(self, ticker: str, days: int = 30) -> List[StockSnapshot]:
        cutoff = self._cutoff_days(days)
        query = (
            f"SELECT * FROM {self._table('stocks')} "
            f"WHERE ticker = @ticker AND date >= @cutoff ORDER BY date DESC"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [StockSnapshot.from_dict(dict(r)) for r in rows]

    async def get_latest_stock_data(self, tickers: Optional[List[str]] = None) -> List[StockSnapshot]:
        if tickers:
            query = (
                f"SELECT s.* FROM {self._table('stocks')} s "
                f"INNER JOIN ("
                f"  SELECT ticker, MAX(date) AS max_date FROM {self._table('stocks')} "
                f"  WHERE ticker IN UNNEST(@tickers) GROUP BY ticker"
                f") latest ON s.ticker = latest.ticker AND s.date = latest.max_date"
            )
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("tickers", "STRING", tickers)
                ]
            )
        else:
            query = (
                f"SELECT s.* FROM {self._table('stocks')} s "
                f"INNER JOIN ("
                f"  SELECT ticker, MAX(date) AS max_date FROM {self._table('stocks')} "
                f"  GROUP BY ticker"
                f") latest ON s.ticker = latest.ticker AND s.date = latest.max_date"
            )
            job_config = bigquery.QueryJobConfig()

        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [StockSnapshot.from_dict(dict(r)) for r in rows]

    # =========================================================================
    # Stats
    # =========================================================================

    async def get_article_count(self, hours: int = 24) -> int:
        cutoff = self._cutoff_timestamp(hours)
        query = (
            f"SELECT COUNT(*) as cnt FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff)"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return rows[0]["cnt"] if rows else 0

    async def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = self._cutoff_timestamp(hours)
        params = [bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff)]

        total = await self.get_article_count(hours)

        # By category
        query = (
            f"SELECT primary_category, COUNT(*) as cnt FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff) GROUP BY primary_category ORDER BY cnt DESC"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        by_category = {r["primary_category"]: r["cnt"] for r in rows}

        # By priority
        query = (
            f"SELECT priority, COUNT(*) as cnt FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff) GROUP BY priority"
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
        )
        by_priority = {r["priority"]: r["cnt"] for r in rows}

        # By source type
        query = (
            f"SELECT source_type, COUNT(*) as cnt FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff) GROUP BY source_type"
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
        )
        by_source = {r["source_type"]: r["cnt"] for r in rows}

        # Average relevance
        query = (
            f"SELECT AVG(relevance_score) as avg_rel FROM {self._table('articles')} "
            f"WHERE fetched_at >= TIMESTAMP(@cutoff)"
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
        )
        avg_relevance = rows[0]["avg_rel"] if rows and rows[0]["avg_rel"] else 0.0

        return {
            "total_articles": total,
            "by_category": by_category,
            "by_priority": by_priority,
            "by_source": by_source,
            "avg_relevance": round(avg_relevance, 3),
            "hours": hours,
        }

    async def close(self) -> None:
        self.client.close()
        logger.info("[STORAGE] BigQuery connection closed")

    # =========================================================================
    # Earnings Operations
    # =========================================================================

    async def save_transcript(self, transcript: EarningsTranscript) -> str:
        row = {
            "transcript_id": transcript.transcript_id,
            "ticker": transcript.ticker,
            "company_name": transcript.company_name,
            "year": transcript.year,
            "quarter": transcript.quarter,
            "transcript_text": transcript.transcript_text,
            "call_date": self._dt_to_iso(transcript.call_date),
            "participants": json.dumps(transcript.participants),
            "fiscal_period": transcript.fiscal_period,
            "ingested_at": self._dt_to_iso(transcript.ingested_at),
            "char_count": transcript.char_count,
            "domain": getattr(transcript, "domain", "quantum"),
        }
        await self._insert_if_not_exists(
            "earnings_transcripts", [row], ["ticker", "year", "quarter"]
        )
        logger.info(f"[EARNINGS] Saved transcript: {transcript.unique_key}")
        return transcript.transcript_id

    async def transcript_exists(self, ticker: str, year: int, quarter: int) -> bool:
        query = (
            f"SELECT 1 FROM {self._table('earnings_transcripts')} "
            f"WHERE ticker = @ticker AND year = @year AND quarter = @quarter LIMIT 1"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("year", "INT64", year),
                bigquery.ScalarQueryParameter("quarter", "INT64", quarter),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    async def save_quotes(self, quotes: List[ExtractedQuote]) -> int:
        if not quotes:
            return 0

        rows = []
        for quote in quotes:
            data = quote.to_dict()
            rows.append({
                "quote_id": data["quote_id"],
                "transcript_id": data["transcript_id"],
                "quote_text": data["quote_text"],
                "context_before": data["context_before"],
                "context_after": data["context_after"],
                "speaker_name": data["speaker_name"],
                "speaker_role": data["speaker_role"],
                "speaker_title": data["speaker_title"],
                "speaker_company": data["speaker_company"],
                "speaker_firm": data["speaker_firm"],
                "quote_type": data["quote_type"],
                "themes": data["themes"],
                "sentiment": data["sentiment"],
                "confidence_level": data["confidence_level"],
                "companies_mentioned": data["companies_mentioned"],
                "technologies_mentioned": data["technologies_mentioned"],
                "competitors_mentioned": data["competitors_mentioned"],
                "metrics_mentioned": data["metrics_mentioned"],
                "relevance_score": data["relevance_score"],
                "is_quotable": bool(data["is_quotable"]),
                "quotability_reason": data["quotability_reason"],
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "year": data["year"],
                "quarter": data["quarter"],
                "call_date": data["call_date"],
                "section": data["section"],
                "position_in_section": data["position_in_section"],
                "extracted_at": data["extracted_at"],
                "extraction_model": data["extraction_model"],
                "extraction_confidence": data["extraction_confidence"],
                "domain": data.get("domain", "quantum"),
            })

        return await self._insert_if_not_exists("earnings_quotes", rows, ["quote_id"])

    async def get_quotes_by_ticker(self, ticker: str, limit: int = 50) -> List[ExtractedQuote]:
        query = (
            f"SELECT * FROM {self._table('earnings_quotes')} "
            f"WHERE ticker = @ticker ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [ExtractedQuote.from_dict(dict(r)) for r in rows]

    async def search_earnings_quotes(
        self, query: str, ticker: Optional[str] = None, limit: int = 30
    ) -> List[ExtractedQuote]:
        """Search earnings quotes by text."""
        pattern = f"%{query}%"
        if ticker:
            bq_query = (
                f"SELECT * FROM {self._table('earnings_quotes')} "
                f"WHERE ticker = @ticker AND ("
                f"  LOWER(quote_text) LIKE LOWER(@pattern) OR "
                f"  LOWER(speaker_name) LIKE LOWER(@pattern) OR "
                f"  LOWER(themes) LIKE LOWER(@pattern) OR "
                f"  LOWER(companies_mentioned) LIKE LOWER(@pattern) OR "
                f"  LOWER(technologies_mentioned) LIKE LOWER(@pattern)"
                f") "
                f"ORDER BY relevance_score DESC LIMIT @lim"
            )
            query_params = [
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        else:
            bq_query = (
                f"SELECT * FROM {self._table('earnings_quotes')} "
                f"WHERE "
                f"  LOWER(quote_text) LIKE LOWER(@pattern) OR "
                f"  LOWER(speaker_name) LIKE LOWER(@pattern) OR "
                f"  LOWER(themes) LIKE LOWER(@pattern) OR "
                f"  LOWER(companies_mentioned) LIKE LOWER(@pattern) OR "
                f"  LOWER(technologies_mentioned) LIKE LOWER(@pattern) "
                f"ORDER BY relevance_score DESC LIMIT @lim"
            )
            query_params = [
                bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        rows = await self._run_sync(
            lambda: list(self.client.query(bq_query, job_config=job_config).result())
        )
        return [ExtractedQuote.from_dict(dict(r)) for r in rows]

    async def get_transcripts_without_quotes(
        self, tickers: Optional[List[str]] = None,
    ) -> List[EarningsTranscript]:
        """Get transcripts that have no extracted quotes yet."""
        if tickers:
            query = (
                f"SELECT t.* FROM {self._table('earnings_transcripts')} t "
                f"LEFT JOIN {self._table('earnings_quotes')} q ON t.transcript_id = q.transcript_id "
                f"WHERE q.quote_id IS NULL AND t.ticker IN UNNEST(@tickers) "
                f"ORDER BY t.ticker, t.year DESC, t.quarter DESC"
            )
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("tickers", "STRING", tickers)]
            )
        else:
            query = (
                f"SELECT t.* FROM {self._table('earnings_transcripts')} t "
                f"LEFT JOIN {self._table('earnings_quotes')} q ON t.transcript_id = q.transcript_id "
                f"WHERE q.quote_id IS NULL "
                f"ORDER BY t.ticker, t.year DESC, t.quarter DESC"
            )
            job_config = bigquery.QueryJobConfig()

        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [EarningsTranscript.from_dict(dict(r)) for r in rows]

    # =========================================================================
    # SEC Operations
    # =========================================================================

    async def save_filing(self, filing: SecFiling) -> str:
        row = {
            "filing_id": filing.filing_id,
            "ticker": filing.ticker,
            "company_name": filing.company_name,
            "cik": filing.cik,
            "accession_number": filing.accession_number,
            "filing_type": filing.filing_type,
            "filing_date": self._dt_to_iso(filing.filing_date),
            "fiscal_year": filing.fiscal_year,
            "fiscal_quarter": filing.fiscal_quarter,
            "primary_document": filing.primary_document,
            "filing_url": filing.filing_url,
            "raw_content": filing.raw_content,
            "sections": json.dumps(filing.sections) if filing.sections else None,
            "ingested_at": self._dt_to_iso(filing.ingested_at),
            "char_count": filing.char_count,
            "domain": getattr(filing, "domain", "quantum"),
        }
        await self._insert_if_not_exists(
            "sec_filings", [row], ["ticker", "filing_type", "fiscal_year", "fiscal_quarter"]
        )
        logger.info(f"[SEC] Saved filing: {filing.unique_key}")
        return filing.filing_id

    async def filing_exists(
        self, ticker: str, filing_type: str, fiscal_year: int, fiscal_quarter: Optional[int] = None,
    ) -> bool:
        params = [
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
            bigquery.ScalarQueryParameter("filing_type", "STRING", filing_type),
            bigquery.ScalarQueryParameter("fiscal_year", "INT64", fiscal_year),
        ]
        if fiscal_quarter is not None:
            query = (
                f"SELECT 1 FROM {self._table('sec_filings')} "
                f"WHERE ticker = @ticker AND filing_type = @filing_type "
                f"AND fiscal_year = @fiscal_year AND fiscal_quarter = @fiscal_quarter LIMIT 1"
            )
            params.append(bigquery.ScalarQueryParameter("fiscal_quarter", "INT64", fiscal_quarter))
        else:
            query = (
                f"SELECT 1 FROM {self._table('sec_filings')} "
                f"WHERE ticker = @ticker AND filing_type = @filing_type "
                f"AND fiscal_year = @fiscal_year AND fiscal_quarter IS NULL LIMIT 1"
            )

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    async def save_nuggets(self, nuggets: List[SecNugget]) -> int:
        if not nuggets:
            return 0

        rows = []
        for nugget in nuggets:
            data = nugget.to_dict()
            rows.append({
                "nugget_id": data["nugget_id"],
                "filing_id": data["filing_id"],
                "nugget_text": data["nugget_text"],
                "context_text": data["context_text"],
                "filing_type": data["filing_type"],
                "section": data["section"],
                "nugget_type": data["nugget_type"],
                "themes": data["themes"],
                "signal_strength": data["signal_strength"],
                "companies_mentioned": data["companies_mentioned"],
                "technologies_mentioned": data["technologies_mentioned"],
                "competitors_named": data["competitors_named"],
                "regulators_mentioned": data["regulators_mentioned"],
                "risk_level": data["risk_level"],
                "is_new_disclosure": bool(data["is_new_disclosure"]),
                "is_actionable": bool(data["is_actionable"]),
                "actionability_reason": data["actionability_reason"],
                "relevance_score": data["relevance_score"],
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "cik": data["cik"],
                "fiscal_year": data["fiscal_year"],
                "fiscal_quarter": data["fiscal_quarter"],
                "filing_date": data["filing_date"],
                "accession_number": data["accession_number"],
                "extracted_at": data["extracted_at"],
                "extraction_model": data["extraction_model"],
                "extraction_confidence": data["extraction_confidence"],
                "domain": data.get("domain", "quantum"),
            })

        return await self._insert_if_not_exists("sec_nuggets", rows, ["nugget_id"])

    async def get_nuggets_by_ticker(self, ticker: str, limit: int = 50) -> List[SecNugget]:
        query = (
            f"SELECT * FROM {self._table('sec_nuggets')} "
            f"WHERE ticker = @ticker ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [SecNugget.from_dict(dict(r)) for r in rows]

    async def search_sec_nuggets(
        self, query: str, ticker: Optional[str] = None, limit: int = 30
    ) -> List[SecNugget]:
        """Search SEC nuggets by text."""
        pattern = f"%{query}%"
        if ticker:
            bq_query = (
                f"SELECT * FROM {self._table('sec_nuggets')} "
                f"WHERE ticker = @ticker AND ("
                f"  LOWER(nugget_text) LIKE LOWER(@pattern) OR "
                f"  LOWER(themes) LIKE LOWER(@pattern) OR "
                f"  LOWER(companies_mentioned) LIKE LOWER(@pattern) OR "
                f"  LOWER(technologies_mentioned) LIKE LOWER(@pattern)"
                f") "
                f"ORDER BY relevance_score DESC LIMIT @lim"
            )
            query_params = [
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        else:
            bq_query = (
                f"SELECT * FROM {self._table('sec_nuggets')} "
                f"WHERE "
                f"  LOWER(nugget_text) LIKE LOWER(@pattern) OR "
                f"  LOWER(themes) LIKE LOWER(@pattern) OR "
                f"  LOWER(companies_mentioned) LIKE LOWER(@pattern) OR "
                f"  LOWER(technologies_mentioned) LIKE LOWER(@pattern) "
                f"ORDER BY relevance_score DESC LIMIT @lim"
            )
            query_params = [
                bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        rows = await self._run_sync(
            lambda: list(self.client.query(bq_query, job_config=job_config).result())
        )
        return [SecNugget.from_dict(dict(r)) for r in rows]

    async def get_filings_without_nuggets(
        self, tickers: Optional[List[str]] = None,
    ) -> List[SecFiling]:
        """Get filings that have no extracted nuggets yet."""
        if tickers:
            query = (
                f"SELECT f.* FROM {self._table('sec_filings')} f "
                f"LEFT JOIN {self._table('sec_nuggets')} n ON f.filing_id = n.filing_id "
                f"WHERE n.nugget_id IS NULL AND f.ticker IN UNNEST(@tickers) "
                f"ORDER BY f.ticker, f.filing_date DESC"
            )
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("tickers", "STRING", tickers)]
            )
        else:
            query = (
                f"SELECT f.* FROM {self._table('sec_filings')} f "
                f"LEFT JOIN {self._table('sec_nuggets')} n ON f.filing_id = n.filing_id "
                f"WHERE n.nugget_id IS NULL "
                f"ORDER BY f.ticker, f.filing_date DESC"
            )
            job_config = bigquery.QueryJobConfig()

        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [SecFiling.from_dict(dict(r)) for r in rows]

    # =========================================================================
    # Podcast Operations
    # =========================================================================

    async def save_podcast_transcript(self, transcript: PodcastTranscript) -> str:
        row = {
            "transcript_id": transcript.transcript_id,
            "episode_id": transcript.episode_id,
            "podcast_id": transcript.podcast_id,
            "podcast_name": transcript.podcast_name,
            "episode_title": transcript.episode_title,
            "episode_url": transcript.episode_url,
            "audio_url": transcript.audio_url,
            "full_text": transcript.full_text,
            "formatted_text": transcript.formatted_text,
            "char_count": transcript.char_count,
            "word_count": transcript.word_count,
            "duration_seconds": transcript.duration_seconds,
            "hosts": self._ensure_list(transcript.hosts),
            "guest_name": transcript.guest_name,
            "guest_title": transcript.guest_title,
            "guest_company": transcript.guest_company,
            "speaker_count": transcript.speaker_count,
            "transcript_source": transcript.transcript_source,
            "status": transcript.status.value if hasattr(transcript.status, "value") else transcript.status,
            "published_at": self._dt_to_iso(transcript.published_at),
            "ingested_at": self._dt_to_iso(transcript.ingested_at),
            "transcribed_at": self._dt_to_iso(transcript.transcribed_at),
            "transcription_cost_usd": transcript.transcription_cost_usd,
        }
        await self._insert_if_not_exists(
            "podcast_transcripts", [row], ["podcast_id", "episode_id"]
        )
        logger.info(f"[PODCAST] Saved transcript: {transcript.podcast_name} — {transcript.episode_title}")
        return transcript.transcript_id

    async def podcast_episode_exists(self, podcast_id: str, episode_id: str) -> bool:
        query = (
            f"SELECT 1 FROM {self._table('podcast_transcripts')} "
            f"WHERE podcast_id = @podcast_id AND episode_id = @episode_id LIMIT 1"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("podcast_id", "STRING", podcast_id),
                bigquery.ScalarQueryParameter("episode_id", "STRING", episode_id),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    async def save_podcast_quotes(self, quotes: List[PodcastQuote]) -> int:
        if not quotes:
            return 0

        rows = []
        for quote in quotes:
            data = quote.to_dict()
            rows.append({
                "quote_id": data["quote_id"],
                "transcript_id": data["transcript_id"],
                "episode_id": data["episode_id"],
                "quote_text": data["quote_text"],
                "context_before": data["context_before"],
                "context_after": data["context_after"],
                "speaker_name": data["speaker_name"],
                "speaker_role": data["speaker_role"],
                "speaker_title": data["speaker_title"],
                "speaker_company": data["speaker_company"],
                "quote_type": data["quote_type"],
                "themes": data["themes"],
                "sentiment": data["sentiment"],
                "companies_mentioned": data["companies_mentioned"],
                "technologies_mentioned": data["technologies_mentioned"],
                "people_mentioned": data["people_mentioned"],
                "relevance_score": data["relevance_score"],
                "is_quotable": bool(data["is_quotable"]),
                "quotability_reason": data["quotability_reason"],
                "podcast_id": data["podcast_id"],
                "podcast_name": data["podcast_name"],
                "episode_title": data["episode_title"],
                "published_at": data["published_at"],
                "extracted_at": data["extracted_at"],
                "extraction_model": data["extraction_model"],
                "extraction_confidence": data["extraction_confidence"],
            })

        return await self._insert_if_not_exists("podcast_quotes", rows, ["quote_id"])

    async def get_podcast_quotes(
        self, podcast_id: Optional[str] = None, limit: int = 50,
    ) -> List[PodcastQuote]:
        params = [bigquery.ScalarQueryParameter("lim", "INT64", limit)]
        if podcast_id:
            query = (
                f"SELECT * FROM {self._table('podcast_quotes')} "
                f"WHERE podcast_id = @podcast_id ORDER BY relevance_score DESC LIMIT @lim"
            )
            params.insert(0, bigquery.ScalarQueryParameter("podcast_id", "STRING", podcast_id))
        else:
            query = (
                f"SELECT * FROM {self._table('podcast_quotes')} "
                f"ORDER BY relevance_score DESC LIMIT @lim"
            )

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [PodcastQuote.from_dict(dict(r)) for r in rows]

    async def search_podcast_quotes(self, query: str, limit: int = 30) -> List[PodcastQuote]:
        sql = (
            f"SELECT * FROM {self._table('podcast_quotes')} "
            f"WHERE CONTAINS_SUBSTR(quote_text, @q) "
            f"OR CONTAINS_SUBSTR(speaker_name, @q) "
            f"OR CONTAINS_SUBSTR(themes, @q) "
            f"OR CONTAINS_SUBSTR(companies_mentioned, @q) "
            f"OR CONTAINS_SUBSTR(technologies_mentioned, @q) "
            f"ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("q", "STRING", query),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(sql, job_config=job_config).result())
        )
        return [PodcastQuote.from_dict(dict(r)) for r in rows]

    # =========================================================================
    # Weekly Briefing Operations
    # =========================================================================

    async def save_weekly_briefing(self, briefing: WeeklyBriefing) -> str:
        row = {
            "id": briefing.id,
            "domain": briefing.domain,
            "week_of": briefing.week_of,
            "created_at": self._dt_to_iso(briefing.created_at),
            "sections": json.dumps([s.to_dict() for s in briefing.sections]),
            "market_movers": json.dumps([m.to_dict() for m in briefing.market_movers]),
            "research_papers": json.dumps([p.to_dict() for p in briefing.research_papers]),
            "articles_analyzed": briefing.articles_analyzed,
            "sections_active": briefing.sections_active,
            "sections_total": briefing.sections_total,
            "generation_cost_usd": briefing.generation_cost_usd,
            "pre_brief_id": briefing.pre_brief_id,
        }
        # Upsert: weekly briefings use INSERT OR REPLACE in SQLite
        await self._upsert_row("weekly_briefings", row, dedup_keys=["domain", "week_of"])
        logger.info(f"[STORAGE] Saved weekly briefing: {briefing.domain} week_of={briefing.week_of}")
        return briefing.id

    async def get_latest_weekly_briefing(self, domain: str = "quantum") -> Optional[WeeklyBriefing]:
        query = (
            f"SELECT * FROM {self._table('weekly_briefings')} "
            f"WHERE domain = @domain ORDER BY created_at DESC LIMIT 1"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("domain", "STRING", domain)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        if not rows:
            return None
        return self._row_to_weekly_briefing(dict(rows[0]))

    async def get_weekly_briefing_by_week(self, domain: str, week_of: str) -> Optional[WeeklyBriefing]:
        query = (
            f"SELECT * FROM {self._table('weekly_briefings')} "
            f"WHERE domain = @domain AND week_of = @week_of LIMIT 1"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("domain", "STRING", domain),
                bigquery.ScalarQueryParameter("week_of", "STRING", week_of),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        if not rows:
            return None
        return self._row_to_weekly_briefing(dict(rows[0]))

    def _row_to_weekly_briefing(self, data: dict) -> WeeklyBriefing:
        """Convert a BigQuery row to WeeklyBriefing."""
        sections_raw = data.get("sections")
        if isinstance(sections_raw, str):
            sections_raw = json.loads(sections_raw)
        elif sections_raw is None:
            sections_raw = []
        sections = [BriefingSection.from_dict(s) for s in sections_raw]

        movers_raw = data.get("market_movers")
        if isinstance(movers_raw, str):
            movers_raw = json.loads(movers_raw)
        elif movers_raw is None:
            movers_raw = []
        market_movers = [MarketMover.from_dict(m) for m in movers_raw]

        papers_raw = data.get("research_papers")
        if isinstance(papers_raw, str):
            papers_raw = json.loads(papers_raw)
        elif papers_raw is None:
            papers_raw = []
        research_papers = [ResearchPaper.from_dict(p) for p in papers_raw]

        return WeeklyBriefing(
            id=data["id"],
            domain=data["domain"],
            week_of=data["week_of"],
            created_at=self._parse_dt(data["created_at"]) or datetime.now(timezone.utc),
            sections=sections,
            market_movers=market_movers,
            research_papers=research_papers,
            articles_analyzed=data.get("articles_analyzed", 0),
            sections_active=data.get("sections_active", 0),
            sections_total=data.get("sections_total", 7),
            generation_cost_usd=data.get("generation_cost_usd", 0.0),
            pre_brief_id=data.get("pre_brief_id"),
        )

    # =========================================================================
    # Case Study Operations (Phase 6)
    # =========================================================================

    async def save_case_studies(self, case_studies: List[CaseStudy]) -> int:
        """Save extracted case studies. Returns count saved."""
        if not case_studies:
            return 0

        rows = []
        for cs in case_studies:
            rows.append({
                "case_study_id": cs.case_study_id,
                "source_type": cs.source_type,
                "source_id": cs.source_id,
                "domain": cs.domain,
                "grounding_quote": cs.grounding_quote,
                "context_text": cs.context_text,
                "use_case_title": cs.use_case_title,
                "use_case_summary": cs.use_case_summary,
                "company": cs.company,
                "industry": cs.industry,
                "technology_stack": self._ensure_list(cs.technology_stack),
                "department": cs.department,
                "implementation_detail": cs.implementation_detail,
                "teams_impacted": self._ensure_list(cs.teams_impacted),
                "scale": cs.scale,
                "timeline": cs.timeline,
                "readiness_level": cs.readiness_level,
                "outcome_metric": cs.outcome_metric,
                "outcome_type": cs.outcome_type,
                "outcome_quantified": bool(cs.outcome_quantified),
                "speaker": cs.speaker,
                "speaker_role": cs.speaker_role,
                "speaker_company": cs.speaker_company,
                "companies_mentioned": self._ensure_list(cs.companies_mentioned),
                "technologies_mentioned": self._ensure_list(cs.technologies_mentioned),
                "people_mentioned": self._ensure_list(cs.people_mentioned),
                "competitors_mentioned": self._ensure_list(cs.competitors_mentioned),
                "qubit_type": cs.qubit_type,
                "gate_fidelity": cs.gate_fidelity,
                "commercial_viability": cs.commercial_viability,
                "scientific_significance": cs.scientific_significance,
                "ai_model_used": cs.ai_model_used,
                "roi_metric": cs.roi_metric,
                "deployment_type": cs.deployment_type,
                "relevance_score": cs.relevance_score,
                "confidence": cs.confidence,
                "metadata": json.dumps(cs.metadata or {}),
                "extracted_at": self._dt_to_iso(cs.extracted_at),
                "extraction_model": cs.extraction_model,
                "extraction_confidence": cs.extraction_confidence,
            })

        return await self._insert_if_not_exists("case_studies", rows, ["case_study_id"])

    async def get_case_studies_by_source(
        self, source_type: str, source_id: str
    ) -> List[CaseStudy]:
        """Get case studies for a specific source item."""
        query = (
            f"SELECT * FROM {self._table('case_studies')} "
            f"WHERE source_type = @source_type AND source_id = @source_id "
            f"ORDER BY relevance_score DESC"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_type", "STRING", source_type),
                bigquery.ScalarQueryParameter("source_id", "STRING", source_id),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [CaseStudy.from_dict(self._bq_row_to_cs_dict(r)) for r in rows]

    async def get_case_studies(
        self,
        domain: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[CaseStudy]:
        """Get case studies with optional filters."""
        where_parts = ["1=1"]
        params = []

        if domain:
            where_parts.append("domain = @domain")
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        if company:
            where_parts.append("company = @company")
            params.append(bigquery.ScalarQueryParameter("company", "STRING", company))
        if industry:
            where_parts.append("industry = @industry")
            params.append(bigquery.ScalarQueryParameter("industry", "STRING", industry))
        if source_type:
            where_parts.append("source_type = @source_type")
            params.append(bigquery.ScalarQueryParameter("source_type", "STRING", source_type))

        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))
        where_clause = " AND ".join(where_parts)

        query = (
            f"SELECT * FROM {self._table('case_studies')} "
            f"WHERE {where_clause} ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return [CaseStudy.from_dict(self._bq_row_to_cs_dict(r)) for r in rows]

    async def case_studies_exist_for_source(
        self, source_type: str, source_id: str
    ) -> bool:
        """Check if case studies already extracted for this source."""
        query = (
            f"SELECT 1 FROM {self._table('case_studies')} "
            f"WHERE source_type = @source_type AND source_id = @source_id LIMIT 1"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_type", "STRING", source_type),
                bigquery.ScalarQueryParameter("source_id", "STRING", source_id),
            ]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0

    async def search_case_studies(
        self, query: str, domain: Optional[str] = None, limit: int = 30
    ) -> List[CaseStudy]:
        """Search case studies by text."""
        params = [
            bigquery.ScalarQueryParameter("q", "STRING", query),
        ]
        where = (
            "(CONTAINS_SUBSTR(use_case_title, @q) OR "
            "CONTAINS_SUBSTR(use_case_summary, @q) OR "
            "CONTAINS_SUBSTR(grounding_quote, @q) OR "
            "CONTAINS_SUBSTR(company, @q))"
        )
        if domain:
            where += " AND domain = @domain"
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))

        sql = (
            f"SELECT * FROM {self._table('case_studies')} "
            f"WHERE {where} ORDER BY relevance_score DESC LIMIT @lim"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(sql, job_config=job_config).result())
        )
        return [CaseStudy.from_dict(self._bq_row_to_cs_dict(r)) for r in rows]

    def _bq_row_to_cs_dict(self, row) -> dict:
        """Convert a BigQuery row to dict suitable for CaseStudy.from_dict()."""
        data = dict(row)
        # ARRAY fields come back as lists natively; list fields need no conversion
        # JSON metadata
        meta = data.get("metadata")
        if meta is None:
            data["metadata"] = {}
        elif isinstance(meta, str):
            try:
                data["metadata"] = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                data["metadata"] = {}
        return data

    # =========================================================================
    # Funding Event Operations (Phase 3)
    # =========================================================================

    async def save_funding_events(self, events: List["FundingEvent"]) -> int:
        """Save extracted funding events. Returns count saved."""
        if not events:
            return 0

        rows = []
        for event in events:
            # Assuming the dataclass has a to_dict method, or doing it manually:
            from dataclasses import asdict
            data = asdict(event)
            
            rows.append({
                "id": data["id"],
                "article_id": data["article_id"],
                "article_url": data["article_url"],
                "domain": data["domain"],
                "startup_name": data["startup_name"],
                "funding_round": data["funding_round"],
                "funding_amount": data["funding_amount"],
                "valuation": data["valuation"],
                "lead_investors": self._ensure_list(data.get("lead_investors")),
                "other_investors": self._ensure_list(data.get("other_investors")),
                "investment_thesis": data["investment_thesis"],
                "known_technologies": self._ensure_list(data.get("known_technologies")),
                "use_of_funds": data["use_of_funds"],
                "extracted_at": self._dt_to_iso(data["extracted_at"]),
                "confidence_score": data["confidence_score"],
                "grounding_quote": data["grounding_quote"],
            })

        return await self._insert_if_not_exists("funding_events", rows, ["id", "article_id"])

    async def get_funding_events(
        self, domain: Optional[str] = None, limit: int = 50
    ) -> List[Any]:
        """Get funding events, optionally filtered by domain."""
        from models.funding import FundingEvent
        params = [bigquery.ScalarQueryParameter("lim", "INT64", limit)]
        
        if domain:
            query = (
                f"SELECT * FROM {self._table('funding_events')} "
                f"WHERE domain = @domain ORDER BY extracted_at DESC LIMIT @lim"
            )
            params.append(bigquery.ScalarQueryParameter("domain", "STRING", domain))
        else:
            query = (
                f"SELECT * FROM {self._table('funding_events')} "
                f"ORDER BY extracted_at DESC LIMIT @lim"
            )
            
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        
        results = []
        for row in rows:
            data = dict(row)
            for list_field in ["lead_investors", "other_investors", "known_technologies"]:
                data[list_field] = self._ensure_list(data.get(list_field))
            for dt_field in ["extracted_at"]:
                val = data.get(dt_field)
                if val and isinstance(val, str):
                    try:
                        data[dt_field] = datetime.fromisoformat(val)
                    except ValueError:
                        data[dt_field] = None
            results.append(FundingEvent(**data))
            
        return results

    async def funding_events_exist_for_article(self, article_id: str) -> bool:
        """Check if funding events were already extracted for this article."""
        query = f"SELECT 1 FROM {self._table('funding_events')} WHERE article_id = @article_id LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("article_id", "STRING", article_id)]
        )
        rows = await self._run_sync(
            lambda: list(self.client.query(query, job_config=job_config).result())
        )
        return len(rows) > 0
