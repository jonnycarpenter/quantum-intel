"""
LLM Client
==========

Resilient async client wrapper for Anthropic Claude API.
Includes retry logic, rate limit handling, and cost tracking.
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional, Dict, Any, List

import httpx

try:
    import anthropic
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    AsyncAnthropic = None

logger = logging.getLogger(__name__)


# Cost per million tokens (Anthropic pricing)
MODEL_COSTS = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
}

DEFAULT_COST = {"input": 3.0, "output": 15.0}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost for an API call."""
    costs = DEFAULT_COST
    model_lower = model.lower()

    for model_key, model_costs in MODEL_COSTS.items():
        if model_key in model_lower:
            costs = model_costs
            break

    if "haiku" in model_lower:
        costs = {"input": 0.25, "output": 1.25}
    elif "sonnet" in model_lower:
        costs = {"input": 3.0, "output": 15.0}

    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return input_cost + output_cost


def _parse_sse_response(sse_text: str) -> Any:
    """
    Parse a raw SSE (Server-Sent Events) stream string into a message-like object.

    Claude Code's localhost proxy returns SSE text even for non-streaming calls.
    This parser reconstructs a response object compatible with the SDK's Message type.
    """
    text_parts: List[str] = []
    input_tokens = 0
    output_tokens = 0
    message_id = ""
    model_name = ""
    stop_reason = "end_turn"

    current_event = None
    for line in sse_text.split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if current_event == "message_start":
                msg = data.get("message", {})
                message_id = msg.get("id", "")
                model_name = msg.get("model", "")
                usage = msg.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)

            elif current_event == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    text_parts.append(delta.get("text", ""))

            elif current_event == "message_delta":
                stop_reason = data.get("delta", {}).get("stop_reason", "end_turn")
                delta_usage = data.get("usage", {})
                output_tokens = delta_usage.get("output_tokens", 0)

    full_text = "".join(text_parts)

    # Build lightweight objects that mimic the SDK's Message/Usage/ContentBlock types
    class _Usage:
        def __init__(self, inp: int, out: int):
            self.input_tokens = inp
            self.output_tokens = out

    class _ContentBlock:
        def __init__(self, text: str):
            self.type = "text"
            self.text = text

    class _Message:
        def __init__(self):
            self.id = message_id
            self.model = model_name
            self.stop_reason = stop_reason
            self.content = [_ContentBlock(full_text)]
            self.usage = _Usage(input_tokens, output_tokens)

    return _Message()


def _parse_json_response(data: dict) -> Any:
    """
    Parse a standard JSON response from the real Anthropic API
    into the same lightweight message-like object used by _parse_sse_response.
    """
    class _Usage:
        def __init__(self, inp: int, out: int):
            self.input_tokens = inp
            self.output_tokens = out

    class _ContentBlock:
        def __init__(self, text: str):
            self.type = "text"
            self.text = text

    class _Message:
        pass

    msg = _Message()
    msg.id = data.get("id", "")
    msg.model = data.get("model", "")
    msg.stop_reason = data.get("stop_reason", "end_turn")

    usage = data.get("usage", {})
    msg.usage = _Usage(usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    content_blocks = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            content_blocks.append(_ContentBlock(block.get("text", "")))
    msg.content = content_blocks

    return msg

class ResilientAsyncClient:
    """
    Async client wrapper with retry logic for Claude API calls.

    Features:
    - Automatic retries with exponential backoff
    - Rate limit handling
    - Timeout management
    - Structured logging
    """

    def __init__(
        self,
        anthropic_api_key: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        self._api_key = anthropic_api_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout

        # Resolve base URL — respects ANTHROPIC_BASE_URL for Claude Code proxy.
        # Force HTTP/1.1 (http2=False) because the Claude Code localhost proxy
        # returns empty responses over HTTP/2 async connections.
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self._messages_url = base_url.rstrip("/") + "/v1/messages"
        # The Claude Code localhost proxy rejects 'temperature' — omit it for proxy calls
        self._is_local_proxy = "localhost" in base_url or "127.0.0.1" in base_url
        self._headers = {
            "x-api-key": anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def messages_create(
        self,
        model: str,
        max_tokens: int,
        messages: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> Any:
        """
        Create a message with retry logic.

        Uses httpx directly to avoid Anthropic SDK issues with the Claude Code
        localhost proxy (which returns raw SSE even for non-streaming calls).

        Args:
            model: Model identifier
            max_tokens: Maximum tokens in response
            messages: List of message dicts
            system: System prompt
            temperature: Sampling temperature
            **kwargs: Additional parameters passed to the API

        Returns:
            API response object

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
        }
        # Claude Code's localhost proxy silently returns empty response when
        # 'temperature' is included, so omit it for proxy calls.
        if not self._is_local_proxy:
            payload["temperature"] = temperature
        if messages:
            payload["messages"] = messages
        if system:
            payload["system"] = system
        # Merge any extra kwargs (excluding SDK-specific ones)
        for k, v in kwargs.items():
            if k not in ("stream",):
                payload[k] = v

        for attempt in range(self.max_retries):
            attempt_start = time.time()

            try:
                async with httpx.AsyncClient(timeout=self.timeout, http2=False) as client:
                    resp = await client.post(
                        self._messages_url,
                        headers=self._headers,
                        json=payload,
                    )

                if resp.status_code == 429:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(
                        f"[LLM] Rate limited (attempt {attempt + 1}/{self.max_retries}) | backoff: {delay:.1f}s"
                    )
                    last_error = Exception("Rate limited")
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code >= 500:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(
                        f"[LLM] Server error {resp.status_code} (attempt {attempt + 1}/{self.max_retries})"
                    )
                    last_error = Exception(f"Server error {resp.status_code}")
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code >= 400:
                    msg = resp.text[:200]
                    logger.error(f"[LLM] Client error {resp.status_code}: {msg}")
                    raise Exception(f"API client error {resp.status_code}: {msg}")

                raw = resp.text

                # Claude Code's localhost proxy returns raw SSE stream text
                # even for non-streaming calls. Parse it into a Message-like object.
                if raw.startswith("event:"):
                    response = _parse_sse_response(raw)
                else:
                    # Standard JSON response from real Anthropic API
                    response = _parse_json_response(resp.json())

                elapsed_ms = int((time.time() - attempt_start) * 1000)
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)
                cost = calculate_cost(model, input_tokens, output_tokens)

                logger.info(
                    f"[LLM] {model} | "
                    f"tokens: {input_tokens}->{output_tokens} | "
                    f"latency: {elapsed_ms}ms | "
                    f"cost: ${cost:.4f}"
                )

                return response

            except httpx.TimeoutException:
                last_error = TimeoutError(f"Request timed out after {self.timeout}s")
                logger.warning(
                    f"[LLM] Timeout (attempt {attempt + 1}/{self.max_retries}) | model: {model}"
                )

            except Exception as e:
                if "API client error" in str(e):
                    raise
                last_error = e
                logger.error(f"[LLM] Unexpected error: {type(e).__name__}: {e}")
                raise

        logger.error(f"[LLM] All {self.max_retries} retries failed | model: {model}")
        raise last_error or Exception("All retries failed")

    async def messages_stream(
        self,
        model: str,
        max_tokens: int,
        messages: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> Any:
        """
        Create a streaming message response.
        Uses httpx directly to stream SSE events.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if not self._is_local_proxy:
            payload["temperature"] = temperature
        if messages:
            payload["messages"] = messages
        if system:
            payload["system"] = system
        
        for k, v in kwargs.items():
            if k not in ("stream",):
                payload[k] = v

        client = httpx.AsyncClient(timeout=self.timeout, http2=False)
        try:
            async with client.stream(
                "POST", 
                self._messages_url, 
                headers=self._headers, 
                json=payload
            ) as response:
                if response.status_code >= 400:
                    text = await response.aread()
                    logger.error(f"[LLM] Stream error {response.status_code}: {text}")
                    raise Exception(f"API stream error {response.status_code}: {text}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            yield json.loads(data_str)
                        except json.JSONDecodeError:
                            pass
        finally:
            await client.aclose()


    def extract_text(self, response: Any) -> str:
        """Extract text content from API response."""
        if hasattr(response, "content") and response.content:
            if isinstance(response.content, list):
                text_blocks = [
                    block.text for block in response.content if hasattr(block, "text")
                ]
                return "\n".join(text_blocks)
            return str(response.content)
        return ""


def get_resilient_async_client(
    anthropic_api_key: str,
    **kwargs,
) -> ResilientAsyncClient:
    """Factory function to create a resilient async client."""
    return ResilientAsyncClient(
        anthropic_api_key=anthropic_api_key,
        **kwargs,
    )
