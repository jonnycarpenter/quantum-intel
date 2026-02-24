"""
Podcast Quote Extractor
=======================

LLM-based extraction of notable quotes from podcast transcripts.
Uses Claude Sonnet for structured extraction with speaker attribution,
domain-specific theme classification, and entity recognition.

Supports both quantum computing and AI/ML podcast domains,
selecting the appropriate extraction prompt based on podcast domain.

Adapted from the earnings QuoteExtractor but tailored for podcast content:
- Longer transcripts (30-60 min episodes vs 10-page earnings call)
- More diverse topics (research, industry, careers, policy)
- Guest experts rather than corporate executives
- Chunked processing for long transcripts

Key features:
- Chunked extraction: 30K char chunks with 3K overlap
- Deduplication: 0.85 similarity threshold across chunks
- Speaker-aware: uses diarization labels when available
- Domain-aware: quantum (15 themes) or AI (10 themes)
"""

import json
import os
import re
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timezone

from models.podcast import (
    PodcastTranscript,
    PodcastQuote,
    PodcastQuoteExtractionResult,
    PodcastQuoteType,
    PodcastQuoteTheme,
)
from utils.llm_client import get_resilient_async_client, calculate_cost
from utils.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

QUANTUM_QUOTE_EXTRACTION_PROMPT = """You are an expert analyst covering the quantum computing industry.

Extract the most notable and insightful verbatim quotes from this podcast transcript.
Focus on quotes that would be valuable for someone tracking the quantum computing ecosystem.

WHAT TO LOOK FOR:
1. **Technical insights** — new hardware results, error correction breakthroughs, algorithm advances
2. **Predictions & timelines** — when quantum will be useful, readiness estimates
3. **Industry dynamics** — competition, funding, partnerships, M&A signals
4. **Candid opinions** — honest assessments, pushback on hype, disagreements
5. **Strategic signals** — company direction, technology bets, use case priorities
6. **Great explanations** — analogies or metaphors that explain quantum concepts clearly
7. **First-time disclosures** — new information not previously public

EXTRACTION RULES:
1. Quotes MUST be verbatim — exact words from the transcript
2. Include the speaker name and role (host/guest)
3. Provide brief context before/after the quote
4. Rate relevance 0.0–1.0 (1.0 = breakthrough insight for the quantum industry)
5. Extract 10-25 quotes per episode — quality over quantity
6. Prefer quotes that stand alone and make sense without heavy context
7. Skip pleasantries, filler, and repetitive statements

PODCAST: {podcast_name}
EPISODE: {episode_title}
PUBLISHED: {published_date}
HOST(S): {hosts}
GUEST: {guest_info}

Respond with ONLY a JSON array of quote objects:
```json
[
  {{
    "quote_text": "exact verbatim quote from transcript",
    "context_before": "brief context before the quote",
    "context_after": "brief context after",
    "speaker_name": "Full Name",
    "speaker_role": "host|guest|unknown",
    "speaker_title": "Professor of Physics",
    "speaker_company": "MIT",
    "quote_type": "technical_insight|prediction|opinion|announcement|analogy|disagreement|recommendation|historical_context",
    "themes": ["hardware_progress", "error_correction"],
    "sentiment": "bullish|bearish|neutral|cautious|excited",
    "companies_mentioned": ["IBM", "Google", "QuEra"],
    "technologies_mentioned": ["neutral atoms", "error correction", "logical qubits"],
    "people_mentioned": ["John Preskill"],
    "relevance_score": 0.85,
    "is_quotable": true,
    "quotability_reason": "Guest reveals new qubit coherence result not yet published"
  }}
]
```

VALID THEMES: {valid_themes}

TRANSCRIPT (chunk {chunk_num}/{total_chunks}):
---
{transcript_chunk}
---"""


AI_QUOTE_EXTRACTION_PROMPT = """You are an expert analyst covering the artificial intelligence and machine learning industry.

Extract the most notable and insightful verbatim quotes from this podcast transcript.
Focus on quotes that would be valuable for someone tracking the AI/ML ecosystem.

WHAT TO LOOK FOR:
1. **Model capabilities** — new LLM launches, benchmark results, scaling breakthroughs
2. **AI safety & alignment** — red-teaming, guardrails, alignment research, responsible AI
3. **AI agents & automation** — autonomous agents, tool use, agentic workflows
4. **Enterprise adoption** — real-world deployments, ROI evidence, transformation stories
5. **Regulation & policy** — government actions, EU AI Act, executive orders, industry standards
6. **Infrastructure & compute** — GPU supply, training clusters, inference optimization
7. **Open source dynamics** — open weights vs. closed, community models, licensing debates
8. **Strategic signals** — company direction, product launches, competitive moves
9. **Candid opinions** — honest assessments, pushback on hype, disagreements
10. **First-time disclosures** — new information not previously public

EXTRACTION RULES:
1. Quotes MUST be verbatim — exact words from the transcript
2. Include the speaker name and role (host/guest)
3. Provide brief context before/after the quote
4. Rate relevance 0.0–1.0 (1.0 = breakthrough insight for the AI industry)
5. Extract 10-25 quotes per episode — quality over quantity
6. Prefer quotes that stand alone and make sense without heavy context
7. Skip pleasantries, filler, and repetitive statements

PODCAST: {podcast_name}
EPISODE: {episode_title}
PUBLISHED: {published_date}
HOST(S): {hosts}
GUEST: {guest_info}

Respond with ONLY a JSON array of quote objects:
```json
[
  {{
    "quote_text": "exact verbatim quote from transcript",
    "context_before": "brief context before the quote",
    "context_after": "brief context after",
    "speaker_name": "Full Name",
    "speaker_role": "host|guest|unknown",
    "speaker_title": "CTO",
    "speaker_company": "Anthropic",
    "quote_type": "technical_insight|prediction|opinion|announcement|analogy|disagreement|recommendation|historical_context",
    "themes": ["llm_capabilities", "ai_safety_alignment"],
    "sentiment": "bullish|bearish|neutral|cautious|excited",
    "companies_mentioned": ["OpenAI", "Anthropic", "Google"],
    "technologies_mentioned": ["GPT-5", "Claude", "transformers"],
    "people_mentioned": ["Sam Altman"],
    "relevance_score": 0.85,
    "is_quotable": true,
    "quotability_reason": "CTO reveals new reasoning architecture not yet published"
  }}
]
```

VALID THEMES: {valid_themes}

TRANSCRIPT (chunk {chunk_num}/{total_chunks}):
---
{transcript_chunk}
---"""

# Map domain to prompt template
DOMAIN_PROMPTS = {
    "quantum": QUANTUM_QUOTE_EXTRACTION_PROMPT,
    "ai": AI_QUOTE_EXTRACTION_PROMPT,
}


# =============================================================================
# EXTRACTOR CLASS
# =============================================================================

class PodcastQuoteExtractor:
    """
    Extract notable quotes from podcast transcripts using Claude.

    Handles long transcripts via chunking:
    - Split transcript into ~30K char chunks with 3K overlap
    - Extract quotes from each chunk
    - Deduplicate across chunks (quotes near chunk boundaries)
    """

    # Chunking parameters
    CHUNK_SIZE = 30_000       # Characters per chunk
    CHUNK_OVERLAP = 3_000     # Overlap between chunks
    DEDUP_SIMILARITY = 0.85   # Quote text similarity threshold for dedup

    def __init__(
        self,
        model: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 16000,
    ):
        self.model = model or os.getenv(
            "PODCAST_EXTRACTION_MODEL", "claude-sonnet-4-6"
        )
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.total_cost = 0.0

    async def extract_quotes(
        self,
        transcript: PodcastTranscript,
        domain: str = "quantum",
    ) -> PodcastQuoteExtractionResult:
        """
        Extract quotes from a podcast transcript.

        Args:
            transcript: The podcast transcript to process.
            domain: "quantum" or "ai" — selects the extraction prompt.

        For transcripts > CHUNK_SIZE chars, processes in chunks and deduplicates.
        """
        text = transcript.formatted_text or transcript.full_text
        if not text or len(text) < 200:
            logger.warning(f"[PODCAST_QUOTES] Transcript too short: {transcript.unique_key}")
            return PodcastQuoteExtractionResult(
                episode_id=transcript.episode_id,
                podcast_id=transcript.podcast_id,
                error="Transcript too short for extraction",
            )

        # Select domain-specific prompt template
        prompt_template = DOMAIN_PROMPTS.get(domain, QUANTUM_QUOTE_EXTRACTION_PROMPT)

        # Build metadata for prompt
        guest_info = "Unknown"
        if transcript.guest_name:
            parts = [transcript.guest_name]
            if transcript.guest_title:
                parts.append(transcript.guest_title)
            if transcript.guest_company:
                parts.append(transcript.guest_company)
            guest_info = ", ".join(parts)

        hosts = ", ".join(transcript.hosts) if transcript.hosts else "Unknown"
        published_date = ""
        if transcript.published_at:
            if isinstance(transcript.published_at, datetime):
                published_date = transcript.published_at.strftime("%Y-%m-%d")
            else:
                published_date = str(transcript.published_at)

        valid_themes = ", ".join(t.value for t in PodcastQuoteTheme)

        # Chunk the transcript
        chunks = self._chunk_text(text)
        logger.info(
            f"[PODCAST_QUOTES] Processing {transcript.unique_key} (domain={domain}): "
            f"{len(text)} chars, {len(chunks)} chunks"
        )

        all_quotes: List[PodcastQuote] = []
        extraction_cost = 0.0

        for i, chunk in enumerate(chunks):
            prompt = prompt_template.format(
                podcast_name=transcript.podcast_name,
                episode_title=transcript.episode_title,
                published_date=published_date,
                hosts=hosts,
                guest_info=guest_info,
                valid_themes=valid_themes,
                chunk_num=i + 1,
                total_chunks=len(chunks),
                transcript_chunk=chunk,
            )

            try:
                quotes, cost = await self._extract_from_chunk(
                    prompt, transcript, chunk_index=i
                )
                all_quotes.extend(quotes)
                extraction_cost += cost
            except Exception as e:
                logger.error(
                    f"[PODCAST_QUOTES] Chunk {i+1}/{len(chunks)} failed "
                    f"for {transcript.unique_key}: {e}"
                )

        # Deduplicate quotes across chunks
        deduped_quotes = self._deduplicate_quotes(all_quotes)

        self.total_cost += extraction_cost
        logger.info(
            f"[PODCAST_QUOTES] {transcript.unique_key}: "
            f"{len(all_quotes)} raw -> {len(deduped_quotes)} deduped quotes, "
            f"cost=${extraction_cost:.4f}"
        )

        return PodcastQuoteExtractionResult(
            episode_id=transcript.episode_id,
            podcast_id=transcript.podcast_id,
            quotes=deduped_quotes,
            total_extracted=len(deduped_quotes),
            extraction_model=self.model,
            extraction_cost_usd=extraction_cost,
        )

    async def _extract_from_chunk(
        self,
        prompt: str,
        transcript: PodcastTranscript,
        chunk_index: int,
    ) -> Tuple[List[PodcastQuote], float]:
        """Send a chunk to Claude for extraction. Returns (quotes, cost)."""
        client = get_resilient_async_client(
            anthropic_api_key=self.anthropic_api_key,
            timeout=180.0,  # 30K char chunks need >60s on Sonnet
        )

        response = await client.messages_create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = calculate_cost(self.model, input_tokens, output_tokens)

        # Parse response
        raw_text = client.extract_text(response)
        quotes = self._parse_quotes_json(
            raw_text, transcript, chunk_index
        )

        return quotes, cost

    def _parse_quotes_json(
        self,
        raw_text: str,
        transcript: PodcastTranscript,
        chunk_index: int,
    ) -> List[PodcastQuote]:
        """Parse JSON array of quotes from LLM response."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = raw_text.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json", 1)[1]
            json_str = json_str.split("```", 1)[0]
        elif "```" in json_str:
            json_str = json_str.split("```", 1)[1]
            json_str = json_str.split("```", 1)[0]

        json_str = json_str.strip()
        if not json_str:
            logger.warning("[PODCAST_QUOTES] Empty response from LLM")
            return []

        try:
            quotes_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[PODCAST_QUOTES] JSON parse error: {e}")
            # Try to salvage partial JSON
            quotes_data = self._salvage_json(json_str)
            if not quotes_data:
                return []

        if not isinstance(quotes_data, list):
            logger.warning("[PODCAST_QUOTES] Response is not a JSON array")
            return []

        quotes: List[PodcastQuote] = []
        now = datetime.now(timezone.utc)

        for item in quotes_data:
            if not isinstance(item, dict):
                continue
            quote_text = item.get("quote_text", "").strip()
            if not quote_text or len(quote_text) < 20:
                continue

            # Normalize themes to comma-separated string
            themes_raw = item.get("themes", [])
            if isinstance(themes_raw, list):
                themes = ", ".join(str(t) for t in themes_raw)
            else:
                themes = str(themes_raw)

            # Normalize entity lists to comma-separated strings
            companies = ", ".join(item.get("companies_mentioned", []))
            technologies = ", ".join(item.get("technologies_mentioned", []))
            people = ", ".join(item.get("people_mentioned", []))

            published_at = None
            if transcript.published_at:
                if isinstance(transcript.published_at, datetime):
                    published_at = transcript.published_at.isoformat()
                else:
                    published_at = str(transcript.published_at)

            quote = PodcastQuote(
                transcript_id=transcript.transcript_id,
                episode_id=transcript.episode_id,
                quote_text=quote_text,
                context_before=item.get("context_before", ""),
                context_after=item.get("context_after", ""),
                speaker_name=item.get("speaker_name", "Unknown"),
                speaker_role=item.get("speaker_role", "guest"),
                speaker_title=item.get("speaker_title"),
                speaker_company=item.get("speaker_company"),
                quote_type=item.get("quote_type", PodcastQuoteType.TECHNICAL_INSIGHT.value),
                themes=themes,
                sentiment=item.get("sentiment", "neutral"),
                companies_mentioned=companies,
                technologies_mentioned=technologies,
                people_mentioned=people,
                relevance_score=float(item.get("relevance_score", 0.5)),
                is_quotable=bool(item.get("is_quotable", False)),
                quotability_reason=item.get("quotability_reason", ""),
                podcast_id=transcript.podcast_id,
                podcast_name=transcript.podcast_name,
                episode_title=transcript.episode_title,
                published_at=published_at,
                extracted_at=now,
                extraction_model=self.model,
                extraction_confidence=0.85,
            )
            quotes.append(quote)

        return quotes

    # =========================================================================
    # Chunking & Deduplication
    # =========================================================================

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks for processing."""
        if len(text) <= self.CHUNK_SIZE:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE

            # Try to break at a paragraph or sentence boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start + self.CHUNK_SIZE - 2000, end)
                if para_break > start:
                    end = para_break
                else:
                    # Look for sentence break
                    sent_break = text.rfind(". ", start + self.CHUNK_SIZE - 1000, end)
                    if sent_break > start:
                        end = sent_break + 1

            chunks.append(text[start:end])
            start = end - self.CHUNK_OVERLAP

        return chunks

    def _deduplicate_quotes(self, quotes: List[PodcastQuote]) -> List[PodcastQuote]:
        """Remove near-duplicate quotes extracted from overlapping chunks."""
        if len(quotes) <= 1:
            return quotes

        unique: List[PodcastQuote] = []
        for quote in quotes:
            is_dup = False
            for existing in unique:
                similarity = self._text_similarity(
                    quote.quote_text, existing.quote_text
                )
                if similarity >= self.DEDUP_SIMILARITY:
                    # Keep the one with higher relevance
                    if quote.relevance_score > existing.relevance_score:
                        unique.remove(existing)
                        unique.append(quote)
                    is_dup = True
                    break

            if not is_dup:
                unique.append(quote)

        return unique

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Simple word-overlap similarity for deduplication."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    @staticmethod
    def _salvage_json(text: str) -> Optional[list]:
        """Try to parse truncated JSON by closing brackets."""
        # Strategy 1: Direct suffix closures (handles unterminated strings/objects)
        for suffix in ["]", '"}]', '"}}]', '": null}]']:
            try:
                return json.loads(text + suffix)
            except json.JSONDecodeError:
                continue
        # Strategy 2: Remove last incomplete object (handles "Expecting property name" errors
        # where JSON is cut mid-object after a comma between top-level array elements)
        last_comma = text.rfind(",")
        last_open_brace = text.rfind("{")
        if last_comma != -1 and last_comma > last_open_brace:
            # Truncation is between objects — remove trailing comma and close array
            try:
                return json.loads(text[:last_comma] + "]")
            except json.JSONDecodeError:
                pass
        return None
