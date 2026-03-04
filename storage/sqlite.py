"""
SQLite Storage Backend
======================

Local development storage using SQLite.
Implements the StorageBackend ABC for articles, digests, and dedup support.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Set, Any

from .base import StorageBackend, ClassifiedArticle
from .schemas import ALL_TABLES, ALL_INDEXES
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


class SQLiteStorage(StorageBackend):
    """SQLite storage backend for local development."""

    def __init__(self, db_path: str = "data/quantum_intel.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_directory()
        self._initialize_db()

    def _ensure_directory(self):
        """Create data directory if needed."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _initialize_db(self):
        """Create tables and indexes."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        for table_sql in ALL_TABLES:
            self._conn.execute(table_sql)

        # Migration: add domain column to existing databases
        # Must run BEFORE indexes since idx_articles_domain references this column
        try:
            self._conn.execute("SELECT domain FROM articles LIMIT 1")
        except sqlite3.OperationalError:
            self._conn.execute("ALTER TABLE articles ADD COLUMN domain TEXT DEFAULT 'quantum'")
            self._conn.commit()
            logger.info("[STORAGE] Migration: added domain column to articles")

        # Migration: add strategic implication columns
        for col in ["time_to_market_impact", "disrupted_industries", "investment_signal"]:
            try:
                self._conn.execute(f"SELECT {col} FROM articles LIMIT 1")
            except sqlite3.OperationalError:
                self._conn.execute(f"ALTER TABLE articles ADD COLUMN {col} TEXT DEFAULT ''")
                self._conn.commit()
                logger.info(f"[STORAGE] Migration: added {col} column to articles")

        # Migration: add domain column to earnings/SEC tables
        for table_name in ["earnings_transcripts", "earnings_quotes", "sec_filings", "sec_nuggets"]:
            try:
                self._conn.execute(f"SELECT domain FROM {table_name} LIMIT 1")
            except sqlite3.OperationalError:
                self._conn.execute(f"ALTER TABLE {table_name} ADD COLUMN domain TEXT DEFAULT 'quantum'")
                self._conn.commit()
                logger.info(f"[STORAGE] Migration: added domain column to {table_name}")

        for index_sql in ALL_INDEXES:
            self._conn.execute(index_sql)

        self._conn.commit()

        logger.info(f"[STORAGE] SQLite initialized: {self.db_path}")

    def _serialize_list(self, lst: Any) -> str:
        """Serialize a list to JSON string for storage."""
        if isinstance(lst, str):
            return lst
        return json.dumps(lst or [])

    def _deserialize_list(self, val: Any) -> List:
        """Deserialize JSON string to list."""
        if val is None:
            return []
        if isinstance(val, list):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []

    def _row_to_article(self, row: sqlite3.Row) -> ClassifiedArticle:
        """Convert a database row to ClassifiedArticle."""
        data = dict(row)
        for list_field in [
            "tags", "companies_mentioned", "technologies_mentioned",
            "people_mentioned", "use_case_domains", "duplicate_urls",
        ]:
            data[list_field] = self._deserialize_list(data.get(list_field))

        data["metadata"] = json.loads(data.get("metadata", "{}") or "{}")
        data["feed_eligible"] = bool(data.get("feed_eligible", 1))

        for dt_field in ["published_at", "fetched_at", "classified_at"]:
            val = data.get(dt_field)
            if val and isinstance(val, str):
                try:
                    data[dt_field] = datetime.fromisoformat(val)
                except ValueError:
                    data[dt_field] = None

        return ClassifiedArticle.from_dict(data)

    # =========================================================================
    # Article Operations
    # =========================================================================

    async def save_articles(self, articles: List[ClassifiedArticle]) -> int:
        """Save classified articles. Returns count saved."""
        saved = 0
        for article in articles:
            try:
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO articles (
                        id, url, title, source_name, source_url, source_type,
                        published_at, date_confidence, fetched_at,
                        summary, full_text, author, tags,
                        primary_category, priority, relevance_score,
                        ai_summary, key_takeaway,
                        companies_mentioned, technologies_mentioned,
                        people_mentioned, use_case_domains,
                        sentiment, confidence, time_to_market_impact,
                        disrupted_industries, investment_signal,
                        classifier_model, classified_at,
                        digest_priority, feed_eligible,
                        content_hash, coverage_count, duplicate_urls,
                        metadata, domain
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?
                    )""",
                    (
                        article.id, article.url, article.title,
                        article.source_name, article.source_url, article.source_type,
                        article.published_at.isoformat() if article.published_at else None,
                        article.date_confidence,
                        article.fetched_at.isoformat() if article.fetched_at else None,
                        article.summary, article.full_text, article.author,
                        self._serialize_list(article.tags),
                        article.primary_category, article.priority, article.relevance_score,
                        article.ai_summary, article.key_takeaway,
                        self._serialize_list(article.companies_mentioned),
                        self._serialize_list(article.technologies_mentioned),
                        self._serialize_list(article.people_mentioned),
                        self._serialize_list(article.use_case_domains),
                        article.sentiment, article.confidence,
                        article.time_to_market_impact,
                        article.disrupted_industries,
                        article.investment_signal,
                        article.classifier_model,
                        article.classified_at.isoformat() if article.classified_at else None,
                        article.digest_priority, int(article.feed_eligible),
                        article.content_hash, article.coverage_count,
                        self._serialize_list(article.duplicate_urls),
                        json.dumps(article.metadata or {}),
                        article.domain,
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
                else:
                    logger.debug(f"[STORAGE] Duplicate URL skipped: {article.url[:60]}")
            except Exception as e:
                logger.warning(f"[STORAGE] Save error: {e}")

        self._conn.commit()
        return saved

    async def get_article_by_url(self, url: str) -> Optional[ClassifiedArticle]:
        """Get a single article by URL."""
        cursor = self._conn.execute(
            "SELECT * FROM articles WHERE url = ?", (url,)
        )
        row = cursor.fetchone()
        return self._row_to_article(row) if row else None

    async def get_recent_articles(
        self, hours: int = 72, limit: int = 500, domain: Optional[str] = None
    ) -> List[ClassifiedArticle]:
        """Get articles from the last N hours. Optionally filter by domain."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        if domain:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE fetched_at >= ? AND domain = ? ORDER BY published_at DESC LIMIT ?",
                (cutoff, domain, limit),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE fetched_at >= ? ORDER BY published_at DESC LIMIT ?",
                (cutoff, limit),
            )
        return [self._row_to_article(row) for row in cursor.fetchall()]

    async def get_articles_by_category(
        self, category: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None
    ) -> List[ClassifiedArticle]:
        """Get articles by primary category. Optionally filter by domain."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        if domain:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE primary_category = ? AND fetched_at >= ? AND domain = ? "
                "ORDER BY published_at DESC LIMIT ?",
                (category, cutoff, domain, limit),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE primary_category = ? AND fetched_at >= ? "
                "ORDER BY published_at DESC LIMIT ?",
                (category, cutoff, limit),
            )
        return [self._row_to_article(row) for row in cursor.fetchall()]

    async def get_articles_by_priority(
        self, priority: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None
    ) -> List[ClassifiedArticle]:
        """Get articles by priority level. Optionally filter by domain."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        if domain:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE priority = ? AND fetched_at >= ? AND domain = ? "
                "ORDER BY relevance_score DESC LIMIT ?",
                (priority, cutoff, domain, limit),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM articles WHERE priority = ? AND fetched_at >= ? "
                "ORDER BY relevance_score DESC LIMIT ?",
                (priority, cutoff, limit),
            )
        return [self._row_to_article(row) for row in cursor.fetchall()]

    async def search_articles(
        self, query: str, hours: int = 168, limit: int = 50, domain: Optional[str] = None
    ) -> List[ClassifiedArticle]:
        """Search articles by text (title, summary, companies). Optionally filter by domain."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        pattern = f"%{query}%"
        if domain:
            cursor = self._conn.execute(
                """SELECT * FROM articles
                WHERE fetched_at >= ? AND domain = ?
                AND (title LIKE ? OR ai_summary LIKE ? OR companies_mentioned LIKE ?)
                ORDER BY relevance_score DESC LIMIT ?""",
                (cutoff, domain, pattern, pattern, pattern, limit),
            )
        else:
            cursor = self._conn.execute(
                """SELECT * FROM articles
                WHERE fetched_at >= ?
                AND (title LIKE ? OR ai_summary LIKE ? OR companies_mentioned LIKE ?)
                ORDER BY relevance_score DESC LIMIT ?""",
                (cutoff, pattern, pattern, pattern, limit),
            )
        return [self._row_to_article(row) for row in cursor.fetchall()]

    # =========================================================================
    # Deduplication Support
    # =========================================================================

    async def url_exists(self, url: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,)
        )
        return cursor.fetchone() is not None

    async def get_recent_urls(self, hours: int = 168) -> Set[str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cursor = self._conn.execute(
            "SELECT url FROM articles WHERE fetched_at >= ?", (cutoff,)
        )
        return {row["url"] for row in cursor.fetchall()}

    async def get_recent_titles(self, hours: int = 168) -> Dict[str, str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cursor = self._conn.execute(
            "SELECT title, url FROM articles WHERE fetched_at >= ?", (cutoff,)
        )
        return {row["title"]: row["url"] for row in cursor.fetchall()}

    async def get_recent_articles_for_dedup(
        self, hours: int = 168, limit: int = 5000
    ) -> List[Dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cursor = self._conn.execute(
            "SELECT id, url, title, content_hash FROM articles WHERE fetched_at >= ? LIMIT ?",
            (cutoff, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Digest Operations
    # =========================================================================

    async def save_digest(self, digest: Digest) -> str:
        self._conn.execute(
            """INSERT OR REPLACE INTO digests
            (id, created_at, period_hours, executive_summary, content,
             total_items, critical_count, high_count, medium_count, low_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                digest.id,
                digest.created_at.isoformat(),
                digest.period_hours,
                digest.executive_summary,
                json.dumps([
                    {
                        "id": item.id, "title": item.title,
                        "source_name": item.source_name, "url": item.url,
                        "summary": item.summary, "category": item.category,
                        "priority": item.priority.value if isinstance(item.priority, Priority) else item.priority,
                        "relevance_score": item.relevance_score,
                    }
                    for item in digest.items
                ]),
                digest.total_items,
                digest.critical_count,
                digest.high_count,
                digest.medium_count,
                digest.low_count,
            ),
        )
        self._conn.commit()
        return digest.id

    async def get_latest_digest(self) -> Optional[Digest]:
        cursor = self._conn.execute(
            "SELECT * FROM digests ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        items_data = json.loads(data.get("content", "[]") or "[]")
        items = [DigestItem(**item) for item in items_data]

        return Digest(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            period_hours=data["period_hours"],
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

    def _row_to_paper(self, row: sqlite3.Row) -> Paper:
        """Convert a database row to Paper."""
        data = dict(row)
        for list_field in ["authors", "categories"]:
            data[list_field] = self._deserialize_list(data.get(list_field))
        for dt_field in ["published_at", "updated_at", "ingested_at"]:
            val = data.get(dt_field)
            if val and isinstance(val, str):
                try:
                    data[dt_field] = datetime.fromisoformat(val)
                except ValueError:
                    data[dt_field] = None
        return Paper.from_dict(data)

    async def save_papers(self, papers: List[Paper]) -> int:
        """Save ArXiv papers. Returns count saved."""
        saved = 0
        for paper in papers:
            try:
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO papers (
                        arxiv_id, title, authors, abstract, categories,
                        published_at, updated_at, ingested_at, pdf_url,
                        relevance_score, paper_type, use_case_category,
                        commercial_readiness, significance_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        paper.arxiv_id, paper.title,
                        self._serialize_list(paper.authors),
                        paper.abstract,
                        self._serialize_list(paper.categories),
                        paper.published_at.isoformat() if paper.published_at else None,
                        paper.updated_at.isoformat() if paper.updated_at else None,
                        paper.ingested_at.isoformat() if paper.ingested_at else None,
                        paper.pdf_url,
                        paper.relevance_score, paper.paper_type,
                        paper.use_case_category, paper.commercial_readiness,
                        paper.significance_summary,
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
                else:
                    logger.debug(f"[STORAGE] Duplicate paper skipped: {paper.arxiv_id}")
            except Exception as e:
                logger.warning(f"[STORAGE] Paper save error: {e}")

        self._conn.commit()
        return saved

    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get a single paper by ArXiv ID."""
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        )
        row = cursor.fetchone()
        return self._row_to_paper(row) if row else None

    async def get_recent_papers(self, days: int = 7, limit: int = 50) -> List[Paper]:
        """Get recent papers, newest first."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = self._conn.execute(
            "SELECT * FROM papers WHERE ingested_at >= ? ORDER BY published_at DESC LIMIT ?",
            (cutoff, limit),
        )
        return [self._row_to_paper(row) for row in cursor.fetchall()]

    async def arxiv_id_exists(self, arxiv_id: str) -> bool:
        """Check if an ArXiv paper is already stored."""
        cursor = self._conn.execute(
            "SELECT 1 FROM papers WHERE arxiv_id = ? LIMIT 1", (arxiv_id,)
        )
        return cursor.fetchone() is not None

    # =========================================================================
    # Stock Operations
    # =========================================================================

    def _row_to_stock(self, row: sqlite3.Row) -> StockSnapshot:
        """Convert a database row to StockSnapshot."""
        return StockSnapshot.from_dict(dict(row))

    async def save_stock_data(self, snapshots: List[StockSnapshot]) -> int:
        """Save stock snapshots. Returns count saved (upserted)."""
        saved = 0
        for snapshot in snapshots:
            try:
                self._conn.execute(
                    """INSERT OR REPLACE INTO stocks (
                        ticker, date, open, high, low, close, volume,
                        change_percent, market_cap, sma_20, sma_50
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snapshot.ticker, snapshot.date,
                        snapshot.open, snapshot.high, snapshot.low,
                        snapshot.close, snapshot.volume,
                        snapshot.change_percent, snapshot.market_cap,
                        snapshot.sma_20, snapshot.sma_50,
                    ),
                )
                saved += 1
            except Exception as e:
                logger.warning(f"[STORAGE] Stock save error ({snapshot.ticker} {snapshot.date}): {e}")

        self._conn.commit()
        return saved

    async def get_stock_data(self, ticker: str, days: int = 30) -> List[StockSnapshot]:
        """Get stock history for a ticker."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor = self._conn.execute(
            "SELECT * FROM stocks WHERE ticker = ? AND date >= ? ORDER BY date DESC",
            (ticker, cutoff),
        )
        return [self._row_to_stock(row) for row in cursor.fetchall()]

    async def get_latest_stock_data(self, tickers: Optional[List[str]] = None) -> List[StockSnapshot]:
        """Get most recent data point for each ticker."""
        if tickers:
            placeholders = ",".join("?" for _ in tickers)
            cursor = self._conn.execute(
                f"""SELECT s.* FROM stocks s
                INNER JOIN (
                    SELECT ticker, MAX(date) as max_date
                    FROM stocks WHERE ticker IN ({placeholders})
                    GROUP BY ticker
                ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date""",
                tuple(tickers),
            )
        else:
            cursor = self._conn.execute(
                """SELECT s.* FROM stocks s
                INNER JOIN (
                    SELECT ticker, MAX(date) as max_date
                    FROM stocks GROUP BY ticker
                ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date"""
            )
        return [self._row_to_stock(row) for row in cursor.fetchall()]

    # =========================================================================
    # Stats
    # =========================================================================

    async def get_article_count(self, hours: int = 24) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cursor = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM articles WHERE fetched_at >= ?", (cutoff,)
        )
        return cursor.fetchone()["cnt"]

    async def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Total count
        total = await self.get_article_count(hours)

        # By category
        cursor = self._conn.execute(
            "SELECT primary_category, COUNT(*) as cnt FROM articles "
            "WHERE fetched_at >= ? GROUP BY primary_category ORDER BY cnt DESC",
            (cutoff,),
        )
        by_category = {row["primary_category"]: row["cnt"] for row in cursor.fetchall()}

        # By priority
        cursor = self._conn.execute(
            "SELECT priority, COUNT(*) as cnt FROM articles "
            "WHERE fetched_at >= ? GROUP BY priority",
            (cutoff,),
        )
        by_priority = {row["priority"]: row["cnt"] for row in cursor.fetchall()}

        # By source type
        cursor = self._conn.execute(
            "SELECT source_type, COUNT(*) as cnt FROM articles "
            "WHERE fetched_at >= ? GROUP BY source_type",
            (cutoff,),
        )
        by_source = {row["source_type"]: row["cnt"] for row in cursor.fetchall()}

        # Average relevance
        cursor = self._conn.execute(
            "SELECT AVG(relevance_score) as avg_rel FROM articles WHERE fetched_at >= ?",
            (cutoff,),
        )
        avg_relevance = cursor.fetchone()["avg_rel"] or 0.0

        return {
            "total_articles": total,
            "by_category": by_category,
            "by_priority": by_priority,
            "by_source": by_source,
            "avg_relevance": round(avg_relevance, 3),
            "hours": hours,
        }

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("[STORAGE] SQLite connection closed")

    # =========================================================================
    # Earnings Operations (Phase 4A)
    # =========================================================================

    async def save_transcript(self, transcript: EarningsTranscript) -> str:
        """Save an earnings transcript. Returns transcript_id."""
        try:
            self._conn.execute(
                """INSERT OR IGNORE INTO earnings_transcripts (
                    transcript_id, ticker, company_name, year, quarter,
                    transcript_text, call_date, participants, fiscal_period,
                    ingested_at, char_count, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    transcript.transcript_id, transcript.ticker,
                    transcript.company_name, transcript.year, transcript.quarter,
                    transcript.transcript_text,
                    transcript.call_date.isoformat() if transcript.call_date else None,
                    json.dumps(transcript.participants),
                    transcript.fiscal_period,
                    transcript.ingested_at.isoformat(),
                    transcript.char_count,
                    getattr(transcript, 'domain', 'quantum'),
                ),
            )
            self._conn.commit()
            logger.info(f"[EARNINGS] Saved transcript: {transcript.unique_key}")
            return transcript.transcript_id
        except Exception as e:
            logger.warning(f"[EARNINGS] Transcript save error: {e}")
            return transcript.transcript_id

    async def transcript_exists(self, ticker: str, year: int, quarter: int) -> bool:
        """Check if transcript already stored."""
        cursor = self._conn.execute(
            "SELECT 1 FROM earnings_transcripts WHERE ticker = ? AND year = ? AND quarter = ? LIMIT 1",
            (ticker, year, quarter),
        )
        return cursor.fetchone() is not None

    async def save_quotes(self, quotes: List[ExtractedQuote]) -> int:
        """Save extracted earnings quotes. Returns count saved."""
        saved = 0
        for quote in quotes:
            try:
                data = quote.to_dict()
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO earnings_quotes (
                        quote_id, transcript_id, quote_text, context_before, context_after,
                        speaker_name, speaker_role, speaker_title, speaker_company, speaker_firm,
                        quote_type, themes, sentiment, confidence_level,
                        companies_mentioned, technologies_mentioned,
                        competitors_mentioned, metrics_mentioned,
                        relevance_score, is_quotable, quotability_reason,
                        ticker, company_name, year, quarter, call_date,
                        section, position_in_section,
                        extracted_at, extraction_model, extraction_confidence,
                        domain
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?
                    )""",
                    (
                        data["quote_id"], data["transcript_id"],
                        data["quote_text"], data["context_before"], data["context_after"],
                        data["speaker_name"], data["speaker_role"],
                        data["speaker_title"], data["speaker_company"], data["speaker_firm"],
                        data["quote_type"], data["themes"], data["sentiment"],
                        data["confidence_level"],
                        data["companies_mentioned"], data["technologies_mentioned"],
                        data["competitors_mentioned"], data["metrics_mentioned"],
                        data["relevance_score"], int(data["is_quotable"]),
                        data["quotability_reason"],
                        data["ticker"], data["company_name"],
                        data["year"], data["quarter"], data["call_date"],
                        data["section"], data["position_in_section"],
                        data["extracted_at"], data["extraction_model"],
                        data["extraction_confidence"],
                        data.get("domain", "quantum"),
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.warning(f"[EARNINGS] Quote save error: {e}")

        self._conn.commit()
        return saved

    async def get_quotes_by_ticker(
        self, ticker: str, limit: int = 50
    ) -> List[ExtractedQuote]:
        """Get quotes for a specific ticker."""
        cursor = self._conn.execute(
            "SELECT * FROM earnings_quotes WHERE ticker = ? ORDER BY relevance_score DESC LIMIT ?",
            (ticker, limit),
        )
        return [ExtractedQuote.from_dict(dict(row)) for row in cursor.fetchall()]

    async def get_transcripts_without_quotes(
        self, tickers: Optional[List[str]] = None
    ) -> List[EarningsTranscript]:
        """Get transcripts that have no extracted quotes yet."""
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            cursor = self._conn.execute(
                f"""SELECT t.* FROM earnings_transcripts t
                    LEFT JOIN earnings_quotes q ON t.transcript_id = q.transcript_id
                    WHERE q.quote_id IS NULL AND t.ticker IN ({placeholders})
                    ORDER BY t.ticker, t.year DESC, t.quarter DESC""",
                tickers,
            )
        else:
            cursor = self._conn.execute(
                """SELECT t.* FROM earnings_transcripts t
                   LEFT JOIN earnings_quotes q ON t.transcript_id = q.transcript_id
                   WHERE q.quote_id IS NULL
                   ORDER BY t.ticker, t.year DESC, t.quarter DESC"""
            )
        return [EarningsTranscript.from_dict(dict(row)) for row in cursor.fetchall()]

    # =========================================================================
    # SEC Operations (Phase 4A)
    # =========================================================================

    async def get_filings_without_nuggets(
        self, tickers: Optional[List[str]] = None
    ) -> List[SecFiling]:
        """Get filings that have no extracted nuggets yet."""
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            cursor = self._conn.execute(
                f"""SELECT f.* FROM sec_filings f
                    LEFT JOIN sec_nuggets n ON f.filing_id = n.filing_id
                    WHERE n.nugget_id IS NULL AND f.ticker IN ({placeholders})
                    ORDER BY f.ticker, f.filing_date DESC""",
                tickers,
            )
        else:
            cursor = self._conn.execute(
                """SELECT f.* FROM sec_filings f
                   LEFT JOIN sec_nuggets n ON f.filing_id = n.filing_id
                   WHERE n.nugget_id IS NULL
                   ORDER BY f.ticker, f.filing_date DESC"""
            )
        return [SecFiling.from_dict(dict(row)) for row in cursor.fetchall()]

    async def save_filing(self, filing: SecFiling) -> str:
        """Save an SEC filing. Returns filing_id."""
        try:
            self._conn.execute(
                """INSERT OR IGNORE INTO sec_filings (
                    filing_id, ticker, company_name, cik,
                    accession_number, filing_type, filing_date,
                    fiscal_year, fiscal_quarter,
                    primary_document, filing_url, raw_content, sections,
                    ingested_at, char_count, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    filing.filing_id, filing.ticker,
                    filing.company_name, filing.cik,
                    filing.accession_number, filing.filing_type,
                    filing.filing_date.isoformat() if filing.filing_date else None,
                    filing.fiscal_year, filing.fiscal_quarter,
                    filing.primary_document, filing.filing_url,
                    filing.raw_content,
                    json.dumps(filing.sections) if filing.sections else None,
                    filing.ingested_at.isoformat(),
                    filing.char_count,
                    getattr(filing, 'domain', 'quantum'),
                ),
            )
            self._conn.commit()
            logger.info(f"[SEC] Saved filing: {filing.unique_key}")
            return filing.filing_id
        except Exception as e:
            logger.warning(f"[SEC] Filing save error: {e}")
            return filing.filing_id

    async def filing_exists(
        self, ticker: str, filing_type: str, fiscal_year: int, fiscal_quarter: int = None
    ) -> bool:
        """Check if filing already stored."""
        if fiscal_quarter is not None:
            cursor = self._conn.execute(
                "SELECT 1 FROM sec_filings WHERE ticker = ? AND filing_type = ? "
                "AND fiscal_year = ? AND fiscal_quarter = ? LIMIT 1",
                (ticker, filing_type, fiscal_year, fiscal_quarter),
            )
        else:
            cursor = self._conn.execute(
                "SELECT 1 FROM sec_filings WHERE ticker = ? AND filing_type = ? "
                "AND fiscal_year = ? AND fiscal_quarter IS NULL LIMIT 1",
                (ticker, filing_type, fiscal_year),
            )
        return cursor.fetchone() is not None

    async def save_nuggets(self, nuggets: List[SecNugget]) -> int:
        """Save extracted SEC nuggets. Returns count saved."""
        saved = 0
        for nugget in nuggets:
            try:
                data = nugget.to_dict()
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO sec_nuggets (
                        nugget_id, filing_id, nugget_text, context_text,
                        filing_type, section,
                        nugget_type, themes, signal_strength,
                        companies_mentioned, technologies_mentioned,
                        competitors_named, regulators_mentioned,
                        risk_level, is_new_disclosure, is_actionable,
                        actionability_reason,
                        relevance_score,
                        ticker, company_name, cik,
                        fiscal_year, fiscal_quarter,
                        filing_date, accession_number,
                        extracted_at, extraction_model, extraction_confidence,
                        domain
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?,
                        ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?
                    )""",
                    (
                        data["nugget_id"], data["filing_id"],
                        data["nugget_text"], data["context_text"],
                        data["filing_type"], data["section"],
                        data["nugget_type"], data["themes"], data["signal_strength"],
                        data["companies_mentioned"], data["technologies_mentioned"],
                        data["competitors_named"], data["regulators_mentioned"],
                        data["risk_level"], int(data["is_new_disclosure"]),
                        int(data["is_actionable"]),
                        data["actionability_reason"],
                        data["relevance_score"],
                        data["ticker"], data["company_name"], data["cik"],
                        data["fiscal_year"], data["fiscal_quarter"],
                        data["filing_date"], data["accession_number"],
                        data["extracted_at"], data["extraction_model"],
                        data["extraction_confidence"],
                        data.get("domain", "quantum"),
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.warning(f"[SEC] Nugget save error: {e}")

        self._conn.commit()
        return saved

    async def get_nuggets_by_ticker(
        self, ticker: str, limit: int = 50
    ) -> List[SecNugget]:
        """Get nuggets for a specific ticker."""
        cursor = self._conn.execute(
            "SELECT * FROM sec_nuggets WHERE ticker = ? ORDER BY relevance_score DESC LIMIT ?",
            (ticker, limit),
        )
        return [SecNugget.from_dict(dict(row)) for row in cursor.fetchall()]

    # =========================================================================
    # Podcast Operations (Phase 4B)
    # =========================================================================

    async def save_podcast_transcript(self, transcript: PodcastTranscript) -> str:
        """Save a podcast transcript. Returns transcript_id."""
        try:
            self._conn.execute(
                """INSERT OR IGNORE INTO podcast_transcripts (
                    transcript_id, episode_id, podcast_id, podcast_name,
                    episode_title, episode_url, audio_url,
                    full_text, formatted_text, char_count, word_count,
                    duration_seconds,
                    hosts, guest_name, guest_title, guest_company, speaker_count,
                    transcript_source, status, published_at,
                    ingested_at, transcribed_at, transcription_cost_usd
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )""",
                (
                    transcript.transcript_id, transcript.episode_id,
                    transcript.podcast_id, transcript.podcast_name,
                    transcript.episode_title, transcript.episode_url,
                    transcript.audio_url,
                    transcript.full_text, transcript.formatted_text,
                    transcript.char_count, transcript.word_count,
                    transcript.duration_seconds,
                    json.dumps(transcript.hosts or []),
                    transcript.guest_name, transcript.guest_title,
                    transcript.guest_company, transcript.speaker_count,
                    transcript.transcript_source,
                    transcript.status.value if hasattr(transcript.status, 'value') else transcript.status,
                    transcript.published_at.isoformat() if isinstance(transcript.published_at, datetime) else transcript.published_at,
                    transcript.ingested_at.isoformat() if isinstance(transcript.ingested_at, datetime) else transcript.ingested_at,
                    transcript.transcribed_at.isoformat() if isinstance(transcript.transcribed_at, datetime) else transcript.transcribed_at,
                    transcript.transcription_cost_usd,
                ),
            )
            self._conn.commit()
            logger.info(f"[PODCAST] Saved transcript: {transcript.podcast_name} — {transcript.episode_title}")
            return transcript.transcript_id
        except Exception as e:
            logger.warning(f"[PODCAST] Transcript save error: {e}")
            return transcript.transcript_id

    async def podcast_episode_exists(self, podcast_id: str, episode_id: str) -> bool:
        """Check if a podcast episode transcript is already stored."""
        cursor = self._conn.execute(
            "SELECT 1 FROM podcast_transcripts WHERE podcast_id = ? AND episode_id = ? LIMIT 1",
            (podcast_id, episode_id),
        )
        return cursor.fetchone() is not None

    async def save_podcast_quotes(self, quotes: List[PodcastQuote]) -> int:
        """Save extracted podcast quotes. Returns count saved."""
        saved = 0
        for quote in quotes:
            try:
                data = quote.to_dict()
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO podcast_quotes (
                        quote_id, transcript_id, episode_id,
                        quote_text, context_before, context_after,
                        speaker_name, speaker_role, speaker_title, speaker_company,
                        quote_type, themes, sentiment,
                        companies_mentioned, technologies_mentioned, people_mentioned,
                        relevance_score, is_quotable, quotability_reason,
                        podcast_id, podcast_name, episode_title, published_at,
                        extracted_at, extraction_model, extraction_confidence
                    ) VALUES (
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?
                    )""",
                    (
                        data["quote_id"], data["transcript_id"], data["episode_id"],
                        data["quote_text"], data["context_before"], data["context_after"],
                        data["speaker_name"], data["speaker_role"],
                        data["speaker_title"], data["speaker_company"],
                        data["quote_type"], data["themes"], data["sentiment"],
                        data["companies_mentioned"], data["technologies_mentioned"],
                        data["people_mentioned"],
                        data["relevance_score"], int(data["is_quotable"]),
                        data["quotability_reason"],
                        data["podcast_id"], data["podcast_name"],
                        data["episode_title"], data["published_at"],
                        data["extracted_at"], data["extraction_model"],
                        data["extraction_confidence"],
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.warning(f"[PODCAST] Quote save error: {e}")

        self._conn.commit()
        return saved

    async def get_podcast_quotes(
        self, podcast_id: Optional[str] = None, limit: int = 50
    ) -> List[PodcastQuote]:
        """Get podcast quotes, optionally filtered by podcast."""
        if podcast_id:
            cursor = self._conn.execute(
                "SELECT * FROM podcast_quotes WHERE podcast_id = ? "
                "ORDER BY relevance_score DESC LIMIT ?",
                (podcast_id, limit),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM podcast_quotes ORDER BY relevance_score DESC LIMIT ?",
                (limit,),
            )
        return [PodcastQuote.from_dict(dict(row)) for row in cursor.fetchall()]

    async def search_podcast_quotes(
        self, query: str, limit: int = 30
    ) -> List[PodcastQuote]:
        """Search podcast quotes by text (quote text, speaker, themes, companies)."""
        pattern = f"%{query}%"
        cursor = self._conn.execute(
            """SELECT * FROM podcast_quotes
            WHERE quote_text LIKE ? OR speaker_name LIKE ?
            OR themes LIKE ? OR companies_mentioned LIKE ?
            OR technologies_mentioned LIKE ?
            ORDER BY relevance_score DESC LIMIT ?""",
            (pattern, pattern, pattern, pattern, pattern, limit),
        )
        return [PodcastQuote.from_dict(dict(row)) for row in cursor.fetchall()]

    # =========================================================================
    # Weekly Briefing Operations
    # =========================================================================

    async def save_weekly_briefing(self, briefing: WeeklyBriefing) -> str:
        """Save a weekly briefing. INSERT OR REPLACE allows re-runs for same week."""
        try:
            self._conn.execute(
                """INSERT OR REPLACE INTO weekly_briefings (
                    id, domain, week_of, created_at,
                    sections, market_movers, research_papers,
                    articles_analyzed, sections_active, sections_total,
                    generation_cost_usd, pre_brief_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    briefing.id,
                    briefing.domain,
                    briefing.week_of,
                    briefing.created_at.isoformat(),
                    json.dumps([s.to_dict() for s in briefing.sections]),
                    json.dumps([m.to_dict() for m in briefing.market_movers]),
                    json.dumps([p.to_dict() for p in briefing.research_papers]),
                    briefing.articles_analyzed,
                    briefing.sections_active,
                    briefing.sections_total,
                    briefing.generation_cost_usd,
                    briefing.pre_brief_id,
                ),
            )
            self._conn.commit()
            logger.info(f"[STORAGE] Saved weekly briefing: {briefing.domain} week_of={briefing.week_of}")
            return briefing.id
        except Exception as e:
            logger.warning(f"[STORAGE] Weekly briefing save error: {e}")
            return briefing.id

    async def get_latest_weekly_briefing(self, domain: str = "quantum") -> Optional[WeeklyBriefing]:
        """Get the most recent weekly briefing for a domain."""
        cursor = self._conn.execute(
            "SELECT * FROM weekly_briefings WHERE domain = ? ORDER BY created_at DESC LIMIT 1",
            (domain,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_weekly_briefing(row)

    async def get_weekly_briefing_by_week(self, domain: str, week_of: str) -> Optional[WeeklyBriefing]:
        """Get a specific week's briefing."""
        cursor = self._conn.execute(
            "SELECT * FROM weekly_briefings WHERE domain = ? AND week_of = ? LIMIT 1",
            (domain, week_of),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_weekly_briefing(row)

    def _row_to_weekly_briefing(self, row: sqlite3.Row) -> WeeklyBriefing:
        """Convert a database row to WeeklyBriefing."""
        data = dict(row)
        sections = [BriefingSection.from_dict(s) for s in json.loads(data.get("sections", "[]") or "[]")]
        market_movers = [MarketMover.from_dict(m) for m in json.loads(data.get("market_movers", "[]") or "[]")]
        research_papers = [ResearchPaper.from_dict(p) for p in json.loads(data.get("research_papers", "[]") or "[]")]
        return WeeklyBriefing(
            id=data["id"],
            domain=data["domain"],
            week_of=data["week_of"],
            created_at=datetime.fromisoformat(data["created_at"]),
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
        saved = 0
        for cs in case_studies:
            try:
                data = cs.to_dict()
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO case_studies (
                        case_study_id, source_type, source_id, domain,
                        grounding_quote, context_text,
                        use_case_title, use_case_summary, company, industry,
                        technology_stack,
                        department, implementation_detail, teams_impacted,
                        scale, timeline, readiness_level,
                        outcome_metric, outcome_type, outcome_quantified,
                        speaker, speaker_role, speaker_company,
                        companies_mentioned, technologies_mentioned,
                        people_mentioned, competitors_mentioned,
                        qubit_type, gate_fidelity, commercial_viability,
                        scientific_significance,
                        ai_model_used, roi_metric, deployment_type,
                        relevance_score, confidence,
                        metadata,
                        extracted_at, extraction_model, extraction_confidence
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?,
                        ?, ?, ?,
                        ?, ?,
                        ?,
                        ?, ?, ?
                    )""",
                    (
                        data["case_study_id"], data["source_type"],
                        data["source_id"], data["domain"],
                        data["grounding_quote"], data["context_text"],
                        data["use_case_title"], data["use_case_summary"],
                        data["company"], data["industry"],
                        data["technology_stack"],
                        data["department"], data["implementation_detail"],
                        data["teams_impacted"],
                        data["scale"], data["timeline"], data["readiness_level"],
                        data["outcome_metric"], data["outcome_type"],
                        int(data["outcome_quantified"]),
                        data["speaker"], data["speaker_role"], data["speaker_company"],
                        data["companies_mentioned"], data["technologies_mentioned"],
                        data["people_mentioned"], data["competitors_mentioned"],
                        data["qubit_type"], data["gate_fidelity"],
                        data["commercial_viability"],
                        data["scientific_significance"],
                        data["ai_model_used"], data["roi_metric"],
                        data["deployment_type"],
                        data["relevance_score"], data["confidence"],
                        data["metadata"],
                        data["extracted_at"], data["extraction_model"],
                        data["extraction_confidence"],
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.warning(f"[CASE_STUDY] Save error: {e}")

        self._conn.commit()
        return saved

    async def get_case_studies_by_source(
        self, source_type: str, source_id: str
    ) -> List[CaseStudy]:
        """Get case studies for a specific source item."""
        cursor = self._conn.execute(
            "SELECT * FROM case_studies WHERE source_type = ? AND source_id = ? "
            "ORDER BY relevance_score DESC",
            (source_type, source_id),
        )
        return [CaseStudy.from_dict(dict(row)) for row in cursor.fetchall()]

    async def get_case_studies(
        self,
        domain: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[CaseStudy]:
        """Get case studies with optional filters."""
        where_parts = []
        params: list = []

        if domain:
            where_parts.append("domain = ?")
            params.append(domain)
        if company:
            where_parts.append("company = ?")
            params.append(company)
        if industry:
            where_parts.append("industry = ?")
            params.append(industry)
        if source_type:
            where_parts.append("source_type = ?")
            params.append(source_type)

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        params.append(limit)

        cursor = self._conn.execute(
            f"SELECT * FROM case_studies WHERE {where_clause} "
            f"ORDER BY relevance_score DESC LIMIT ?",
            params,
        )
        return [CaseStudy.from_dict(dict(row)) for row in cursor.fetchall()]

    async def case_studies_exist_for_source(
        self, source_type: str, source_id: str
    ) -> bool:
        """Check if case studies already extracted for this source."""
        cursor = self._conn.execute(
            "SELECT 1 FROM case_studies WHERE source_type = ? AND source_id = ? LIMIT 1",
            (source_type, source_id),
        )
        return cursor.fetchone() is not None

    async def search_case_studies(
        self, query: str, domain: Optional[str] = None, limit: int = 30
    ) -> List[CaseStudy]:
        """Search case studies by text."""
        search_pattern = f"%{query}%"
        params: list = [search_pattern, search_pattern, search_pattern, search_pattern]
        domain_filter = ""
        if domain:
            domain_filter = " AND domain = ?"
            params.append(domain)
        params.append(limit)

        cursor = self._conn.execute(
            f"""SELECT * FROM case_studies
                WHERE (use_case_title LIKE ? OR use_case_summary LIKE ?
                       OR grounding_quote LIKE ? OR company LIKE ?)
                {domain_filter}
                ORDER BY relevance_score DESC LIMIT ?""",
            params,
        )
        return [CaseStudy.from_dict(dict(row)) for row in cursor.fetchall()]

    # =========================================================================
    # Funding Event Operations (Phase 3)
    # =========================================================================

    async def save_funding_events(self, events: List["FundingEvent"]) -> int:
        """Save extracted funding events. Returns count saved."""
        saved = 0
        for event in events:
            try:
                # Assuming the dataclass has a to_dict method, or doing it manually:
                from dataclasses import asdict
                data = asdict(event)
                
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO funding_events (
                        id, article_id, article_url, domain,
                        startup_name, funding_round, funding_amount, valuation,
                        lead_investors, other_investors,
                        investment_thesis, known_technologies, use_of_funds,
                        extracted_at, confidence_score, grounding_quote
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?, ?
                    )""",
                    (
                        data["id"], data["article_id"], data["article_url"], data["domain"],
                        data["startup_name"], data["funding_round"], data["funding_amount"], data["valuation"],
                        self._serialize_list(data["lead_investors"]),
                        self._serialize_list(data["other_investors"]),
                        data["investment_thesis"],
                        self._serialize_list(data["known_technologies"]),
                        data["use_of_funds"],
                        data["extracted_at"].isoformat() if isinstance(data["extracted_at"], datetime) else data["extracted_at"],
                        data["confidence_score"], data["grounding_quote"],
                    ),
                )
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.warning(f"[FUNDING_EVENT] Save error: {e}")

        self._conn.commit()
        return saved

    async def get_funding_events(
        self, domain: Optional[str] = None, limit: int = 50
    ) -> List[Any]:
        """Get funding events, optionally filtered by domain."""
        from models.funding import FundingEvent
        if domain:
            cursor = self._conn.execute(
                "SELECT * FROM funding_events WHERE domain = ? ORDER BY extracted_at DESC LIMIT ?",
                (domain, limit),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM funding_events ORDER BY extracted_at DESC LIMIT ?",
                (limit,),
            )
        
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            data["lead_investors"] = self._deserialize_list(data["lead_investors"])
            data["other_investors"] = self._deserialize_list(data["other_investors"])
            data["known_technologies"] = self._deserialize_list(data["known_technologies"])
            if data["extracted_at"] and isinstance(data["extracted_at"], str):
                try:
                    data["extracted_at"] = datetime.fromisoformat(data["extracted_at"])
                except ValueError:
                    data["extracted_at"] = None
            results.append(FundingEvent(**data))
        return results

    async def funding_events_exist_for_article(self, article_id: str) -> bool:
        """Check if funding events were already extracted for this article."""
        cursor = self._conn.execute(
            "SELECT 1 FROM funding_events WHERE article_id = ? LIMIT 1",
            (article_id,),
        )
        return cursor.fetchone() is not None
