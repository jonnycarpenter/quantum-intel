"""
Test Agents
===========

Tests for RouterAgent and IntelligenceAgent.
Uses mocked LLM client to avoid real API calls.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Any

from agents.router import RouterAgent
from agents.intelligence import IntelligenceAgent
from agents.schemas import VALID_ROUTES


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
    id: str = "tool_123"

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
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.messages_create = AsyncMock()
    mock.extract_text = lambda response: "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return mock


# ============================================================================
# ROUTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_router_digest_intent():
    """Test router classifies digest intent correctly."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "digest",
            "confidence": 0.95,
            "reasoning": "User wants the daily briefing",
        }))]
    )

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("Show me today's digest")

    assert result.route == "digest"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_router_stock_intent():
    """Test router classifies stock query correctly."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "stock_query",
            "confidence": 0.9,
            "reasoning": "User asking about stock price",
        }))]
    )

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("What's IONQ trading at?")

    assert result.route == "stock_query"


@pytest.mark.asyncio
async def test_router_paper_intent():
    """Test router classifies paper search correctly."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "paper_search",
            "confidence": 0.88,
            "reasoning": "User looking for research papers",
        }))]
    )

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("Find papers on quantum error correction")

    assert result.route == "paper_search"


@pytest.mark.asyncio
async def test_router_fallback_on_parse_error():
    """Test router falls back to keyword heuristics on bad JSON."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text="this is not valid json at all")]
    )

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("What's happening with IONQ stock?")

    # Should fallback to keyword matching and find stock_query
    assert result.route == "stock_query"
    assert result.confidence <= 0.7


@pytest.mark.asyncio
async def test_router_fallback_on_llm_failure():
    """Test router falls back when LLM call fails entirely."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.side_effect = Exception("API error")

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("Tell me about recent papers on arxiv")

    assert result.route == "paper_search"
    assert result.confidence == 0.7


@pytest.mark.asyncio
async def test_router_default_route():
    """Test router defaults to quick_query for ambiguous input."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.side_effect = Exception("API error")

    router = RouterAgent(llm_client=mock_llm)
    result = await router.route("Hello, how are you?")

    assert result.route == "quick_query"


# ============================================================================
# ROUTER DOMAIN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_router_ai_domain_uses_ai_prompt():
    """Test router uses AI system prompt when domain=ai."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "quick_query",
            "confidence": 0.9,
            "reasoning": "AI news query",
        }))]
    )

    router = RouterAgent(llm_client=mock_llm, domain="ai")
    result = await router.route("What's new with GPT-5?")

    # Verify the AI prompt was used (check the system param in the call)
    call_kwargs = mock_llm.messages_create.call_args
    system_text = call_kwargs.kwargs.get("system", "") or call_kwargs[1].get("system", "")
    assert "AI intelligence system" in system_text
    assert result.route == "quick_query"


@pytest.mark.asyncio
async def test_router_domain_override_per_call():
    """Test route() domain param overrides instance domain."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text=json.dumps({
            "route": "quick_query",
            "confidence": 0.85,
            "reasoning": "Query about AI models",
        }))]
    )

    # Instance is quantum, but call overrides to AI
    router = RouterAgent(llm_client=mock_llm, domain="quantum")
    result = await router.route("What's new with OpenAI?", domain="ai")

    call_kwargs = mock_llm.messages_create.call_args
    system_text = call_kwargs.kwargs.get("system", "") or call_kwargs[1].get("system", "")
    assert "AI intelligence system" in system_text


@pytest.mark.asyncio
async def test_router_ai_fallback_keywords():
    """Test AI-specific keyword fallback recognizes AI terms."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.side_effect = Exception("API error")

    router = RouterAgent(llm_client=mock_llm, domain="ai")
    result = await router.route("Tell me about the latest GPT model")

    assert result.route == "quick_query"
    assert result.confidence == 0.7
    assert "AI-specific" in result.reasoning


# ============================================================================
# INTELLIGENCE AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_agent_simple_text_response():
    """Test agent returns text directly when no tools are needed."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text="Quantum computing is advancing rapidly.")]
    )

    agent = IntelligenceAgent(llm_client=mock_llm)
    response = await agent.answer("What is quantum computing?")

    assert "advancing rapidly" in response.answer
    assert response.tool_calls_made == 0


@pytest.mark.asyncio
async def test_agent_tool_calling_loop():
    """Test agent executes tool call and returns final answer."""
    mock_llm = make_mock_llm()

    # First call: model requests a tool
    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="corpus_search",
            input={"query": "IonQ news"},
            id="tool_001",
        )],
        stop_reason="tool_use",
    )

    # Second call: model returns final text
    text_response = MockResponse(
        content=[MockTextBlock(text="Based on my search, IonQ has made progress.")]
    )

    mock_llm.messages_create.side_effect = [tool_response, text_response]

    agent = IntelligenceAgent(llm_client=mock_llm)
    # Mock the tool execution
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=json.dumps({
        "results": [{"title": "IonQ Update", "url": "https://example.com/ionq"}],
        "total_found": 1,
        "query": "IonQ news",
    }))
    agent._tools["corpus_search"] = mock_tool

    response = await agent.answer("What's happening with IonQ?")

    assert response.tool_calls_made == 1
    assert "IonQ" in response.answer
    # Domain should be injected into corpus_search calls
    mock_tool.execute.assert_called_once_with(query="IonQ news", domain="quantum")


@pytest.mark.asyncio
async def test_agent_max_tool_calls_guard():
    """Test agent stops after max tool calls."""
    mock_llm = make_mock_llm()

    # Always return tool_use (infinite loop scenario)
    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="corpus_search",
            input={"query": "test"},
            id="tool_loop",
        )],
        stop_reason="tool_use",
    )
    mock_llm.messages_create.return_value = tool_response

    agent = IntelligenceAgent(llm_client=mock_llm, max_tool_calls=3)

    # Mock corpus_search tool
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=json.dumps({
        "results": [], "total_found": 0, "query": "test",
    }))
    agent._tools["corpus_search"] = mock_tool

    response = await agent.answer("Keep searching forever")

    assert response.tool_calls_made == 3
    assert mock_tool.execute.call_count == 3


@pytest.mark.asyncio
async def test_agent_handles_tool_error():
    """Test agent handles tool execution errors gracefully."""
    mock_llm = make_mock_llm()

    # First call: request tool
    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="web_search",
            input={"query": "test"},
            id="tool_err",
        )],
        stop_reason="tool_use",
    )

    # Second call: return text after error
    text_response = MockResponse(
        content=[MockTextBlock(text="I couldn't find results via web search.")]
    )

    mock_llm.messages_create.side_effect = [tool_response, text_response]

    agent = IntelligenceAgent(llm_client=mock_llm)

    # Mock tool that raises
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(side_effect=Exception("Connection error"))
    agent._tools["web_search"] = mock_tool

    response = await agent.answer("Search the web")

    assert response.tool_calls_made == 1
    # Agent should still produce a response
    assert response.answer != ""


@pytest.mark.asyncio
async def test_agent_extracts_sources():
    """Test agent extracts source URLs from tool results."""
    mock_llm = make_mock_llm()

    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="corpus_search",
            input={"query": "quantum"},
            id="tool_src",
        )],
        stop_reason="tool_use",
    )
    text_response = MockResponse(
        content=[MockTextBlock(text="Here are the results.")]
    )
    mock_llm.messages_create.side_effect = [tool_response, text_response]

    agent = IntelligenceAgent(llm_client=mock_llm)

    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=json.dumps({
        "results": [
            {"title": "Article 1", "url": "https://example.com/1"},
            {"title": "Article 2", "url": "https://example.com/2"},
        ],
        "total_found": 2,
        "query": "quantum",
    }))
    agent._tools["corpus_search"] = mock_tool

    response = await agent.answer("What's new in quantum?")

    assert len(response.sources) == 2
    assert response.sources[0]["url"] == "https://example.com/1"
    assert response.sources[1]["url"] == "https://example.com/2"


# ============================================================================
# INTELLIGENCE AGENT DOMAIN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_agent_ai_domain_uses_ai_prompt():
    """Test agent uses AI system prompt when domain=ai."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text="OpenAI released GPT-5 yesterday.")]
    )

    agent = IntelligenceAgent(llm_client=mock_llm, domain="ai")
    response = await agent.answer("What's new with OpenAI?")

    call_kwargs = mock_llm.messages_create.call_args
    system_text = call_kwargs.kwargs.get("system", "") or call_kwargs[1].get("system", "")
    assert "AI industry intelligence analyst" in system_text
    assert "Substance Over Hype" in system_text


@pytest.mark.asyncio
async def test_agent_domain_override_per_call():
    """Test answer() domain param overrides instance domain."""
    mock_llm = make_mock_llm()
    mock_llm.messages_create.return_value = MockResponse(
        content=[MockTextBlock(text="AI safety is important.")]
    )

    # Instance is quantum, but call overrides to AI
    agent = IntelligenceAgent(llm_client=mock_llm, domain="quantum")
    response = await agent.answer("Tell me about AI safety", domain="ai")

    call_kwargs = mock_llm.messages_create.call_args
    system_text = call_kwargs.kwargs.get("system", "") or call_kwargs[1].get("system", "")
    assert "AI industry intelligence analyst" in system_text


@pytest.mark.asyncio
async def test_agent_injects_domain_into_corpus_search():
    """Test agent injects domain into corpus_search tool calls."""
    mock_llm = make_mock_llm()

    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="corpus_search",
            input={"query": "AI model releases"},
            id="tool_domain",
        )],
        stop_reason="tool_use",
    )
    text_response = MockResponse(
        content=[MockTextBlock(text="Found AI results.")]
    )
    mock_llm.messages_create.side_effect = [tool_response, text_response]

    agent = IntelligenceAgent(llm_client=mock_llm, domain="ai")

    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=json.dumps({
        "results": [], "total_found": 0, "query": "AI model releases",
    }))
    agent._tools["corpus_search"] = mock_tool

    await agent.answer("What AI models were released recently?")

    # Verify domain was injected
    mock_tool.execute.assert_called_once_with(query="AI model releases", domain="ai")


@pytest.mark.asyncio
async def test_agent_does_not_inject_domain_into_other_tools():
    """Test agent does NOT inject domain into non-corpus tools."""
    mock_llm = make_mock_llm()

    tool_response = MockResponse(
        content=[MockToolUseBlock(
            name="web_search",
            input={"query": "OpenAI news"},
            id="tool_web",
        )],
        stop_reason="tool_use",
    )
    text_response = MockResponse(
        content=[MockTextBlock(text="Found web results.")]
    )
    mock_llm.messages_create.side_effect = [tool_response, text_response]

    agent = IntelligenceAgent(llm_client=mock_llm, domain="ai")

    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=json.dumps({
        "results": [], "total_found": 0, "query": "OpenAI news",
    }))
    agent._tools["web_search"] = mock_tool

    await agent.answer("Search the web for OpenAI news")

    # web_search should NOT receive domain
    mock_tool.execute.assert_called_once_with(query="OpenAI news")
