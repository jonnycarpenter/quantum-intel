"""
Test Earnings Models
====================

Tests for EarningsTranscript, ExtractedQuote, and related enums.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from models.earnings import (
    EarningsTranscript,
    ExtractedQuote,
    QuoteExtractionResult,
    SpeakerRole,
    QuoteType,
    ConfidenceLevel,
    CallSection,
)


def test_transcript_creation():
    """Test creating an EarningsTranscript."""
    t = EarningsTranscript(
        ticker="IONQ",
        company_name="IonQ Inc.",
        year=2025,
        quarter=3,
        transcript_text="Good morning everyone. Welcome to the Q3 earnings call...",
    )
    assert t.ticker == "IONQ"
    assert t.year == 2025
    assert t.quarter == 3
    assert t.transcript_id  # UUID generated
    assert t.char_count == len(t.transcript_text)
    assert t.unique_key == "IONQ_2025_Q3"


def test_transcript_unique_key():
    """Test unique key format for dedup."""
    t = EarningsTranscript(
        ticker="QBTS",
        company_name="D-Wave Quantum Inc.",
        year=2024,
        quarter=4,
        transcript_text="Hello.",
    )
    assert t.unique_key == "QBTS_2024_Q4"


def test_quote_creation():
    """Test creating an ExtractedQuote with all fields."""
    q = ExtractedQuote(
        transcript_id="test-transcript-123",
        quote_text="We expect to achieve quantum advantage by 2026",
        speaker_name="Peter Chapman",
        speaker_role=SpeakerRole.CEO,
        quote_type=QuoteType.TIMELINE_OUTLOOK,
        ticker="IONQ",
        company_name="IonQ Inc.",
        year=2025,
        quarter=3,
    )
    assert q.speaker_role == SpeakerRole.CEO
    assert q.quote_type == QuoteType.TIMELINE_OUTLOOK
    assert q.relevance_score == 0.5  # default
    assert q.is_quotable is False  # default
    assert q.quote_id  # UUID generated


def test_quote_to_dict():
    """Test quote serialization to dict."""
    q = ExtractedQuote(
        transcript_id="test-123",
        quote_text="Revenue grew 25% year over year",
        speaker_name="Thomas Kramer",
        speaker_role=SpeakerRole.CFO,
        quote_type=QuoteType.REVENUE_METRIC,
        themes=["revenue_growth", "financial_performance"],
        companies_mentioned=["IonQ"],
        technologies_mentioned=["trapped ion"],
        relevance_score=0.85,
        is_quotable=True,
        quotability_reason="Direct revenue metric",
        ticker="IONQ",
        company_name="IonQ Inc.",
        year=2025,
        quarter=3,
        section=CallSection.PREPARED_REMARKS,
    )
    d = q.to_dict()
    assert d["speaker_role"] == "cfo"
    assert d["quote_type"] == "revenue_metric"
    assert d["themes"] == "revenue_growth,financial_performance"
    assert d["companies_mentioned"] == "IonQ"
    assert d["relevance_score"] == 0.85
    assert d["is_quotable"] is True
    assert d["section"] == "prepared_remarks"


def test_quote_from_dict():
    """Test deserializing a quote from dict (DB round-trip)."""
    d = {
        "quote_id": "q-123",
        "transcript_id": "t-456",
        "quote_text": "We see strong demand",
        "context_before": "",
        "context_after": "",
        "speaker_name": "CEO",
        "speaker_role": "ceo",
        "speaker_title": "CEO",
        "speaker_company": "IonQ",
        "speaker_firm": None,
        "quote_type": "strategy",
        "themes": "quantum_hardware,partnerships",
        "sentiment": "bullish",
        "confidence_level": "cautious",
        "companies_mentioned": "IBM,Google",
        "technologies_mentioned": "trapped ion",
        "competitors_mentioned": "IBM",
        "metrics_mentioned": "",
        "relevance_score": 0.9,
        "is_quotable": 1,
        "quotability_reason": "Strategic direction",
        "ticker": "IONQ",
        "company_name": "IonQ Inc.",
        "year": 2025,
        "quarter": 3,
        "call_date": None,
        "section": "prepared_remarks",
        "position_in_section": 0,
        "extracted_at": "2025-01-15T10:00:00+00:00",
        "extraction_model": "claude-sonnet-4-6-20250514",
        "extraction_confidence": 0.85,
    }
    q = ExtractedQuote.from_dict(d)
    assert q.quote_id == "q-123"
    assert q.speaker_role == SpeakerRole.CEO
    assert q.quote_type == QuoteType.STRATEGY
    assert q.themes == ["quantum_hardware", "partnerships"]
    assert q.companies_mentioned == ["IBM", "Google"]
    assert q.is_quotable is True
    assert q.relevance_score == 0.9


def test_extraction_result():
    """Test QuoteExtractionResult."""
    quotes = [
        ExtractedQuote(
            transcript_id="t-1",
            quote_text="Quote 1",
            speaker_name="CEO",
            ticker="IONQ",
            company_name="IonQ",
            year=2025,
            quarter=3,
        ),
        ExtractedQuote(
            transcript_id="t-1",
            quote_text="Quote 2",
            speaker_name="CFO",
            ticker="IONQ",
            company_name="IonQ",
            year=2025,
            quarter=3,
        ),
    ]
    result = QuoteExtractionResult(
        transcript_id="t-1",
        ticker="IONQ",
        company_name="IonQ",
        quotes=quotes,
        total_quotes=2,
        extraction_model="claude-sonnet-4-6-20250514",
    )
    assert result.total_quotes == 2
    assert len(result.quotes) == 2


def test_speaker_role_enum():
    """Test SpeakerRole enum values."""
    assert SpeakerRole.CEO.value == "ceo"
    assert SpeakerRole.ANALYST.value == "analyst"
    assert SpeakerRole("cfo") == SpeakerRole.CFO


def test_quote_type_enum():
    """Test QuoteType enum covers all quantum categories."""
    expected = {
        "strategy", "guidance", "competitive", "technology_milestone",
        "timeline_outlook", "risk_factor", "analyst_pressure",
        "partnership", "revenue_metric",
    }
    actual = {qt.value for qt in QuoteType}
    assert actual == expected


def test_confidence_level_enum():
    """Test ConfidenceLevel enum values."""
    assert ConfidenceLevel.DEFINITIVE.value == "definitive"
    assert ConfidenceLevel.SPECULATIVE.value == "speculative"
