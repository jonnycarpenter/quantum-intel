"""
Test BigQuery Storage Backend
==============================

Mock-based tests for BigQueryStorage. All GCP calls are mocked —
no credentials or project needed to run these tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from storage.base import ClassifiedArticle
from models.paper import Paper
from models.stock import StockSnapshot
from models.earnings import EarningsTranscript, ExtractedQuote
from models.sec_filing import SecFiling, SecNugget
from models.case_study import CaseStudy


# =============================================================================
# Fixtures — create a BigQueryStorage without hitting real GCP
# =============================================================================

def _make_bq_storage():
    """Create a BigQueryStorage instance with fully mocked GCP client."""
    from storage.bigquery import BigQueryStorage

    # Bypass __init__ to avoid real GCP calls
    instance = object.__new__(BigQueryStorage)
    instance.project_id = "test-project"
    instance.dataset_id = "test_dataset"
    instance.location = "us-central1"
    instance.full_dataset = "test-project.test_dataset"
    instance.client = MagicMock()
    return instance


@pytest.fixture
def bq_storage():
    """BigQueryStorage with mocked client."""
    with patch("storage.bigquery.bigquery"):
        return _make_bq_storage()


# =============================================================================
# Helpers
# =============================================================================

def make_article(**kwargs) -> ClassifiedArticle:
    """Helper to create test articles."""
    defaults = {
        "url": f"https://example.com/{kwargs.get('id', 'test')}",
        "title": "Test Quantum Article",
        "source_name": "Test Source",
        "primary_category": "hardware_milestone",
        "priority": "high",
        "relevance_score": 0.8,
        "ai_summary": "A test article about quantum computing.",
    }
    defaults.update(kwargs)
    return ClassifiedArticle(**defaults)


def make_paper(**kwargs) -> Paper:
    """Helper to create test papers."""
    defaults = {
        "arxiv_id": kwargs.get("arxiv_id", "2301.12345"),
        "title": "Quantum Error Correction via Surface Codes",
        "authors": ["Alice Smith", "Bob Jones"],
        "abstract": "A novel approach to quantum error correction.",
        "categories": ["quant-ph", "cs.ET"],
        "published_at": datetime(2025, 1, 15, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    return Paper(**defaults)


def make_stock(**kwargs) -> StockSnapshot:
    """Helper to create test stock snapshots."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    defaults = {
        "ticker": "IONQ",
        "date": today,
        "open": 12.50,
        "high": 13.00,
        "low": 12.25,
        "close": 12.75,
        "volume": 1500000,
        "change_percent": 2.0,
        "market_cap": 3500000000.0,
        "sma_20": 12.30,
        "sma_50": 11.80,
    }
    defaults.update(kwargs)
    return StockSnapshot(**defaults)


# =============================================================================
# Helper method tests
# =============================================================================

class TestHelperMethods:
    """Test internal utility methods on BigQueryStorage."""

    def test_ensure_list_none(self, bq_storage):
        assert bq_storage._ensure_list(None) == []

    def test_ensure_list_already_list(self, bq_storage):
        assert bq_storage._ensure_list(["a", "b"]) == ["a", "b"]

    def test_ensure_list_json_string(self, bq_storage):
        assert bq_storage._ensure_list('["a", "b"]') == ["a", "b"]

    def test_ensure_list_plain_string(self, bq_storage):
        assert bq_storage._ensure_list("hello") == ["hello"]

    def test_ensure_list_empty_string(self, bq_storage):
        assert bq_storage._ensure_list("") == []

    def test_dt_to_iso_none(self, bq_storage):
        assert bq_storage._dt_to_iso(None) is None

    def test_dt_to_iso_datetime(self, bq_storage):
        dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = bq_storage._dt_to_iso(dt)
        assert "2025-06-15" in result

    def test_dt_to_iso_string_passthrough(self, bq_storage):
        assert bq_storage._dt_to_iso("2025-06-15T00:00:00") == "2025-06-15T00:00:00"

    def test_dt_to_iso_int_returns_none(self, bq_storage):
        assert bq_storage._dt_to_iso(12345) is None

    def test_parse_dt_none(self, bq_storage):
        assert bq_storage._parse_dt(None) is None

    def test_parse_dt_datetime(self, bq_storage):
        dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
        assert bq_storage._parse_dt(dt) == dt

    def test_parse_dt_iso_string(self, bq_storage):
        result = bq_storage._parse_dt("2025-06-15T12:00:00+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_parse_dt_invalid_string(self, bq_storage):
        assert bq_storage._parse_dt("not-a-date") is None

    def test_table_fully_qualified(self, bq_storage):
        assert bq_storage._table("articles") == "`test-project.test_dataset.articles`"

    def test_cutoff_timestamp(self, bq_storage):
        result = bq_storage._cutoff_timestamp(24)
        # Should be roughly 24 hours ago in ISO format
        assert "T" in result

    def test_cutoff_days(self, bq_storage):
        result = bq_storage._cutoff_days(7)
        # Should be a YYYY-MM-DD string
        assert len(result) == 10
        assert "-" in result


# =============================================================================
# Row conversion tests
# =============================================================================

class TestRowConversion:
    """Test BQ row → model object conversion."""

    def test_row_to_article(self, bq_storage):
        """Verify BigQuery row dict converts to ClassifiedArticle."""
        row = {
            "id": "test-id",
            "url": "https://example.com/test",
            "title": "Quantum Breakthrough",
            "source_name": "Nature",
            "source_url": "https://nature.com",
            "source_type": "rss",
            "published_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "date_confidence": "high",
            "fetched_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "summary": "A summary",
            "full_text": "Full article text",
            "author": "Dr. Smith",
            "tags": ["quantum", "hardware"],
            "primary_category": "hardware_milestone",
            "priority": "critical",
            "relevance_score": 0.95,
            "ai_summary": "An AI summary",
            "key_takeaway": "Big deal",
            "companies_mentioned": ["IonQ"],
            "technologies_mentioned": ["trapped ion"],
            "people_mentioned": ["Dr. Smith"],
            "use_case_domains": ["computing"],
            "sentiment": "positive",
            "confidence": 0.9,
            "classifier_model": "claude-3.5-sonnet",
            "classified_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "digest_priority": "high",
            "feed_eligible": True,
            "content_hash": "abc123",
            "coverage_count": 1,
            "duplicate_urls": [],
            "metadata": "{}",
            "domain": "quantum",
        }
        article = bq_storage._row_to_article(row)
        assert isinstance(article, ClassifiedArticle)
        assert article.title == "Quantum Breakthrough"
        assert article.primary_category == "hardware_milestone"
        assert article.companies_mentioned == ["IonQ"]
        assert article.domain == "quantum"

    def test_row_to_article_json_metadata(self, bq_storage):
        """Verify JSON string metadata is parsed."""
        row = {
            "id": "test-id",
            "url": "https://example.com/test",
            "title": "Test",
            "source_name": "Test",
            "source_url": "",
            "source_type": "rss",
            "published_at": None,
            "date_confidence": None,
            "fetched_at": datetime.now(timezone.utc),
            "summary": "",
            "full_text": "",
            "author": "",
            "tags": None,
            "primary_category": "other",
            "priority": "low",
            "relevance_score": 0.5,
            "ai_summary": "",
            "key_takeaway": "",
            "companies_mentioned": None,
            "technologies_mentioned": None,
            "people_mentioned": None,
            "use_case_domains": None,
            "sentiment": "neutral",
            "confidence": 0.5,
            "classifier_model": "",
            "classified_at": None,
            "digest_priority": None,
            "feed_eligible": None,
            "content_hash": "",
            "coverage_count": 0,
            "duplicate_urls": None,
            "metadata": json.dumps({"source": "test"}),
            "domain": "ai",
        }
        article = bq_storage._row_to_article(row)
        assert article.metadata == {"source": "test"}


# =============================================================================
# Article operation tests
# =============================================================================

class TestArticleOperations:
    """Test article save/get with mocked BQ client."""

    @pytest.mark.asyncio
    async def test_save_articles_empty(self, bq_storage):
        """Saving empty list returns 0 without BQ calls."""
        result = await bq_storage.save_articles([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_articles_calls_merge(self, bq_storage):
        """save_articles should call _merge_rows with correct args."""
        article = make_article(id="art-1")
        bq_storage._merge_rows = AsyncMock(return_value=1)

        result = await bq_storage.save_articles([article])
        assert result == 1
        bq_storage._merge_rows.assert_called_once()
        call_args = bq_storage._merge_rows.call_args
        assert call_args[0][0] == "articles"  # table name
        assert call_args[1]["merge_key"] == "url"

    @pytest.mark.asyncio
    async def test_get_article_by_url_found(self, bq_storage):
        """get_article_by_url returns article when row exists."""
        mock_row = {
            "id": "found-id",
            "url": "https://example.com/found",
            "title": "Found Article",
            "source_name": "Test",
            "source_url": "",
            "source_type": "rss",
            "published_at": datetime.now(timezone.utc),
            "date_confidence": "high",
            "fetched_at": datetime.now(timezone.utc),
            "summary": "",
            "full_text": "",
            "author": "",
            "tags": [],
            "primary_category": "hardware_milestone",
            "priority": "high",
            "relevance_score": 0.8,
            "ai_summary": "Summary",
            "key_takeaway": "",
            "companies_mentioned": [],
            "technologies_mentioned": [],
            "people_mentioned": [],
            "use_case_domains": [],
            "sentiment": "neutral",
            "confidence": 0.8,
            "classifier_model": "claude",
            "classified_at": None,
            "digest_priority": None,
            "feed_eligible": True,
            "content_hash": "",
            "coverage_count": 0,
            "duplicate_urls": [],
            "metadata": "{}",
            "domain": "quantum",
        }
        # Mock the query result to return our row
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
        bq_storage.client.query.return_value.result.return_value = mock_result

        bq_storage._run_sync = AsyncMock(return_value=[mock_row])
        article = await bq_storage.get_article_by_url("https://example.com/found")
        assert article is not None
        assert article.title == "Found Article"

    @pytest.mark.asyncio
    async def test_get_article_by_url_not_found(self, bq_storage):
        """get_article_by_url returns None when no row found."""
        bq_storage._run_sync = AsyncMock(return_value=[])
        article = await bq_storage.get_article_by_url("https://example.com/missing")
        assert article is None

    @pytest.mark.asyncio
    async def test_url_exists_true(self, bq_storage):
        """url_exists returns True when row found."""
        bq_storage._run_sync = AsyncMock(return_value=[{"1": 1}])
        assert await bq_storage.url_exists("https://example.com/exists") is True

    @pytest.mark.asyncio
    async def test_url_exists_false(self, bq_storage):
        """url_exists returns False when no row found."""
        bq_storage._run_sync = AsyncMock(return_value=[])
        assert await bq_storage.url_exists("https://example.com/nope") is False

    @pytest.mark.asyncio
    async def test_get_article_count(self, bq_storage):
        """get_article_count returns correct count."""
        bq_storage._run_sync = AsyncMock(return_value=[{"cnt": 42}])
        count = await bq_storage.get_article_count(hours=24)
        assert count == 42

    @pytest.mark.asyncio
    async def test_get_article_count_empty(self, bq_storage):
        """get_article_count returns 0 when no rows."""
        bq_storage._run_sync = AsyncMock(return_value=[])
        count = await bq_storage.get_article_count(hours=24)
        assert count == 0


# =============================================================================
# Paper operation tests
# =============================================================================

class TestPaperOperations:

    @pytest.mark.asyncio
    async def test_save_papers_empty(self, bq_storage):
        result = await bq_storage.save_papers([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_papers(self, bq_storage):
        """save_papers calls _insert_if_not_exists with arxiv_id dedup."""
        paper = make_paper()
        bq_storage._insert_if_not_exists = AsyncMock(return_value=1)

        result = await bq_storage.save_papers([paper])
        assert result == 1
        bq_storage._insert_if_not_exists.assert_called_once()
        call_args = bq_storage._insert_if_not_exists.call_args
        assert call_args[0][0] == "papers"
        assert call_args[0][2] == ["arxiv_id"]


# =============================================================================
# Stock operation tests
# =============================================================================

class TestStockOperations:

    @pytest.mark.asyncio
    async def test_save_stock_data_empty(self, bq_storage):
        result = await bq_storage.save_stock_data([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_stock_data(self, bq_storage):
        """save_stock_data calls _upsert_row with ticker+date dedup."""
        snap = make_stock()
        bq_storage._upsert_row = AsyncMock(return_value=True)

        result = await bq_storage.save_stock_data([snap])
        assert result == 1
        bq_storage._upsert_row.assert_called_once()
        call_args = bq_storage._upsert_row.call_args
        assert call_args[0][0] == "stocks"
        assert call_args[1]["dedup_keys"] == ["ticker", "date"]


# =============================================================================
# Earnings operation tests
# =============================================================================

class TestEarningsOperations:

    @pytest.mark.asyncio
    async def test_save_transcript(self, bq_storage):
        """save_transcript builds correct row and calls _insert_if_not_exists."""
        transcript = EarningsTranscript(
            transcript_id="t1",
            ticker="IONQ",
            company_name="IonQ Inc",
            year=2025,
            quarter=3,
            transcript_text="Earnings call text here.",
        )
        bq_storage._insert_if_not_exists = AsyncMock(return_value=1)

        result = await bq_storage.save_transcript(transcript)
        bq_storage._insert_if_not_exists.assert_called_once()
        call_args = bq_storage._insert_if_not_exists.call_args
        rows = call_args[0][1]
        assert rows[0]["ticker"] == "IONQ"
        assert rows[0]["year"] == 2025
        assert call_args[0][2] == ["ticker", "year", "quarter"]

    @pytest.mark.asyncio
    async def test_transcript_exists(self, bq_storage):
        """transcript_exists delegates to BQ query."""
        bq_storage._run_sync = AsyncMock(return_value=[{"1": 1}])
        assert await bq_storage.transcript_exists("IONQ", 2025, 3) is True

        bq_storage._run_sync = AsyncMock(return_value=[])
        assert await bq_storage.transcript_exists("IONQ", 2099, 1) is False


# =============================================================================
# SEC operation tests
# =============================================================================

class TestSecOperations:

    @pytest.mark.asyncio
    async def test_save_filing(self, bq_storage):
        """save_filing builds correct row and calls _insert_if_not_exists."""
        filing = SecFiling(
            filing_id="f1",
            ticker="IONQ",
            company_name="IonQ Inc",
            cik="0001725579",
            filing_type="10-K",
            fiscal_year=2024,
        )
        bq_storage._insert_if_not_exists = AsyncMock(return_value=1)

        await bq_storage.save_filing(filing)
        bq_storage._insert_if_not_exists.assert_called_once()
        call_args = bq_storage._insert_if_not_exists.call_args
        rows = call_args[0][1]
        assert rows[0]["ticker"] == "IONQ"
        assert rows[0]["filing_type"] == "10-K"
        assert "fiscal_year" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_filing_exists(self, bq_storage):
        """filing_exists delegates to BQ query."""
        bq_storage._run_sync = AsyncMock(return_value=[{"1": 1}])
        assert await bq_storage.filing_exists("IONQ", "10-K", 2024) is True


# =============================================================================
# Case study operation tests
# =============================================================================

class TestCaseStudyOperations:

    @pytest.mark.asyncio
    async def test_save_case_studies_empty(self, bq_storage):
        result = await bq_storage.save_case_studies([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_case_studies(self, bq_storage):
        """save_case_studies builds correct row structure."""
        cs = CaseStudy(
            case_study_id="cs-1",
            source_type="article",
            source_id="art-123",
            domain="ai",
            grounding_quote="We deployed AI and saved $10M",
            use_case_title="AI Cost Savings at Acme Corp",
            company="Acme Corp",
            industry="Manufacturing",
        )
        # Mock _insert_if_not_exists
        bq_storage._insert_if_not_exists = AsyncMock(return_value=1)

        result = await bq_storage.save_case_studies([cs])
        assert result == 1
        call_args = bq_storage._insert_if_not_exists.call_args
        rows = call_args[0][1]
        assert len(rows) == 1
        assert rows[0]["company"] == "Acme Corp"
        assert rows[0]["domain"] == "ai"


# =============================================================================
# Close test
# =============================================================================

class TestLifecycle:

    @pytest.mark.asyncio
    async def test_close(self, bq_storage):
        """close() calls client.close()."""
        await bq_storage.close()
        bq_storage.client.close.assert_called_once()
