"""
Earnings Call Models
====================

Data models for earnings call transcripts and extracted executive quotes.
Part of the "Executive Voice" pipeline — runs separately from the core article orchestrator.

Key Features:
- Verbatim quote extraction with speaker attribution
- Confidence level tracking (definitive vs hedged responses)
- Q&A section awareness for analyst pressure signals
- Quantum-specific quote taxonomy

Usage:
    quote = ExtractedQuote(
        quote_text="We are investing $3 billion in quantum computing over the next 5 years",
        speaker_name="Arvind Krishna",
        speaker_role=SpeakerRole.CEO,
        quote_type=QuoteType.TECHNOLOGY_MILESTONE,
        confidence_level=ConfidenceLevel.DEFINITIVE,
        section=CallSection.PREPARED_REMARKS,
        ticker="IBM",
        ...
    )
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


# =============================================================================
# ENUMS — Earnings Call Taxonomy (Quantum-Specific)
# =============================================================================

class SpeakerRole(str, Enum):
    """Speaker role on the earnings call."""
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    COO = "coo"
    EVP = "evp"               # Executive Vice President
    VP = "vp"                 # Vice President
    ANALYST = "analyst"       # Wall Street analyst asking questions
    OTHER_EXEC = "other_exec"
    OPERATOR = "operator"
    UNKNOWN = "unknown"


class QuoteType(str, Enum):
    """
    Type of quote — what kind of insight does it provide?

    Quantum-specific taxonomy:
    - strategy → Corporate quantum strategy direction
    - technology_milestone → Hardware/software achievements
    - timeline_outlook → Predictions on quantum readiness
    - competitive → Competitor commentary
    - analyst_pressure → What Wall Street is worried about (GOLD)
    """
    STRATEGY = "strategy"                        # Strategic priorities, quantum roadmap
    GUIDANCE = "guidance"                        # Forward-looking financial guidance
    COMPETITIVE = "competitive"                  # Competitor commentary
    TECHNOLOGY_MILESTONE = "technology_milestone"  # Hardware/software achievements
    TIMELINE_OUTLOOK = "timeline_outlook"        # Quantum readiness predictions
    RISK_FACTOR = "risk_factor"                  # Headwinds, challenges, barriers
    ANALYST_PRESSURE = "analyst_pressure"        # Analyst pushing on sensitive topic
    PARTNERSHIP = "partnership"                   # Quantum partnerships, collaborations
    REVENUE_METRIC = "revenue_metric"            # Quantum revenue, bookings, deals


class ConfidenceLevel(str, Enum):
    """
    How confident/definitive is the speaker?

    CRITICAL: 'hedged' responses to analyst questions are often
    the most valuable signals — what are they NOT saying clearly?
    """
    DEFINITIVE = "definitive"    # Strong: "We will...", "We are..."
    CAUTIOUS = "cautious"        # Qualified: "We expect...", "We believe..."
    SPECULATIVE = "speculative"  # Uncertain: "We think...", "It's possible..."
    HEDGED = "hedged"            # Heavy caveats: "Subject to...", "Depending on..."


class CallSection(str, Enum):
    """
    Which part of the earnings call did this come from?

    Q&A section often contains more candid insights because
    analysts push for specifics that aren't in prepared remarks.
    """
    PREPARED_REMARKS = "prepared_remarks"
    QA = "qa"
    UNKNOWN = "unknown"


class QuoteTheme(str, Enum):
    """
    Taxonomy of themes for quote classification.
    Aligned with quantum computing strategic priorities.
    """
    # Hardware & Architecture
    QUBIT_SCALING = "qubit_scaling"
    ERROR_CORRECTION = "error_correction"
    PROCESSOR_ARCHITECTURE = "processor_architecture"

    # Software & Platform
    QUANTUM_SOFTWARE = "quantum_software"
    CLOUD_QUANTUM = "cloud_quantum"
    HYBRID_CLASSICAL = "hybrid_classical"

    # Commercial & Market
    ENTERPRISE_ADOPTION = "enterprise_adoption"
    QUANTUM_REVENUE = "quantum_revenue"
    CUSTOMER_PIPELINE = "customer_pipeline"
    QUANTUM_ADVANTAGE = "quantum_advantage"

    # Use Cases
    DRUG_DISCOVERY = "drug_discovery"
    FINANCIAL_OPTIMIZATION = "financial_optimization"
    CYBERSECURITY_PQC = "cybersecurity_pqc"
    MATERIALS_SCIENCE = "materials_science"
    AI_ML_INTERSECTION = "ai_ml_intersection"

    # Competition & Strategy
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    TALENT_WORKFORCE = "talent_workforce"
    IP_PATENTS = "ip_patents"
    GOVERNMENT_DEFENSE = "government_defense"

    # General
    MARKET_DYNAMICS = "market_dynamics"
    GEOPOLITICS = "geopolitics"
    TIMELINE_REALITY = "timeline_reality"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class EarningsTranscript:
    """
    Raw earnings call transcript fetched from API Ninjas.
    Stored as-is before quote extraction.
    """
    transcript_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    company_name: str = ""
    year: int = 0
    quarter: int = 0
    transcript_text: str = ""
    call_date: Optional[datetime] = None

    # Metadata from API
    participants: List[Dict[str, str]] = field(default_factory=list)
    fiscal_period: str = ""

    # Internal tracking
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    char_count: int = 0
    domain: str = "quantum"

    def __post_init__(self):
        """Compute char count if not set."""
        if self.transcript_text and not self.char_count:
            self.char_count = len(self.transcript_text)

    @property
    def unique_key(self) -> str:
        """Unique key for dedup: TICKER_YEAR_QN."""
        return f"{self.ticker}_{self.year}_Q{self.quarter}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "transcript_id": self.transcript_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "year": self.year,
            "quarter": self.quarter,
            "transcript_text": self.transcript_text,
            "call_date": self.call_date.isoformat() if self.call_date else None,
            "participants": str(self.participants),
            "fiscal_period": self.fiscal_period,
            "ingested_at": self.ingested_at.isoformat(),
            "char_count": self.char_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EarningsTranscript":
        """Create from dictionary (from storage)."""
        return cls(
            transcript_id=data.get("transcript_id", str(uuid.uuid4())),
            ticker=data.get("ticker", ""),
            company_name=data.get("company_name", ""),
            year=int(data.get("year", 0)),
            quarter=int(data.get("quarter", 0)),
            transcript_text=data.get("transcript_text", ""),
            call_date=datetime.fromisoformat(data["call_date"]) if data.get("call_date") else None,
            fiscal_period=data.get("fiscal_period", ""),
            ingested_at=datetime.fromisoformat(data["ingested_at"]) if data.get("ingested_at") else datetime.now(timezone.utc),
            char_count=int(data.get("char_count", 0)),
        )


@dataclass
class ExtractedQuote:
    """
    A verbatim executive quote extracted from an earnings call.

    Quotes are extracted during ingestion using LLM-based analysis.
    Each transcript typically yields 10-20 high-value quotes that are
    tagged with themes, speaker role, and confidence level.

    Special attention to:
    - Q&A section analyst questions (what Wall Street worries about)
    - Hedged responses (potential weakness signals)
    - Technology milestone claims (quantum computing specifics)
    """

    # Identity
    quote_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transcript_id: str = ""

    # The quote itself — verbatim
    quote_text: str = ""
    context_before: Optional[str] = None
    context_after: Optional[str] = None

    # Speaker attribution
    speaker_name: str = ""
    speaker_role: SpeakerRole = SpeakerRole.UNKNOWN
    speaker_title: Optional[str] = None
    speaker_company: Optional[str] = None
    speaker_firm: Optional[str] = None  # Analyst firm if applicable

    # Quote classification
    quote_type: QuoteType = QuoteType.STRATEGY
    themes: List[str] = field(default_factory=list)  # QuoteTheme values
    sentiment: str = "neutral"  # bullish / bearish / cautious / neutral
    confidence_level: ConfidenceLevel = ConfidenceLevel.CAUTIOUS

    # Entity references
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)
    competitors_mentioned: List[str] = field(default_factory=list)
    metrics_mentioned: List[str] = field(default_factory=list)

    # Relevance & quotability
    relevance_score: float = 0.5  # 0.0-1.0: how relevant to quantum
    is_quotable: bool = False
    quotability_reason: Optional[str] = None

    # Source context
    ticker: str = ""
    company_name: str = ""
    year: int = 0
    quarter: int = 0
    call_date: Optional[datetime] = None
    section: CallSection = CallSection.UNKNOWN
    position_in_section: int = 0

    # Audit fields
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_model: str = "claude-sonnet-4-6-20250514"
    extraction_confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "quote_id": self.quote_id,
            "transcript_id": self.transcript_id,
            "quote_text": self.quote_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role.value,
            "speaker_title": self.speaker_title,
            "speaker_company": self.speaker_company,
            "speaker_firm": self.speaker_firm,
            "quote_type": self.quote_type.value,
            "themes": ",".join(self.themes),
            "sentiment": self.sentiment,
            "confidence_level": self.confidence_level.value,
            "companies_mentioned": ",".join(self.companies_mentioned),
            "technologies_mentioned": ",".join(self.technologies_mentioned),
            "competitors_mentioned": ",".join(self.competitors_mentioned),
            "metrics_mentioned": ",".join(self.metrics_mentioned),
            "relevance_score": self.relevance_score,
            "is_quotable": self.is_quotable,
            "quotability_reason": self.quotability_reason,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "year": self.year,
            "quarter": self.quarter,
            "call_date": self.call_date.isoformat() if self.call_date else None,
            "section": self.section.value,
            "position_in_section": self.position_in_section,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_model": self.extraction_model,
            "extraction_confidence": self.extraction_confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedQuote":
        """Create from dictionary (from storage)."""
        return cls(
            quote_id=data.get("quote_id", str(uuid.uuid4())),
            transcript_id=data.get("transcript_id", ""),
            quote_text=data.get("quote_text", ""),
            context_before=data.get("context_before"),
            context_after=data.get("context_after"),
            speaker_name=data.get("speaker_name", ""),
            speaker_role=SpeakerRole(data.get("speaker_role", "unknown")),
            speaker_title=data.get("speaker_title"),
            speaker_company=data.get("speaker_company"),
            speaker_firm=data.get("speaker_firm"),
            quote_type=QuoteType(data.get("quote_type", "strategy")),
            themes=data.get("themes", "").split(",") if data.get("themes") else [],
            sentiment=data.get("sentiment", "neutral"),
            confidence_level=ConfidenceLevel(data.get("confidence_level", "cautious")),
            companies_mentioned=data.get("companies_mentioned", "").split(",") if data.get("companies_mentioned") else [],
            technologies_mentioned=data.get("technologies_mentioned", "").split(",") if data.get("technologies_mentioned") else [],
            competitors_mentioned=data.get("competitors_mentioned", "").split(",") if data.get("competitors_mentioned") else [],
            metrics_mentioned=data.get("metrics_mentioned", "").split(",") if data.get("metrics_mentioned") else [],
            relevance_score=float(data.get("relevance_score", 0.5)),
            is_quotable=bool(data.get("is_quotable", False)),
            quotability_reason=data.get("quotability_reason"),
            ticker=data.get("ticker", ""),
            company_name=data.get("company_name", ""),
            year=int(data.get("year", 0)),
            quarter=int(data.get("quarter", 0)),
            call_date=datetime.fromisoformat(data["call_date"]) if data.get("call_date") else None,
            section=CallSection(data.get("section", "unknown")),
            position_in_section=int(data.get("position_in_section", 0)),
            extracted_at=datetime.fromisoformat(data["extracted_at"]) if data.get("extracted_at") else datetime.now(timezone.utc),
            extraction_model=data.get("extraction_model", "claude-sonnet-4-6-20250514"),
            extraction_confidence=float(data.get("extraction_confidence", 0.8)),
        )

    def to_display_dict(self) -> Dict[str, Any]:
        """Display-friendly version for API responses (excludes embedding)."""
        return {
            "quote_id": self.quote_id,
            "quote_text": self.quote_text,
            "speaker": {
                "name": self.speaker_name,
                "role": self.speaker_role.value,
                "title": self.speaker_title,
                "company": self.speaker_company,
                "firm": self.speaker_firm,
            },
            "classification": {
                "quote_type": self.quote_type.value,
                "themes": self.themes,
                "sentiment": self.sentiment,
                "confidence_level": self.confidence_level.value,
            },
            "entities": {
                "companies_mentioned": self.companies_mentioned,
                "technologies_mentioned": self.technologies_mentioned,
                "competitors_mentioned": self.competitors_mentioned,
            },
            "relevance_score": self.relevance_score,
            "is_quotable": self.is_quotable,
            "source": {
                "ticker": self.ticker,
                "company": self.company_name,
                "year": self.year,
                "quarter": self.quarter,
                "call_date": self.call_date.isoformat() if self.call_date else None,
                "section": self.section.value,
            },
        }

    def to_citation_dict(self) -> Dict[str, Any]:
        """Minimal dict for briefing citations."""
        return {
            "quote_id": self.quote_id,
            "quote_text": self.quote_text,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role.value,
            "company": self.company_name,
            "ticker": self.ticker,
            "quarter": f"Q{self.quarter} {self.year}",
            "section": self.section.value,
        }


@dataclass
class QuoteExtractionResult:
    """Result of quote extraction from an earnings transcript."""

    # Source info
    transcript_id: str = ""
    ticker: str = ""
    company_name: str = ""
    year: int = 0
    quarter: int = 0

    # Extraction results
    quotes: List[ExtractedQuote] = field(default_factory=list)
    total_quotes: int = 0
    quotable_count: int = 0

    # Statistics
    quotes_by_section: Dict[str, int] = field(default_factory=dict)
    quotes_by_type: Dict[str, int] = field(default_factory=dict)
    quotes_by_role: Dict[str, int] = field(default_factory=dict)

    # Process metadata
    success: bool = False
    error_message: Optional[str] = None
    extraction_model: str = "claude-sonnet-4-6-20250514"
    extraction_time_seconds: float = 0.0
    transcript_length: int = 0

    def compute_statistics(self):
        """Compute statistics from extracted quotes."""
        self.total_quotes = len(self.quotes)
        self.quotable_count = sum(1 for q in self.quotes if q.is_quotable)

        self.quotes_by_section = {}
        for q in self.quotes:
            section = q.section.value
            self.quotes_by_section[section] = self.quotes_by_section.get(section, 0) + 1

        self.quotes_by_type = {}
        for q in self.quotes:
            qtype = q.quote_type.value
            self.quotes_by_type[qtype] = self.quotes_by_type.get(qtype, 0) + 1

        self.quotes_by_role = {}
        for q in self.quotes:
            role = q.speaker_role.value
            self.quotes_by_role[role] = self.quotes_by_role.get(role, 0) + 1
