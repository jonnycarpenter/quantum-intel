"""
Test Agent Tools
================

Tests for corpus search, stock data, arxiv search, and podcast search tools.
Web search is tested with mocked Tavily client.
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from storage.sqlite import SQLiteStorage
from storage.base import ClassifiedArticle
from models.paper import Paper
from models.stock import StockSnapshot
from tools.corpus_search import CorpusSearchTool
from tools.stock_data import StockDataTool
from tools.arxiv_search import ArXivSearchTool
from tools.podcast_search import PodcastSearchTool


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except PermissionError:
        pass


@pytest_asyncio.fixture
async def storage(tmp_db):
    """Create a SQLiteStorage instance with temp DB."""
    store = SQLiteStorage(db_path=tmp_db)
    yield store
    await store.close()


def make_article(**kwargs) -> ClassifiedArticle:
    """Helper to create test articles."""
    defaults = {
        "url": f"https://example.com/{kwargs.get('id', 'test')}",
        "title": "IonQ Achieves Quantum Error Correction Milestone",
        "source_name": "The Quantum Insider",
        "primary_category": "error_correction",
        "priority": "high",
        "relevance_score": 0.85,
        "ai_summary": "IonQ demonstrates breakthrough in quantum error correction.",
        "key_takeaway": "Error rates reduced by 50%.",
        "companies_mentioned": ["IonQ"],
        "technologies_mentioned": ["trapped-ion"],
    }
    defaults.update(kwargs)
    return ClassifiedArticle(**defaults)


def make_paper(**kwargs) -> Paper:
    """Helper to create test papers."""
    defaults = {
        "arxiv_id": kwargs.get("arxiv_id", "2401.12345"),
        "title": "Quantum Error Correction with Surface Codes",
        "authors": ["A. Researcher", "B. Scientist"],
        "abstract": "We present a novel approach to quantum error correction using surface codes.",
        "categories": ["quant-ph"],
        "published_at": datetime(2026, 2, 15, tzinfo=timezone.utc),
        "relevance_score": 7.0,
        "paper_type": "incremental",
        "commercial_readiness": "mid_term",
    }
    defaults.update(kwargs)
    return Paper(**defaults)


def make_stock(**kwargs) -> StockSnapshot:
    """Helper to create test stock snapshots."""
    defaults = {
        "ticker": "IONQ",
        "date": "2026-02-19",
        "open": 10.50,
        "high": 11.00,
        "low": 10.20,
        "close": 10.80,
        "volume": 5000000,
        "change_percent": 2.5,
        "sma_20": 10.50,
        "sma_50": 10.00,
    }
    defaults.update(kwargs)
    return StockSnapshot(**defaults)


# ============================================================================
# CORPUS SEARCH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_corpus_search_returns_results(storage):
    """Test corpus search with seeded data."""
    articles = [
        make_article(id="a1", title="IonQ Error Correction Breakthrough"),
        make_article(id="a2", title="D-Wave Quantum Annealing Update", primary_category="hardware_milestone"),
    ]
    await storage.save_articles(articles)

    tool = CorpusSearchTool()
    tool._storage = storage
    tool._embeddings = None  # Skip semantic search

    result = await tool.execute(query="error correction")
    data = json.loads(result)

    assert data["total_found"] >= 1
    assert any("IonQ" in r.get("title", "") for r in data["results"])


@pytest.mark.asyncio
async def test_corpus_search_empty_corpus(storage):
    """Test corpus search with no data returns zero results."""
    tool = CorpusSearchTool()
    tool._storage = storage
    tool._embeddings = None  # Explicitly disable semantic search

    # Bypass _ensure_initialized so it doesn't load live ChromaDB
    tool._ensure_initialized = lambda: None

    result = await tool.execute(query="quantum computing")
    data = json.loads(result)

    assert data["total_found"] == 0
    assert "message" in data


@pytest.mark.asyncio
async def test_corpus_search_category_filter(storage):
    """Test corpus search with category filter."""
    articles = [
        make_article(id="a1", primary_category="error_correction"),
        make_article(id="a2", primary_category="hardware_milestone",
                     title="New Processor Launch"),
    ]
    await storage.save_articles(articles)

    tool = CorpusSearchTool()
    tool._storage = storage
    tool._embeddings = None

    result = await tool.execute(query="quantum", category="hardware_milestone")
    data = json.loads(result)

    assert data["total_found"] >= 1
    assert all(
        r.get("category") == "hardware_milestone"
        for r in data["results"]
    )


# ============================================================================
# STOCK DATA TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_stock_data_valid_ticker(storage):
    """Test stock data with valid ticker and data."""
    snapshots = [
        make_stock(date="2026-02-17", close=10.00),
        make_stock(date="2026-02-18", close=10.50),
        make_stock(date="2026-02-19", close=10.80),
    ]
    await storage.save_stock_data(snapshots)

    tool = StockDataTool()
    tool._storage = storage

    result = await tool.execute(ticker="IONQ", days=30)
    data = json.loads(result)

    assert data["ticker"] == "IONQ"
    assert "company_info" in data
    assert data["company_info"]["company"] == "IonQ Inc."
    assert data["summary"]["latest_close"] == 10.80
    assert data["total_data_points"] == 3


@pytest.mark.asyncio
async def test_stock_data_invalid_ticker():
    """Test stock data with unknown ticker."""
    tool = StockDataTool()

    result = await tool.execute(ticker="FAKE")
    data = json.loads(result)

    assert "error" in data
    assert "FAKE" in data["error"]


@pytest.mark.asyncio
async def test_stock_data_empty(storage):
    """Test stock data with valid ticker but no data."""
    tool = StockDataTool()
    tool._storage = storage

    result = await tool.execute(ticker="IONQ")
    data = json.loads(result)

    assert "message" in data
    assert "No stock data" in data["message"]


# ============================================================================
# ARXIV SEARCH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_arxiv_search_returns_papers(storage):
    """Test arxiv search with seeded papers."""
    papers = [
        make_paper(arxiv_id="2401.11111", title="Surface Code Error Correction"),
        make_paper(arxiv_id="2401.22222", title="Trapped Ion Quantum Computing"),
    ]
    await storage.save_papers(papers)

    tool = ArXivSearchTool()
    tool._storage = storage

    result = await tool.execute(query="error correction")
    data = json.loads(result)

    assert data["total_found"] >= 1
    assert any("Surface Code" in r["title"] for r in data["results"])


@pytest.mark.asyncio
async def test_arxiv_search_empty_corpus(storage):
    """Test arxiv search with no papers."""
    tool = ArXivSearchTool()
    tool._storage = storage

    result = await tool.execute(query="quantum")
    data = json.loads(result)

    assert data["total_found"] == 0
    assert "message" in data


# ============================================================================
# PODCAST SEARCH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_podcast_search_empty(storage):
    """Test podcast search with no data returns empty results."""
    tool = PodcastSearchTool()
    tool._storage = storage

    result = await tool.execute(query="quantum computing podcast")
    data = json.loads(result)

    assert data["status"] == "ok"
    assert data["count"] == 0
    assert data["results"] == []


# ============================================================================
# WEB SEARCH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_web_search_no_api_key():
    """Test web search handles missing API key gracefully."""
    from tools.web_search import WebSearchTool

    with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=False):
        tool = WebSearchTool()
        tool._client = None  # Reset any cached client

        result = await tool.execute(query="quantum computing")
        data = json.loads(result)

        assert "error" in data or data["total_found"] == 0
