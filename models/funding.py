"""
Funding Models
==============

Data models for Venture Capital and Startup funding events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class FundingEvent:
    """
    A distinct funding event or round extracted from an article.
    """
    id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))
    article_id: str = ""
    article_url: str = ""
    domain: str = ""  # "quantum" or "ai"
    
    # Financial details
    startup_name: str = ""
    funding_round: str = ""  # e.g., "Seed", "Series A", "Venture Round"
    funding_amount: str = ""  # e.g., "$100M"
    valuation: str = ""       # e.g., "$1B"
    lead_investors: List[str] = field(default_factory=list)
    other_investors: List[str] = field(default_factory=list)
    
    # Context
    investment_thesis: str = "" # Why the investors chose to invest
    known_technologies: List[str] = field(default_factory=list)
    use_of_funds: str = ""
    
    # Metadata
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = 0.8
    grounding_quote: str = "" # The verbatim text proving this happened


@dataclass
class FundingExtractionResult:
    """Result returned by the FundingExtractor."""
    article_id: str
    success: bool = True
    funding_events: List[FundingEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    extraction_time_seconds: float = 0.0
    extraction_cost_usd: float = 0.0
    extraction_model: str = ""
    source_length: int = 0
