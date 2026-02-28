"""
Test Exa Fetcher
=================

Tests for the ExaFetcher with mocked Exa API.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from fetchers.exa import ExaFetcher
from config.settings import IngestionConfig
from models.article import SourceType


def make_config(**kwargs):
    """Create a test config with Exa API key."""
    defaults = {"exa_api_key": "exa-test-key-12345"}
    defaults.update(kwargs)
    return IngestionConfig(**defaults)


def make_exa_result(**kwargs):
    """Create a mock Exa search result object."""
    result = MagicMock()
    result.url = kwargs.get("url", "https://example.com/quantum-article")
    result.title = kwargs.get("title", "Quantum Computing Breakthrough")
    result.text = kwargs.get("text", "A major advance in quantum error correction was announced.")
    result.published_date = kwargs.get("published_date", "2025-02-15T12:00:00Z")
    result.author = kwargs.get("author", None)
    result.image = kwargs.get("image", None)
    return result


def make_exa_response(results=None):
    """Create a mock Exa search response."""
    response = MagicMock()
    response.results = results if results is not None else [make_exa_result()]
    return response


@patch("fetchers.exa.Exa")
def test_init_requires_api_key(mock_client):
    """Test that ExaFetcher requires an API key."""
    with pytest.raises(ValueError, match="EXA_API_KEY"):
        ExaFetcher(IngestionConfig(exa_api_key=""))


@patch("fetchers.exa.Exa")
def test_init_with_valid_key(mock_client):
    """Test successful initialization with API key."""
    config = make_config()
    fetcher = ExaFetcher(config)
    assert fetcher.client is not None
    mock_client.assert_called_once_with(api_key="exa-test-key-12345")


@patch("fetchers.exa.Exa")
def test_parse_result_basic(mock_client):
    """Test parsing a single Exa result into RawArticle."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "quantum computing", "theme": "hardware_error_correction", "id": 39}
    result = make_exa_result()

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert article.url == "https://example.com/quantum-article"
    assert article.title == "Quantum Computing Breakthrough"
    assert article.source_name == "Exa Search"
    assert article.metadata["source_type"] == SourceType.EXA.value
    assert article.metadata["theme"] == "hardware_error_correction"
    assert article.metadata["query_id"] == 39
    assert article.content_hash is not None
    assert article.date_confidence == "exact"


@patch("fetchers.exa.Exa")
def test_parse_result_no_date(mock_client):
    """Test parsing result without published_date."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_exa_result(published_date=None)

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert article.date_confidence == "fetched"


@patch("fetchers.exa.Exa")
def test_parse_result_iso_date_with_milliseconds(mock_client):
    """Test parsing ISO 8601 date with milliseconds (Exa format)."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_exa_result(published_date="2025-02-15T01:36:32.547Z")

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert article.date_confidence == "exact"
    assert article.published_at.year == 2025
    assert article.published_at.month == 2
    assert article.published_at.day == 15


@patch("fetchers.exa.Exa")
def test_parse_result_missing_url(mock_client):
    """Test that results without URL are skipped."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_exa_result(url="")

    article = fetcher._parse_result(result, query_config)
    assert article is None


@patch("fetchers.exa.Exa")
def test_parse_result_missing_title(mock_client):
    """Test that results without title are skipped."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    result = make_exa_result(title="")

    article = fetcher._parse_result(result, query_config)
    assert article is None


@pytest.mark.asyncio
@patch("fetchers.exa.Exa")
async def test_fetch_all_queries_dedup(mock_client_class):
    """Test that cross-query URL dedup works."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Both queries return the same URL
    mock_client.search_and_contents.return_value = make_exa_response(
        [make_exa_result(url="https://example.com/same-article")]
    )

    config = make_config()
    fetcher = ExaFetcher(config)

    queries = [
        {"query": "query 1", "theme": "theme_a", "id": 1},
        {"query": "query 2", "theme": "theme_b", "id": 2},
    ]

    articles = await fetcher.fetch_all_queries(queries=queries)
    # Same URL should only appear once
    assert len(articles) == 1


@pytest.mark.asyncio
@patch("fetchers.exa.Exa")
async def test_fetch_all_queries_theme_filter(mock_client_class):
    """Test theme-based query filtering."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search_and_contents.return_value = make_exa_response()

    config = make_config()
    fetcher = ExaFetcher(config)

    # Only run queries for one theme
    articles = await fetcher.fetch_all_queries(themes=["cybersecurity_pqc"])
    # Should only run queries matching the theme
    assert mock_client.search_and_contents.call_count <= 10  # max queries in one theme


@pytest.mark.asyncio
@patch("fetchers.exa.Exa")
async def test_fetch_query_error_handling(mock_client_class):
    """Test that single query errors don't abort the batch."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # First call succeeds, second raises, third succeeds
    mock_client.search_and_contents.side_effect = [
        make_exa_response([make_exa_result(url="https://example.com/1")]),
        Exception("API rate limit"),
        make_exa_response([make_exa_result(url="https://example.com/3")]),
    ]

    config = make_config()
    fetcher = ExaFetcher(config)

    queries = [
        {"query": "q1", "theme": "t", "id": 1},
        {"query": "q2", "theme": "t", "id": 2},
        {"query": "q3", "theme": "t", "id": 3},
    ]

    articles = await fetcher.fetch_all_queries(queries=queries)
    # Should still get articles from q1 and q3
    assert len(articles) == 2


@pytest.mark.asyncio
@patch("fetchers.exa.Exa")
async def test_fetch_query_uses_date_range(mock_client_class):
    """Test that fetch_query passes date range parameters."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search_and_contents.return_value = make_exa_response()

    config = make_config()
    fetcher = ExaFetcher(config)

    queries = [{"query": "test query", "theme": "test", "id": 1}]
    await fetcher.fetch_all_queries(queries=queries)

    # Verify search_and_contents was called with date parameters
    call_kwargs = mock_client.search_and_contents.call_args
    assert "start_published_date" in str(call_kwargs)
    assert "end_published_date" in str(call_kwargs)


@patch("fetchers.exa.Exa")
def test_parse_result_content_truncation(mock_client):
    """Test that long content is truncated to 2000 chars."""
    config = make_config()
    fetcher = ExaFetcher(config)

    query_config = {"query": "test", "theme": "test", "id": 1}
    long_text = "x" * 5000
    result = make_exa_result(text=long_text)

    article = fetcher._parse_result(result, query_config)
    assert article is not None
    assert len(article.summary) == 2000
