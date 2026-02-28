"""
Agent Schemas
=============

Anthropic API tool definitions and shared agent dataclasses.
Used by RouterAgent and IntelligenceAgent.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ============================================================================
# TOOL DEFINITIONS (Anthropic API format)
# ============================================================================

QUANTUM_CATEGORIES = [
    "hardware_milestone", "error_correction", "algorithm_research",
    "use_case_drug_discovery", "use_case_finance", "use_case_optimization",
    "use_case_cybersecurity", "use_case_energy_materials", "use_case_ai_ml",
    "use_case_other", "education_workforce",
    "company_earnings", "funding_ipo", "partnership_contract",
    "personnel_leadership", "policy_regulation", "geopolitics",
    "market_analysis", "skepticism_critique",
]

AI_CATEGORIES = [
    "ai_model_release", "ai_product_launch", "ai_infrastructure",
    "ai_safety_alignment", "ai_open_source", "ai_use_case_enterprise",
    "ai_use_case_healthcare", "ai_use_case_finance", "ai_use_case_other",
    "ai_research_breakthrough",
    "company_earnings", "funding_ipo", "partnership_contract",
    "personnel_leadership", "policy_regulation", "geopolitics",
    "market_analysis", "skepticism_critique",
]

ALL_CATEGORIES = sorted(set(QUANTUM_CATEGORIES + AI_CATEGORIES))

CORPUS_SEARCH_TOOL = {
    "name": "corpus_search",
    "description": (
        "Search the intelligence corpus of classified articles and papers. "
        "Uses semantic similarity and keyword matching. Use this for questions "
        "about recent news, company activity, technology developments, or industry trends."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing what you're looking for",
            },
            "category": {
                "type": "string",
                "description": "Filter by content category",
                "enum": ALL_CATEGORIES,
            },
            "priority": {
                "type": "string",
                "description": "Filter by priority level",
                "enum": ["critical", "high", "medium", "low"],
            },
            "hours": {
                "type": "integer",
                "description": "Look back window in hours (default: 168 = 7 days)",
                "default": 168,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for real-time information using Exa. "
        "Use this when corpus results are insufficient, for very recent events, "
        "or when the user asks about something not yet in the corpus."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Web search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
                "default": 5,
            },
            "days": {
                "type": "integer",
                "description": "Limit results to the last N days (default: 7)",
                "default": 7,
            },
        },
        "required": ["query"],
    },
}

STOCK_DATA_TOOL = {
    "name": "stock_data",
    "description": (
        "Get stock market data for tracked companies. "
        "Returns current price, historical data, moving averages, "
        "and change percentages. Tickers include quantum (IONQ, QBTS, RGTI, "
        "QUBT, ARQQ, QMCO, LAES) and major tech (GOOGL, IBM, MSFT, AMZN, HON, NVDA, QTUM)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol (e.g., 'IONQ', 'GOOGL')",
            },
            "days": {
                "type": "integer",
                "description": "Number of days of history to return (default: 30)",
                "default": 30,
            },
        },
        "required": ["ticker"],
    },
}

ARXIV_SEARCH_TOOL = {
    "name": "arxiv_search",
    "description": (
        "Search ArXiv papers in the corpus. "
        "Returns paper metadata including title, authors, abstract, "
        "categories, relevance score, and commercial readiness assessment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for ArXiv papers",
            },
            "days": {
                "type": "integer",
                "description": "Look back window in days (default: 30)",
                "default": 30,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default: 10)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}

PODCAST_SEARCH_TOOL = {
    "name": "podcast_search",
    "description": (
        "Search podcast transcripts and extracted quotes from quantum computing "
        "and AI podcasts. Returns speaker quotes, themes, and episode metadata."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for podcast quotes and transcripts",
            },
            "podcast_id": {
                "type": "string",
                "description": "Optional podcast ID to filter results to a specific show",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default: 15)",
                "default": 15,
            },
        },
        "required": ["query"],
    },
}

# All tools available to the Intelligence Agent
ALL_INTELLIGENCE_TOOLS = [
    CORPUS_SEARCH_TOOL,
    WEB_SEARCH_TOOL,
    STOCK_DATA_TOOL,
    ARXIV_SEARCH_TOOL,
    PODCAST_SEARCH_TOOL,
]

# Valid routes for the Router Agent
VALID_ROUTES = frozenset({
    "digest",
    "quick_query",
    "stock_query",
    "paper_search",
    "deep_research",
})


# ============================================================================
# AGENT RESPONSE DATACLASSES
# ============================================================================

@dataclass
class RouterResult:
    """Result from the Router Agent's intent classification."""
    route: str
    confidence: float = 0.8
    reasoning: str = ""
    reformulated_query: Optional[str] = None


@dataclass
class AgentResponse:
    """Response from the Intelligence Agent."""
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls_made: int = 0
    model: str = ""
