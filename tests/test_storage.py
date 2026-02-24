"""
Test Storage
============

Tests for SQLite storage backend.
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from storage.sqlite import SQLiteStorage
from storage.base import ClassifiedArticle
from models.paper import Paper
from models.stock import StockSnapshot


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
        "title": "Test Quantum Article",
        "source_name": "Test Source",
        "primary_category": "hardware_milestone",
        "priority": "high",
        "relevance_score": 0.8,
        "ai_summary": "A test article about quantum computing.",
    }
    defaults.update(kwargs)
    return ClassifiedArticle(**defaults)


@pytest.mark.asyncio
async def test_save_and_retrieve(storage):
    """Test saving and retrieving articles."""
    article = make_article(id="article-1")
    saved = await storage.save_articles([article])
    assert saved == 1

    retrieved = await storage.get_article_by_url(article.url)
    assert retrieved is not None
    assert retrieved.title == "Test Quantum Article"
    assert retrieved.primary_category == "hardware_milestone"


@pytest.mark.asyncio
async def test_duplicate_url_skipped(storage):
    """Test that duplicate URLs are skipped."""
    article1 = make_article(url="https://example.com/same")
    article2 = make_article(url="https://example.com/same")

    saved1 = await storage.save_articles([article1])
    saved2 = await storage.save_articles([article2])

    assert saved1 == 1
    assert saved2 == 0  # Duplicate skipped


@pytest.mark.asyncio
async def test_get_recent_articles(storage):
    """Test retrieving recent articles."""
    articles = [
        make_article(id="a1", url="https://example.com/a1"),
        make_article(id="a2", url="https://example.com/a2"),
        make_article(id="a3", url="https://example.com/a3"),
    ]
    await storage.save_articles(articles)

    recent = await storage.get_recent_articles(hours=1)
    assert len(recent) == 3


@pytest.mark.asyncio
async def test_get_by_category(storage):
    """Test filtering by category."""
    await storage.save_articles([
        make_article(id="hw", url="https://example.com/hw", primary_category="hardware_milestone"),
        make_article(id="ec", url="https://example.com/ec", primary_category="error_correction"),
    ])

    hw = await storage.get_articles_by_category("hardware_milestone")
    assert len(hw) == 1
    assert hw[0].primary_category == "hardware_milestone"


@pytest.mark.asyncio
async def test_url_exists(storage):
    """Test URL existence check."""
    await storage.save_articles([make_article(url="https://example.com/exists")])

    assert await storage.url_exists("https://example.com/exists") is True
    assert await storage.url_exists("https://example.com/missing") is False


@pytest.mark.asyncio
async def test_search_articles(storage):
    """Test text search."""
    await storage.save_articles([
        make_article(id="ionq", url="https://example.com/ionq", title="IonQ Gate Fidelity Record",
                     companies_mentioned=["IonQ"]),
        make_article(id="dwave", url="https://example.com/dwave", title="D-Wave Annealing Update",
                     companies_mentioned=["D-Wave"]),
    ])

    results = await storage.search_articles("IonQ")
    assert len(results) >= 1
    assert any("IonQ" in r.title for r in results)


@pytest.mark.asyncio
async def test_stats(storage):
    """Test statistics."""
    await storage.save_articles([
        make_article(id="s1", url="https://example.com/s1", priority="high"),
        make_article(id="s2", url="https://example.com/s2", priority="medium"),
        make_article(id="s3", url="https://example.com/s3", priority="medium"),
    ])

    stats = await storage.get_stats(hours=1)
    assert stats["total_articles"] == 3
    assert stats["by_priority"]["high"] == 1
    assert stats["by_priority"]["medium"] == 2


@pytest.mark.asyncio
async def test_close(storage):
    """Test closing connection."""
    await storage.close()
    # Should not error on double close
    await storage.close()


# =========================================================================
# Paper Operations (Phase 2)
# =========================================================================

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


@pytest.mark.asyncio
async def test_save_and_get_paper(storage):
    """Test saving and retrieving papers."""
    paper = make_paper()
    saved = await storage.save_papers([paper])
    assert saved == 1

    retrieved = await storage.get_paper_by_arxiv_id("2301.12345")
    assert retrieved is not None
    assert retrieved.title == "Quantum Error Correction via Surface Codes"
    assert retrieved.authors == ["Alice Smith", "Bob Jones"]
    assert retrieved.categories == ["quant-ph", "cs.ET"]


@pytest.mark.asyncio
async def test_paper_duplicate_skipped(storage):
    """Test that duplicate arxiv_ids are skipped."""
    paper1 = make_paper(arxiv_id="2301.11111")
    paper2 = make_paper(arxiv_id="2301.11111")

    saved1 = await storage.save_papers([paper1])
    saved2 = await storage.save_papers([paper2])

    assert saved1 == 1
    assert saved2 == 0


@pytest.mark.asyncio
async def test_get_recent_papers(storage):
    """Test retrieving recent papers."""
    papers = [
        make_paper(arxiv_id="2301.00001"),
        make_paper(arxiv_id="2301.00002"),
    ]
    await storage.save_papers(papers)

    recent = await storage.get_recent_papers(days=1)
    assert len(recent) == 2


@pytest.mark.asyncio
async def test_arxiv_id_exists(storage):
    """Test arxiv_id existence check."""
    await storage.save_papers([make_paper(arxiv_id="2301.99999")])

    assert await storage.arxiv_id_exists("2301.99999") is True
    assert await storage.arxiv_id_exists("2301.00000") is False


# =========================================================================
# Stock Operations (Phase 2)
# =========================================================================

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


@pytest.mark.asyncio
async def test_save_and_get_stock(storage):
    """Test saving and retrieving stock data."""
    snap = make_stock()
    saved = await storage.save_stock_data([snap])
    assert saved == 1

    data = await storage.get_stock_data("IONQ", days=30)
    assert len(data) == 1
    assert data[0].ticker == "IONQ"
    assert data[0].close == 12.75
    assert data[0].volume == 1500000


@pytest.mark.asyncio
async def test_stock_upsert(storage):
    """Test that stock data is upserted (updated on conflict)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap1 = make_stock(ticker="IONQ", date=today, close=12.75)
    snap2 = make_stock(ticker="IONQ", date=today, close=13.00)

    await storage.save_stock_data([snap1])
    await storage.save_stock_data([snap2])

    data = await storage.get_stock_data("IONQ", days=30)
    assert len(data) == 1
    assert data[0].close == 13.00  # Updated, not duplicated


@pytest.mark.asyncio
async def test_get_latest_stock_data(storage):
    """Test getting latest snapshot per ticker."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from datetime import timedelta
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    snapshots = [
        make_stock(ticker="IONQ", date=yesterday, close=12.50),
        make_stock(ticker="IONQ", date=today, close=12.75),
        make_stock(ticker="QBTS", date=yesterday, close=5.00),
        make_stock(ticker="QBTS", date=today, close=5.25),
    ]
    await storage.save_stock_data(snapshots)

    latest = await storage.get_latest_stock_data(tickers=["IONQ", "QBTS"])
    assert len(latest) == 2

    ionq = next(s for s in latest if s.ticker == "IONQ")
    assert ionq.date == today
    assert ionq.close == 12.75

    qbts = next(s for s in latest if s.ticker == "QBTS")
    assert qbts.date == today


@pytest.mark.asyncio
async def test_get_latest_stock_all_tickers(storage):
    """Test getting latest for all tickers (no filter)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await storage.save_stock_data([
        make_stock(ticker="IONQ", date=today),
        make_stock(ticker="QBTS", date=today, close=5.25, volume=800000),
    ])

    latest = await storage.get_latest_stock_data()
    assert len(latest) == 2
