"""
Agent Memory & Compaction Engine
================================

Handles long-term conversation compaction and short-term working memory (scratchpad)
for the Ket Zero Guide Agent.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from utils.llm_client import ResilientAsyncClient

logger = logging.getLogger(__name__)


class CompactionEngine:
    """
    Summarizes long conversation histories into dense strategic recaps
    to prevent context window exhaustion and reduce token costs.
    """

    def __init__(self, llm_client: ResilientAsyncClient, model: str = "claude-3-5-haiku-20241022"):
        self.llm = llm_client
        self.model = model
        self.system_prompt = (
            "You are an expert summarizer for an AI executive assistant. "
            "Your job is to read the previous conversation summary along with the newest "
            "turns of the conversation, and generate a new, highly condensed 'Strategic Recap'.\n\n"
            "Rules:\n"
            "1. Retain all factual information, user preferences, and strategic context.\n"
            "2. Preserve explicit data points (numbers, tickers, names).\n"
            "3. Omit pleasantries, intro text, and formatting fluff.\n"
            "4. Keep it under 500 words if possible.\n"
            "5. Structure it clearly so the next AI agent can instantly understand the user's intent."
        )

    async def compact(
        self,
        current_summary: Optional[str],
        new_messages: List[Dict[str, str]]
    ) -> str:
        """
        Takes the existing summary and the N newest messages, and generates
        a new compacted summary.
        """
        logger.info(f"[MEMORY] Compacting {len(new_messages)} new messages into summary.")
        
        prompt = "Here is the existing conversation summary:\n"
        prompt += f"<current_summary>\n{current_summary or 'None'}\n</current_summary>\n\n"
        
        prompt += "Here are the newest conversation turns:\n<new_turns>\n"
        for msg in new_messages:
            role = msg.get("role", "unknown")
            # Handle list-based content (e.g., tool results) gracefully by stringifying
            content = msg.get("content", "")
            if isinstance(content, list):
                content = json.dumps(content)
            
            # Truncate extremely long assistant outputs to save cost during compaction
            if role == "assistant" and len(content) > 2000:
                content = content[:2000] + "... [truncated]"
                
            prompt += f"{role.upper()}: {content}\n\n"
        prompt += "</new_turns>\n\nGenerate the new expanded Strategic Recap."

        try:
            response = await self.llm.messages_create(
                model=self.model,
                max_tokens=1000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            
            # Parse response block
            text_blocks = [blk.text for blk in response.content if blk.type == "text"]
            new_summary = "\n".join(text_blocks).strip()
            return new_summary
            
        except Exception as e:
            logger.error(f"[MEMORY] Compaction failed: {e}")
            # Fallback: just return the old summary if compaction fails
            return current_summary or ""

class ScratchpadTool:
    """
    Exposes a tool for the agent to explicitly persist short-term working memory 
    across conversation turns without bloating the standard LLM messages list.
    """

    def __init__(self):
        self._memory = {}

    def get_context(self, session_id: str) -> str:
        """Retrieve the current scratchpad string for a session."""
        return self._memory.get(session_id, "")

    def clear(self, session_id: str) -> None:
        """Clear the scratchpad for a given session."""
        if session_id in self._memory:
            del self._memory[session_id]

    async def execute(self, content: str, session_id: str = "default") -> str:
        """
        Overwrite or append to the scratchpad memory.
        """
        try:
            # For simplicity, we just overwrite the scratchpad with the agent's new generated block
            self._memory[session_id] = content
            logger.info(f"[SCRATCHPAD] Updated for session {session_id} to '{content[:50]}...'")
            return json.dumps({
                "status": "success", 
                "message": "Scratchpad memory updated successfully. It will be injected into your prompt on the next turn."
            })
        except Exception as e:
            logger.error(f"[SCRATCHPAD] Failed to write memory: {e}")
            return json.dumps({"status": "error", "message": f"Failed to write: {e}"})

