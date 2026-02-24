"""
Earnings Quote Extractor
========================

LLM-based extraction of verbatim quotes from earnings call transcripts.
Uses Claude Sonnet for high-quality, structured quote extraction with
speaker attribution, classification, and entity extraction.
"""

import json
import os
import re
from typing import Optional, List
from datetime import datetime, timezone

from models.earnings import (
    EarningsTranscript,
    ExtractedQuote,
    QuoteExtractionResult,
    SpeakerRole,
    QuoteType,
    ConfidenceLevel,
    CallSection,
)
from config.settings import EarningsConfig
from config.earnings_tickers import CORE_TICKERS as QUANTUM_CORE_TICKERS
from config.ai_earnings_tickers import AI_CORE_TICKERS
from utils.llm_client import get_resilient_async_client
from utils.logger import get_logger

logger = get_logger(__name__)


QUOTE_EXTRACTION_PROMPT = """You are an expert financial analyst specializing in quantum computing.

Extract verbatim quotes from this earnings call transcript. Focus on quotes that reveal:
- Strategic direction and technology roadmap
- Competitive positioning and advantages/threats
- Revenue guidance and financial metrics
- Technology milestones and timelines
- Risk factors and challenges
- Partnership announcements
- Analyst pressure points (tough questions)

EXTRACTION RULES:
1. Quotes MUST be verbatim — exact words from the transcript
2. Include the speaker name and their role (CEO, CFO, analyst, etc.)
3. Provide brief context before/after the quote
4. Rate relevance 0.0–1.0 (1.0 = extremely relevant to quantum computing)
5. For {tier} tickers, {tier_guidance}

TICKER: {ticker}
COMPANY: {company_name}
PERIOD: Q{quarter} {year}

Respond with ONLY a JSON array of quote objects:
```json
[
  {{
    "quote_text": "exact verbatim quote",
    "context_before": "brief context before the quote",
    "context_after": "brief context after",
    "speaker_name": "John Smith",
    "speaker_role": "ceo|cfo|coo|cto|vp|analyst|moderator|other",
    "speaker_title": "CEO",
    "speaker_company": "IonQ",
    "speaker_firm": "Goldman Sachs",
    "quote_type": "strategy|guidance|competitive|technology_milestone|timeline_outlook|risk_factor|analyst_pressure|partnership|revenue_metric",
    "themes": ["quantum_hardware", "revenue_growth"],
    "sentiment": "bullish|bearish|neutral|cautious|confident",
    "confidence_level": "definitive|high_confidence|cautious|speculative|hedged",
    "companies_mentioned": ["IBM", "Google"],
    "technologies_mentioned": ["trapped ion", "error correction"],
    "competitors_mentioned": ["IBM"],
    "metrics_mentioned": ["$100M ARR"],
    "relevance_score": 0.9,
    "is_quotable": true,
    "quotability_reason": "CEO directly addresses quantum revenue milestones",
    "section": "prepared_remarks|qa_session|opening|closing|unknown",
    "position_in_section": 0
  }}
]
```

Extract the most significant 10-25 quotes. Focus on quality over quantity."""


AI_QUOTE_EXTRACTION_PROMPT = """You are an expert financial analyst specializing in artificial intelligence and machine learning.

Extract verbatim quotes from this earnings call transcript. Focus on quotes that reveal:
- AI revenue and monetization metrics (AI ARR, AI bookings, inference volume)
- AI capital expenditure and infrastructure investments (GPU spend, data center build-out)
- AI product launches and competitive positioning (model launches, platform updates)
- AI strategy and technology roadmap (foundation models, agentic AI, enterprise AI)
- AI safety and regulatory considerations
- Competitive dynamics in AI (vs OpenAI, Google, Meta, AWS, etc.)
- AI customer wins and deployment scale
- AI talent and R&D investment priorities
- Analyst pressure points on AI spend ROI

EXTRACTION RULES:
1. Quotes MUST be verbatim — exact words from the transcript
2. Include the speaker name and their role (CEO, CFO, analyst, etc.)
3. Provide brief context before/after the quote
4. Rate relevance 0.0–1.0 (1.0 = extremely relevant to AI business strategy)
5. For {tier} tickers, {tier_guidance}

TICKER: {ticker}
COMPANY: {company_name}
PERIOD: Q{quarter} {year}

Respond with ONLY a JSON array of quote objects:
```json
[
  {{
    "quote_text": "exact verbatim quote",
    "context_before": "brief context before the quote",
    "context_after": "brief context after",
    "speaker_name": "John Smith",
    "speaker_role": "ceo|cfo|coo|cto|vp|analyst|moderator|other",
    "speaker_title": "CEO",
    "speaker_company": "Palantir",
    "speaker_firm": "Goldman Sachs",
    "quote_type": "strategy|guidance|competitive|technology_milestone|timeline_outlook|risk_factor|analyst_pressure|partnership|revenue_metric",
    "themes": ["ai_revenue", "gpu_infrastructure"],
    "sentiment": "bullish|bearish|neutral|cautious|confident",
    "confidence_level": "definitive|high_confidence|cautious|speculative|hedged",
    "companies_mentioned": ["OpenAI", "Google"],
    "technologies_mentioned": ["LLM", "inference optimization"],
    "competitors_mentioned": ["AWS"],
    "metrics_mentioned": ["$1B AI revenue"],
    "relevance_score": 0.9,
    "is_quotable": true,
    "quotability_reason": "CEO reveals AI revenue surpassed $1B annualized run rate",
    "section": "prepared_remarks|qa_session|opening|closing|unknown",
    "position_in_section": 0
  }}
]
```

Extract the most significant 10-25 quotes. Focus on quality over quantity."""


# Map domain to prompt template
DOMAIN_QUOTE_PROMPTS = {
    "quantum": QUOTE_EXTRACTION_PROMPT,
    "ai": AI_QUOTE_EXTRACTION_PROMPT,
}

# Map domain to core tickers list
DOMAIN_CORE_TICKERS = {
    "quantum": QUANTUM_CORE_TICKERS,
    "ai": AI_CORE_TICKERS,
}


class QuoteExtractor:
    """
    LLM-based extractor for earnings call quotes.

    Uses Claude Sonnet to extract verbatim quotes with speaker attribution,
    classification, and entity extraction.
    """

    def __init__(self, config: Optional[EarningsConfig] = None):
        self.config = config or EarningsConfig()

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("[QUOTE_EXTRACTOR] No ANTHROPIC_API_KEY set")

        self.client = get_resilient_async_client(
            anthropic_api_key=api_key, timeout=180.0
        )
        self.model = self.config.extraction_model
        self.temperature = self.config.extraction_temperature
        self.max_tokens = self.config.extraction_max_tokens

    async def extract_quotes(
        self, transcript: EarningsTranscript, domain: str = "quantum"
    ) -> QuoteExtractionResult:
        """
        Extract quotes from an earnings transcript.

        Args:
            transcript: EarningsTranscript with transcript_text
            domain: "quantum" or "ai" — selects extraction prompt and core ticker list

        Returns:
            QuoteExtractionResult with extracted quotes
        """
        logger.info(
            f"[QUOTE_EXTRACTOR] Extracting from {transcript.unique_key} "
            f"(domain={domain}, {transcript.char_count:,} chars)"
        )

        # Select domain-specific prompt and core tickers
        prompt_template = DOMAIN_QUOTE_PROMPTS.get(domain, QUOTE_EXTRACTION_PROMPT)
        core_tickers = DOMAIN_CORE_TICKERS.get(domain, QUANTUM_CORE_TICKERS)

        # Determine tier-specific guidance
        is_core = transcript.ticker in core_tickers
        tier = "core" if is_core else "secondary"
        domain_label = "AI" if domain == "ai" else "quantum"
        tier_guidance = (
            f"extract ALL {domain_label}-relevant quotes — this is a core {domain_label} company"
            if is_core
            else f"only extract quotes specifically mentioning {domain_label} technology, "
            f"{domain_label}-related initiatives, or {domain_label} competitive positioning"
        )

        # Truncate transcript if needed
        text = transcript.transcript_text
        if len(text) > self.config.max_transcript_chars:
            logger.info(
                f"[QUOTE_EXTRACTOR] Truncating transcript from {len(text):,} "
                f"to {self.config.max_transcript_chars:,} chars"
            )
            text = text[: self.config.max_transcript_chars]

        prompt = prompt_template.format(
            ticker=transcript.ticker,
            company_name=transcript.company_name,
            quarter=transcript.quarter,
            year=transcript.year,
            tier=tier,
            tier_guidance=tier_guidance,
        )

        try:
            response = await self.client.messages_create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"TRANSCRIPT:\n\n{text}",
                    }
                ],
                temperature=self.temperature,
            )

            response_text = self.client.extract_text(response)
            quotes = self._parse_quotes(response_text, transcript)

            result = QuoteExtractionResult(
                transcript_id=transcript.transcript_id,
                ticker=transcript.ticker,
                company_name=transcript.company_name,
                quotes=quotes,
                total_quotes=len(quotes),
                extraction_model=self.model,
            )

            logger.info(
                f"[QUOTE_EXTRACTOR] Extracted {len(quotes)} quotes from "
                f"{transcript.unique_key}"
            )
            return result

        except Exception as e:
            logger.error(
                f"[QUOTE_EXTRACTOR] Extraction error for {transcript.unique_key}: {e}"
            )
            return QuoteExtractionResult(
                transcript_id=transcript.transcript_id,
                ticker=transcript.ticker,
                company_name=transcript.company_name,
                quotes=[],
                total_quotes=0,
                extraction_model=self.model,
            )

    def _parse_quotes(
        self, text: str, transcript: EarningsTranscript
    ) -> List[ExtractedQuote]:
        """Parse LLM response into ExtractedQuote objects."""
        parsed = self._parse_json_array(text)
        if not parsed:
            return []

        quotes: List[ExtractedQuote] = []
        for i, item in enumerate(parsed):
            try:
                quote = ExtractedQuote(
                    transcript_id=transcript.transcript_id,
                    quote_text=item.get("quote_text", ""),
                    context_before=item.get("context_before", ""),
                    context_after=item.get("context_after", ""),
                    speaker_name=item.get("speaker_name", "Unknown"),
                    speaker_role=self._parse_enum(
                        SpeakerRole, item.get("speaker_role", "other")
                    ),
                    speaker_title=item.get("speaker_title", ""),
                    speaker_company=item.get("speaker_company", ""),
                    speaker_firm=item.get("speaker_firm", ""),
                    quote_type=self._parse_enum(
                        QuoteType, item.get("quote_type", "strategy")
                    ),
                    themes=item.get("themes", []),
                    sentiment=item.get("sentiment", "neutral"),
                    confidence_level=self._parse_enum(
                        ConfidenceLevel, item.get("confidence_level", "cautious")
                    ),
                    companies_mentioned=item.get("companies_mentioned", []),
                    technologies_mentioned=item.get("technologies_mentioned", []),
                    competitors_mentioned=item.get("competitors_mentioned", []),
                    metrics_mentioned=item.get("metrics_mentioned", []),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    is_quotable=bool(item.get("is_quotable", False)),
                    quotability_reason=item.get("quotability_reason", ""),
                    ticker=transcript.ticker,
                    company_name=transcript.company_name,
                    year=transcript.year,
                    quarter=transcript.quarter,
                    call_date=transcript.call_date,
                    section=self._parse_enum(
                        CallSection, item.get("section", "unknown")
                    ),
                    position_in_section=int(item.get("position_in_section", i)),
                    extraction_model=self.model,
                )
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"[QUOTE_EXTRACTOR] Parse error on quote #{i}: {e}")
                continue

        return quotes

    def _parse_enum(self, enum_class, value):
        """Safely parse an enum value."""
        try:
            return enum_class(value)
        except (ValueError, KeyError):
            return list(enum_class)[0]  # Default to first value

    def _parse_json_array(self, text: str) -> Optional[List[dict]]:
        """Parse a JSON array from LLM response."""
        # Try direct parse
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Try from code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Try finding array in text
        bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
        if bracket_match:
            try:
                data = json.loads(bracket_match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        logger.warning("[QUOTE_EXTRACTOR] Failed to parse JSON array from response")
        return None
