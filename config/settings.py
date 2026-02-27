"""
Ingestion Pipeline Configuration
================================

Configuration and constants for the Quantum Intelligence Hub ingestion pipeline.
Includes core ingestion, agent, earnings, SEC, and StockNews configs.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class IngestionConfig:
    """Configuration for the ingestion pipeline."""

    # API Keys (from environment)
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    tavily_api_key: str = field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY", "")
    )

    # Ingestion Settings
    rss_poll_interval_hours: int = 4
    max_articles_per_feed: int = 20
    max_article_age_days: int = 7

    # Classification (Haiku for cost efficiency on high volume)
    classifier_model: str = field(
        default_factory=lambda: os.getenv(
            "CLASSIFICATION_MODEL", "claude-haiku-4-5"
        )
    )
    classifier_temperature: float = 0.1
    classifier_max_concurrent: int = 5

    # Digest generation
    digest_hours: int = 72
    digest_max_items: int = 50
    digest_model: str = field(
        default_factory=lambda: os.getenv(
            "DIGEST_MODEL", "claude-sonnet-4-6"
        )
    )

    # Tavily
    tavily_search_depth: str = "advanced"  # "basic" or "advanced"
    tavily_max_results_per_query: int = 10

    # ArXiv
    arxiv_rate_limit_seconds: float = 3.0
    arxiv_max_results_per_query: int = 50

    # Stock data
    stock_data_provider: str = field(
        default_factory=lambda: os.getenv("STOCK_DATA_PROVIDER", "yfinance")
    )
    stock_fetch_days: int = 60


@dataclass
class AgentConfig:
    """Configuration for the intelligence agent layer."""

    # API Keys (from environment)
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    tavily_api_key: str = field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY", "")
    )

    # Router Agent
    router_model: str = field(
        default_factory=lambda: os.getenv(
            "ROUTER_MODEL", "claude-haiku-4-5"
        )
    )

    # Intelligence Agent
    intelligence_model: str = field(
        default_factory=lambda: os.getenv(
            "INTELLIGENCE_MODEL", "claude-sonnet-4-6"
        )
    )
    intelligence_temperature: float = 0.3
    max_tool_calls: int = 5
    intelligence_max_tokens: int = 2048


# ============================================================================
# Voice Pipeline Configs (Phase 4A)
# ============================================================================

@dataclass
class EarningsConfig:
    """Configuration for the Earnings Call pipeline."""

    # API Ninjas
    api_ninja_api_key: str = field(
        default_factory=lambda: os.getenv("API_NINJA_API_KEY", "")
    )
    api_ninja_base_url: str = "https://api.api-ninjas.com/v1"
    api_ninja_rate_limit_seconds: float = 1.0
    max_quarters_to_fetch: int = 4  # per ticker

    # Quote extraction
    extraction_model: str = field(
        default_factory=lambda: os.getenv(
            "EARNINGS_EXTRACTION_MODEL", "claude-sonnet-4-6"
        )
    )
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 16_000  # Must be large enough for 10-25 quotes of JSON
    max_transcript_chars: int = 150_000  # Truncate long transcripts


@dataclass
class SecConfig:
    """Configuration for the SEC Filing pipeline (uses sec-api.io)."""

    # sec-api.io endpoints
    sec_api_query_url: str = "https://api.sec-api.io"
    sec_api_extractor_url: str = "https://api.sec-api.io/extractor"
    sec_api_archive_url: str = "https://archive.sec-api.io"
    sec_api_key: str = field(
        default_factory=lambda: os.getenv("SECIO_API_KEY", "")
    )
    sec_api_rate_limit_seconds: float = 0.5  # 500ms between requests
    filing_types: List[str] = field(
        default_factory=lambda: ["10-K", "10-Q", "8-K"]
    )
    # Sections to extract from 10-K/10-Q (sec-api.io section IDs)
    extract_sections: List[str] = field(
        default_factory=lambda: ["1", "1A", "7", "7A"]
    )

    # EDGAR fallback (free — just needs User-Agent)
    edgar_data_url: str = "https://data.sec.gov"
    edgar_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "SEC_USER_AGENT", "QuantumIntelHub admin@example.com"
        )
    )

    # Nugget extraction
    extraction_model: str = field(
        default_factory=lambda: os.getenv(
            "SEC_EXTRACTION_MODEL", "claude-sonnet-4-6"
        )
    )
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 16_000  # Must be large enough for 15+ nuggets of JSON
    max_filing_chars: int = 200_000  # Truncate large filings


@dataclass
class StockNewsConfig:
    """Configuration for StockNews API integration."""

    api_key: str = field(
        default_factory=lambda: os.getenv("STOCKNEWS_API_KEY", "")
    )
    base_url: str = "https://stocknewsapi.com/api/v1"
    max_items_per_request: int = 50
    rate_limit_seconds: float = 1.0


@dataclass
class PodcastConfig:
    """Configuration for the Podcast ingestion pipeline."""

    # AssemblyAI
    assemblyai_api_key: str = field(
        default_factory=lambda: os.getenv("ASSEMBLYAI_API_KEY", "")
    )

    # Quote extraction
    extraction_model: str = field(
        default_factory=lambda: os.getenv(
            "PODCAST_EXTRACTION_MODEL", "claude-sonnet-4-6"
        )
    )
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 4096

    # Transcript chunking
    chunk_size: int = 30_000         # Characters per chunk
    chunk_overlap: int = 3_000       # Overlap between chunks
    dedup_similarity: float = 0.85   # Dedup threshold

    # Episode discovery
    max_episode_age_days: int = 14   # 14-day lookback for weekly Sunday runs
    max_episodes_per_run: int = 5    # Limit per podcast per run
    rss_poll_interval_hours: int = 12


# ============================================================================
# Weekly Briefing Config
# ============================================================================

@dataclass
class WeeklyBriefingConfig:
    """Configuration for the Weekly Briefing pipeline (2-agent)."""

    # Research Agent (Sonnet — fast, cheap analysis)
    research_model: str = field(
        default_factory=lambda: os.getenv("BRIEFING_RESEARCH_MODEL", "claude-sonnet-4-6")
    )
    research_temperature: float = 0.1
    research_max_tokens: int = 4096
    research_batch_size: int = 40

    # Briefing Agent (Opus — strategic synthesis quality)
    briefing_model: str = field(
        default_factory=lambda: os.getenv("BRIEFING_SYNTHESIS_MODEL", "claude-opus-4-6")
    )
    briefing_temperature: float = 0.3
    briefing_max_tokens: int = 16000

    # Data windows
    lookback_days: int = 14
    min_priority: str = "medium"  # Include medium, high, critical
    max_articles: int = 500

    # Market movers
    market_mover_threshold_pct: float = 5.0
    stock_lookback_days: int = 14

    # Voice enrichment
    max_quotes_per_ticker: int = 3
    max_nuggets_per_ticker: int = 3
    max_podcast_quotes: int = 10

    # Cost tracking
    track_costs: bool = True


# ============================================================================
# Case Study Config (Phase 6)
# ============================================================================

@dataclass
class CaseStudyConfig:
    """Configuration for the Case Study extraction pipeline."""

    extraction_model: str = field(
        default_factory=lambda: os.getenv(
            "CASE_STUDY_EXTRACTION_MODEL", "claude-sonnet-4-6"
        )
    )
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 16_000
    max_source_chars: int = 150_000      # Truncate long sources
    chunk_size: int = 30_000             # For long content
    chunk_overlap: int = 3_000
    dedup_similarity: float = 0.85
    max_case_studies_per_source: int = 10  # Cap per source item


# ============================================================================
# SOURCE BLOCKLISTS
# ============================================================================

BLOCKED_SOURCES: List[str] = [
    # Add sources that produce high-volume, low-value content as discovered
]

BLOCKED_DOMAINS: List[str] = [
    # Domains that are off-topic for quantum computing intelligence
]
