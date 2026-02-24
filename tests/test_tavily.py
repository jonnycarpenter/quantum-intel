"""
Test Tavily Fetcher
===================

Tests for the TavilyFetcher with mocked Tavily API.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from fetchers.tavily import TavilyFetcher
from config.settings import IngestionConfig
from models.article import SourceType


def make_config(**kwargs):
    """Create a test config with Tavily API key."""
    defaults = {"tavily_api_key": "tvly-test-key-12345"}
    defaults.update(kwargs)
    return IngestionConfig(**defaults)


def make_tavily_result(**kwargs):
    """Create a mock Tavily search result."""
    defaults = {
        "url": "https://example.com/quantum-article",
        "title": "Quantum Computing Breakthrough",
        "content": "A major advance in quantum error correction was announced.",
        "score": 0.95,
        "published_date": "2025-02-15",
    }
    defaults.update(kwargs)
    return defaults


@patch("fetchers.tavily.TavilyClient")
def test_init_requires_api_key(mock_client):
    """Test that TavilyFetcher requires an API key."""
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        TavilyFetcher(IngestionConfig(tavily_api_key=""))


@patch("fetchers.tavily.TavilyClient")
def test_init_with_valid_key(mock_client):
    """Test successful initialization with API key."""
    config = make_config()
    fetcher = TavilyFetcher(config)
    assert fetcher.client is not None
    mock_client.assert_called_once_with(api_key="tvly-test-key-12345")


@patch("fetchers.tavily.TavilyClient")
def test_parse_result_basic(mock_client):
    """Test parsing a single Tavily result into RawArticle."""
    config = make_config()
    fetcher = TavilyFetcher(config)

    query_config = {"query": "quantum computing", "theme": "hardware_error_correction", "id": 39}
    result = make_tavily_result()

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert article.url == "https://example.com/quantum-article"
    assert article.title == "Quantum Computing Breakthrough"
    assert article.source_name == "Tavily Search"
    assert article.metadata["source_type"] == SourceType.TAVILY.value
    assert article.metadata["theme"] == "hardware_error_correction"
    assert article.metadata["query_id"] == 39
    assert article.metadata["tavily_score"] == 0.95
    assert article.content_hash is not None
    assert article.date_confidence == "exact"


@patch("fetchers.tavily.TavilyClient")
def test_parse_result_no_date(mock_client):
    """Test parsing result without published_date."""
    config = make_config()
    fetcher = TavilyFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_tavily_result(published_date=None)

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert article.date_confidence == "fetched"


@patch("fetchers.tavily.TavilyClient")
def test_parse_result_missing_url(mock_client):
    """Test that results without URL are skipped."""
    config = make_config()
    fetcher = TavilyFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_tavily_result(url="")

    article = fetcher._parse_result(result, query_config)
    assert article is None


@patch("fetchers.tavily.TavilyClient")
def test_parse_result_missing_title(mock_client):
    """Test that results without title are skipped."""
    config = make_config()
    fetcher = TavilyFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_tavily_result(title="")

    article = fetcher._parse_result(result, query_config)
    assert article is None


@pytest.mark.asyncio
@patch("fetchers.tavily.TavilyClient")
async def test_fetch_all_queries_dedup(mock_client_class):
    """Test that cross-query URL dedup works."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Two queries return the same URL
    mock_client.search.return_value = {
        "results": [
            make_tavily_result(url="https://example.com/same-article"),
        ]
    }

    config = make_config()
    fetcher = TavilyFetcher(config)

    queries = [
        {"query": "query 1", "theme": "theme_a", "id": 1},
        {"query": "query 2", "theme": "theme_b", "id": 2},
    ]

    articles = await fetcher.fetch_all_queries(queries=queries)
    # Same URL should only appear once
    assert len(articles) == 1


@pytest.mark.asyncio
@patch("fetchers.tavily.TavilyClient")
async def test_fetch_all_queries_theme_filter(mock_client_class):
    """Test theme-based query filtering."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {"results": [make_tavily_result()]}

    config = make_config()
    fetcher = TavilyFetcher(config)

    # Only run queries for one theme
    articles = await fetcher.fetch_all_queries(themes=["cybersecurity_pqc"])
    # Should only run queries matching the theme
    assert mock_client.search.call_count <= 10  # max queries in one theme


@pytest.mark.asyncio
@patch("fetchers.tavily.TavilyClient")
async def test_fetch_query_error_handling(mock_client_class):
    """Test that single query errors don't abort the batch."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # First call succeeds, second raises
    mock_client.search.side_effect = [
        {"results": [make_tavily_result(url="https://example.com/1")]},
        Exception("API rate limit"),
        {"results": [make_tavily_result(url="https://example.com/3")]},
    ]

    config = make_config()
    fetcher = TavilyFetcher(config)

    queries = [
        {"query": "q1", "theme": "t", "id": 1},
        {"query": "q2", "theme": "t", "id": 2},
        {"query": "q3", "theme": "t", "id": 3},
    ]

    articles = await fetcher.fetch_all_queries(queries=queries)
    # Should still get articles from q1 and q3
    assert len(articles) == 2
