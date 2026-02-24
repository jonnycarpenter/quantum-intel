"""
Podcast Models
==============

Data models for the podcast ingestion pipeline.
Covers podcasts, episodes, transcripts, and extracted quotes.

Uses Python dataclasses (project convention) — NOT Pydantic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


# =============================================================================
# ENUMS — Podcast Pipeline Taxonomy
# =============================================================================

class EpisodeStatus(str, Enum):
    """Processing status for a podcast episode."""
    PENDING = "pending"
    FETCHING_AUDIO = "fetching_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_QUOTES = "extracting_quotes"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TranscriptSource(str, Enum):
    """How the transcript was obtained."""
    ASSEMBLYAI = "assemblyai"           # Paid: audio → text with speaker diarization
    YOUTUBE_CAPTIONS = "youtube_captions"  # Free: pull from YouTube auto/manual captions
    SHOW_NOTES = "show_notes"           # Free: scraped from podcast website
    MANUAL = "manual"                   # Manually provided transcript
    UNKNOWN = "unknown"


class PodcastQuoteTheme(str, Enum):
    """
    Quote themes for podcast content across quantum computing and AI domains.
    These parallel the earnings QuoteTheme but are tailored to
    what guests discuss on podcasts vs. earnings calls.
    """
    # --- Quantum computing themes ---
    HARDWARE_PROGRESS = "hardware_progress"          # Qubit improvements, new architectures
    ERROR_CORRECTION = "error_correction"            # QEC breakthroughs, logical qubits
    ALGORITHM_ADVANCE = "algorithm_advance"          # New algorithms, complexity results
    COMMERCIAL_READINESS = "commercial_readiness"    # Timeline to practical use
    FUNDING_INVESTMENT = "funding_investment"         # VC, government grants, IPOs
    TALENT_WORKFORCE = "talent_workforce"            # Hiring, education, skills gap
    COMPETITIVE_LANDSCAPE = "competitive_landscape"  # Company comparisons, modality debates
    USE_CASE_INSIGHT = "use_case_insight"            # Drug discovery, finance, materials
    POLICY_REGULATION = "policy_regulation"          # Export controls, standards, NIST
    QUANTUM_NETWORKING = "quantum_networking"        # Quantum internet, QKD, entanglement distribution
    QUANTUM_SENSING = "quantum_sensing"              # Sensing applications
    FOUNDATIONAL_SCIENCE = "foundational_science"    # Physics breakthroughs, theory
    INDUSTRY_OUTLOOK = "industry_outlook"            # Market predictions, hype vs reality
    SKEPTICISM_CRITIQUE = "skepticism_critique"      # Honest assessments, challenges
    EDUCATION_OUTREACH = "education_outreach"        # Public understanding, workforce development

    # --- AI / ML themes ---
    LLM_CAPABILITIES = "llm_capabilities"            # Model launches, benchmarks, scaling laws
    AI_SAFETY_ALIGNMENT = "ai_safety_alignment"      # Alignment research, red-teaming, guardrails
    AI_AGENTS = "ai_agents"                          # Autonomous agents, tool use, workflows
    ENTERPRISE_AI = "enterprise_ai"                  # Business adoption, deployment, ROI
    AI_REGULATION_POLICY = "ai_regulation_policy"    # Government policy, EU AI Act, executive orders
    OPEN_SOURCE_AI = "open_source_ai"                # Open weights, community models, licensing
    AI_INFRASTRUCTURE = "ai_infrastructure"          # GPUs, training clusters, inference optimization
    AI_PRODUCT_LAUNCHES = "ai_product_launches"      # New products, features, APIs
    AI_RESEARCH_BREAKTHROUGHS = "ai_research_breakthroughs"  # Papers, novel techniques
    AI_BUSINESS_IMPACT = "ai_business_impact"        # ROI, transformation stories, use cases


class PodcastQuoteType(str, Enum):
    """Type of insight the quote provides."""
    TECHNICAL_INSIGHT = "technical_insight"      # Deep technical explanation
    PREDICTION = "prediction"                    # Future outlook / timeline
    OPINION = "opinion"                          # Expert judgment / perspective
    ANNOUNCEMENT = "announcement"                # Breaking news / first disclosure
    ANALOGY = "analogy"                          # Great explanatory metaphor
    DISAGREEMENT = "disagreement"                # Pushback on conventional wisdom
    RECOMMENDATION = "recommendation"            # Advice for the field
    HISTORICAL_CONTEXT = "historical_context"    # Important background


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PodcastEpisode:
    """
    A single podcast episode discovered from RSS or manual entry.
    This is the unit of work for the pipeline.
    """
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    podcast_id: str = ""              # Links to PodcastSourceConfig.podcast_id
    podcast_name: str = ""
    title: str = ""
    description: str = ""
    published_at: Optional[datetime] = None
    audio_url: Optional[str] = None   # Direct link to audio file (MP3/M4A)
    episode_url: Optional[str] = None  # Link to episode page
    duration_seconds: Optional[int] = None
    season: Optional[int] = None
    episode_number: Optional[int] = None
    guest_name: Optional[str] = None
    guest_title: Optional[str] = None
    guest_company: Optional[str] = None
    hosts: List[str] = field(default_factory=list)

    # Processing state
    status: str = EpisodeStatus.PENDING.value
    error_message: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def unique_key(self) -> str:
        """Human-readable key for logging."""
        return f"{self.podcast_id}:{self.title[:50]}"


@dataclass
class PodcastTranscript:
    """
    Full transcript of a podcast episode.
    May include speaker diarization from AssemblyAI.
    """
    transcript_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    episode_id: str = ""
    podcast_id: str = ""
    podcast_name: str = ""
    episode_title: str = ""
    episode_url: Optional[str] = None
    audio_url: Optional[str] = None
    published_at: Optional[datetime] = None

    # Transcript content
    full_text: str = ""               # Raw transcript text
    formatted_text: Optional[str] = None  # Speaker-labeled version
    word_count: int = 0
    char_count: int = 0
    duration_seconds: Optional[int] = None

    # Speaker diarization metadata
    has_speaker_labels: bool = False
    speaker_count: int = 0
    speakers: List[Dict[str, str]] = field(default_factory=list)
    # e.g. [{"label": "Speaker A", "name": "Sebastian Hassinger", "role": "host"}]

    # Resolution metadata
    transcript_source: str = TranscriptSource.ASSEMBLYAI.value
    status: EpisodeStatus = EpisodeStatus.PENDING
    transcription_cost_usd: float = 0.0

    # Guest/host metadata
    guest_name: Optional[str] = None
    guest_title: Optional[str] = None
    guest_company: Optional[str] = None
    hosts: List[str] = field(default_factory=list)

    # Timestamps
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    transcribed_at: Optional[datetime] = None

    @property
    def unique_key(self) -> str:
        return f"{self.podcast_id}:{self.episode_title[:50]}"


@dataclass
class PodcastQuote:
    """
    An extracted quote from a podcast transcript.
    Parallel to earnings ExtractedQuote but adapted for podcast content.
    """
    quote_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transcript_id: str = ""
    episode_id: str = ""

    # The quote itself
    quote_text: str = ""
    context_before: str = ""
    context_after: str = ""

    # Speaker attribution
    speaker_name: str = ""
    speaker_role: str = "guest"       # "host", "guest", "unknown"
    speaker_title: Optional[str] = None
    speaker_company: Optional[str] = None

    # Classification
    quote_type: str = PodcastQuoteType.TECHNICAL_INSIGHT.value
    themes: str = ""                  # Comma-separated PodcastQuoteTheme values
    sentiment: str = "neutral"        # bullish, bearish, neutral, cautious, excited

    # Entities
    companies_mentioned: str = ""
    technologies_mentioned: str = ""
    people_mentioned: str = ""

    # Relevance
    relevance_score: float = 0.5
    is_quotable: bool = False         # Suitable for digest/newsletter inclusion
    quotability_reason: str = ""

    # Source context
    podcast_id: str = ""
    podcast_name: str = ""
    episode_title: str = ""
    published_at: Optional[str] = None  # ISO string for storage

    # Audit
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_model: str = ""
    extraction_confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SQLite storage."""
        return {
            "quote_id": self.quote_id,
            "transcript_id": self.transcript_id,
            "episode_id": self.episode_id,
            "quote_text": self.quote_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role,
            "speaker_title": self.speaker_title or "",
            "speaker_company": self.speaker_company or "",
            "quote_type": self.quote_type,
            "themes": self.themes,
            "sentiment": self.sentiment,
            "companies_mentioned": self.companies_mentioned,
            "technologies_mentioned": self.technologies_mentioned,
            "people_mentioned": self.people_mentioned,
            "relevance_score": self.relevance_score,
            "is_quotable": self.is_quotable,
            "quotability_reason": self.quotability_reason,
            "podcast_id": self.podcast_id,
            "podcast_name": self.podcast_name,
            "episode_title": self.episode_title,
            "published_at": self.published_at or "",
            "extracted_at": self.extracted_at.isoformat() if isinstance(self.extracted_at, datetime) else str(self.extracted_at),
            "extraction_model": self.extraction_model,
            "extraction_confidence": self.extraction_confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PodcastQuote":
        """Create from dictionary (from SQLite row)."""
        # Handle datetime fields
        extracted_at = data.get("extracted_at")
        if isinstance(extracted_at, str) and extracted_at:
            try:
                extracted_at = datetime.fromisoformat(extracted_at)
            except ValueError:
                extracted_at = datetime.now(timezone.utc)
        elif not isinstance(extracted_at, datetime):
            extracted_at = datetime.now(timezone.utc)

        return cls(
            quote_id=data.get("quote_id", str(uuid.uuid4())),
            transcript_id=data.get("transcript_id", ""),
            episode_id=data.get("episode_id", ""),
            quote_text=data.get("quote_text", ""),
            context_before=data.get("context_before", ""),
            context_after=data.get("context_after", ""),
            speaker_name=data.get("speaker_name", ""),
            speaker_role=data.get("speaker_role", "guest"),
            speaker_title=data.get("speaker_title"),
            speaker_company=data.get("speaker_company"),
            quote_type=data.get("quote_type", PodcastQuoteType.TECHNICAL_INSIGHT.value),
            themes=data.get("themes", ""),
            sentiment=data.get("sentiment", "neutral"),
            companies_mentioned=data.get("companies_mentioned", ""),
            technologies_mentioned=data.get("technologies_mentioned", ""),
            people_mentioned=data.get("people_mentioned", ""),
            relevance_score=float(data.get("relevance_score", 0.5)),
            is_quotable=bool(data.get("is_quotable", False)),
            quotability_reason=data.get("quotability_reason", ""),
            podcast_id=data.get("podcast_id", ""),
            podcast_name=data.get("podcast_name", ""),
            episode_title=data.get("episode_title", ""),
            published_at=data.get("published_at"),
            extracted_at=extracted_at,
            extraction_model=data.get("extraction_model", ""),
            extraction_confidence=float(data.get("extraction_confidence", 0.8)),
        )


@dataclass
class PodcastQuoteExtractionResult:
    """Result of quote extraction from a single episode transcript."""
    episode_id: str = ""
    podcast_id: str = ""
    quotes: List[PodcastQuote] = field(default_factory=list)
    total_extracted: int = 0
    extraction_model: str = ""
    extraction_cost_usd: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.total_extracted > 0
