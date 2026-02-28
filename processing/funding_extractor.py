"""
Funding Extractor
=================

Extracts structured Venture Capital funding events from raw article text.
"""

import json
import time
from typing import List, Optional
from anthropic import AsyncAnthropic

from models.funding import FundingEvent, FundingExtractionResult
from config.prompts import FUNDING_EXTRACTOR_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)


class FundingExtractor:
    """Uses Claude to parse articles for exact VC funding data."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        # Estimated cost per 1k tokens for sonnet
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015

    def _calculate_cost(self, usage) -> float:
        """Estimate the API cost for the request."""
        if not usage:
            return 0.0
        in_tokens = getattr(usage, "input_tokens", 0)
        out_tokens = getattr(usage, "output_tokens", 0)
        return (in_tokens / 1000 * self.cost_per_1k_input) + (out_tokens / 1000 * self.cost_per_1k_output)

    async def extract_funding_events(
        self, article_id: str, article_url: str, full_text: str, domain: str = "quantum"
    ) -> FundingExtractionResult:
        """
        Analyze a text and extract any VC funding events.
        """
        start_time = time.time()
        result = FundingExtractionResult(
            article_id=article_id,
            source_length=len(full_text) if full_text else 0
        )

        if not full_text or len(full_text.split()) < 50:
            result.success = False
            result.error_message = "Text too short for reliable extraction"
            return result

        try:
            # Build the prompt
            prompt = (
                f"DOMAIN: {domain.upper()}\n\n"
                f"ARTICLE CONTENT:\n{full_text}\n"
            )

            # Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.0,
                system=FUNDING_EXTRACTOR_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Calculate cost and time
            result.extraction_time_seconds = time.time() - start_time
            result.extraction_cost_usd = self._calculate_cost(response.usage)
            result.extraction_model = self.model

            raw_text = response.content[0].text.strip()
            
            # Defensive check for markdown json blocks (even though we asked not to)
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            raw_text = raw_text.strip()

            if not raw_text or raw_text == "[]":
                # No events found
                return result

            # Parse JSON
            parsed_data = json.loads(raw_text)
            if not isinstance(parsed_data, list):
                parsed_data = [parsed_data]

            # Convert to DataClasses
            events = []
            for item in parsed_data:
                # Basic validation
                if not item.get("startup_name") or not item.get("funding_amount"):
                    continue
                    
                event = FundingEvent(
                    article_id=article_id,
                    article_url=article_url,
                    domain=domain,
                    startup_name=item.get("startup_name", ""),
                    funding_round=item.get("funding_round", ""),
                    funding_amount=item.get("funding_amount", ""),
                    valuation=item.get("valuation", ""),
                    lead_investors=item.get("lead_investors", []),
                    other_investors=item.get("other_investors", []),
                    investment_thesis=item.get("investment_thesis", ""),
                    known_technologies=item.get("known_technologies", []),
                    use_of_funds=item.get("use_of_funds", ""),
                    grounding_quote=item.get("grounding_quote", ""),
                    confidence_score=float(item.get("confidence_score", 0.8))
                )
                events.append(event)
            
            result.funding_events = events
            logger.info(f"[EXTRACTOR] Found {len(events)} funding events for article {article_id}")

        except json.JSONDecodeError as e:
            result.success = False
            result.error_message = f"JSON parsing failed: {e}\nRaw text: {raw_text[:100]}..."
            logger.error(f"[EXTRACTOR] JSON Error on {article_id}: {e}")
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"[EXTRACTOR] Error on {article_id}: {e}")

        return result
