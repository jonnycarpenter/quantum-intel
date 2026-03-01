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
            "include_text": {
                "type": "string",
                "description": "If provided, only returns pages containing this specific text string (useful for forcing exact mention of a term).",
            },
            "exclude_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of domains to explicitly exclude from the search results (e.g. ['wikipedia.org', 'youtube.com']).",
            }
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

SUBMIT_FEEDBACK_TOOL = {
    "name": "submit_user_feedback",
    "description": (
        "Submit user feedback, feature requests, or bug reports directly to the engineering team. "
        "Use this when a user complains about the platform, asks for a new feature, or explicitly wants to send feedback."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "feedback_type": {
                "type": "string",
                "description": "Category of the feedback",
                "enum": ["bug", "feature_request", "general_feedback"],
            },
            "message": {
                "type": "string",
                "description": "The actual message summarizing the user's feedback",
            },
            "user_context": {
                "type": "string",
                "description": "Optional context about what the user was doing when they submitted the feedback",
            },
        },
        "required": ["feedback_type", "message"],
    },
}

WRITE_SCRATCHPAD_TOOL = {
    "name": "write_to_scratchpad",
    "description": (
        "Write raw text to your internal scratchpad memory. This memory will be injected into your system prompt on the very next turn. "
        "Use this to hold onto intermediate thoughts, lists of company tickers, or facts while you use other tools to gather more information. "
        "Note: Overwrites the existing scratchpad."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The information you want to save into your working memory.",
            }
        },
        "required": ["content"],
    },
}

ADHOC_SEC_TOOL = {
    "name": "fetch_adhoc_sec_filing",
    "description": (
        "Trigger the ingestion pipeline to fetch an SEC filing (10-K, 10-Q, 8-K) for a given ticker, "
        "extract its quotes with an LLM, and save it to the database for all users. Use this when the user asks on-demand "
        "for a filing we don't have. Warning: This takes ~30-60 seconds to complete."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g. IONQ, GOOGL).",
            },
            "filing_type": {
                "type": "string",
                "description": "The SEC form type requested.",
                "enum": ["10-K", "10-Q", "8-K"],
            }
        },
        "required": ["ticker", "filing_type"],
    },
}

ADHOC_EARNINGS_TOOL = {
    "name": "fetch_adhoc_earnings_call",
    "description": (
        "Trigger the ingestion pipeline to fetch an earnings call transcript for a given ticker and quarter, "
        "extract its strategic quotes with an LLM, and save it to the database for all users. "
        "Warning: This takes ~30-60 seconds to complete."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g. IONQ, GOOGL).",
            },
            "year": {
                "type": "integer",
                "description": "The four-digit fiscal year.",
            },
            "quarter": {
                "type": "integer",
                "description": "The fiscal quarter (1-4).",
            }
        },
        "required": ["ticker", "year", "quarter"],
    },
}

FRONTEND_COMMAND_TOOL = {
    "name": "dispatch_frontend_command",
    "description": (
        "Control the user's React frontend by emitting a WebSocket/SSE event. "
        "Use this exclusively when the user says things like 'Take me to the pipeline', 'Show me AI companies', "
        "or 'Open the ad-hoc analysis window'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Command type (e.g. 'navigate', 'apply_filters', 'open_modal').",
            },
            "target": {
                "type": "string",
                "description": "The route (e.g. '/pipeline', '/brief') or modal ID representing the destination.",
            },
            "filters": {
                "type": "object",
                "description": "JSON object mapping filter names to values if the user wants specific data shown (e.g. {'domain': 'quantum'}).",
                "additionalProperties": {"type": "string"}
            }
        },
        "required": ["action"],
    },
}

PLATFORM_KNOWLEDGE_TOOL = {
    "name": "query_platform_features",
    "description": (
        "Search the internal Ket Zero Knowledge Base for help documentation and platform guides. "
        "Use this when the user asks questions like 'How do I use X?', 'What does the brevity score mean?', or 'How does the feed work?'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's question about the platform.",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of guide chunks to return (default: 3).",
                "default": 3,
            }
        },
        "required": ["query"],
    },
}

NANO_BANANA_TOOL = {
    "name": "generate_infographic",
    "description": (
        "Generate a professional infographic, diagram, or data visualization using the Nano Banana 2 (Gemini Imagen 3) engine. "
        "Use this tool when creating Ad-Hoc Analysis reports, or when the user explicitly asks for a visual representation. "
        "Returns a markdown image string you must embed in your response."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A highly detailed, comprehensive description of the image to generate. Be specific about colors, layout, and textual elements.",
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Aspect ratio of the generated image (e.g. '16:9', '1:1', '4:3').",
                "default": "16:9",
            },
            "style": {
                "type": "string",
                "description": "The style of the image (e.g. 'clean vector art', 'minimalist dashboard screenshot', '3d isometric tech diagram').",
                "default": "clean vector art",
            }
        },
        "required": ["prompt"],
    },
}

FIND_SIMILAR_TOOL = {
    "name": "find_similar_articles",
    "description": (
        "Use Exa's neural network to find web pages that are highly similar in context and quality to a specific target URL. "
        "Use this tool when a user provides a URL they like and asks to find 'more stuff like this', or when you find a great "
        "source via web_search and want to discover related high-value intelligence sources (e.g. competitors, related funding rounds). "
        "Do NOT use this tool for keyword searches; this tool ONLY accepts a valid URL."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The exact URL of the web page you want to find similar content for.",
            },
            "num_results": {
                "type": "integer",
                "description": "Maximum number of lookalike URLs to return (default: 5).",
                "default": 5,
            },
            "exclude_source_domain": {
                "type": "boolean",
                "description": "If true, exclude other pages from the same website to force discovery of new sources.",
                "default": True,
            }
        },
        "required": ["url"],
    }
}

SEARCH_CASE_STUDIES_TOOL = {
    "name": "search_case_studies",
    "description": (
        "Search explicitly through parsed case studies. "
        "Useful for understanding how companies or industries are deploying technology, "
        "their specific use cases, blockers, metrics, and outcomes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or topics to search for within case cases.",
            },
            "domain": {
                "type": "string",
                "description": "Domain to filter by, typically 'quantum' or 'ai'.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return. Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

SEARCH_EARNINGS_QUOTES_TOOL = {
    "name": "search_earnings_quotes",
    "description": (
        "Search the database of historical earnings quotes. "
        "Useful for finding out exactly what a company (or overall industry) has said "
        "about a specific topic (e.g. 'GPU CapEx', 'deployment blockers') during earnings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or keyword to search for in quotes, themes, tech mentioned, etc.",
            },
            "ticker": {
                "type": "string",
                "description": "Optional stock ticker symbol to narrow search down to a specific company.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return. Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

SEARCH_SEC_NUGGETS_TOOL = {
    "name": "search_sec_nuggets",
    "description": (
        "Search the database of historical SEC filing risk factors, MD&A insights, and nuggets. "
        "Useful for understanding official company disclosures, risk factors, or strategic statements."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or keyword to search for in nuggets.",
            },
            "ticker": {
                "type": "string",
                "description": "Optional stock ticker symbol to narrow search down to a specific company.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return. Default 5.",
                "default": 5,
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
    SUBMIT_FEEDBACK_TOOL,
    WRITE_SCRATCHPAD_TOOL,
    ADHOC_SEC_TOOL,
    ADHOC_EARNINGS_TOOL,
    FRONTEND_COMMAND_TOOL,
    PLATFORM_KNOWLEDGE_TOOL,
    NANO_BANANA_TOOL,
    FIND_SIMILAR_TOOL,
    SEARCH_CASE_STUDIES_TOOL,
    SEARCH_EARNINGS_QUOTES_TOOL,
    SEARCH_SEC_NUGGETS_TOOL,
]

# Valid routes for the Router Agent
VALID_ROUTES = frozenset({
    "digest",
    "quick_query",
    "stock_query",
    "paper_search",
    "deep_research",
    "full_report",
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
