"""
Article Models
==============

Data models for article ingestion and classification in the Quantum Intelligence Hub.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any


class ContentCategory(str, Enum):
    """
    Primary content categories for intelligence classification.
    29 categories: 11 quantum-specific + 8 shared business + 10 AI-specific.
    """
    # Quantum-specific categories (11)
    HARDWARE_MILESTONE = "hardware_milestone"
    ERROR_CORRECTION = "error_correction"
    ALGORITHM_RESEARCH = "algorithm_research"
    USE_CASE_DRUG_DISCOVERY = "use_case_drug_discovery"
    USE_CASE_FINANCE = "use_case_finance"
    USE_CASE_OPTIMIZATION = "use_case_optimization"
    USE_CASE_CYBERSECURITY = "use_case_cybersecurity"
    USE_CASE_ENERGY_MATERIALS = "use_case_energy_materials"
    USE_CASE_AI_ML = "use_case_ai_ml"
    USE_CASE_OTHER = "use_case_other"
    EDUCATION_WORKFORCE = "education_workforce"

    # Shared business categories (8) — used by both quantum and AI domains
    COMPANY_EARNINGS = "company_earnings"
    FUNDING_IPO = "funding_ipo"
    PARTNERSHIP_CONTRACT = "partnership_contract"
    PERSONNEL_LEADERSHIP = "personnel_leadership"
    POLICY_REGULATION = "policy_regulation"
    GEOPOLITICS = "geopolitics"
    MARKET_ANALYSIS = "market_analysis"
    SKEPTICISM_CRITIQUE = "skepticism_critique"

    # AI-specific categories (10)
    AI_MODEL_RELEASE = "ai_model_release"
    AI_PRODUCT_LAUNCH = "ai_product_launch"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    AI_SAFETY_ALIGNMENT = "ai_safety_alignment"
    AI_OPEN_SOURCE = "ai_open_source"
    AI_USE_CASE_ENTERPRISE = "ai_use_case_enterprise"
    AI_USE_CASE_HEALTHCARE = "ai_use_case_healthcare"
    AI_USE_CASE_FINANCE = "ai_use_case_finance"
    AI_USE_CASE_OTHER = "ai_use_case_other"
    AI_RESEARCH_BREAKTHROUGH = "ai_research_breakthrough"


class Priority(str, Enum):
    """Priority levels for articles. 4 levels (spec adds 'critical' above reference)."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    """Source types for article ingestion."""
    RSS = "rss"
    TAVILY = "tavily"
    ARXIV = "arxiv"
    STOCK = "stock"
    PODCAST = "podcast"
    PRESS_RELEASE = "press_release"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class DateConfidence(str, Enum):
    """Confidence level for article published_at dates."""
    EXACT = "exact"
    SCRAPED = "scraped"
    INFERRED = "inferred"
    ANALYZED = "analyzed"
    FETCHED = "fetched"


class AgeStatus(str, Enum):
    """Article freshness status."""
    FRESH = "fresh"          # 0-7 days
    RECENT = "recent"        # 8-30 days
    HISTORICAL = "historical"  # 30+ days


@dataclass
class RawArticle:
    """
    Raw article data from any data source (RSS, Tavily, etc).
    """
    url: str
    title: str
    source_name: str
    source_url: str
    published_at: datetime
    summary: str = ""
    full_text: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal tracking
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    date_confidence: str = "fetched"
    content_hash: Optional[str] = None

    def __post_init__(self):
        """Ensure published_at is a datetime object."""
        if isinstance(self.published_at, str):
            for fmt in [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
            ]:
                try:
                    self.published_at = datetime.strptime(self.published_at, fmt)
                    break
                except ValueError:
                    continue


@dataclass
class ClassificationResult:
    """
    Classification result from Claude analysis.
    """
    article_url: str
    primary_category: str  # One of ContentCategory values
    priority: Priority = Priority.MEDIUM
    relevance_score: float = 0.5
    summary: str = ""
    key_takeaway: str = ""
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)
    people_mentioned: List[str] = field(default_factory=list)
    use_case_domains: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    confidence: float = 0.8

    # Metadata
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    classifier_model: str = ""
    raw_response: Optional[Dict[str, Any]] = None

    @classmethod
    def from_llm_response(cls, article_url: str, response: Dict[str, Any]) -> "ClassificationResult":
        """Create ClassificationResult from Claude's JSON response."""
        # Validate category
        primary_cat = response.get("primary_category", "market_analysis").lower().replace(" ", "_")
        valid_categories = [e.value for e in ContentCategory]
        if primary_cat not in valid_categories:
            primary_cat = "market_analysis"

        # Parse priority
        priority_str = response.get("priority", "medium").lower()
        try:
            priority = Priority(priority_str)
        except ValueError:
            priority = Priority.MEDIUM

        return cls(
            article_url=article_url,
            primary_category=primary_cat,
            priority=priority,
            relevance_score=float(response.get("relevance_score", 0.5)),
            summary=response.get("summary", ""),
            key_takeaway=response.get("key_takeaway", ""),
            companies_mentioned=response.get("companies_mentioned", []),
            technologies_mentioned=response.get("technologies_mentioned", []),
            people_mentioned=response.get("people_mentioned", []),
            use_case_domains=response.get("use_case_domains", []),
            sentiment=response.get("sentiment", "neutral"),
            confidence=float(response.get("confidence", 0.8)),
            raw_response=response,
        )


@dataclass
class DigestItem:
    """A single item in a digest."""
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    title: str = ""
    source_name: str = ""
    url: str = ""
    summary: str = ""
    category: str = ""
    priority: Priority = Priority.MEDIUM
    relevance_score: float = 0.5
    published_at: Optional[datetime] = None
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)


@dataclass
class Digest:
    """A complete intelligence digest."""
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_hours: int = 72
    executive_summary: str = ""
    items: List[DigestItem] = field(default_factory=list)
    total_items: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
