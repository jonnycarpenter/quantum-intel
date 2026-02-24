"""
Weekly Briefing Models
======================

Data models for the weekly intelligence briefing pipeline.
Two-agent architecture: Research Agent produces PreBrief observations,
Briefing Agent synthesizes into narrative sections with voice enrichment.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import json
import uuid


# =============================================================================
# RESEARCH AGENT OUTPUT MODELS
# =============================================================================

@dataclass
class PreBriefObservation:
    """Single observation from the Research Agent."""
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    priority_tag: str = ""        # "P1", "P2", "P3", "P4", "P5", "market", "research"
    signal_type: str = ""         # "development", "deal", "regulatory", "research", "risk", "milestone"
    companies: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    article_ids: List[str] = field(default_factory=list)
    summary: str = ""
    relevance_score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "topic": self.topic,
            "priority_tag": self.priority_tag,
            "signal_type": self.signal_type,
            "companies": self.companies,
            "technologies": self.technologies,
            "article_ids": self.article_ids,
            "summary": self.summary,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreBriefObservation":
        return cls(
            observation_id=data.get("observation_id", str(uuid.uuid4())),
            topic=data.get("topic", ""),
            priority_tag=data.get("priority_tag", ""),
            signal_type=data.get("signal_type", ""),
            companies=data.get("companies", []),
            technologies=data.get("technologies", []),
            article_ids=data.get("article_ids", []),
            summary=data.get("summary", ""),
            relevance_score=float(data.get("relevance_score", 0.5)),
        )


@dataclass
class PreBrief:
    """Full output of the Research Agent."""
    pre_brief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "quantum"
    observations: List[PreBriefObservation] = field(default_factory=list)
    article_count: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    batch_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pre_brief_id": self.pre_brief_id,
            "domain": self.domain,
            "observations": [o.to_dict() for o in self.observations],
            "article_count": self.article_count,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "batch_count": self.batch_count,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreBrief":
        return cls(
            pre_brief_id=data.get("pre_brief_id", str(uuid.uuid4())),
            domain=data.get("domain", "quantum"),
            observations=[PreBriefObservation.from_dict(o) for o in data.get("observations", [])],
            article_count=int(data.get("article_count", 0)),
            period_start=datetime.fromisoformat(data["period_start"]) if data.get("period_start") else None,
            period_end=datetime.fromisoformat(data["period_end"]) if data.get("period_end") else None,
            batch_count=int(data.get("batch_count", 0)),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
        )


# =============================================================================
# BRIEFING AGENT OUTPUT MODELS
# =============================================================================

@dataclass
class VoiceQuote:
    """Unified quote wrapper for earnings/SEC/podcast quotes in briefing context."""
    text: str = ""
    speaker: str = ""
    role: str = ""
    company: str = ""
    source_type: str = ""         # "earnings", "sec", "podcast"
    source_context: str = ""      # e.g. "Q4 2025 Earnings Call", "10-K FY2025", "Latent Space Podcast, Feb 18"
    relevance_score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "speaker": self.speaker,
            "role": self.role,
            "company": self.company,
            "source_type": self.source_type,
            "source_context": self.source_context,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceQuote":
        return cls(
            text=data.get("text", ""),
            speaker=data.get("speaker", ""),
            role=data.get("role", ""),
            company=data.get("company", ""),
            source_type=data.get("source_type", ""),
            source_context=data.get("source_context", ""),
            relevance_score=float(data.get("relevance_score", 0.5)),
        )


@dataclass
class Citation:
    """Article reference for inline citations."""
    number: int = 0
    article_id: str = ""
    title: str = ""
    url: str = ""
    source_name: str = ""
    published_at: Optional[str] = None  # ISO string

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "article_id": self.article_id,
            "title": self.title,
            "url": self.url,
            "source_name": self.source_name,
            "published_at": self.published_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        return cls(
            number=int(data.get("number", 0)),
            article_id=data.get("article_id", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            source_name=data.get("source_name", ""),
            published_at=data.get("published_at"),
        )


@dataclass
class BriefingSection:
    """One thematic section of the weekly briefing."""
    section_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    header: str = ""
    priority_tag: str = ""        # "P1"..."P5"
    priority_label: str = ""      # e.g. "Quantum Advantage"
    narrative: str = ""           # Markdown with inline [1], [2] citations
    voice_quotes: List[VoiceQuote] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    has_content: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "header": self.header,
            "priority_tag": self.priority_tag,
            "priority_label": self.priority_label,
            "narrative": self.narrative,
            "voice_quotes": [vq.to_dict() for vq in self.voice_quotes],
            "citations": [c.to_dict() for c in self.citations],
            "has_content": self.has_content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BriefingSection":
        return cls(
            section_id=data.get("section_id", str(uuid.uuid4())),
            header=data.get("header", ""),
            priority_tag=data.get("priority_tag", ""),
            priority_label=data.get("priority_label", ""),
            narrative=data.get("narrative", ""),
            voice_quotes=[VoiceQuote.from_dict(vq) for vq in data.get("voice_quotes", [])],
            citations=[Citation.from_dict(c) for c in data.get("citations", [])],
            has_content=bool(data.get("has_content", False)),
        )


@dataclass
class MarketMover:
    """Stock with >5% weekly change plus context."""
    ticker: str = ""
    company_name: str = ""
    close: Optional[float] = None
    change_pct: float = 0.0
    context_text: str = ""        # AI-generated context linking move to news
    linked_article_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "close": self.close,
            "change_pct": self.change_pct,
            "context_text": self.context_text,
            "linked_article_ids": self.linked_article_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketMover":
        return cls(
            ticker=data.get("ticker", ""),
            company_name=data.get("company_name", ""),
            close=data.get("close"),
            change_pct=float(data.get("change_pct", 0.0)),
            context_text=data.get("context_text", ""),
            linked_article_ids=data.get("linked_article_ids", []),
        )


@dataclass
class ResearchPaper:
    """Paper selected for the briefing."""
    arxiv_id: str = ""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    why_it_matters: str = ""      # Briefing Agent commentary
    commercial_readiness: Optional[str] = None
    relevance_score: Optional[float] = None
    abs_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "why_it_matters": self.why_it_matters,
            "commercial_readiness": self.commercial_readiness,
            "relevance_score": self.relevance_score,
            "abs_url": self.abs_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPaper":
        return cls(
            arxiv_id=data.get("arxiv_id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            why_it_matters=data.get("why_it_matters", ""),
            commercial_readiness=data.get("commercial_readiness"),
            relevance_score=data.get("relevance_score"),
            abs_url=data.get("abs_url", ""),
        )


# =============================================================================
# TOP-LEVEL BRIEFING MODEL
# =============================================================================

@dataclass
class WeeklyBriefing:
    """
    Top-level weekly briefing object.

    Contains all sections, market movers, and research papers.
    Stored as a single row in weekly_briefings table with JSON-serialized fields.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "quantum"
    week_of: str = ""             # ISO date string "2026-02-17" (Monday of the week)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sections: List[BriefingSection] = field(default_factory=list)
    market_movers: List[MarketMover] = field(default_factory=list)
    research_papers: List[ResearchPaper] = field(default_factory=list)
    articles_analyzed: int = 0
    sections_active: int = 0
    sections_total: int = 7       # P1-P5 + Market + Research
    generation_cost_usd: float = 0.0
    pre_brief_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "week_of": self.week_of,
            "created_at": self.created_at.isoformat(),
            "sections": [s.to_dict() for s in self.sections],
            "market_movers": [m.to_dict() for m in self.market_movers],
            "research_papers": [p.to_dict() for p in self.research_papers],
            "articles_analyzed": self.articles_analyzed,
            "sections_active": self.sections_active,
            "sections_total": self.sections_total,
            "generation_cost_usd": self.generation_cost_usd,
            "pre_brief_id": self.pre_brief_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklyBriefing":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            domain=data.get("domain", "quantum"),
            week_of=data.get("week_of", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            sections=[BriefingSection.from_dict(s) for s in data.get("sections", [])],
            market_movers=[MarketMover.from_dict(m) for m in data.get("market_movers", [])],
            research_papers=[ResearchPaper.from_dict(p) for p in data.get("research_papers", [])],
            articles_analyzed=int(data.get("articles_analyzed", 0)),
            sections_active=int(data.get("sections_active", 0)),
            sections_total=int(data.get("sections_total", 7)),
            generation_cost_usd=float(data.get("generation_cost_usd", 0.0)),
            pre_brief_id=data.get("pre_brief_id"),
        )
