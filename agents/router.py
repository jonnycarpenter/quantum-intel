"""
Router Agent
============

Fast intent classification using Claude Haiku.
Routes user queries to the appropriate handler.
Domain-aware: selects prompts and fallback keywords based on domain.
"""

import json
import logging
import os
from typing import Optional

from agents.schemas import RouterResult, VALID_ROUTES
from config.prompts import ROUTER_PROMPTS, ROUTER_SYSTEM_PROMPT
from config.tickers import ALL_TICKERS
from utils.llm_client import ResilientAsyncClient

logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Classifies user intent and routes to the correct agent/handler.

    Uses Haiku for fast, cheap classification.
    Falls back to keyword heuristics if parsing fails.
    Domain-aware: quantum vs AI prompts and keyword sets.
    """

    def __init__(
        self,
        llm_client: ResilientAsyncClient,
        model: Optional[str] = None,
        domain: str = "quantum",
    ):
        self.llm = llm_client
        self.model = model or os.getenv("ROUTER_MODEL", "claude-haiku-4-5-20251001")
        self.domain = domain

    async def route(self, user_message: str, domain: Optional[str] = None) -> RouterResult:
        """
        Classify user intent and return routing decision.

        Args:
            user_message: The user's query
            domain: Override domain for this call (defaults to instance domain)

        Returns:
            RouterResult with route, confidence, reasoning
        """
        active_domain = domain or self.domain
        logger.info(
            f"[ROUTER] Classifying intent for: '{user_message[:80]}...' "
            f"(domain={active_domain})"
        )

        system_prompt = ROUTER_PROMPTS.get(active_domain, ROUTER_SYSTEM_PROMPT)

        try:
            response = await self.llm.messages_create(
                model=self.model,
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.0,
            )

            text = self.llm.extract_text(response)
            result = self._parse_response(text)
            logger.info(
                f"[ROUTER] Route: {result.route} "
                f"(confidence: {result.confidence:.2f}) — {result.reasoning}"
            )
            return result

        except Exception as e:
            logger.warning(f"[ROUTER] LLM routing failed: {e} — using fallback")
            return self._fallback_route(user_message, active_domain)

    def _parse_response(self, text: str) -> RouterResult:
        """Parse LLM JSON response into RouterResult.

        Raises ValueError on parse failure so route() can fall back to keywords.
        """
        # Extract JSON from potential markdown wrapping
        clean = text.strip()
        if "```" in clean:
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]

        data = json.loads(clean)  # Raises JSONDecodeError on bad input
        route = data.get("route", "quick_query").lower()

        if route not in VALID_ROUTES:
            route = "quick_query"

        return RouterResult(
            route=route,
            confidence=float(data.get("confidence", 0.8)),
            reasoning=data.get("reasoning", ""),
            reformulated_query=data.get("reformulated_query"),
        )

    def _fallback_route(self, message: str, domain: str = "quantum") -> RouterResult:
        """Keyword-based fallback routing when LLM fails."""
        msg = message.lower().strip()

        # Check for digest intent
        if any(kw in msg for kw in ["digest", "briefing", "daily", "summary", "latest news"]):
            return RouterResult(
                route="digest",
                confidence=0.7,
                reasoning="Keyword match: digest/briefing intent",
            )

        # Check for stock intent — ticker symbols or financial keywords
        tickers_lower = {t.lower() for t in ALL_TICKERS}
        words = set(msg.split())
        if words & tickers_lower or any(kw in msg for kw in [
            "stock", "price", "trading", "market cap", "shares",
        ]):
            return RouterResult(
                route="stock_query",
                confidence=0.7,
                reasoning="Keyword match: stock/ticker intent",
            )

        # Check for paper intent
        if any(kw in msg for kw in ["paper", "arxiv", "research paper", "publication"]):
            return RouterResult(
                route="paper_search",
                confidence=0.7,
                reasoning="Keyword match: paper/research intent",
            )

        # Check for deep research intent
        if any(kw in msg for kw in ["report", "comprehensive", "deep dive", "compare all"]):
            return RouterResult(
                route="deep_research",
                confidence=0.6,
                reasoning="Keyword match: deep research intent",
            )

        # Domain-specific keyword enrichment for AI
        if domain == "ai" and any(kw in msg for kw in [
            "gpt", "claude", "gemini", "llama", "openai", "anthropic",
            "model release", "frontier model", "llm", "transformer",
            "rlhf", "fine-tuning", "alignment", "ai safety",
        ]):
            return RouterResult(
                route="quick_query",
                confidence=0.7,
                reasoning="Keyword match: AI-specific query",
            )

        # Default
        return RouterResult(
            route="quick_query",
            confidence=0.5,
            reasoning="No strong keyword match — defaulting to quick_query",
        )
