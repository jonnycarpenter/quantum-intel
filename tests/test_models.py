"""
Test Models
===========

Tests for data models and enums.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from models.article import (
    ContentCategory, Priority, SourceType, DateConfidence,
    RawArticle, ClassificationResult, DigestItem, Digest,
)


def test_content_categories():
    """Verify all 29 content categories exist (11 quantum + 8 shared + 10 AI)."""
    assert len(ContentCategory) == 29
    # Quantum-specific
    assert ContentCategory.HARDWARE_MILESTONE.value == "hardware_milestone"
    assert ContentCategory.SKEPTICISM_CRITIQUE.value == "skepticism_critique"
    # AI-specific
    assert ContentCategory.AI_MODEL_RELEASE.value == "ai_model_release"
    assert ContentCategory.AI_RESEARCH_BREAKTHROUGH.value == "ai_research_breakthrough"


def test_priority_levels():
    """Verify 4 priority levels including critical."""
    assert len(Priority) == 4
    assert Priority.CRITICAL.value == "critical"
    assert Priority.HIGH.value == "high"
    assert Priority.MEDIUM.value == "medium"
    assert Priority.LOW.value == "low"


def test_source_types():
    """Verify source types."""
    assert SourceType.RSS.value == "rss"
    assert SourceType.TAVILY.value == "tavily"
    assert SourceType.ARXIV.value == "arxiv"


def test_raw_article_creation():
    """Test creating a RawArticle."""
    article = RawArticle(
        url="https://example.com/article",
        title="IonQ Achieves 99.9% Gate Fidelity",
        source_name="The Quantum Insider",
        source_url="https://thequantuminsider.com/feed/",
        published_at=datetime.now(timezone.utc),
        summary="IonQ announced...",
    )
    assert article.url == "https://example.com/article"
    assert article.date_confidence == "fetched"
    assert article.metadata == {}


def test_classification_from_llm_response():
    """Test ClassificationResult.from_llm_response."""
    response = {
        "primary_category": "hardware_milestone",
        "priority": "high",
        "relevance_score": 0.85,
        "summary": "IonQ achieved significant gate fidelity improvement.",
        "key_takeaway": "Gate fidelity now at 99.9%",
        "companies_mentioned": ["IonQ"],
        "technologies_mentioned": ["trapped-ion"],
        "people_mentioned": [],
        "use_case_domains": [],
        "sentiment": "bullish",
        "confidence": 0.9,
    }

    result = ClassificationResult.from_llm_response("https://example.com", response)
    assert result.primary_category == "hardware_milestone"
    assert result.priority == Priority.HIGH
    assert result.relevance_score == 0.85
    assert "IonQ" in result.companies_mentioned


def test_classification_invalid_category_fallback():
    """Test that invalid categories fall back to market_analysis."""
    response = {
        "primary_category": "nonexistent_category",
        "priority": "invalid_priority",
    }
    result = ClassificationResult.from_llm_response("https://example.com", response)
    assert result.primary_category == "market_analysis"
    assert result.priority == Priority.MEDIUM
