"""
Intelligence Agent
==================

Tool-calling agent powered by Claude Sonnet.
Uses Anthropic's native tool_use API to answer questions
about the quantum computing and AI ecosystems.
Domain-aware: selects system prompt based on active domain.
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any

from agents.schemas import AgentResponse, ALL_INTELLIGENCE_TOOLS
from config.prompts import INTELLIGENCE_PROMPTS, INTELLIGENCE_AGENT_SYSTEM_PROMPT
from tools.corpus_search import CorpusSearchTool
from tools.web_search import WebSearchTool
from tools.stock_data import StockDataTool
from tools.arxiv_search import ArXivSearchTool
from tools.podcast_search import PodcastSearchTool
from utils.llm_client import ResilientAsyncClient

logger = logging.getLogger(__name__)

# Route hints for the system prompt
ROUTE_HINTS = {
    "stock_query": "The user is asking about stocks or market data. Prioritize the stock_data tool.",
    "paper_search": "The user is asking about research papers. Prioritize the arxiv_search tool.",
    "digest": "The user wants a digest or summary of recent news. Use corpus_search to find recent high-priority articles.",
    "quick_query": "",
    "deep_research": "The user wants deep analysis. Use multiple tools to gather comprehensive information.",
}


class IntelligenceAgent:
    """
    Tool-calling agent for answering intelligence questions.

    Runs an iterative tool-calling loop:
    1. Send messages with tool definitions
    2. If response has tool_use blocks, execute tools and append results
    3. Repeat until text response or max iterations

    Domain-aware: uses quantum or AI system prompt based on domain.
    """

    def __init__(
        self,
        llm_client: ResilientAsyncClient,
        model: Optional[str] = None,
        max_tool_calls: int = 5,
        domain: str = "quantum",
    ):
        self.llm = llm_client
        self.model = model or os.getenv(
            "INTELLIGENCE_MODEL", "claude-sonnet-4-5-20250929"
        )
        self.max_tool_calls = max_tool_calls
        self.temperature = float(os.getenv("INTELLIGENCE_AGENT_TEMP", "0.3"))
        self.domain = domain

        # Initialize tools
        self._tools: Dict[str, Any] = {
            "corpus_search": CorpusSearchTool(),
            "web_search": WebSearchTool(),
            "stock_data": StockDataTool(),
            "arxiv_search": ArXivSearchTool(),
            "podcast_search": PodcastSearchTool(),
        }

    async def answer(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        route_hint: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> AgentResponse:
        """
        Answer a user question using tool-calling.

        Args:
            user_message: The user's question
            conversation_history: Optional prior messages for multi-turn
            route_hint: Optional route from the router for tool prioritization
            domain: Override domain for this call (defaults to instance domain)

        Returns:
            AgentResponse with answer, sources, and metadata
        """
        active_domain = domain or self.domain
        logger.info(
            f"[AGENT] Processing query: '{user_message[:80]}...' "
            f"(domain={active_domain})"
        )

        # Build system prompt with domain awareness and optional route hint
        system = INTELLIGENCE_PROMPTS.get(active_domain, INTELLIGENCE_AGENT_SYSTEM_PROMPT)
        hint = ROUTE_HINTS.get(route_hint, "")
        if hint:
            system += f"\n\nROUTE HINT: {hint}"

        # Build messages
        messages: List[Dict[str, Any]] = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        tool_calls_made = 0
        sources: List[Dict[str, Any]] = []

        # Tool-calling loop
        while tool_calls_made < self.max_tool_calls:
            try:
                response = await self.llm.messages_create(
                    model=self.model,
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                    tools=ALL_INTELLIGENCE_TOOLS,
                    temperature=self.temperature,
                )
            except Exception as e:
                logger.error(f"[AGENT] LLM call failed: {e}")
                return AgentResponse(
                    answer=f"I encountered an error while processing your query: {e}",
                    sources=sources,
                    tool_calls_made=tool_calls_made,
                    model=self.model,
                )

            # Check stop reason
            stop_reason = getattr(response, "stop_reason", "end_turn")

            # Process content blocks
            has_tool_use = False
            text_parts: List[str] = []
            tool_results: List[Dict[str, Any]] = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    has_tool_use = True
                    tool_calls_made += 1

                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    logger.info(
                        f"[AGENT] Tool call #{tool_calls_made}: "
                        f"{tool_name}({json.dumps(tool_input, default=str)[:100]})"
                    )

                    # Inject domain into corpus_search calls
                    if tool_name == "corpus_search":
                        tool_input["domain"] = active_domain

                    # Execute tool
                    result = await self._execute_tool(tool_name, tool_input)

                    # Track sources from tool results
                    self._extract_sources(tool_name, result, sources)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    })

            if has_tool_use:
                # Append assistant response and tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # No tool calls — we have our final answer
                answer_text = "\n".join(text_parts) if text_parts else ""
                logger.info(
                    f"[AGENT] Complete — {tool_calls_made} tool calls, "
                    f"{len(sources)} sources"
                )
                return AgentResponse(
                    answer=answer_text,
                    sources=sources,
                    tool_calls_made=tool_calls_made,
                    model=self.model,
                )

        # Max tool calls reached — return whatever text we have
        logger.warning(
            f"[AGENT] Max tool calls ({self.max_tool_calls}) reached"
        )
        final_text = "\n".join(text_parts) if text_parts else (
            "I've gathered information using multiple tools but reached the "
            "maximum number of tool calls. Here's what I found so far."
        )
        return AgentResponse(
            answer=final_text,
            sources=sources,
            tool_calls_made=tool_calls_made,
            model=self.model,
        )

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return its result string."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            result = await tool.execute(**tool_input)
            return result
        except Exception as e:
            logger.error(f"[AGENT] Tool '{tool_name}' error: {e}")
            return json.dumps({
                "error": f"Tool execution failed: {type(e).__name__}: {e}",
            })

    def _extract_sources(
        self,
        tool_name: str,
        result_json: str,
        sources: List[Dict[str, Any]],
    ) -> None:
        """Extract source URLs from tool results for citation."""
        try:
            data = json.loads(result_json)
            results = data.get("results", [])
            for item in results:
                url = item.get("url") or item.get("abs_url")
                if url:
                    source = {
                        "url": url,
                        "title": item.get("title", ""),
                        "tool": tool_name,
                    }
                    # Avoid duplicate URLs
                    if not any(s["url"] == url for s in sources):
                        sources.append(source)
        except (json.JSONDecodeError, AttributeError):
            pass
