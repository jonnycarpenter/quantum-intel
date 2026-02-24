"""
ArXiv Paper Model
=================

Data model for ArXiv papers in the Quantum Intelligence Hub.
Maps to the `papers` table in storage/schemas.py.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from models.article import RawArticle, SourceType


@dataclass
class Paper:
    """
    ArXiv paper data.

    Stored in the `papers` table for paper-specific queries,
    and also converted to RawArticle for the unified classification pipeline.
    """

    arxiv_id: str
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    categories: List[str] = field(default_factory=list)
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pdf_url: Optional[str] = None

    # LLM-generated fields (populated later by scoring pipeline)
    relevance_score: Optional[float] = None
    paper_type: Optional[str] = None  # breakthrough, incremental, review, theoretical
    use_case_category: Optional[str] = None
    commercial_readiness: Optional[str] = None  # near_term, mid_term, long_term, theoretical
    significance_summary: Optional[str] = None

    @property
    def abs_url(self) -> str:
        """ArXiv abstract page URL."""
        return f"https://arxiv.org/abs/{self.arxiv_id}"

    @classmethod
    def from_arxiv_entry(cls, entry_data: Dict[str, Any]) -> "Paper":
        """
        Create a Paper from parsed ArXiv API entry data.

        Args:
            entry_data: Dict with keys: arxiv_id, title, authors, abstract,
                       categories, published, updated, pdf_url
        """
        published_at = entry_data.get("published")
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                published_at = None

        updated_at = entry_data.get("updated")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                updated_at = None

        return cls(
            arxiv_id=entry_data.get("arxiv_id", ""),
            title=entry_data.get("title", "").strip(),
            authors=entry_data.get("authors", []),
            abstract=entry_data.get("abstract", "").strip(),
            categories=entry_data.get("categories", []),
            published_at=published_at,
            updated_at=updated_at,
            pdf_url=entry_data.get("pdf_url"),
        )

    def to_raw_article(self, query_metadata: Optional[Dict[str, Any]] = None) -> RawArticle:
        """
        Convert to RawArticle for the unified classification pipeline.

        Args:
            query_metadata: Optional extra metadata from the query that found this paper
        """
        content_for_hash = f"{self.title}|{self.abstract[:200]}"
        content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()

        metadata = {
            "source_type": SourceType.ARXIV.value,
            "arxiv_id": self.arxiv_id,
            "authors": self.authors,
            "categories": self.categories,
            "pdf_url": self.pdf_url,
        }
        if query_metadata:
            metadata.update(query_metadata)

        return RawArticle(
            url=self.abs_url,
            title=self.title,
            source_name="ArXiv",
            source_url=self.abs_url,
            published_at=self.published_at or datetime.now(timezone.utc),
            summary=self.abstract[:2000],
            full_text=self.abstract,
            author=", ".join(self.authors[:5]) if self.authors else None,
            tags=self.categories,
            date_confidence="exact" if self.published_at else "fetched",
            content_hash=content_hash,
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "categories": self.categories,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "pdf_url": self.pdf_url,
            "relevance_score": self.relevance_score,
            "paper_type": self.paper_type,
            "use_case_category": self.use_case_category,
            "commercial_readiness": self.commercial_readiness,
            "significance_summary": self.significance_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paper":
        """Create from dictionary (from storage)."""
        for dt_field in ["published_at", "updated_at", "ingested_at"]:
            val = data.get(dt_field)
            if val and isinstance(val, str):
                try:
                    data[dt_field] = datetime.fromisoformat(val)
                except ValueError:
                    data[dt_field] = None

        # Ensure list fields
        if isinstance(data.get("authors"), str):
            import json
            try:
                data["authors"] = json.loads(data["authors"])
            except (json.JSONDecodeError, TypeError):
                data["authors"] = []

        if isinstance(data.get("categories"), str):
            import json
            try:
                data["categories"] = json.loads(data["categories"])
            except (json.JSONDecodeError, TypeError):
                data["categories"] = []

        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
