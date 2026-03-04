from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Patent:
    """
    Represents a technical patent or application retrieved from the
    USPTO PatentsView API to track competitor R&D signals.
    """
    id: str  # e.g., "US1234567B2"
    title: str
    abstract: str
    assignee: str  # Primary company (e.g., "Google LLC")
    inventors: List[str]
    filing_date: str  # YYYY-MM-DD
    publication_date: str  # YYYY-MM-DD
    patent_url: str
    domain: str = "quantum"  # 'quantum' or 'ai'
    
    # Optional strategic analysis fields
    relevance_score: Optional[float] = None
    innovation_category: Optional[str] = None
    
    # Processing metadata
    created_at: str = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "assignee": self.assignee,
            "inventors": self.inventors,
            "filing_date": self.filing_date,
            "publication_date": self.publication_date,
            "patent_url": self.patent_url,
            "domain": self.domain,
            "relevance_score": self.relevance_score,
            "innovation_category": self.innovation_category,
            "created_at": self.created_at
        }
