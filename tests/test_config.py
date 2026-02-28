"""
Test Config
===========

Tests for configuration modules.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import IngestionConfig
from config.rss_sources import RSS_FEEDS
from config.tickers import ALL_TICKERS, PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, PRIVATE_COMPANIES
from config.exa_queries import EXA_QUERIES, get_queries_by_theme, THEMES
from config.arxiv_queries import ARXIV_QUERIES, ARXIV_CATEGORIES


def test_ingestion_config_defaults():
    """Test IngestionConfig has sensible defaults."""
    config = IngestionConfig()
    assert config.rss_poll_interval_hours == 4
    assert config.max_articles_per_feed == 20
    assert config.classifier_temperature == 0.1
    assert "haiku" in config.classifier_model


def test_rss_feeds_count():
    """Verify we have 18+ RSS feeds across 4 tiers."""
    assert len(RSS_FEEDS) >= 18
    tiers = set(f["tier"] for f in RSS_FEEDS)
    assert tiers == {1, 2, 3, 4}


def test_rss_feeds_have_required_fields():
    """Each feed must have name, url, tier."""
    for feed in RSS_FEEDS:
        assert "name" in feed, f"Feed missing name: {feed}"
        assert "url" in feed, f"Feed missing url: {feed}"
        assert "tier" in feed, f"Feed missing tier: {feed}"
        assert feed["url"].startswith("http"), f"Invalid URL: {feed['url']}"


def test_ticker_counts():
    """Verify ticker counts match spec."""
    assert len(PURE_PLAY_TICKERS) == 8
    assert len(MAJOR_TECH_TICKERS) == 6
    assert len(ALL_TICKERS) >= 15
    assert "IONQ" in ALL_TICKERS
    assert "GOOGL" in ALL_TICKERS


def test_private_companies():
    """Verify private companies list."""
    assert len(PRIVATE_COMPANIES) >= 10
    names = [p["company"] for p in PRIVATE_COMPANIES]
    assert "Quantinuum" in names
    assert "PsiQuantum" in names


def test_exa_queries_count():
    """Verify 52 Exa queries across 9 themes."""
    assert len(EXA_QUERIES) == 52
    assert len(THEMES) == 9


def test_exa_queries_by_theme():
    """Each theme should have queries."""
    for theme in THEMES:
        queries = get_queries_by_theme(theme)
        assert len(queries) >= 4, f"Theme {theme} has only {len(queries)} queries"


def test_arxiv_queries():
    """Verify ArXiv queries."""
    assert len(ARXIV_QUERIES) == 6
    assert len(ARXIV_CATEGORIES) == 4
