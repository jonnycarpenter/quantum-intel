"""
Content Classifier
==================

Claude-based content classification for quantum computing intelligence.
Uses Haiku for cost efficiency on high-volume classification.
"""

import json
import re
import os
from typing import Optional

from models.article import RawArticle, ClassificationResult, ContentCategory, Priority
from config.prompts import CLASSIFIER_SYSTEM_PROMPT, AI_CLASSIFIER_SYSTEM_PROMPT
from config.settings import IngestionConfig
from config.ai_source_boosts import AI_SOURCE_BOOSTS
from utils.llm_client import get_resilient_async_client
from utils.logger import get_logger

logger = get_logger(__name__)


# Source-based score boosts (higher-quality quantum sources get a boost)
SOURCE_BOOSTS = {
    "the quantum insider": 0.10,
    "quantum computing report": 0.10,
    "nature": 0.15,
    "mit news": 0.10,
    "quanta magazine": 0.10,
    "ibm quantum": 0.05,
    "google": 0.05,
    "ionq": 0.05,
    "d-wave": 0.05,
}


class ContentClassifier:
    """
    LLM-based content classifier for intelligence articles.

    Uses Claude Haiku for cost-efficient classification of articles into
    domain-specific categories with priority, relevance scoring,
    and entity extraction. Supports both quantum and AI domains.
    """

    def __init__(self, config: Optional[IngestionConfig] = None, domain: str = "quantum"):
        self.config = config or IngestionConfig()
        self.domain = domain

        api_key = self.config.anthropic_api_key
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not api_key:
            logger.warning("[CLASSIFIER] No ANTHROPIC_API_KEY set — classification will fail")

        self.client = get_resilient_async_client(anthropic_api_key=api_key)
        self.model = self.config.classifier_model
        self.temperature = self.config.classifier_temperature

    async def classify(self, article: RawArticle) -> Optional[ClassificationResult]:
        """
        Classify a single article.

        Args:
            article: RawArticle to classify

        Returns:
            ClassificationResult or None if classification fails
        """
        # Build content for classification
        content_parts = [f"Title: {article.title}"]
        if article.source_name:
            content_parts.append(f"Source: {article.source_name}")
        if article.summary:
            content_parts.append(f"Content: {article.summary[:3000]}")
        elif article.full_text:
            content_parts.append(f"Content: {article.full_text[:3000]}")

        user_message = "\n".join(content_parts)

        # Select prompt based on domain
        system_prompt = (
            AI_CLASSIFIER_SYSTEM_PROMPT
            if self.domain == "ai"
            else CLASSIFIER_SYSTEM_PROMPT
        )

        try:
            response = await self.client.messages_create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=self.temperature,
            )

            text = self.client.extract_text(response)
            parsed = self._parse_json_response(text)

            if parsed is None:
                logger.warning(f"[CLASSIFIER] Failed to parse response for: {article.title[:50]}")
                return None

            result = ClassificationResult.from_llm_response(article.url, parsed)
            result.classifier_model = self.model

            # Apply source boost
            result = self._apply_source_boost(result, article.source_name)

            return result

        except Exception as e:
            logger.warning(f"[CLASSIFIER] Error classifying '{article.title[:50]}': {e}")
            return None

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in text
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _apply_source_boost(
        self, result: ClassificationResult, source_name: str
    ) -> ClassificationResult:
        """Apply source-based relevance score boost."""
        if not source_name:
            return result

        boost_map = AI_SOURCE_BOOSTS if self.domain == "ai" else SOURCE_BOOSTS
        source_lower = source_name.lower()
        for source_pattern, boost in boost_map.items():
            if source_pattern in source_lower:
                original = result.relevance_score
                result.relevance_score = min(1.0, result.relevance_score + boost)
                logger.debug(
                    f"[CLASSIFIER] Source boost: {source_name} +{boost} "
                    f"({original:.2f} -> {result.relevance_score:.2f})"
                )
                break

        return result
