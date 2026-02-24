"""
Test Paper Model
================

Tests for the Paper dataclass and its conversions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from models.paper import Paper
from models.article import SourceType


def test_paper_creation():
    """Test creating a Paper dataclass."""
    paper = Paper(
        arxiv_id="2301.12345",
        title="Quantum Error Correction with Surface Codes",
        authors=["Alice Smith", "Bob Jones"],
        abstract="We present a novel approach to quantum error correction.",
        categories=["quant-ph", "cs.ET"],
        published_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
    )
    assert paper.arxiv_id == "2301.12345"
    assert len(paper.authors) == 2
    assert paper.abs_url == "https://arxiv.org/abs/2301.12345"
    assert paper.relevance_score is None  # LLM-generated, not set yet


def test_paper_from_arxiv_entry():
    """Test creating Paper from parsed ArXiv API entry."""
    entry_data = {
        "arxiv_id": "2402.98765",
        "title": "  Quantum Drug Discovery via VQE  ",
        "authors": ["Charlie Brown", "Diana Prince"],
        "abstract": "  A new method for drug discovery using variational quantum eigensolver.  ",
        "categories": ["quant-ph"],
        "published": "2025-02-10T14:30:00+00:00",
        "updated": "2025-02-12T10:00:00Z",
        "pdf_url": "https://arxiv.org/pdf/2402.98765v1",
    }

    paper = Paper.from_arxiv_entry(entry_data)
    assert paper.arxiv_id == "2402.98765"
    assert paper.title == "Quantum Drug Discovery via VQE"  # Stripped
    assert paper.abstract == "A new method for drug discovery using variational quantum eigensolver."
    assert paper.published_at is not None
    assert paper.updated_at is not None
    assert paper.pdf_url == "https://arxiv.org/pdf/2402.98765v1"


def test_paper_to_raw_article():
    """Test converting Paper to RawArticle for classification pipeline."""
    paper = Paper(
        arxiv_id="2301.12345",
        title="Quantum Computing Breakthrough",
        authors=["Alice Smith"],
        abstract="We demonstrate quantum advantage in optimization.",
        categories=["quant-ph"],
        published_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        pdf_url="https://arxiv.org/pdf/2301.12345v1",
    )

    raw = paper.to_raw_article(query_metadata={"arxiv_query_name": "optimization"})
    assert raw.url == "https://arxiv.org/abs/2301.12345"
    assert raw.title == "Quantum Computing Breakthrough"
    assert raw.source_name == "ArXiv"
    assert raw.summary == "We demonstrate quantum advantage in optimization."
    assert raw.author == "Alice Smith"
    assert raw.metadata["source_type"] == SourceType.ARXIV.value
    assert raw.metadata["arxiv_id"] == "2301.12345"
    assert raw.metadata["arxiv_query_name"] == "optimization"
    assert raw.content_hash is not None
    assert raw.date_confidence == "exact"


def test_paper_to_raw_article_no_date():
    """Test RawArticle conversion when Paper has no published_at."""
    paper = Paper(
        arxiv_id="2301.99999",
        title="Some Paper",
        abstract="Abstract text",
    )
    raw = paper.to_raw_article()
    assert raw.date_confidence == "fetched"
    assert raw.published_at is not None  # Falls back to now()


def test_paper_to_dict_and_back():
    """Test Paper serialization round-trip."""
    paper = Paper(
        arxiv_id="2301.12345",
        title="Test Paper",
        authors=["Author A", "Author B"],
        abstract="Abstract",
        categories=["quant-ph"],
        published_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        pdf_url="https://arxiv.org/pdf/2301.12345v1",
        relevance_score=0.9,
        paper_type="breakthrough",
    )

    d = paper.to_dict()
    assert d["arxiv_id"] == "2301.12345"
    assert d["authors"] == ["Author A", "Author B"]
    assert d["relevance_score"] == 0.9

    restored = Paper.from_dict(d)
    assert restored.arxiv_id == paper.arxiv_id
    assert restored.title == paper.title
    assert restored.authors == paper.authors
    assert restored.relevance_score == 0.9


def test_paper_from_dict_with_json_strings():
    """Test Paper.from_dict when lists come as JSON strings (from DB)."""
    d = {
        "arxiv_id": "2301.11111",
        "title": "Test",
        "authors": '["Author A", "Author B"]',
        "categories": '["quant-ph"]',
        "abstract": "Abstract",
    }

    paper = Paper.from_dict(d)
    assert paper.authors == ["Author A", "Author B"]
    assert paper.categories == ["quant-ph"]
