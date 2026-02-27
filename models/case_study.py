"""
Case Study Models
==================

Data models for high-fidelity intelligence extraction across all data sources.
Part of the "Case Studies" pipeline — extracts structured narratives from articles,
podcasts, earnings calls, SEC filings, and ArXiv papers.

Key Features:
- Grounding quotes: every case study anchored in verbatim source text
- Full story extraction: company, industry, department, implementation, outcome
- Domain-aware: quantum-specific fields (qubit type, fidelity) and AI-specific fields (ROI, model used)
- Source-polymorphic: one model serves articles, podcasts, earnings, SEC, ArXiv

Usage:
    cs = CaseStudy(
        use_case_title="Digital Twin for Assembly Line Optimization",
        grounding_quote="We deployed a digital twin across three assembly lines...",
        company="Siemens",
        industry="manufacturing",
        outcome_metric="40% reduction in assembly time",
        outcome_type="efficiency",
        source_type="podcast",
        source_id="transcript_abc123",
        domain="ai",
    )
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
import json
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class CaseStudySourceType(str, Enum):
    """What kind of source the case study was extracted from."""
    ARTICLE = "article"
    PODCAST = "podcast"
    EARNINGS = "earnings"
    SEC_FILING = "sec_filing"
    ARXIV = "arxiv"


class OutcomeType(str, Enum):
    """Classification of the outcome achieved."""
    EFFICIENCY = "efficiency"               # Time/cost reduction
    REVENUE = "revenue"                     # Revenue/growth impact
    ACCURACY = "accuracy"                   # Quality/precision improvement
    SCALE = "scale"                         # Deployment scale milestone
    COST_REDUCTION = "cost_reduction"       # Direct cost savings
    SPEED = "speed"                         # Performance/throughput gains
    RISK_REDUCTION = "risk_reduction"       # Risk/compliance improvements
    SCIENTIFIC = "scientific"               # Research/scientific milestone
    COMPETITIVE = "competitive"             # Competitive advantage gained
    PARTNERSHIP = "partnership"             # Strategic partnership formed
    REGULATORY = "regulatory"              # Regulatory milestone
    OTHER = "other"


class ReadinessLevel(str, Enum):
    """Technology readiness / deployment maturity."""
    PRODUCTION = "production"               # In production at scale
    PILOT = "pilot"                         # Pilot/POC stage
    ANNOUNCED = "announced"                 # Announced but not deployed
    RESEARCH = "research"                   # Research-stage only
    THEORETICAL = "theoretical"             # Theoretical/proposed


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CaseStudy:
    """
    A structured, high-fidelity intelligence extract from any source.

    Every case study is grounded in a verbatim quote from the source material.
    Fields are designed to capture the full story — who, what, where, how, outcome.

    Source polymorphism: source_type + source_id form a polymorphic FK to
    articles, podcast_transcripts, earnings_transcripts, sec_filings, or papers.
    """

    # === Identity ===
    case_study_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "article"            # CaseStudySourceType value
    source_id: str = ""                     # FK to source table
    domain: str = "quantum"                 # "quantum" or "ai"

    # === Grounding (always required) ===
    grounding_quote: str = ""               # Verbatim text from source
    context_text: Optional[str] = None      # Surrounding context

    # === Core case study fields (always extracted) ===
    use_case_title: str = ""                # Short title
    use_case_summary: str = ""              # 2-3 sentence narrative
    company: str = ""                       # Primary company
    industry: str = ""                      # Industry vertical
    technology_stack: List[str] = field(default_factory=list)  # Technologies used

    # === Implementation detail (optional) ===
    department: Optional[str] = None
    implementation_detail: Optional[str] = None
    teams_impacted: List[str] = field(default_factory=list)
    scale: Optional[str] = None             # "3 assembly lines, 1 plant"
    timeline: Optional[str] = None          # "6 months", "deployed Q3 2025"
    readiness_level: str = "announced"      # ReadinessLevel value

    # === Outcome (the gold) ===
    outcome_metric: Optional[str] = None    # "40% reduction in assembly time"
    outcome_type: Optional[str] = None      # OutcomeType value
    outcome_quantified: bool = False        # True if metric has a number

    # === Speaker attribution (podcast/earnings) ===
    speaker: Optional[str] = None
    speaker_role: Optional[str] = None
    speaker_company: Optional[str] = None

    # === Entity extraction (always) ===
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)
    people_mentioned: List[str] = field(default_factory=list)
    competitors_mentioned: List[str] = field(default_factory=list)

    # === Quantum-specific fields ===
    qubit_type: Optional[str] = None        # "trapped ion", "superconducting"
    gate_fidelity: Optional[str] = None     # "99.5% two-qubit gate fidelity"
    commercial_viability: Optional[str] = None  # "near-term", "5-year horizon"
    scientific_significance: Optional[str] = None

    # === AI-specific fields ===
    ai_model_used: Optional[str] = None     # "GPT-4", "Claude", "custom LLM"
    roi_metric: Optional[str] = None        # "$2M annual savings"
    deployment_type: Optional[str] = None   # "cloud", "on-premise", "edge"

    # === Quality ===
    relevance_score: float = 0.5
    confidence: float = 0.8

    # === Overflow metadata ===
    metadata: Dict[str, Any] = field(default_factory=dict)

    # === Audit ===
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_model: str = "claude-sonnet-4-6-20250514"
    extraction_confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "case_study_id": self.case_study_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "domain": self.domain,
            "grounding_quote": self.grounding_quote,
            "context_text": self.context_text,
            "use_case_title": self.use_case_title,
            "use_case_summary": self.use_case_summary,
            "company": self.company,
            "industry": self.industry,
            "technology_stack": ",".join(self.technology_stack),
            "department": self.department,
            "implementation_detail": self.implementation_detail,
            "teams_impacted": ",".join(self.teams_impacted),
            "scale": self.scale,
            "timeline": self.timeline,
            "readiness_level": self.readiness_level,
            "outcome_metric": self.outcome_metric,
            "outcome_type": self.outcome_type,
            "outcome_quantified": self.outcome_quantified,
            "speaker": self.speaker,
            "speaker_role": self.speaker_role,
            "speaker_company": self.speaker_company,
            "companies_mentioned": ",".join(self.companies_mentioned),
            "technologies_mentioned": ",".join(self.technologies_mentioned),
            "people_mentioned": ",".join(self.people_mentioned),
            "competitors_mentioned": ",".join(self.competitors_mentioned),
            "qubit_type": self.qubit_type,
            "gate_fidelity": self.gate_fidelity,
            "commercial_viability": self.commercial_viability,
            "scientific_significance": self.scientific_significance,
            "ai_model_used": self.ai_model_used,
            "roi_metric": self.roi_metric,
            "deployment_type": self.deployment_type,
            "relevance_score": self.relevance_score,
            "confidence": self.confidence,
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_model": self.extraction_model,
            "extraction_confidence": self.extraction_confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseStudy":
        """Create from dictionary (from storage)."""

        def _split_csv(val) -> List[str]:
            """Split comma-separated string into list, handling None/empty."""
            if not val:
                return []
            if isinstance(val, list):
                return val
            return [x.strip() for x in str(val).split(",") if x.strip()]

        # Parse metadata JSON
        meta = data.get("metadata")
        if meta is None:
            metadata = {}
        elif isinstance(meta, str):
            try:
                metadata = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        elif isinstance(meta, dict):
            metadata = meta
        else:
            metadata = {}

        # Parse extracted_at
        extracted_at = data.get("extracted_at")
        if extracted_at and isinstance(extracted_at, str):
            try:
                extracted_at = datetime.fromisoformat(extracted_at)
            except ValueError:
                extracted_at = datetime.now(timezone.utc)
        elif not isinstance(extracted_at, datetime):
            extracted_at = datetime.now(timezone.utc)

        return cls(
            case_study_id=data.get("case_study_id", str(uuid.uuid4())),
            source_type=data.get("source_type", "article"),
            source_id=data.get("source_id", ""),
            domain=data.get("domain", "quantum"),
            grounding_quote=data.get("grounding_quote", ""),
            context_text=data.get("context_text"),
            use_case_title=data.get("use_case_title", ""),
            use_case_summary=data.get("use_case_summary", ""),
            company=data.get("company", ""),
            industry=data.get("industry", ""),
            technology_stack=_split_csv(data.get("technology_stack")),
            department=data.get("department"),
            implementation_detail=data.get("implementation_detail"),
            teams_impacted=_split_csv(data.get("teams_impacted")),
            scale=data.get("scale"),
            timeline=data.get("timeline"),
            readiness_level=data.get("readiness_level", "announced"),
            outcome_metric=data.get("outcome_metric"),
            outcome_type=data.get("outcome_type"),
            outcome_quantified=bool(data.get("outcome_quantified", False)),
            speaker=data.get("speaker"),
            speaker_role=data.get("speaker_role"),
            speaker_company=data.get("speaker_company"),
            companies_mentioned=_split_csv(data.get("companies_mentioned")),
            technologies_mentioned=_split_csv(data.get("technologies_mentioned")),
            people_mentioned=_split_csv(data.get("people_mentioned")),
            competitors_mentioned=_split_csv(data.get("competitors_mentioned")),
            qubit_type=data.get("qubit_type"),
            gate_fidelity=data.get("gate_fidelity"),
            commercial_viability=data.get("commercial_viability"),
            scientific_significance=data.get("scientific_significance"),
            ai_model_used=data.get("ai_model_used"),
            roi_metric=data.get("roi_metric"),
            deployment_type=data.get("deployment_type"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            confidence=float(data.get("confidence", 0.8)),
            metadata=metadata,
            extracted_at=extracted_at,
            extraction_model=data.get("extraction_model", "claude-sonnet-4-6-20250514"),
            extraction_confidence=float(data.get("extraction_confidence", 0.8)),
        )

    def to_display_dict(self) -> Dict[str, Any]:
        """Display-friendly version for API responses."""
        result = {
            "case_study_id": self.case_study_id,
            "use_case_title": self.use_case_title,
            "use_case_summary": self.use_case_summary,
            "grounding_quote": self.grounding_quote,
            "company": self.company,
            "industry": self.industry,
            "technology_stack": self.technology_stack,
            "readiness_level": self.readiness_level,
            "relevance_score": self.relevance_score,
            "source_type": self.source_type,
            "domain": self.domain,
        }

        # Include outcome if present
        if self.outcome_metric:
            result["outcome_metric"] = self.outcome_metric
            result["outcome_type"] = self.outcome_type
            result["outcome_quantified"] = self.outcome_quantified

        # Include implementation detail if present
        if self.implementation_detail:
            result["implementation_detail"] = self.implementation_detail
        if self.department:
            result["department"] = self.department
        if self.scale:
            result["scale"] = self.scale
        if self.timeline:
            result["timeline"] = self.timeline

        # Include speaker for podcast/earnings
        if self.speaker:
            result["speaker"] = self.speaker
            result["speaker_role"] = self.speaker_role
            result["speaker_company"] = self.speaker_company

        # Include domain-specific fields
        if self.domain == "quantum":
            if self.qubit_type:
                result["qubit_type"] = self.qubit_type
            if self.gate_fidelity:
                result["gate_fidelity"] = self.gate_fidelity
            if self.commercial_viability:
                result["commercial_viability"] = self.commercial_viability
            if self.scientific_significance:
                result["scientific_significance"] = self.scientific_significance
        elif self.domain == "ai":
            if self.ai_model_used:
                result["ai_model_used"] = self.ai_model_used
            if self.roi_metric:
                result["roi_metric"] = self.roi_metric
            if self.deployment_type:
                result["deployment_type"] = self.deployment_type

        return result

    def to_briefing_format(self) -> Dict[str, Any]:
        """Format for inclusion in weekly briefings."""
        result = {
            "title": self.use_case_title,
            "summary": self.use_case_summary,
            "quote": self.grounding_quote,
            "company": self.company,
            "industry": self.industry,
            "relevance": self.relevance_score,
            "source_type": self.source_type,
            "voice": "case_study",
        }
        if self.outcome_metric:
            result["outcome"] = self.outcome_metric
        if self.readiness_level:
            result["readiness"] = self.readiness_level
        if self.speaker:
            result["speaker"] = f"{self.speaker}, {self.speaker_role or ''}"
        return result


@dataclass
class CaseStudyExtractionResult:
    """Result from case study extraction on a single source item."""

    source_type: str = ""
    source_id: str = ""

    # Extraction results
    case_studies: List[CaseStudy] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None

    # Stats
    total_extracted: int = 0
    source_length: int = 0
    extraction_time_seconds: float = 0.0
    extraction_model: str = "claude-sonnet-4-6-20250514"
    extraction_cost_usd: float = 0.0

    # Computed stats
    by_outcome_type: Dict[str, int] = field(default_factory=dict)
    by_readiness_level: Dict[str, int] = field(default_factory=dict)
    quantified_outcomes_count: int = 0
    unique_companies: List[str] = field(default_factory=list)
    unique_industries: List[str] = field(default_factory=list)

    def compute_statistics(self):
        """Compute summary statistics from extracted case studies."""
        self.total_extracted = len(self.case_studies)
        self.quantified_outcomes_count = sum(
            1 for cs in self.case_studies if cs.outcome_quantified
        )

        # Count by outcome type
        outcome_counts: Dict[str, int] = {}
        for cs in self.case_studies:
            if cs.outcome_type:
                outcome_counts[cs.outcome_type] = outcome_counts.get(cs.outcome_type, 0) + 1
        self.by_outcome_type = outcome_counts

        # Count by readiness level
        readiness_counts: Dict[str, int] = {}
        for cs in self.case_studies:
            readiness_counts[cs.readiness_level] = readiness_counts.get(cs.readiness_level, 0) + 1
        self.by_readiness_level = readiness_counts

        # Unique companies and industries
        companies: set = set()
        industries: set = set()
        for cs in self.case_studies:
            if cs.company:
                companies.add(cs.company)
            if cs.industry:
                industries.add(cs.industry)
        self.unique_companies = sorted(list(companies))
        self.unique_industries = sorted(list(industries))

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary for logging/reporting."""
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "success": self.success,
            "total_extracted": self.total_extracted,
            "quantified_outcomes": self.quantified_outcomes_count,
            "unique_companies": self.unique_companies,
            "unique_industries": self.unique_industries,
            "extraction_time_seconds": round(self.extraction_time_seconds, 2),
            "extraction_cost_usd": round(self.extraction_cost_usd, 4),
        }
