"""
Test Deduplication
==================

Tests for deduplication service.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone

from processing.deduplication import (
    normalize_title,
    title_similarity,
    DeduplicationService,
    ArticleAggregator,
)
from models.article import RawArticle


def test_normalize_title():
    """Test title normalization."""
    assert normalize_title("IonQ Achieves 99.9% Gate Fidelity!") == "ionq achieves 999 gate fidelity"
    assert normalize_title("  Hello   World  ") == "hello world"


def test_title_similarity_identical():
    """Identical titles should have similarity 1.0."""
    assert title_similarity("quantum computing breakthrough", "quantum computing breakthrough") == 1.0


def test_title_similarity_different():
    """Very different titles should have low similarity."""
    sim = title_similarity("quantum computing", "basketball scores today")
    assert sim < 0.2


def test_title_similarity_similar():
    """Similar titles should have high similarity."""
    sim = title_similarity(
        "IonQ Achieves New Gate Fidelity Record",
        "IonQ Achieves New Record in Gate Fidelity",
    )
    assert sim > 0.7


@pytest.mark.asyncio
async def test_dedup_url_match():
    """Test URL-based dedup."""
    service = DeduplicationService()

    # Add URL to cache
    service.add_to_cache(url="https://example.com/article1", title="Test Article")

    article = RawArticle(
        url="https://example.com/article1",
        title="Test Article",
        source_name="Test",
        source_url="",
        published_at=datetime.now(timezone.utc),
    )

    is_dup, _, match_type = await service.check_duplicate(article)
    assert is_dup is True
    assert match_type == "url"


@pytest.mark.asyncio
async def test_dedup_new_article():
    """Test that new articles are not flagged as duplicates."""
    service = DeduplicationService()

    article = RawArticle(
        url="https://example.com/brand-new",
        title="Completely New Article About Quantum",
        source_name="Test",
        source_url="",
        published_at=datetime.now(timezone.utc),
    )

    is_dup, _, match_type = await service.check_duplicate(article)
    assert is_dup is False


def test_article_aggregator():
    """Test article aggregation of similar stories."""
    agg = ArticleAggregator(threshold=0.7)

    agg.add_article({"title": "IonQ Hits Gate Fidelity Record", "url": "a", "summary": "Long text here", "source_name": "Source A"})
    agg.add_article({"title": "IonQ Hits New Gate Fidelity Record", "url": "b", "summary": "Short", "source_name": "Source B"})
    agg.add_article({"title": "D-Wave Launches New Annealer", "url": "c", "summary": "Different story", "source_name": "Source C"})

    results = agg.get_aggregated_articles()
    assert len(results) == 2  # Two distinct stories

    # The IonQ group should have coverage_count 2
    ionq_story = [r for r in results if "IonQ" in r["title"]][0]
    assert ionq_story["coverage_count"] == 2
