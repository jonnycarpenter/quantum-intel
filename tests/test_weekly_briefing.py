"""
Test Weekly Briefing
====================

Tests for models, strategic priorities, JSON parser, storage round-trip,
and pipeline assembly (with mocked LLM).
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.weekly_briefing import (
    WeeklyBriefing, BriefingSection, VoiceQuote, Citation,
    MarketMover, ResearchPaper, PreBrief, PreBriefObservation,
)
from config.strategic_priorities import (
    QUANTUM_PRIORITIES, AI_PRIORITIES, DOMAIN_PRIORITIES,
    get_priority_for_category, format_priorities_block,
)
from config.settings import WeeklyBriefingConfig
from processing.weekly_briefing import WeeklyBriefingPipeline


# =============================================================================
# MODEL ROUND-TRIP TESTS
# =============================================================================

def test_pre_brief_observation_round_trip():
    """PreBriefObservation serializes and deserializes correctly."""
    obs = PreBriefObservation(
        topic="IonQ demonstrates quantum advantage in optimization",
        priority_tag="P1",
        signal_type="milestone",
        companies=["IonQ"],
        technologies=["trapped ion"],
        article_ids=["a1", "a2"],
        summary="IonQ showed 100x speedup over classical for portfolio optimization.",
        relevance_score=0.9,
    )
    d = obs.to_dict()
    restored = PreBriefObservation.from_dict(d)
    assert restored.topic == obs.topic
    assert restored.priority_tag == "P1"
    assert restored.companies == ["IonQ"]
    assert restored.article_ids == ["a1", "a2"]
    assert restored.relevance_score == 0.9


def test_pre_brief_round_trip():
    """PreBrief with observations serializes and deserializes correctly."""
    obs = PreBriefObservation(topic="Test", priority_tag="P2", summary="summary")
    pb = PreBrief(
        domain="quantum",
        observations=[obs],
        article_count=50,
        period_start=datetime(2026, 2, 10, tzinfo=timezone.utc),
        period_end=datetime(2026, 2, 22, tzinfo=timezone.utc),
        batch_count=2,
    )
    d = pb.to_dict()
    restored = PreBrief.from_dict(d)
    assert restored.domain == "quantum"
    assert restored.article_count == 50
    assert len(restored.observations) == 1
    assert restored.observations[0].priority_tag == "P2"
    assert restored.period_start.year == 2026
    assert restored.batch_count == 2


def test_voice_quote_round_trip():
    """VoiceQuote serializes correctly."""
    vq = VoiceQuote(
        text="We expect quantum revenue to double in 2026",
        speaker="Peter Chapman",
        role="CEO",
        company="IonQ",
        source_type="earnings",
        source_context="Q4 2025 Earnings Call",
        relevance_score=0.85,
    )
    d = vq.to_dict()
    restored = VoiceQuote.from_dict(d)
    assert restored.speaker == "Peter Chapman"
    assert restored.source_type == "earnings"
    assert restored.relevance_score == 0.85


def test_citation_round_trip():
    """Citation serializes correctly."""
    c = Citation(
        number=1,
        article_id="abc123",
        title="IonQ Achieves Quantum Advantage",
        url="https://example.com/article",
        source_name="TechCrunch",
        published_at="2026-02-20T10:00:00+00:00",
    )
    d = c.to_dict()
    restored = Citation.from_dict(d)
    assert restored.number == 1
    assert restored.url == "https://example.com/article"


def test_briefing_section_round_trip():
    """BriefingSection with voice quotes and citations serializes correctly."""
    section = BriefingSection(
        header="Quantum Advantage Breakthroughs",
        priority_tag="P1",
        priority_label="Quantum Advantage",
        narrative="IonQ demonstrated a 100x speedup [1] in optimization problems.",
        voice_quotes=[
            VoiceQuote(text="This changes everything", speaker="CEO", source_type="earnings"),
        ],
        citations=[
            Citation(number=1, title="IonQ Breakthrough", url="https://example.com"),
        ],
        has_content=True,
    )
    d = section.to_dict()
    restored = BriefingSection.from_dict(d)
    assert restored.has_content is True
    assert restored.priority_tag == "P1"
    assert len(restored.voice_quotes) == 1
    assert len(restored.citations) == 1
    assert restored.voice_quotes[0].speaker == "CEO"


def test_market_mover_round_trip():
    """MarketMover serializes correctly."""
    mm = MarketMover(
        ticker="IONQ",
        company_name="IonQ Inc.",
        close=15.42,
        change_pct=12.3,
        context_text="Following quantum advantage announcement",
        linked_article_ids=["a1"],
    )
    d = mm.to_dict()
    restored = MarketMover.from_dict(d)
    assert restored.ticker == "IONQ"
    assert restored.change_pct == 12.3
    assert restored.close == 15.42


def test_research_paper_round_trip():
    """ResearchPaper serializes correctly."""
    rp = ResearchPaper(
        arxiv_id="2602.12345",
        title="Fault-Tolerant Quantum Computing with Cat Qubits",
        authors=["Alice", "Bob", "Charlie"],
        why_it_matters="Reduces overhead for fault tolerance by 10x",
        commercial_readiness="near_term",
        relevance_score=8.5,
        abs_url="https://arxiv.org/abs/2602.12345",
    )
    d = rp.to_dict()
    restored = ResearchPaper.from_dict(d)
    assert restored.arxiv_id == "2602.12345"
    assert len(restored.authors) == 3
    assert restored.commercial_readiness == "near_term"


def test_weekly_briefing_full_round_trip():
    """Full WeeklyBriefing with all nested objects round-trips correctly."""
    briefing = WeeklyBriefing(
        domain="quantum",
        week_of="2026-02-17",
        sections=[
            BriefingSection(
                header="Quantum Advantage",
                priority_tag="P1",
                priority_label="Quantum Advantage",
                narrative="Big news this week [1].",
                voice_quotes=[VoiceQuote(text="Quote", speaker="CEO", source_type="earnings")],
                citations=[Citation(number=1, title="Article", url="https://example.com")],
                has_content=True,
            ),
            BriefingSection(
                header="Error Correction",
                priority_tag="P2",
                priority_label="Error Correction & Logical Qubits",
                has_content=False,
            ),
        ],
        market_movers=[
            MarketMover(ticker="IONQ", close=15.0, change_pct=8.5, context_text="Big week"),
        ],
        research_papers=[
            ResearchPaper(arxiv_id="2602.11111", title="Paper", authors=["Alice"]),
        ],
        articles_analyzed=150,
        sections_active=1,
        sections_total=7,
        generation_cost_usd=0.1234,
    )
    d = briefing.to_dict()

    # Verify JSON serialization works
    json_str = json.dumps(d, default=str)
    assert len(json_str) > 100

    # Round-trip
    restored = WeeklyBriefing.from_dict(d)
    assert restored.domain == "quantum"
    assert restored.week_of == "2026-02-17"
    assert len(restored.sections) == 2
    assert restored.sections[0].has_content is True
    assert restored.sections[1].has_content is False
    assert len(restored.market_movers) == 1
    assert len(restored.research_papers) == 1
    assert restored.articles_analyzed == 150
    assert restored.sections_active == 1
    assert restored.generation_cost_usd == 0.1234


# =============================================================================
# STRATEGIC PRIORITIES TESTS
# =============================================================================

def test_quantum_priorities_count():
    """Quantum domain has exactly 5 priorities."""
    assert len(QUANTUM_PRIORITIES) == 5


def test_ai_priorities_count():
    """AI domain has exactly 5 priorities."""
    assert len(AI_PRIORITIES) == 5


def test_priority_tags_sequential():
    """Priority tags are P1-P5 for both domains."""
    for priorities in [QUANTUM_PRIORITIES, AI_PRIORITIES]:
        tags = [p.tag for p in priorities]
        assert tags == ["P1", "P2", "P3", "P4", "P5"]


def test_quantum_p1_is_quantum_advantage():
    """Quantum P1 is 'Quantum Advantage'."""
    assert QUANTUM_PRIORITIES[0].label == "Quantum Advantage"


def test_ai_p1_is_enterprise_roi():
    """AI P1 is 'Enterprise AI & ROI'."""
    assert AI_PRIORITIES[0].label == "Enterprise AI & ROI"


def test_category_mapping_quantum():
    """Quantum categories map to correct priorities."""
    assert get_priority_for_category("use_case_finance", "quantum") == "P1"
    assert get_priority_for_category("error_correction", "quantum") == "P2"
    assert get_priority_for_category("hardware_milestone", "quantum") == "P3"
    assert get_priority_for_category("funding_ipo", "quantum") == "P4"
    assert get_priority_for_category("policy_regulation", "quantum") == "P5"


def test_category_mapping_ai():
    """AI categories map to correct priorities."""
    assert get_priority_for_category("ai_use_case_enterprise", "ai") == "P1"
    assert get_priority_for_category("ai_model_release", "ai") == "P2"
    assert get_priority_for_category("ai_safety_alignment", "ai") == "P3"
    assert get_priority_for_category("ai_infrastructure", "ai") == "P4"
    assert get_priority_for_category("ai_open_source", "ai") == "P5"


def test_unmapped_category_returns_unmatched():
    """Unknown categories return 'unmatched'."""
    assert get_priority_for_category("nonexistent_category", "quantum") == "unmatched"
    assert get_priority_for_category("nonexistent_category", "ai") == "unmatched"


def test_domain_priorities_map():
    """DOMAIN_PRIORITIES has both domains."""
    assert "quantum" in DOMAIN_PRIORITIES
    assert "ai" in DOMAIN_PRIORITIES


def test_format_priorities_block():
    """format_priorities_block produces readable text with all tags."""
    block = format_priorities_block("quantum")
    assert "P1:" in block
    assert "P5:" in block
    assert "Quantum Advantage" in block

    ai_block = format_priorities_block("ai")
    assert "Enterprise AI & ROI" in ai_block


# =============================================================================
# JSON PARSER TESTS
# =============================================================================

def test_json_parser_direct():
    """Tier 1: Direct JSON parse."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    result = pipeline._parse_json_robust('[{"topic": "test"}]')
    assert isinstance(result, list)
    assert result[0]["topic"] == "test"


def test_json_parser_code_block():
    """Tier 2: JSON inside ```json code block."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    text = 'Here is the analysis:\n```json\n[{"topic": "code block test"}]\n```\nEnd.'
    result = pipeline._parse_json_robust(text)
    assert isinstance(result, list)
    assert result[0]["topic"] == "code block test"


def test_json_parser_embedded():
    """Tier 3: JSON embedded in surrounding text."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    text = 'Here is the output:\n{"sections": [{"header": "test"}]}\nDone.'
    result = pipeline._parse_json_robust(text)
    assert isinstance(result, dict)
    assert result["sections"][0]["header"] == "test"


def test_json_parser_empty():
    """Empty or None input returns None."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    assert pipeline._parse_json_robust("") is None
    assert pipeline._parse_json_robust("   ") is None


def test_json_parser_garbage():
    """Completely unparseable text returns None."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    assert pipeline._parse_json_robust("This is just plain text with no JSON.") is None


# =============================================================================
# STORAGE ROUND-TRIP TEST
# =============================================================================

def test_storage_round_trip():
    """Save and retrieve a weekly briefing from SQLite."""
    from storage.sqlite import SQLiteStorage

    async def _run():
        db_path = "data/test_weekly_briefing.db"
        storage = SQLiteStorage(db_path=db_path)

        briefing = WeeklyBriefing(
            domain="quantum",
            week_of="2026-02-17",
            sections=[
                BriefingSection(
                    header="Quantum Advantage",
                    priority_tag="P1",
                    priority_label="Quantum Advantage",
                    narrative="Testing storage [1].",
                    voice_quotes=[VoiceQuote(text="Test quote", speaker="CEO", source_type="earnings")],
                    citations=[Citation(number=1, title="Test Article", url="https://test.com")],
                    has_content=True,
                ),
            ],
            market_movers=[
                MarketMover(ticker="IONQ", close=15.0, change_pct=8.5, context_text="test"),
            ],
            research_papers=[
                ResearchPaper(arxiv_id="2602.99999", title="Test Paper", authors=["Author"]),
            ],
            articles_analyzed=100,
            sections_active=1,
            sections_total=7,
            generation_cost_usd=0.05,
        )

        # Save
        briefing_id = await storage.save_weekly_briefing(briefing)
        assert briefing_id

        # Retrieve latest
        retrieved = await storage.get_latest_weekly_briefing(domain="quantum")
        assert retrieved is not None
        assert retrieved.domain == "quantum"
        assert retrieved.week_of == "2026-02-17"
        assert len(retrieved.sections) == 1
        assert retrieved.sections[0].has_content is True
        assert retrieved.sections[0].voice_quotes[0].text == "Test quote"
        assert len(retrieved.market_movers) == 1
        assert retrieved.market_movers[0].ticker == "IONQ"
        assert len(retrieved.research_papers) == 1
        assert retrieved.articles_analyzed == 100

        # Retrieve by week
        by_week = await storage.get_weekly_briefing_by_week("quantum", "2026-02-17")
        assert by_week is not None
        assert by_week.id == retrieved.id

        # Domain isolation
        ai_briefing = await storage.get_latest_weekly_briefing(domain="ai")
        assert ai_briefing is None

        await storage.close()

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

    asyncio.run(_run())


# =============================================================================
# PIPELINE TESTS (mocked LLM)
# =============================================================================

def test_empty_briefing_structure():
    """_empty_briefing returns a valid WeeklyBriefing with all sections inactive."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    pipeline.config = WeeklyBriefingConfig()

    briefing = pipeline._empty_briefing("quantum")
    assert briefing.domain == "quantum"
    assert briefing.sections_active == 0
    assert len(briefing.sections) == 5  # P1-P5
    for s in briefing.sections:
        assert s.has_content is False


def test_empty_briefing_ai():
    """_empty_briefing for AI domain has AI-specific labels."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    pipeline.config = WeeklyBriefingConfig()

    briefing = pipeline._empty_briefing("ai")
    assert briefing.domain == "ai"
    labels = [s.priority_label for s in briefing.sections]
    assert "Enterprise AI & ROI" in labels
    assert "Open Source Dynamics" in labels


def test_market_mover_threshold():
    """Market movers should only include tickers with >5% change."""
    pipeline = WeeklyBriefingPipeline.__new__(WeeklyBriefingPipeline)
    pipeline.config = WeeklyBriefingConfig()

    # Simulate filtering logic
    candidates = [
        {"ticker": "IONQ", "change_pct": 12.0, "close": 15.0},
        {"ticker": "GOOGL", "change_pct": 2.0, "close": 180.0},
        {"ticker": "RGTI", "change_pct": -8.0, "close": 3.0},
        {"ticker": "IBM", "change_pct": 4.9, "close": 200.0},
    ]
    threshold = pipeline.config.market_mover_threshold_pct
    filtered = [c for c in candidates if abs(c["change_pct"]) >= threshold]

    assert len(filtered) == 2
    tickers = [c["ticker"] for c in filtered]
    assert "IONQ" in tickers
    assert "RGTI" in tickers
    assert "GOOGL" not in tickers
    assert "IBM" not in tickers


def test_config_defaults():
    """WeeklyBriefingConfig has expected default values."""
    cfg = WeeklyBriefingConfig()
    assert "sonnet" in cfg.research_model
    assert "opus" in cfg.briefing_model
    assert cfg.research_batch_size == 40
    assert cfg.lookback_days == 14
    assert cfg.market_mover_threshold_pct == 5.0
    assert cfg.max_quotes_per_ticker == 3
    assert cfg.max_nuggets_per_ticker == 3
    assert cfg.max_podcast_quotes == 10
    assert cfg.briefing_max_tokens == 16000
