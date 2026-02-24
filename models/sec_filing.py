"""
SEC Filing Models
==================

Data models for SEC filings and extracted regulatory nuggets.
Part of the "Regulatory Voice" pipeline — runs separately from the core article orchestrator.

Key Features:
- Verbatim disclosure extraction from 10-K, 10-Q, 8-K filings
- Risk factor analysis (Item 1A — legally mandated disclosures)
- New disclosure detection (first-time risk mentions = high-priority signals)
- Quantum-specific nugget taxonomy

Usage:
    nugget = SecNugget(
        nugget_text="We face significant competition in quantum computing from IonQ and Rigetti",
        filing_type=FilingType.FORM_10K,
        section=FilingSection.RISK_FACTORS,
        nugget_type=NuggetType.COMPETITIVE_DISCLOSURE,
        signal_strength=SignalStrength.EXPLICIT,
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
# ENUMS — SEC Filing Taxonomy (Quantum-Specific)
# =============================================================================

class FilingType(str, Enum):
    """SEC filing form types."""
    FORM_10K = "10-K"          # Annual report
    FORM_10Q = "10-Q"          # Quarterly report
    FORM_8K = "8-K"            # Current report (material events)
    FORM_S1 = "S-1"            # IPO registration
    FORM_DEF14A = "DEF 14A"    # Proxy statement
    FORM_20F = "20-F"          # Foreign issuer annual
    FORM_6K = "6-K"            # Foreign issuer current
    OTHER = "other"


class FilingSection(str, Enum):
    """
    Key sections of SEC filings.

    Item 1A (Risk Factors) is often the most valuable for competitive intel
    because companies MUST disclose material risks.
    """
    RISK_FACTORS = "risk_factors"              # Item 1A — GOLD MINE
    BUSINESS = "business"                      # Item 1 — Business overview
    MDA = "mda"                                # Item 7 — MD&A
    LEGAL_PROCEEDINGS = "legal_proceedings"    # Item 3
    MARKET_RISK = "market_risk"                # Item 7A
    PROPERTIES = "properties"                  # Item 2
    EXHIBITS = "exhibits"                      # Item 15
    FORWARD_LOOKING = "forward_looking"        # Forward-looking statements
    EXECUTIVE_COMPENSATION = "executive_comp"  # Proxy sections
    UNKNOWN = "unknown"


class NuggetType(str, Enum):
    """
    Type of insight from the filing — quantum computing specific.

    Critical for quantum intelligence:
    - COMPETITIVE_DISCLOSURE: Named competitors (required by law)
    - TECHNOLOGY_INVESTMENT: R&D spending on quantum
    - QUANTUM_READINESS: Commercial deployment disclosures
    """
    COMPETITIVE_DISCLOSURE = "competitive_disclosure"  # Named quantum competitors
    RISK_ADMISSION = "risk_admission"                  # Material quantum risks
    TECHNOLOGY_INVESTMENT = "technology_investment"      # R&D, quantum investment
    IP_PATENT = "ip_patent"                            # Intellectual property, patents
    REGULATORY_COMPLIANCE = "regulatory_compliance"    # Export controls, compliance
    FORWARD_GUIDANCE = "forward_guidance"              # Future quantum plans
    MATERIAL_CHANGE = "material_change"                # 8-K events
    QUANTUM_READINESS = "quantum_readiness"            # Commercialization status


class SignalStrength(str, Enum):
    """
    How explicit/strong is the disclosure signal?

    EXPLICIT disclosures are legally required when material.
    BURIED disclosures may indicate sensitive information.
    NEW disclosures (first-time mentions) are the most valuable.
    """
    EXPLICIT = "explicit"    # Clear, prominent disclosure
    STANDARD = "standard"    # Normal disclosure language
    HEDGED = "hedged"        # Heavy legal caveats
    BURIED = "buried"        # Deep in filing, minimal prominence
    NEW = "new"              # First-time disclosure (very valuable)


class NuggetTheme(str, Enum):
    """
    Taxonomy of themes aligned with quantum computing strategic priorities.
    """
    # Hardware & Architecture
    QUBIT_SCALING = "qubit_scaling"
    ERROR_CORRECTION = "error_correction"
    PROCESSOR_ROADMAP = "processor_roadmap"

    # Software & Platform
    QUANTUM_SOFTWARE = "quantum_software"
    CLOUD_QUANTUM_SERVICE = "cloud_quantum_service"
    HYBRID_CLASSICAL = "hybrid_classical"

    # Commercial
    ENTERPRISE_CUSTOMERS = "enterprise_customers"
    REVENUE_RECOGNITION = "revenue_recognition"
    PARTNERSHIP_ALLIANCE = "partnership_alliance"

    # Use Cases
    DRUG_DISCOVERY = "drug_discovery"
    FINANCIAL_OPTIMIZATION = "financial_optimization"
    CYBERSECURITY_PQC = "cybersecurity_pqc"
    MATERIALS_SCIENCE = "materials_science"

    # Risk & Compliance
    EXPORT_CONTROLS = "export_controls"
    TALENT_RETENTION = "talent_retention"
    IP_LITIGATION = "ip_litigation"
    SUPPLY_CHAIN = "supply_chain"

    # General
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    MARKET_DYNAMICS = "market_dynamics"
    GEOPOLITICS = "geopolitics"
    MACROECONOMIC = "macroeconomic"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SecFiling:
    """
    Raw SEC filing metadata and content fetched from EDGAR.
    Stored as-is before nugget extraction.
    """
    filing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    company_name: str = ""
    cik: str = ""
    accession_number: str = ""
    filing_type: str = "10-K"  # String, not enum, for flexibility with EDGAR data
    filing_date: Optional[datetime] = None
    fiscal_year: int = 0
    fiscal_quarter: Optional[int] = None
    primary_document: str = ""
    filing_url: str = ""
    raw_content: Optional[str] = None
    sections: Optional[Dict[str, str]] = None

    # Internal tracking
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    char_count: int = 0

    def __post_init__(self):
        """Compute char count if not set."""
        if self.raw_content and not self.char_count:
            self.char_count = len(self.raw_content)

    @property
    def unique_key(self) -> str:
        """Unique key for dedup."""
        return f"{self.ticker}_{self.filing_type}_{self.fiscal_year}" + (
            f"_Q{self.fiscal_quarter}" if self.fiscal_quarter else ""
        )

    @property
    def accession_formatted(self) -> str:
        """Format accession number for URLs (remove dashes)."""
        return self.accession_number.replace("-", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "filing_id": self.filing_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "cik": self.cik,
            "accession_number": self.accession_number,
            "filing_type": self.filing_type,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "primary_document": self.primary_document,
            "filing_url": self.filing_url,
            "raw_content": self.raw_content,
            "sections": str(self.sections) if self.sections else None,
            "ingested_at": self.ingested_at.isoformat(),
            "char_count": self.char_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecFiling":
        """Create from dictionary (from storage)."""
        return cls(
            filing_id=data.get("filing_id", str(uuid.uuid4())),
            ticker=data.get("ticker", ""),
            company_name=data.get("company_name", ""),
            cik=data.get("cik", ""),
            accession_number=data.get("accession_number", ""),
            filing_type=data.get("filing_type", "10-K"),
            filing_date=datetime.fromisoformat(data["filing_date"]) if data.get("filing_date") else None,
            fiscal_year=int(data.get("fiscal_year", 0)),
            fiscal_quarter=int(data["fiscal_quarter"]) if data.get("fiscal_quarter") else None,
            primary_document=data.get("primary_document", ""),
            filing_url=data.get("filing_url", ""),
            raw_content=data.get("raw_content"),
            ingested_at=datetime.fromisoformat(data["ingested_at"]) if data.get("ingested_at") else datetime.now(timezone.utc),
            char_count=int(data.get("char_count", 0)),
        )


@dataclass
class SecNugget:
    """
    An extracted verbatim insight from an SEC filing.

    Nuggets are extracted during ingestion using LLM-based analysis.
    Each 10-K typically yields 15-30 high-value nuggets from
    risk factors and MD&A sections.

    Special attention to:
    - Risk factors (Item 1A) — legally required disclosures
    - Competitive mentions — who they name as threats
    - New disclosures — first-time mentions are signals
    - 8-K material events — leadership changes, M&A, etc.
    """

    # Identity
    nugget_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filing_id: str = ""

    # The nugget itself — verbatim
    nugget_text: str = ""
    context_text: Optional[str] = None

    # Filing context
    filing_type: FilingType = FilingType.FORM_10K
    section: FilingSection = FilingSection.UNKNOWN

    # Nugget classification
    nugget_type: NuggetType = NuggetType.RISK_ADMISSION
    themes: List[str] = field(default_factory=list)  # NuggetTheme values
    signal_strength: SignalStrength = SignalStrength.STANDARD

    # Entity references
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)
    competitors_named: List[str] = field(default_factory=list)
    regulators_mentioned: List[str] = field(default_factory=list)

    # Risk assessment
    risk_level: str = "medium"  # high / medium / low
    is_new_disclosure: bool = False
    is_actionable: bool = False
    actionability_reason: Optional[str] = None

    # Relevance scoring
    relevance_score: float = 0.5  # 0.0-1.0: how relevant to quantum computing

    # Source context
    ticker: str = ""
    company_name: str = ""
    cik: str = ""
    fiscal_year: int = 0
    fiscal_quarter: Optional[int] = None
    filing_date: Optional[datetime] = None
    accession_number: Optional[str] = None

    # Audit fields
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_model: str = "claude-sonnet-4-6-20250514"
    extraction_confidence: float = 0.8

    # Domain
    domain: str = "quantum"

    @property
    def display_source(self) -> str:
        """Human-readable source string."""
        if self.fiscal_quarter:
            return f"{self.company_name} {self.filing_type.value} Q{self.fiscal_quarter} {self.fiscal_year}"
        return f"{self.company_name} {self.filing_type.value} {self.fiscal_year}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        def _enum_val(v):
            """Safely extract .value from enum or return string as-is."""
            return v.value if hasattr(v, 'value') else str(v)

        return {
            "nugget_id": self.nugget_id,
            "filing_id": self.filing_id,
            "nugget_text": self.nugget_text,
            "context_text": self.context_text,
            "filing_type": _enum_val(self.filing_type),
            "section": _enum_val(self.section),
            "nugget_type": _enum_val(self.nugget_type),
            "themes": ",".join(self.themes),
            "signal_strength": _enum_val(self.signal_strength),
            "companies_mentioned": ",".join(self.companies_mentioned),
            "technologies_mentioned": ",".join(self.technologies_mentioned),
            "competitors_named": ",".join(self.competitors_named),
            "regulators_mentioned": ",".join(self.regulators_mentioned),
            "risk_level": self.risk_level,
            "is_new_disclosure": self.is_new_disclosure,
            "is_actionable": self.is_actionable,
            "actionability_reason": self.actionability_reason,
            "relevance_score": self.relevance_score,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "cik": self.cik,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "accession_number": self.accession_number,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_model": self.extraction_model,
            "extraction_confidence": self.extraction_confidence,
            "domain": self.domain,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecNugget":
        """Create from dictionary (from storage)."""
        return cls(
            nugget_id=data.get("nugget_id", str(uuid.uuid4())),
            filing_id=data.get("filing_id", ""),
            nugget_text=data.get("nugget_text", ""),
            context_text=data.get("context_text"),
            filing_type=FilingType(data.get("filing_type", "10-K")),
            section=FilingSection(data.get("section", "unknown")),
            nugget_type=NuggetType(data.get("nugget_type", "risk_admission")),
            themes=data.get("themes", "").split(",") if data.get("themes") else [],
            signal_strength=SignalStrength(data.get("signal_strength", "standard")),
            companies_mentioned=data.get("companies_mentioned", "").split(",") if data.get("companies_mentioned") else [],
            technologies_mentioned=data.get("technologies_mentioned", "").split(",") if data.get("technologies_mentioned") else [],
            competitors_named=data.get("competitors_named", "").split(",") if data.get("competitors_named") else [],
            regulators_mentioned=data.get("regulators_mentioned", "").split(",") if data.get("regulators_mentioned") else [],
            risk_level=data.get("risk_level", "medium"),
            is_new_disclosure=bool(data.get("is_new_disclosure", False)),
            is_actionable=bool(data.get("is_actionable", False)),
            actionability_reason=data.get("actionability_reason"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            ticker=data.get("ticker", ""),
            company_name=data.get("company_name", ""),
            cik=data.get("cik", ""),
            fiscal_year=int(data.get("fiscal_year", 0)),
            fiscal_quarter=int(data["fiscal_quarter"]) if data.get("fiscal_quarter") else None,
            filing_date=datetime.fromisoformat(data["filing_date"]) if data.get("filing_date") else None,
            accession_number=data.get("accession_number"),
            extracted_at=datetime.fromisoformat(data["extracted_at"]) if data.get("extracted_at") else datetime.now(timezone.utc),
            extraction_model=data.get("extraction_model", "claude-sonnet-4-6-20250514"),
            extraction_confidence=float(data.get("extraction_confidence", 0.8)),
            domain=data.get("domain", "quantum"),
        )

    def to_display_dict(self) -> Dict[str, Any]:
        """Display-friendly version for API responses."""
        return {
            "nugget_id": self.nugget_id,
            "nugget_text": self.nugget_text,
            "filing_type": self.filing_type.value,
            "section": self.section.value,
            "nugget_type": self.nugget_type.value,
            "themes": self.themes,
            "signal_strength": self.signal_strength.value,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "competitors_named": self.competitors_named,
            "risk_level": self.risk_level,
            "is_new_disclosure": self.is_new_disclosure,
            "relevance_score": self.relevance_score,
            "is_actionable": self.is_actionable,
            "display_source": self.display_source,
        }

    def to_briefing_format(self) -> Dict[str, Any]:
        """Format for inclusion in briefings."""
        return {
            "text": self.nugget_text,
            "source": self.display_source,
            "section": self.section.value.replace("_", " ").title(),
            "type": self.nugget_type.value.replace("_", " ").title(),
            "relevance": self.relevance_score,
            "competitors": self.competitors_named,
            "is_new": self.is_new_disclosure,
            "voice": "regulatory",
        }


@dataclass
class NuggetExtractionResult:
    """Result from SEC filing nugget extraction."""

    filing_id: str = ""
    ticker: str = ""
    company_name: str = ""
    filing_type: str = "10-K"
    fiscal_year: int = 0
    fiscal_quarter: Optional[int] = None

    # Extraction results
    nuggets: List[SecNugget] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None

    # Stats
    filing_length: int = 0
    extraction_time_seconds: float = 0.0
    extraction_model: str = "claude-sonnet-4-6-20250514"

    # Computed stats
    total_nuggets: int = 0
    actionable_count: int = 0
    by_nugget_type: Dict[str, int] = field(default_factory=dict)
    by_section: Dict[str, int] = field(default_factory=dict)
    competitors_found: List[str] = field(default_factory=list)
    new_disclosures_count: int = 0

    def compute_statistics(self):
        """Compute summary statistics from extracted nuggets."""
        self.total_nuggets = len(self.nuggets)
        self.actionable_count = sum(1 for n in self.nuggets if n.is_actionable)
        self.new_disclosures_count = sum(1 for n in self.nuggets if n.is_new_disclosure)

        # Count by type
        type_counts: Dict[str, int] = {}
        for n in self.nuggets:
            key = n.nugget_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
        self.by_nugget_type = type_counts

        # Count by section
        section_counts: Dict[str, int] = {}
        for n in self.nuggets:
            key = n.section.value
            section_counts[key] = section_counts.get(key, 0) + 1
        self.by_section = section_counts

        # Unique competitors
        all_competitors: set = set()
        for n in self.nuggets:
            all_competitors.update(n.competitors_named)
        self.competitors_found = sorted(list(all_competitors))

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary for logging/reporting."""
        return {
            "filing_id": self.filing_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "filing_type": self.filing_type,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "success": self.success,
            "total_nuggets": self.total_nuggets,
            "actionable_count": self.actionable_count,
            "new_disclosures": self.new_disclosures_count,
            "competitors_found": self.competitors_found,
            "extraction_time_seconds": round(self.extraction_time_seconds, 2),
        }
