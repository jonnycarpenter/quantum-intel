"""
Quantum Intelligence Hub — Agent Tools (Phase 3)

Tools available to the Intelligence Agent for answering user queries.
"""

from tools.corpus_search import CorpusSearchTool
from tools.web_search import WebSearchTool
from tools.stock_data import StockDataTool
from tools.arxiv_search import ArXivSearchTool
from tools.podcast_search import PodcastSearchTool

TOOL_REGISTRY = {
    "corpus_search": CorpusSearchTool,
    "web_search": WebSearchTool,
    "stock_data": StockDataTool,
    "arxiv_search": ArXivSearchTool,
    "podcast_search": PodcastSearchTool,
}

__all__ = [
    "CorpusSearchTool",
    "WebSearchTool",
    "StockDataTool",
    "ArXivSearchTool",
    "PodcastSearchTool",
    "TOOL_REGISTRY",
]
