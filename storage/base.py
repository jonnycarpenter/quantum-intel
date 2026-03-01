"""
Storage Backend — Abstract Base Class
======================================

Abstract interface for storage backends. Implementations can swap
between SQLite (dev) and BigQuery (prod) without changing business logic.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set, Any
from dataclasses import dataclass, field, asdict

from models.article import (
    RawArticle,
    ClassificationResult,
    Digest,
    DigestItem,
    ContentCategory,
    Priority,
    SourceType,
)
from models.paper import Paper
from models.stock import StockSnapshot
from models.earnings import EarningsTranscript, ExtractedQuote
from models.sec_filing import SecFiling, SecNugget
from models.podcast import PodcastTranscript, PodcastQuote
from models.weekly_briefing import WeeklyBriefing
from models.case_study import CaseStudy


@dataclass
class ClassifiedArticle:
    """
    Combined article + classification data for storage.
    Primary data model for persisted articles.
    """
    # Core Article Data
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    url: str = ""
    title: str = ""
    source_name: str = ""
    source_url: str = ""
    source_type: str = SourceType.RSS.value
    published_at: Optional[datetime] = None
    date_confidence: str = "fetched"
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""
    full_text: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Classification Data
    primary_category: str = "market_analysis"
    priority: str = "medium"
    relevance_score: float = 0.5
    ai_summary: str = ""
    key_takeaway: str = ""
    companies_mentioned: List[str] = field(default_factory=list)
    technologies_mentioned: List[str] = field(default_factory=list)
    people_mentioned: List[str] = field(default_factory=list)
    use_case_domains: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    confidence: float = 0.8
    classifier_model: str = ""
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Digest Data
    digest_priority: str = "medium"
    feed_eligible: bool = True

    # Deduplication Data
    content_hash: Optional[str] = None
    coverage_count: int = 1
    duplicate_urls: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Domain
    domain: str = "quantum"  # "quantum" or "ai"

    @classmethod
    def from_raw_and_classification(
        cls,
        raw: RawArticle,
        classification: ClassificationResult,
    ) -> "ClassifiedArticle":
        """Combine RawArticle + ClassificationResult."""
        base_priority = (
            classification.priority.value
            if isinstance(classification.priority, Priority)
            else str(classification.priority)
        )

        # Merge ROI / use-case fields from LLM response into metadata
        merged_metadata = dict(raw.metadata)
        if classification.raw_response:
            roi_keys = [
                "roi_confirmed", "roi_type", "roi_metrics",
                "industries", "departments", "ai_technology",
                "implementation_scale",
                "reality_check_score", "reality_check_reasoning",
            ]
            for key in roi_keys:
                val = classification.raw_response.get(key)
                if val is not None:
                    merged_metadata[key] = val

        return cls(
            url=raw.url,
            title=raw.title,
            source_name=raw.source_name,
            source_url=raw.source_url,
            source_type=raw.metadata.get("source_type", "rss"),
            published_at=raw.published_at if isinstance(raw.published_at, datetime) else None,
            date_confidence=getattr(raw, "date_confidence", "fetched"),
            fetched_at=raw.fetched_at,
            summary=raw.summary,
            full_text=raw.full_text,
            author=raw.author,
            tags=raw.tags,
            primary_category=str(classification.primary_category),
            priority=base_priority,
            relevance_score=classification.relevance_score,
            ai_summary=classification.summary,
            key_takeaway=classification.key_takeaway,
            companies_mentioned=classification.companies_mentioned,
            technologies_mentioned=classification.technologies_mentioned,
            people_mentioned=classification.people_mentioned,
            use_case_domains=classification.use_case_domains,
            sentiment=classification.sentiment,
            confidence=classification.confidence,
            classifier_model=classification.classifier_model,
            classified_at=classification.classified_at,
            digest_priority=base_priority,
            content_hash=raw.content_hash,
            metadata=merged_metadata,
            domain=raw.metadata.get("domain", "quantum"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        for dt_field in ["published_at", "fetched_at", "classified_at"]:
            if data.get(dt_field) and isinstance(data[dt_field], datetime):
                data[dt_field] = data[dt_field].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClassifiedArticle":
        """Create from dictionary (from storage)."""
        for dt_field in ["published_at", "fetched_at", "classified_at"]:
            if data.get(dt_field) and isinstance(data[dt_field], str):
                try:
                    data[dt_field] = datetime.fromisoformat(data[dt_field])
                except ValueError:
                    data[dt_field] = None
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class StorageBackend(ABC):
    """
    Abstract storage interface.
    Same contract for SQLite (dev) and BigQuery (prod).
    """

    # Article Operations
    @abstractmethod
    async def save_articles(self, articles: List[ClassifiedArticle]) -> int:
        """Save classified articles. Returns count saved."""
        pass

    @abstractmethod
    async def get_article_by_url(self, url: str) -> Optional[ClassifiedArticle]:
        """Get a single article by URL."""
        pass

    @abstractmethod
    async def get_recent_articles(self, hours: int = 72, limit: int = 500, domain: Optional[str] = None) -> List[ClassifiedArticle]:
        """Get articles from the last N hours, newest first. Optionally filter by domain."""
        pass

    @abstractmethod
    async def get_articles_by_category(self, category: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None) -> List[ClassifiedArticle]:
        """Get articles by primary category. Optionally filter by domain."""
        pass

    @abstractmethod
    async def get_articles_by_priority(self, priority: str, hours: int = 168, limit: int = 100, domain: Optional[str] = None) -> List[ClassifiedArticle]:
        """Get articles by priority level. Optionally filter by domain."""
        pass

    @abstractmethod
    async def search_articles(self, query: str, hours: int = 168, limit: int = 50, domain: Optional[str] = None) -> List[ClassifiedArticle]:
        """Search articles by text. Optionally filter by domain."""
        pass

    # Deduplication Support
    @abstractmethod
    async def url_exists(self, url: str) -> bool:
        """Check if URL exists in storage."""
        pass

    @abstractmethod
    async def get_recent_urls(self, hours: int = 168) -> Set[str]:
        """Get all URLs from last N hours for dedup."""
        pass

    @abstractmethod
    async def get_recent_titles(self, hours: int = 168) -> Dict[str, str]:
        """Get recent title->URL mapping for fuzzy dedup."""
        pass

    @abstractmethod
    async def get_recent_articles_for_dedup(self, hours: int = 168, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get minimal article data for dedup cache building."""
        pass

    # Digest Operations
    @abstractmethod
    async def save_digest(self, digest: Digest) -> str:
        """Save a generated digest. Returns digest ID."""
        pass

    @abstractmethod
    async def get_latest_digest(self) -> Optional[Digest]:
        """Get the most recent digest."""
        pass

    # Paper Operations
    @abstractmethod
    async def save_papers(self, papers: List[Paper]) -> int:
        """Save ArXiv papers. Returns count saved."""
        pass

    @abstractmethod
    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get a single paper by ArXiv ID."""
        pass

    @abstractmethod
    async def get_recent_papers(self, days: int = 7, limit: int = 50) -> List[Paper]:
        """Get recent papers, newest first."""
        pass

    @abstractmethod
    async def arxiv_id_exists(self, arxiv_id: str) -> bool:
        """Check if an ArXiv paper is already stored."""
        pass

    # Stock Operations
    @abstractmethod
    async def save_stock_data(self, snapshots: List[StockSnapshot]) -> int:
        """Save stock snapshots. Returns count saved."""
        pass

    @abstractmethod
    async def get_stock_data(self, ticker: str, days: int = 30) -> List[StockSnapshot]:
        """Get stock history for a ticker."""
        pass

    @abstractmethod
    async def get_latest_stock_data(self, tickers: Optional[List[str]] = None) -> List[StockSnapshot]:
        """Get most recent data point for each ticker."""
        pass

    # Stats
    @abstractmethod
    async def get_article_count(self, hours: int = 24) -> int:
        """Get count of articles in time window."""
        pass

    @abstractmethod
    async def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics."""
        pass

    # =========================================================================
    # Earnings Operations (Phase 4A)
    # =========================================================================

    @abstractmethod
    async def save_transcript(self, transcript: EarningsTranscript) -> str:
        """Save an earnings transcript. Returns transcript_id."""
        ...

    @abstractmethod
    async def transcript_exists(self, ticker: str, year: int, quarter: int) -> bool:
        """Check if transcript already stored."""
        ...

    @abstractmethod
    async def save_quotes(self, quotes: List[ExtractedQuote]) -> int:
        """Save extracted earnings quotes. Returns count saved."""
        ...

    @abstractmethod
    async def get_quotes_by_ticker(
        self, ticker: str, limit: int = 50
    ) -> List[ExtractedQuote]:
        """Get quotes for a specific ticker."""
        ...

    # =========================================================================
    # SEC Operations (Phase 4A)
    # =========================================================================

    @abstractmethod
    async def save_filing(self, filing: SecFiling) -> str:
        """Save an SEC filing. Returns filing_id."""
        ...

    @abstractmethod
    async def filing_exists(
        self, ticker: str, filing_type: str, fiscal_year: int, fiscal_quarter: Optional[int] = None
    ) -> bool:
        """Check if filing already stored."""
        ...

    @abstractmethod
    async def save_nuggets(self, nuggets: List[SecNugget]) -> int:
        """Save extracted SEC nuggets. Returns count saved."""
        ...

    @abstractmethod
    async def get_nuggets_by_ticker(
        self, ticker: str, limit: int = 50
    ) -> List[SecNugget]:
        """Get nuggets for a specific ticker."""
        ...

    # =========================================================================
    # Podcast Operations (Phase 4B)
    # =========================================================================

    @abstractmethod
    async def save_podcast_transcript(self, transcript: PodcastTranscript) -> str:
        """Save a podcast transcript. Returns transcript_id."""
        ...

    @abstractmethod
    async def podcast_episode_exists(self, podcast_id: str, episode_id: str) -> bool:
        """Check if a podcast episode transcript is already stored."""
        ...

    @abstractmethod
    async def save_podcast_quotes(self, quotes: List[PodcastQuote]) -> int:
        """Save extracted podcast quotes. Returns count saved."""
        ...

    @abstractmethod
    async def get_podcast_quotes(
        self, podcast_id: Optional[str] = None, limit: int = 50
    ) -> List[PodcastQuote]:
        """Get podcast quotes, optionally filtered by podcast."""
        ...

    @abstractmethod
    async def search_podcast_quotes(
        self, query: str, limit: int = 30
    ) -> List[PodcastQuote]:
        """Search podcast quotes by text."""
        ...

    # =========================================================================
    # Weekly Briefing Operations
    # =========================================================================

    @abstractmethod
    async def save_weekly_briefing(self, briefing: WeeklyBriefing) -> str:
        """Save a weekly briefing. Returns briefing ID."""
        ...

    @abstractmethod
    async def get_latest_weekly_briefing(self, domain: str = "quantum") -> Optional[WeeklyBriefing]:
        """Get the most recent weekly briefing for a domain."""
        ...

    @abstractmethod
    async def get_weekly_briefing_by_week(self, domain: str, week_of: str) -> Optional[WeeklyBriefing]:
        """Get a specific week's briefing."""
        ...

    # =========================================================================
    # Case Study Operations (Phase 6)
    # =========================================================================

    @abstractmethod
    async def save_case_studies(self, case_studies: List[CaseStudy]) -> int:
        """Save extracted case studies. Returns count saved."""
        ...

    @abstractmethod
    async def get_case_studies_by_source(
        self, source_type: str, source_id: str
    ) -> List[CaseStudy]:
        """Get case studies for a specific source item."""
        ...

    @abstractmethod
    async def get_case_studies(
        self,
        domain: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[CaseStudy]:
        """Get case studies with optional filters."""
        ...

    @abstractmethod
    async def case_studies_exist_for_source(
        self, source_type: str, source_id: str
    ) -> bool:
        """Check if case studies already extracted for this source."""
        ...

    @abstractmethod
    async def search_case_studies(
        self, query: str, domain: Optional[str] = None, limit: int = 30
    ) -> List[CaseStudy]:
        """Search case studies by text."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close storage connections."""
        pass
