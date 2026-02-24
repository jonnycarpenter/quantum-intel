"""
Test Podcast Models & Pipeline Components
==========================================

Tests for PodcastEpisode, PodcastTranscript, PodcastQuote,
PodcastQuoteExtractor, PodcastFetcher, and storage round-trips.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timezone

from models.podcast import (
    PodcastEpisode,
    PodcastTranscript,
    PodcastQuote,
    PodcastQuoteExtractionResult,
    EpisodeStatus,
    TranscriptSource,
    PodcastQuoteTheme,
    PodcastQuoteType,
)
from config.podcast_sources import (
    ALL_PODCAST_SOURCES,
    ENABLED_PODCAST_SOURCES,
    PODCAST_SOURCE_MAP,
    THE_NEW_QUANTUM_ERA,
    THE_SUPERPOSITION_GUY,
    THE_QUANTUM_DIVIDE,
    IMPACT_QUANTUM,
    QUANTUM_TECH_POD,
    IEEE_QUANTUM_PODCAST,
    COGNITIVE_REVOLUTION,
    LATENT_SPACE,
    PRACTICAL_AI,
    TWIML_AI,
    NO_PRIORS,
    LAST_WEEK_IN_AI,
    HARD_FORK,
)


# ============================================================================
# Model Tests
# ============================================================================

def test_episode_creation():
    """Test creating a PodcastEpisode."""
    ep = PodcastEpisode(
        episode_id="ep-001",
        podcast_id="new-quantum-era",
        title="Episode 79: Quantum Error Correction Advances",
        audio_url="https://example.com/audio.mp3",
    )
    assert ep.episode_id == "ep-001"
    assert ep.podcast_id == "new-quantum-era"
    assert ep.status == EpisodeStatus.PENDING.value
    assert ep.audio_url is not None


def test_episode_unique_key():
    """Test unique key format."""
    ep = PodcastEpisode(
        episode_id="ep-042",
        podcast_id="new-quantum-era",
        title="Quantum Networking Deep Dive",
    )
    assert ep.unique_key == "new-quantum-era:Quantum Networking Deep Dive"


def test_transcript_creation():
    """Test creating a PodcastTranscript."""
    text = "Speaker A: Welcome to the show. Speaker B: Thanks for having me."
    t = PodcastTranscript(
        episode_id="ep-001",
        podcast_id="new-quantum-era",
        podcast_name="The New Quantum Era",
        episode_title="Quantum Error Correction",
        full_text=text,
        char_count=len(text),
        word_count=len(text.split()),
    )
    assert t.transcript_id  # UUID generated
    assert t.podcast_id == "new-quantum-era"
    assert t.char_count == len(text)
    assert t.word_count > 0
    assert "new-quantum-era" in t.unique_key


def test_transcript_defaults():
    """Test default values on transcript."""
    t = PodcastTranscript(
        episode_id="ep-002",
        podcast_id="test_pod",
        podcast_name="Test Podcast",
        episode_title="Test Episode",
    )
    assert t.transcript_source == TranscriptSource.ASSEMBLYAI.value
    assert t.hosts == []
    assert t.speaker_count == 0


def test_quote_creation():
    """Test creating a PodcastQuote with all fields."""
    q = PodcastQuote(
        transcript_id="trans-123",
        episode_id="ep-001",
        quote_text="We've achieved a 10x improvement in logical qubit error rates",
        speaker_name="Dr. Jane Smith",
        speaker_role="guest",
        speaker_title="Chief Scientist",
        speaker_company="QuEra Computing",
        quote_type=PodcastQuoteType.TECHNICAL_INSIGHT.value,
        themes="hardware_progress, error_correction",
        relevance_score=0.92,
        is_quotable=True,
        quotability_reason="First public disclosure of new error rates",
        podcast_id="new-quantum-era",
        podcast_name="The New Quantum Era",
        episode_title="Quantum Error Correction",
    )
    assert q.quote_id  # UUID generated
    assert q.relevance_score == 0.92
    assert q.is_quotable is True
    assert "error_correction" in q.themes


def test_quote_to_dict_roundtrip():
    """Test quote serialization and deserialization."""
    now = datetime.now(timezone.utc)
    q = PodcastQuote(
        transcript_id="trans-123",
        episode_id="ep-001",
        quote_text="Quantum computing will transform drug discovery within 5 years",
        speaker_name="Dr. John Doe",
        speaker_role="guest",
        quote_type=PodcastQuoteType.PREDICTION.value,
        themes="commercial_readiness, use_case_insight",
        sentiment="bullish",
        companies_mentioned="Pfizer, Merck",
        technologies_mentioned="variational quantum eigensolver",
        relevance_score=0.78,
        podcast_id="new-quantum-era",
        podcast_name="The New Quantum Era",
        episode_title="Pharma Meets Quantum",
        extracted_at=now,
    )

    data = q.to_dict()
    assert isinstance(data, dict)
    assert data["quote_text"] == q.quote_text
    assert data["speaker_name"] == "Dr. John Doe"
    assert data["relevance_score"] == 0.78

    # Roundtrip
    q2 = PodcastQuote.from_dict(data)
    assert q2.quote_text == q.quote_text
    assert q2.speaker_name == q.speaker_name
    assert q2.relevance_score == q.relevance_score
    assert q2.podcast_id == "new-quantum-era"


def test_extraction_result():
    """Test PodcastQuoteExtractionResult creation."""
    result = PodcastQuoteExtractionResult(
        episode_id="ep-001",
        podcast_id="new-quantum-era",
        quotes=[],
        total_extracted=0,
        extraction_model="claude-sonnet-4-6",
        extraction_cost_usd=0.012,
    )
    assert result.total_extracted == 0
    assert result.error is None
    assert result.extraction_cost_usd == 0.012


# ============================================================================
# Enum Tests
# ============================================================================

def test_episode_status_enum():
    """Test EpisodeStatus enum values."""
    assert EpisodeStatus.PENDING.value == "pending"
    assert EpisodeStatus.TRANSCRIBING.value == "transcribing"
    assert EpisodeStatus.COMPLETED.value == "completed"
    assert EpisodeStatus.FAILED.value == "failed"


def test_transcript_source_enum():
    """Test TranscriptSource enum values."""
    assert TranscriptSource.ASSEMBLYAI.value == "assemblyai"
    assert TranscriptSource.YOUTUBE_CAPTIONS.value == "youtube_captions"
    assert TranscriptSource.SHOW_NOTES.value == "show_notes"


def test_quote_theme_enum():
    """Test PodcastQuoteTheme has all 25 themes (15 quantum + 10 AI)."""
    themes = list(PodcastQuoteTheme)
    assert len(themes) == 25
    # Quantum themes
    assert PodcastQuoteTheme.HARDWARE_PROGRESS in themes
    assert PodcastQuoteTheme.ERROR_CORRECTION in themes
    assert PodcastQuoteTheme.COMPETITIVE_LANDSCAPE in themes
    assert PodcastQuoteTheme.QUANTUM_NETWORKING in themes
    # AI themes
    assert PodcastQuoteTheme.LLM_CAPABILITIES in themes
    assert PodcastQuoteTheme.AI_SAFETY_ALIGNMENT in themes
    assert PodcastQuoteTheme.AI_AGENTS in themes
    assert PodcastQuoteTheme.ENTERPRISE_AI in themes


def test_quote_type_enum():
    """Test PodcastQuoteType has all 8 types."""
    types = list(PodcastQuoteType)
    assert len(types) == 8
    assert PodcastQuoteType.TECHNICAL_INSIGHT in types
    assert PodcastQuoteType.PREDICTION in types
    assert PodcastQuoteType.ANALOGY in types


# ============================================================================
# Config Tests
# ============================================================================

def test_podcast_sources_defined():
    """Test that podcast sources are properly configured."""
    assert len(ALL_PODCAST_SOURCES) == 13
    assert THE_NEW_QUANTUM_ERA in ALL_PODCAST_SOURCES
    assert IMPACT_QUANTUM in ALL_PODCAST_SOURCES
    assert COGNITIVE_REVOLUTION in ALL_PODCAST_SOURCES
    assert LATENT_SPACE in ALL_PODCAST_SOURCES


def test_all_podcasts_enabled():
    """All 13 podcasts should be enabled."""
    assert len(ENABLED_PODCAST_SOURCES) == 13
    for src in ENABLED_PODCAST_SOURCES:
        assert src.enabled is True


def test_enabled_podcasts_have_rss():
    """All enabled podcasts must have RSS URLs."""
    for src in ENABLED_PODCAST_SOURCES:
        assert src.rss_url, f"{src.name} is enabled but has no RSS URL"
        assert src.enabled is True


def test_podcast_source_map():
    """Test that source map has correct keys."""
    assert "new-quantum-era" in PODCAST_SOURCE_MAP
    assert "impact-quantum" in PODCAST_SOURCE_MAP
    assert "quantum-divide" in PODCAST_SOURCE_MAP
    assert PODCAST_SOURCE_MAP["new-quantum-era"].name == "The New Quantum Era"


def test_the_new_quantum_era_config():
    """Verify The New Quantum Era source config."""
    src = THE_NEW_QUANTUM_ERA
    assert src.podcast_id == "new-quantum-era"
    assert "feeds.transistor.fm" in src.rss_url
    assert "Sebastian Hassinger" in src.hosts
    assert src.enabled is True


def test_impact_quantum_config():
    """Verify Impact Quantum source config."""
    src = IMPACT_QUANTUM
    assert src.podcast_id == "impact-quantum"
    assert "captivate.fm" in src.rss_url
    assert "Candace Gillhoolley" in src.hosts
    assert src.enabled is True


def test_superposition_guy_config():
    """Verify Superposition Guy source config."""
    src = THE_SUPERPOSITION_GUY
    assert src.podcast_id == "superposition-guy"
    assert "yboger.com" in src.rss_url
    assert "Yuval Boger" in src.hosts
    assert src.enabled is True


def test_quantum_divide_config():
    """Verify Quantum Divide source config."""
    src = THE_QUANTUM_DIVIDE
    assert src.podcast_id == "quantum-divide"
    assert "transistor.fm" in src.rss_url
    assert "Dan Holme" in src.hosts
    assert src.enabled is True
    assert src.domain == "quantum"


def test_cognitive_revolution_config():
    """Verify Cognitive Revolution AI podcast config."""
    src = COGNITIVE_REVOLUTION
    assert src.podcast_id == "cognitive-revolution"
    assert "megaphone.fm" in src.rss_url
    assert "Nathan Labenz" in src.hosts
    assert src.enabled is True
    assert src.domain == "ai"


def test_latent_space_config():
    """Verify Latent Space AI podcast config."""
    src = LATENT_SPACE
    assert src.podcast_id == "latent-space"
    assert "flightcast.com" in src.rss_url
    assert "swyx" in src.hosts
    assert src.domain == "ai"


def test_no_priors_config():
    """Verify No Priors AI podcast config."""
    src = NO_PRIORS
    assert src.podcast_id == "no-priors"
    assert "megaphone.fm" in src.rss_url
    assert "Sarah Guo" in src.hosts
    assert src.domain == "ai"


def test_quantum_podcasts_default_domain():
    """Quantum podcasts should have domain='quantum' by default."""
    quantum_sources = [THE_NEW_QUANTUM_ERA, THE_SUPERPOSITION_GUY, THE_QUANTUM_DIVIDE,
                       IMPACT_QUANTUM, QUANTUM_TECH_POD, IEEE_QUANTUM_PODCAST]
    for src in quantum_sources:
        assert src.domain == "quantum", f"{src.name} has wrong domain: {src.domain}"


def test_ai_podcasts_domain():
    """AI podcasts should have domain='ai'."""
    ai_sources = [COGNITIVE_REVOLUTION, LATENT_SPACE, PRACTICAL_AI,
                  TWIML_AI, NO_PRIORS, LAST_WEEK_IN_AI, HARD_FORK]
    for src in ai_sources:
        assert src.domain == "ai", f"{src.name} has wrong domain: {src.domain}"


# ============================================================================
# Quote Extractor Unit Tests
# ============================================================================

def test_extractor_chunking():
    """Test text chunking for long transcripts."""
    from processing.podcast_quote_extractor import PodcastQuoteExtractor

    ext = PodcastQuoteExtractor()

    # Short text — single chunk
    short = "Hello " * 100
    chunks = ext._chunk_text(short)
    assert len(chunks) == 1

    # Long text — multiple chunks
    long_text = "A" * 65_000
    chunks = ext._chunk_text(long_text)
    assert len(chunks) > 1
    # Verify all text is covered
    assert all(len(c) <= ext.CHUNK_SIZE for c in chunks)


def test_extractor_deduplication():
    """Test quote deduplication across chunks."""
    from processing.podcast_quote_extractor import PodcastQuoteExtractor

    ext = PodcastQuoteExtractor()
    now = datetime.now(timezone.utc)

    q1 = PodcastQuote(
        transcript_id="t1", episode_id="e1",
        quote_text="We achieved 99.9 percent fidelity on our two qubit gates this quarter in our lab",
        speaker_name="Dr. Smith", speaker_role="guest",
        relevance_score=0.9,
        podcast_id="p1", podcast_name="Test", episode_title="Ep 1",
        extracted_at=now,
    )
    q2 = PodcastQuote(
        transcript_id="t1", episode_id="e1",
        quote_text="We achieved 99.9 percent fidelity on our two qubit gates this quarter in our lab results",
        speaker_name="Dr. Smith", speaker_role="guest",
        relevance_score=0.85,
        podcast_id="p1", podcast_name="Test", episode_title="Ep 1",
        extracted_at=now,
    )
    q3 = PodcastQuote(
        transcript_id="t1", episode_id="e1",
        quote_text="The market for quantum computing is growing rapidly across multiple sectors worldwide",
        speaker_name="Mr. Jones", speaker_role="host",
        relevance_score=0.6,
        podcast_id="p1", podcast_name="Test", episode_title="Ep 1",
        extracted_at=now,
    )

    deduped = ext._deduplicate_quotes([q1, q2, q3])
    # q1 and q2 are near-duplicates; q3 is distinct
    assert len(deduped) == 2
    # Higher relevance should be kept
    texts = [q.quote_text for q in deduped]
    assert q1.quote_text in texts  # Higher relevance
    assert q3.quote_text in texts  # Distinct


def test_text_similarity():
    """Test word-overlap similarity calculation."""
    from processing.podcast_quote_extractor import PodcastQuoteExtractor

    sim = PodcastQuoteExtractor._text_similarity

    # Identical
    assert sim("hello world", "hello world") == 1.0

    # Completely different
    assert sim("hello world", "foo bar") == 0.0

    # Partial overlap
    score = sim(
        "quantum computing advances rapidly",
        "quantum computing progresses rapidly forward"
    )
    assert 0.3 < score < 0.8

    # Empty
    assert sim("", "hello") == 0.0


# ============================================================================
# Storage Round-Trip Tests
# ============================================================================

def test_storage_podcast_transcript_roundtrip():
    """Test saving and retrieving podcast transcripts via SQLite."""
    from storage.sqlite import SQLiteStorage
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    storage = None
    try:
        storage = SQLiteStorage(db_path=db_path)

        transcript = PodcastTranscript(
            episode_id="ep-test-001",
            podcast_id="new-quantum-era",
            podcast_name="The New Quantum Era",
            episode_title="Test Episode: Storage Round-Trip",
            full_text="Host: Welcome. Guest: Thank you for having me.",
            formatted_text="[Sebastian Hassinger]: Welcome.\n[Dr. Expert]: Thank you for having me.",
            hosts=["Sebastian Hassinger"],
            guest_name="Dr. Expert",
            guest_title="Professor",
            guest_company="MIT",
            transcript_source=TranscriptSource.ASSEMBLYAI.value,
            status=EpisodeStatus.COMPLETED,
        )

        # Save
        tid = asyncio.get_event_loop().run_until_complete(
            storage.save_podcast_transcript(transcript)
        )
        assert tid == transcript.transcript_id

        # Check exists
        exists = asyncio.get_event_loop().run_until_complete(
            storage.podcast_episode_exists("new-quantum-era", "ep-test-001")
        )
        assert exists is True

        # Check non-existent
        not_exists = asyncio.get_event_loop().run_until_complete(
            storage.podcast_episode_exists("new-quantum-era", "ep-nonexistent")
        )
        assert not_exists is False

    finally:
        if storage:
            asyncio.get_event_loop().run_until_complete(storage.close())
        try:
            os.unlink(db_path)
        except PermissionError:
            pass


def test_storage_podcast_quotes_roundtrip():
    """Test saving and searching podcast quotes via SQLite."""
    from storage.sqlite import SQLiteStorage
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    storage = None
    try:
        storage = SQLiteStorage(db_path=db_path)
        now = datetime.now(timezone.utc)

        # Must save a transcript first (FK constraint)
        transcript = PodcastTranscript(
            transcript_id="trans-001",
            episode_id="ep-001",
            podcast_id="new-quantum-era",
            podcast_name="The New Quantum Era",
            episode_title="The Race to Scale",
            full_text="Host: Welcome. Guest: Thank you.",
        )
        asyncio.get_event_loop().run_until_complete(
            storage.save_podcast_transcript(transcript)
        )

        quotes = [
            PodcastQuote(
                transcript_id="trans-001",
                episode_id="ep-001",
                quote_text="Neutral atom quantum computers will reach 10,000 qubits by 2028",
                speaker_name="Dr. Alex",
                speaker_role="guest",
                quote_type="prediction",
                themes="hardware_progress, competitive_landscape",
                companies_mentioned="QuEra, Atom Computing",
                technologies_mentioned="neutral atoms",
                relevance_score=0.95,
                is_quotable=True,
                quotability_reason="Bold timeline prediction from industry insider",
                podcast_id="new-quantum-era",
                podcast_name="The New Quantum Era",
                episode_title="The Race to Scale",
                extracted_at=now,
            ),
            PodcastQuote(
                transcript_id="trans-001",
                episode_id="ep-001",
                quote_text="Error correction is the single biggest challenge remaining",
                speaker_name="Sebastian Hassinger",
                speaker_role="host",
                quote_type="opinion",
                themes="error_correction",
                relevance_score=0.7,
                podcast_id="new-quantum-era",
                podcast_name="The New Quantum Era",
                episode_title="The Race to Scale",
                extracted_at=now,
            ),
        ]

        # Save
        saved = asyncio.get_event_loop().run_until_complete(
            storage.save_podcast_quotes(quotes)
        )
        assert saved == 2

        # Get all quotes
        retrieved = asyncio.get_event_loop().run_until_complete(
            storage.get_podcast_quotes(podcast_id="new-quantum-era")
        )
        assert len(retrieved) == 2
        # Should be sorted by relevance DESC
        assert retrieved[0].relevance_score >= retrieved[1].relevance_score

        # Search
        results = asyncio.get_event_loop().run_until_complete(
            storage.search_podcast_quotes("neutral atoms")
        )
        assert len(results) >= 1
        assert "neutral atom" in results[0].quote_text.lower()

        # Search by speaker
        host_quotes = asyncio.get_event_loop().run_until_complete(
            storage.search_podcast_quotes("Sebastian Hassinger")
        )
        assert len(host_quotes) >= 1

    finally:
        if storage:
            asyncio.get_event_loop().run_until_complete(storage.close())
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # Windows file lock — will be cleaned up by OS
