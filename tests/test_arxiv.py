"""
Test ArXiv Fetcher
==================

Tests for the ArXivFetcher with mocked HTTP responses.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from fetchers.arxiv import ArXivFetcher
from config.settings import IngestionConfig
from models.paper import Paper


# Sample ArXiv Atom XML response
SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query Results</title>
  <entry>
    <id>http://arxiv.org/abs/2501.12345v1</id>
    <title>Quantum Error Correction with Surface Codes</title>
    <summary>We present a novel approach to quantum error correction
using surface codes that achieves record-breaking fidelity.</summary>
    <published>{published_date}</published>
    <updated>{published_date}</updated>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <category term="quant-ph"/>
    <category term="cs.ET"/>
    <link href="https://arxiv.org/abs/2501.12345v1" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2501.12345v1" title="pdf" type="application/pdf" rel="related"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2501.67890v2</id>
    <title>Variational Quantum Eigensolver for Drug Discovery</title>
    <summary>An application of VQE to molecular simulation for pharmaceutical research.</summary>
    <published>{published_date2}</published>
    <updated>{published_date2}</updated>
    <author><name>Charlie Brown</name></author>
    <category term="quant-ph"/>
    <link href="https://arxiv.org/abs/2501.67890v2" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2501.67890v2" title="pdf" type="application/pdf" rel="related"/>
  </entry>
</feed>
"""


def make_fresh_xml(days_ago_1=1, days_ago_2=2):
    """Generate XML with dates relative to now."""
    now = datetime.now(timezone.utc)
    d1 = (now - timedelta(days=days_ago_1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d2 = (now - timedelta(days=days_ago_2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return SAMPLE_ARXIV_XML.format(published_date=d1, published_date2=d2)


def make_old_xml():
    """Generate XML with dates older than max_article_age_days."""
    old = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return SAMPLE_ARXIV_XML.format(published_date=old, published_date2=old)


def test_parse_atom_response():
    """Test parsing ArXiv Atom XML response."""
    fetcher = ArXivFetcher(IngestionConfig())
    xml = make_fresh_xml()
    entries = fetcher._parse_atom_response(xml)

    assert len(entries) == 2

    entry1 = entries[0]
    assert entry1["arxiv_id"] == "2501.12345"
    assert entry1["title"] == "Quantum Error Correction with Surface Codes"
    assert "surface codes" in entry1["abstract"]
    assert entry1["authors"] == ["Alice Smith", "Bob Jones"]
    assert "quant-ph" in entry1["categories"]
    assert "cs.ET" in entry1["categories"]
    assert entry1["pdf_url"] == "https://arxiv.org/pdf/2501.12345v1"

    entry2 = entries[1]
    assert entry2["arxiv_id"] == "2501.67890"


def test_parse_atom_date_filtering():
    """Test that old papers are filtered out."""
    fetcher = ArXivFetcher(IngestionConfig(max_article_age_days=7))
    xml = make_old_xml()
    entries = fetcher._parse_atom_response(xml)

    # All entries should be filtered (30 days old > 7 day limit)
    assert len(entries) == 0


def test_parse_atom_invalid_xml():
    """Test handling of invalid XML."""
    fetcher = ArXivFetcher(IngestionConfig())
    entries = fetcher._parse_atom_response("<invalid>xml<broken")
    assert len(entries) == 0


def test_parse_entry_strips_version():
    """Test that version suffix (v1, v2) is stripped from arxiv_id."""
    fetcher = ArXivFetcher(IngestionConfig())
    xml = make_fresh_xml()
    entries = fetcher._parse_atom_response(xml)

    # 2501.12345v1 -> 2501.12345 (v1 stripped)
    assert entries[0]["arxiv_id"] == "2501.12345"
    # 2501.67890v2 -> 2501.67890 (v2 stripped)
    assert entries[1]["arxiv_id"] == "2501.67890"


@pytest.mark.asyncio
async def test_fetch_all_queries_dedup():
    """Test cross-query dedup by arxiv_id."""
    fetcher = ArXivFetcher(IngestionConfig())
    xml = make_fresh_xml()

    # Mock aiohttp to return same XML for all queries
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=xml)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()))

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session_class.return_value = AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock(),
        )

        articles, papers = await fetcher.fetch_all_queries()

    # Even though multiple queries return same papers,
    # dedup should keep unique arxiv_ids only
    arxiv_ids = [p.arxiv_id for p in papers]
    assert len(arxiv_ids) == len(set(arxiv_ids))


def test_paper_from_parsed_entry():
    """Test creating Paper from parsed entry data."""
    fetcher = ArXivFetcher(IngestionConfig())
    xml = make_fresh_xml()
    entries = fetcher._parse_atom_response(xml)

    paper = Paper.from_arxiv_entry(entries[0])
    assert paper.arxiv_id == "2501.12345"
    assert paper.title == "Quantum Error Correction with Surface Codes"
    assert paper.authors == ["Alice Smith", "Bob Jones"]
    assert paper.categories == ["quant-ph", "cs.ET"]
    assert paper.published_at is not None


def test_paper_to_raw_article_conversion():
    """Test that Paper converts to RawArticle correctly."""
    fetcher = ArXivFetcher(IngestionConfig())
    xml = make_fresh_xml()
    entries = fetcher._parse_atom_response(xml)

    paper = Paper.from_arxiv_entry(entries[0])
    raw = paper.to_raw_article(query_metadata={"arxiv_query_name": "error_correction"})

    assert raw.url == "https://arxiv.org/abs/2501.12345"
    assert raw.source_name == "ArXiv"
    assert raw.metadata["arxiv_id"] == "2501.12345"
    assert raw.metadata["arxiv_query_name"] == "error_correction"
    assert raw.content_hash is not None
