"""
Test Integration
================

End-to-end integration tests for the agent pipeline.
Uses mocked LLM but real storage (temp SQLite).
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import List, Any

from storage.sqlite import SQLiteStorage
from storage.base import ClassifiedArticle
from models.paper import Paper
from models.stock import StockSnapshot
from agents.router import RouterAgent
from agents.intelligence import IntelligenceAgent


# ============================================================================
# MOCK HELPERS
# ============================================================================

@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    name: str = ""
    input: dict = None
    id: str = "tool_int"

    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class MockResponse:
    content: List[Any] = None
    stop_reason: str = "end_turn"
    usage: MockUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = []
        if self.usage is None:
            self.usage = MockUsage()


def make_mock_llm():
    mock = MagicMock()
    mock.messages_create = AsyncMock()
    mock.extract_text = lambda response: "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return mock


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except PermissionError:
        pass


@pytest_asyncio.fixture
async def storage(tmp_db):
    store = SQLiteStorage(db_path=tmp_db)
    yield store
    await store.close()


@pytest_asyncio.fixture
async def seeded_storage(storage):
    """Storage with test articles, papers, and stocks."""
    articles = [
        ClassifiedArticle(
            url="https://example.com/ionq-milestone",
            title="IonQ Achieves 99.9% Gate Fidelity",
            source_name="The Quantum Insider",
            primary_category="hardware_milestone",
            priority="critical",
            relevance_score=0.95,
            ai_summary="IonQ demonstrates record gate fidelity on trapped-ion processor.",
            key_takeaway="Highest gate fidelity achieved on commercial hardware.",
            companies_mentioned=["IonQ"],
            technologies_mentioned=["trapped-ion"],
        ),
        ClassifiedArticle(
            url="https://example.com/ibm-error",
            title="IBM Demonstrates Quantum Error Correction",
            source_name="Nature",
            primary_category="error_correction",
            priority="high",
            relevance_score=0.88,
            ai_summary="IBM shows surface code error correction on Eagle processor.",
            companies_mentioned=["IBM"],
            technologies_mentioned=["superconducting"],
        ),
        ClassifiedArticle(
            url="https://example.com/dwave-funding",
            title="D-Wave Secures $150M Funding Round",
            source_name="TechCrunch",
            primary_category="funding_ipo",
            priority="high",
            relevance_score=0.75,
            ai_summary="D-Wave raises $150M to expand quantum annealing platform.",
            companies_mentioned=["D-Wave"],
        ),
    ]
    await storage.save_articles(articles)

    papers = [
        Paper(
            arxiv_id="2401.99999",
            title="Surface Code Error Correction at Scale",
            authors=["A. Researcher"],
            abstract="We present scalable quantum error correction using surface codes.",
            categories=["quant-ph"],
            published_at=datetime(2026, 2, 15, tzinfo=timezone.utc),
            relevance_score=8.0,
            paper_type="breakthrough",
            commercial_readiness="mid_term",
        ),
    ]
    await storage.save_papers(papers)

    stocks = [
        StockSnapshot(ticker="IONQ", date="2026-02-18", close=12.50, volume=3000000, change_percent=1.5, sma_20=12.00, sma_50=11.50),
        StockSnapshot(ticker="IONQ", date="2026-02-19", close=12.80, volume=3500000, change_percent=2.4, sma_20=12.10, sma_50=11.60),
    ]
    await storage.save_stock_data(stocks)

    return storage


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_pipeline_quick_query(seeded_storage):
    """Test complete pipeline: route → agent → answer with corpus search."""
    mock_llm = make_mock_llm()

    # Router returns quick_query
    router_response = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "quick_query",
            "confidence": 0.9,
            "reasoning": "General quantum question",
        }))]
    )

    # Agent: first requests corpus_search, then returns text
    tool_call_response = MockResponse(
        content=[MockToolUseBlock(
            name="corpus_search",
            input={"query": "IonQ"},
            id="tool_q1",
        )],
        stop_reason="tool_use",
    )
    final_response = MockResponse(
        content=[MockTextBlock(
            text="IonQ achieved 99.9% gate fidelity, a major milestone in trapped-ion computing."
        )]
    )

    mock_llm.messages_create.side_effect = [router_response, tool_call_response, final_response]

    router = RouterAgent(llm_client=mock_llm)
    agent = IntelligenceAgent(llm_client=mock_llm)
    agent._tools["corpus_search"]._storage = seeded_storage
    agent._tools["corpus_search"]._embeddings = None

    # Route
    route = await router.route("What's happening with IonQ?")
    assert route.route == "quick_query"

    # Answer
    response = await agent.answer("What's happening with IonQ?", route_hint=route.route)
    assert "IonQ" in response.answer
    assert response.tool_calls_made == 1


@pytest.mark.asyncio
async def test_full_pipeline_stock_query(seeded_storage):
    """Test stock query pipeline."""
    mock_llm = make_mock_llm()

    router_response = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "stock_query",
            "confidence": 0.95,
            "reasoning": "Asking about stock price",
        }))]
    )

    tool_call_response = MockResponse(
        content=[MockToolUseBlock(
            name="stock_data",
            input={"ticker": "IONQ", "days": 30},
            id="tool_s1",
        )],
        stop_reason="tool_use",
    )
    final_response = MockResponse(
        content=[MockTextBlock(
            text="IONQ is currently trading at $12.80, up 2.4% today."
        )]
    )

    mock_llm.messages_create.side_effect = [router_response, tool_call_response, final_response]

    router = RouterAgent(llm_client=mock_llm)
    agent = IntelligenceAgent(llm_client=mock_llm)
    agent._tools["stock_data"]._storage = seeded_storage

    route = await router.route("What's IONQ trading at?")
    assert route.route == "stock_query"

    response = await agent.answer("What's IONQ trading at?", route_hint=route.route)
    assert "12.80" in response.answer
    assert response.tool_calls_made == 1


@pytest.mark.asyncio
async def test_full_pipeline_paper_search(seeded_storage):
    """Test paper search pipeline."""
    mock_llm = make_mock_llm()

    router_response = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "paper_search",
            "confidence": 0.88,
            "reasoning": "Looking for papers",
        }))]
    )

    tool_call_response = MockResponse(
        content=[MockToolUseBlock(
            name="arxiv_search",
            input={"query": "error correction"},
            id="tool_p1",
        )],
        stop_reason="tool_use",
    )
    final_response = MockResponse(
        content=[MockTextBlock(
            text="I found a paper on surface code error correction at scale."
        )]
    )

    mock_llm.messages_create.side_effect = [router_response, tool_call_response, final_response]

    router = RouterAgent(llm_client=mock_llm)
    agent = IntelligenceAgent(llm_client=mock_llm)
    agent._tools["arxiv_search"]._storage = seeded_storage

    route = await router.route("Find papers on error correction")
    assert route.route == "paper_search"

    response = await agent.answer("Find papers on error correction", route_hint=route.route)
    assert "surface code" in response.answer.lower() or "error correction" in response.answer.lower()
    assert response.tool_calls_made == 1
