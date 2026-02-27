"""
Case Study Extractor
=====================

LLM-based extraction of structured case studies from any source type.
Domain-aware (quantum/ai) + source-aware (article/podcast/earnings/sec/arxiv).
Each combination selects a specialized prompt template.

Follows the proven patterns from:
- processing/quote_extractor.py (earnings quotes)
- processing/nugget_extractor.py (SEC nuggets)
- processing/podcast_quote_extractor.py (podcast quotes — chunking, dedup)

Usage:
    extractor = CaseStudyExtractor()
    result = await extractor.extract_from_article(article, domain="ai")
    result = await extractor.extract_from_podcast(transcript, domain="quantum")
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from models.case_study import CaseStudy, CaseStudyExtractionResult
from storage.base import ClassifiedArticle
from models.paper import Paper
from models.earnings import EarningsTranscript
from models.sec_filing import SecFiling
from models.podcast import PodcastTranscript
from config.settings import CaseStudyConfig
from utils.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# JSON OUTPUT SCHEMA (shared by all 10 prompts)
# =============================================================================

CASE_STUDY_JSON_SCHEMA = """
[
  {
    "use_case_title": "Short descriptive title of the case study/story",
    "use_case_summary": "2-3 sentence narrative of the full story",
    "grounding_quote": "Verbatim text from the source that grounds this case study",
    "context_text": "Surrounding context for the grounding quote",
    "company": "Primary company implementing or discussed",
    "industry": "Industry vertical (e.g., manufacturing, healthcare, finance, defense)",
    "technology_stack": ["technology1", "technology2"],
    "department": "Department or team (e.g., Production Engineering, Fraud Detection) or null",
    "implementation_detail": "How they did it — specifics of the deployment or null",
    "teams_impacted": ["team1", "team2"],
    "scale": "Scale description (e.g., '3 assembly lines, 1 plant') or null",
    "timeline": "Timeline description (e.g., '6 months', 'deployed Q3 2025') or null",
    "readiness_level": "production|pilot|announced|research|theoretical",
    "outcome_metric": "Quantified outcome (e.g., '40% reduction in assembly time') or null",
    "outcome_type": "efficiency|revenue|accuracy|scale|cost_reduction|speed|risk_reduction|scientific|competitive|partnership|regulatory|other|null",
    "outcome_quantified": true,
    "speaker": "Speaker name (for podcast/earnings) or null",
    "speaker_role": "Speaker role or null",
    "speaker_company": "Speaker company or null",
    "companies_mentioned": ["Company1", "Company2"],
    "technologies_mentioned": ["Tech1", "Tech2"],
    "people_mentioned": ["Person1"],
    "competitors_mentioned": ["Competitor1"],
    "relevance_score": 0.85,
    "confidence": 0.9
  }
]
"""

# Quantum-specific fields appended to quantum prompts
QUANTUM_EXTRA_FIELDS = """
    "qubit_type": "trapped ion|superconducting|photonic|neutral atom|topological|other|null",
    "gate_fidelity": "Fidelity metric (e.g., '99.5% two-qubit gate fidelity') or null",
    "commercial_viability": "near-term|mid-term|long-term|theoretical|null",
    "scientific_significance": "Why this matters for the field, or null"
"""

# AI-specific fields appended to AI prompts
AI_EXTRA_FIELDS = """
    "ai_model_used": "Name of AI model used (e.g., 'GPT-4', 'Claude', 'custom LLM') or null",
    "roi_metric": "ROI metric (e.g., '$2M annual savings', '3x faster') or null",
    "deployment_type": "cloud|on-premise|edge|hybrid|null"
"""


# =============================================================================
# PROMPT TEMPLATES — 10 combinations (2 domains x 5 source types)
# =============================================================================

# ---------------------------------------------------------------------------
# AI DOMAIN PROMPTS
# ---------------------------------------------------------------------------

AI_ARTICLE_PROMPT = """You are an expert AI industry analyst specializing in enterprise AI deployments and real-world business outcomes.

Extract structured case studies from this article. Focus on REAL STORIES of AI adoption — not announcements or speculation.

WHAT TO EXTRACT:
1. **Enterprise deployments** — Company X deployed AI technology Y in department Z and achieved outcome W
2. **ROI stories** — Quantified business outcomes (cost savings, revenue lift, time reduction)
3. **Implementation journeys** — How they did it, what teams were involved, what scale
4. **Competitive moves** — Strategic AI investments, partnerships, acquisitions
5. **Product launches with customer impact** — Not just announcements, but what happened after

EXTRACTION RULES:
1. Every case study MUST be grounded in a verbatim quote from the article
2. Prioritize quantified outcomes over vague claims
3. Extract industry AND department when mentioned (e.g., "retail / demand planning")
4. Set outcome_quantified=true ONLY if there is a specific number/percentage
5. Distinguish between pilot/POC and production deployment
6. Extract 1-5 case studies per article — quality over quantity
7. Skip promotional fluff without substance

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these AI-specific fields per object:
""" + AI_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

AI_PODCAST_PROMPT = """You are an expert AI industry analyst extracting structured intelligence from podcast conversations.

Extract case studies from this podcast transcript. Focus on STORIES told by speakers — real experiences, deployments, lessons learned.

WHAT TO EXTRACT:
1. **First-person deployment stories** — "We built...", "Our team deployed...", "At [Company], we..."
2. **Customer stories** — Speakers describing what their customers achieved with AI
3. **Technology evaluations** — Comparisons, what worked, what didn't
4. **Strategic decisions** — Why a company chose a particular AI approach
5. **Lessons learned** — Practical insights from real implementations

EXTRACTION RULES:
1. Every case study MUST have a verbatim grounding quote from the transcript
2. ALWAYS attribute the speaker — name, role, company
3. Distinguish between first-hand experience and second-hand reporting
4. Capture the narrative arc: problem → solution → outcome
5. Extract department and team details when mentioned
6. Set confidence lower for speculative/forward-looking statements
7. Extract 3-10 case studies per episode — quality over quantity

PODCAST: {podcast_name}
EPISODE: {episode_title}
GUEST: {guest_info}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these AI-specific fields per object:
""" + AI_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

AI_EARNINGS_PROMPT = """You are an expert financial analyst specializing in AI revenue and enterprise adoption metrics.

Extract structured case studies from this earnings call transcript. Focus on AI-related business outcomes and strategic decisions.

WHAT TO EXTRACT:
1. **AI revenue metrics** — ARR, bookings, inference volume, customer growth
2. **Customer deployment stories** — Named customers using AI products
3. **AI capex/infrastructure** — GPU spend, data center investments, compute scaling
4. **Product and platform launches** — AI features shipped, platform announcements
5. **Competitive positioning** — How the company positions against AI competitors

EXTRACTION RULES:
1. Every case study MUST be grounded in a verbatim quote from the transcript
2. ALWAYS attribute to the speaker (CEO, CFO, analyst, etc.)
3. Focus on quantified outcomes — revenue numbers, customer counts, growth rates
4. Distinguish between actual results and forward guidance
5. Flag hedge language: "approximately", "we expect", "on track"
6. For {tier} tickers, {tier_guidance}
7. Extract 3-10 case studies per transcript

TICKER: {ticker}
COMPANY: {company_name}
PERIOD: Q{quarter} {year}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these AI-specific fields per object:
""" + AI_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

AI_SEC_PROMPT = """You are an expert SEC filing analyst specializing in AI business strategy and investment disclosures.

Extract structured case studies from this SEC filing. Focus on AI-related disclosures that reveal business strategy.

WHAT TO EXTRACT:
1. **AI capex disclosures** — Infrastructure investments, GPU/compute spending
2. **AI revenue disclosures** — Revenue attribution to AI products/services
3. **Strategic partnerships** — AI-related partnerships, licensing, collaboration
4. **Risk factors** — AI-specific risks acknowledged (competition, regulation, talent)
5. **Customer/deployment disclosures** — Named AI customers or deployment milestones

EXTRACTION RULES:
1. Every case study MUST be grounded in verbatim text from the filing
2. Prioritize new disclosures over boilerplate
3. Extract financial figures when available
4. Note the filing section (risk factors, MD&A, business overview)
5. Flag first-time disclosures as high confidence
6. For {tier} tickers, {tier_guidance}
7. Extract 3-8 case studies per filing

TICKER: {ticker}
COMPANY: {company_name}
FILING TYPE: {filing_type}
FISCAL PERIOD: {fiscal_period}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these AI-specific fields per object:
""" + AI_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

AI_ARXIV_PROMPT = """You are an expert AI research analyst who translates academic papers into business-relevant intelligence.

Extract a BUSINESS-FRIENDLY case study from this ArXiv paper abstract. Your goal is to explain:
1. WHAT the paper introduces (technique, model, approach)
2. WHY it matters for the AI industry (benchmark results, capabilities unlocked)
3. BUSINESS IMPLICATIONS (who would use this, what problems it solves, timeline to adoption)

EXTRACTION RULES:
1. Use 1-2 sentences from the abstract as the grounding quote
2. Write use_case_summary as a business-friendly explanation — no jargon
3. Assess readiness_level honestly: most papers are "research" or "theoretical"
4. If benchmark results are mentioned, extract them as outcome_metric
5. Identify which industries or use cases would benefit
6. Extract 1 case study per paper (the paper itself IS the case study)
7. Set technology_stack to the key techniques/architectures discussed

Respond with ONLY a JSON array containing exactly 1 case study object:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these AI-specific fields per object:
""" + AI_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

# ---------------------------------------------------------------------------
# QUANTUM DOMAIN PROMPTS
# ---------------------------------------------------------------------------

QUANTUM_ARTICLE_PROMPT = """You are an expert quantum computing analyst specializing in technology milestones and commercial progress.

Extract structured case studies from this article. Focus on REAL PROGRESS — not hype.

WHAT TO EXTRACT:
1. **Hardware milestones** — Qubit counts, gate fidelities, processor announcements
2. **Error correction advances** — Logical qubit demonstrations, fault tolerance progress
3. **Enterprise quantum POCs** — Companies testing quantum solutions
4. **Use case demonstrations** — Drug discovery, finance, optimization, cybersecurity applications
5. **Commercial partnerships** — Quantum companies partnering with enterprises
6. **Government/defense contracts** — DOE, DARPA, defense quantum programs

EXTRACTION RULES:
1. Every case study MUST be grounded in a verbatim quote from the article
2. Extract qubit type and fidelity metrics when mentioned
3. Distinguish between lab demonstrations and commercial readiness
4. Be skeptical of unverified performance claims
5. Note commercial viability timeline (near-term, mid-term, long-term)
6. Extract 1-5 case studies per article — quality over quantity
7. Skip general "quantum is coming" commentary without substance

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these quantum-specific fields per object:
""" + QUANTUM_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

QUANTUM_PODCAST_PROMPT = """You are an expert quantum computing analyst extracting structured intelligence from podcast conversations.

Extract case studies from this podcast transcript. Focus on expert insights about quantum technology and business progress.

WHAT TO EXTRACT:
1. **Technology roadmaps** — Speakers describing their company's quantum hardware/software plans
2. **Use case discussions** — Real-world quantum applications being explored or deployed
3. **Competitive assessments** — Comparisons between quantum platforms and approaches
4. **Timeline predictions** — When quantum advantage will be achieved, readiness estimates
5. **Candid admissions** — Honest assessments of challenges, setbacks, technical barriers
6. **Partnership/customer discussions** — Who is working with whom

EXTRACTION RULES:
1. Every case study MUST have a verbatim grounding quote from the transcript
2. ALWAYS attribute the speaker — name, role, company
3. Extract qubit type and technical specifications when mentioned
4. Note whether claims are about current capabilities or future plans
5. Assess commercial viability honestly
6. Extract 3-10 case studies per episode

PODCAST: {podcast_name}
EPISODE: {episode_title}
GUEST: {guest_info}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these quantum-specific fields per object:
""" + QUANTUM_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

QUANTUM_EARNINGS_PROMPT = """You are an expert financial analyst specializing in quantum computing companies.

Extract structured case studies from this earnings call transcript. Focus on quantum business metrics and technology milestones.

WHAT TO EXTRACT:
1. **Quantum revenue metrics** — Revenue, bookings, backlog, customer counts
2. **Technology milestone claims** — Qubit roadmap progress, fidelity achievements
3. **Government contracts** — DOE, DARPA, defense-related quantum deals
4. **Customer deployment stories** — Named customers using quantum platforms
5. **Competitive positioning** — How they compare to IBM, Google, IonQ, etc.
6. **Cash runway and risk** — Financial sustainability signals

EXTRACTION RULES:
1. Every case study MUST be grounded in a verbatim quote from the transcript
2. ALWAYS attribute to the speaker (CEO, CFO, CTO, analyst, etc.)
3. Focus on quantified outcomes — revenue, contract values, qubit counts
4. Distinguish between actual results and forward guidance
5. Extract qubit type and technology platform details
6. For {tier} tickers, {tier_guidance}
7. Extract 3-10 case studies per transcript

TICKER: {ticker}
COMPANY: {company_name}
PERIOD: Q{quarter} {year}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these quantum-specific fields per object:
""" + QUANTUM_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

QUANTUM_SEC_PROMPT = """You are an expert SEC filing analyst specializing in the quantum computing industry.

Extract structured case studies from this SEC filing. Focus on quantum-relevant disclosures.

WHAT TO EXTRACT:
1. **Competitive disclosures** — Named quantum competitors in legally mandated risk factors
2. **Technology investment** — R&D spending on quantum, qubit roadmap disclosures
3. **Government contracts** — DOE/DARPA/DOD quantum programs
4. **IP and patents** — Quantum-related intellectual property
5. **Export control risks** — ITAR, EAR, CFIUS implications for quantum technology
6. **Customer/partnership disclosures** — Named quantum customers or partners

EXTRACTION RULES:
1. Every case study MUST be grounded in verbatim text from the filing
2. Prioritize "buried" disclosures over boilerplate
3. Flag first-time disclosures as high confidence
4. Extract financial figures when available
5. Note the filing section context
6. For {tier} tickers, {tier_guidance}
7. Extract 3-8 case studies per filing

TICKER: {ticker}
COMPANY: {company_name}
FILING TYPE: {filing_type}
FISCAL PERIOD: {fiscal_period}

Respond with ONLY a JSON array of case study objects:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these quantum-specific fields per object:
""" + QUANTUM_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""

QUANTUM_ARXIV_PROMPT = """You are an expert quantum computing research analyst who translates academic papers into business-relevant intelligence.

Extract a BUSINESS-FRIENDLY case study from this ArXiv paper abstract. Your goal is to explain:
1. WHAT the paper introduces (algorithm, hardware result, error correction technique)
2. WHY it matters scientifically (fidelity improvements, scaling implications, theoretical breakthrough)
3. BUSINESS IMPLICATIONS (which industries benefit, timeline to commercial use, who should care)

EXTRACTION RULES:
1. Use 1-2 sentences from the abstract as the grounding quote
2. Write use_case_summary for a business audience — explain significance without jargon
3. Extract qubit type, gate fidelity, and other technical metrics
4. Assess commercial_viability honestly: "near-term" only if real hardware demonstrated
5. Identify applicable industries (pharma, finance, defense, materials, etc.)
6. Extract 1 case study per paper
7. Set readiness_level based on what was actually demonstrated (not claimed)

Respond with ONLY a JSON array containing exactly 1 case study object:
""" + CASE_STUDY_JSON_SCHEMA + """
Also include these quantum-specific fields per object:
""" + QUANTUM_EXTRA_FIELDS + """

Return ONLY the JSON array, no other text."""


# =============================================================================
# PROMPT REGISTRY
# =============================================================================

DOMAIN_SOURCE_PROMPTS = {
    ("ai", "article"): AI_ARTICLE_PROMPT,
    ("ai", "podcast"): AI_PODCAST_PROMPT,
    ("ai", "earnings"): AI_EARNINGS_PROMPT,
    ("ai", "sec_filing"): AI_SEC_PROMPT,
    ("ai", "arxiv"): AI_ARXIV_PROMPT,
    ("quantum", "article"): QUANTUM_ARTICLE_PROMPT,
    ("quantum", "podcast"): QUANTUM_PODCAST_PROMPT,
    ("quantum", "earnings"): QUANTUM_EARNINGS_PROMPT,
    ("quantum", "sec_filing"): QUANTUM_SEC_PROMPT,
    ("quantum", "arxiv"): QUANTUM_ARXIV_PROMPT,
}


# =============================================================================
# TIER GUIDANCE (reused from quote/nugget extractors)
# =============================================================================

TIER_GUIDANCE = {
    "core": "This is a CORE domain-specific company. Extract ALL relevant case studies with high detail.",
    "secondary": "This is a SECONDARY company with broader business. Focus on domain-specific disclosures only.",
}


# =============================================================================
# EXTRACTOR CLASS
# =============================================================================

class CaseStudyExtractor:
    """
    LLM-based extraction of structured case studies from any source type.

    Domain-aware (quantum/ai) + source-aware (article/podcast/earnings/sec/arxiv).
    Each combination selects a specialized prompt template.
    """

    CHUNK_SIZE = 30_000
    CHUNK_OVERLAP = 3_000
    DEDUP_SIMILARITY = 0.85

    def __init__(
        self,
        config: Optional[CaseStudyConfig] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 16_000,
    ):
        self.config = config or CaseStudyConfig()
        self.model = model or self.config.extraction_model
        self.temperature = temperature
        self.max_tokens = max_tokens or self.config.extraction_max_tokens

        # Lazy-load LLM client
        self._client = None

    async def _get_client(self):
        """Lazy-load the LLM client."""
        if self._client is None:
            from utils.llm_client import ResilientAsyncClient
            self._client = ResilientAsyncClient()
        return self._client

    # =========================================================================
    # Public extraction methods — one per source type
    # =========================================================================

    async def extract_from_article(
        self, article: ClassifiedArticle, domain: str = "quantum"
    ) -> CaseStudyExtractionResult:
        """Extract case studies from a classified article."""
        text = article.full_text or article.summary or ""
        if not text.strip():
            return CaseStudyExtractionResult(
                source_type="article", source_id=article.id,
                success=False, error_message="No text content",
            )

        context = {"title": article.title, "source": article.source_name}
        return await self._extract(
            text=text,
            source_type="article",
            source_id=article.id,
            domain=domain,
            context=context,
        )

    async def extract_from_podcast(
        self, transcript: PodcastTranscript, domain: str = "quantum"
    ) -> CaseStudyExtractionResult:
        """Extract case studies from a podcast transcript."""
        text = transcript.formatted_text or transcript.full_text or ""
        if not text.strip():
            return CaseStudyExtractionResult(
                source_type="podcast", source_id=transcript.transcript_id,
                success=False, error_message="No transcript text",
            )

        guest_info = ""
        if transcript.guest_name:
            parts = [transcript.guest_name]
            if transcript.guest_title:
                parts.append(transcript.guest_title)
            if transcript.guest_company:
                parts.append(transcript.guest_company)
            guest_info = ", ".join(parts)

        context = {
            "podcast_name": transcript.podcast_name,
            "episode_title": transcript.episode_title,
            "guest_info": guest_info or "Unknown",
        }
        return await self._extract(
            text=text,
            source_type="podcast",
            source_id=transcript.transcript_id,
            domain=domain,
            context=context,
        )

    async def extract_from_earnings(
        self, transcript: EarningsTranscript, domain: str = "quantum",
        tier: str = "core",
    ) -> CaseStudyExtractionResult:
        """Extract case studies from an earnings call transcript."""
        text = transcript.transcript_text or ""
        if not text.strip():
            return CaseStudyExtractionResult(
                source_type="earnings", source_id=transcript.transcript_id,
                success=False, error_message="No transcript text",
            )

        context = {
            "ticker": transcript.ticker,
            "company_name": transcript.company_name,
            "year": transcript.year,
            "quarter": transcript.quarter,
            "tier": tier,
            "tier_guidance": TIER_GUIDANCE.get(tier, TIER_GUIDANCE["core"]),
        }
        return await self._extract(
            text=text,
            source_type="earnings",
            source_id=transcript.transcript_id,
            domain=domain,
            context=context,
        )

    async def extract_from_sec(
        self, filing: SecFiling, domain: str = "quantum",
        tier: str = "core",
    ) -> CaseStudyExtractionResult:
        """Extract case studies from an SEC filing."""
        # Use sections if available, otherwise raw content
        if filing.sections and isinstance(filing.sections, dict):
            text = "\n\n".join(
                f"=== {section.upper()} ===\n{content}"
                for section, content in filing.sections.items()
                if content
            )
        else:
            text = filing.raw_content or ""

        if not text.strip():
            return CaseStudyExtractionResult(
                source_type="sec_filing", source_id=filing.filing_id,
                success=False, error_message="No filing content",
            )

        fiscal_period = f"FY{filing.fiscal_year}"
        if filing.fiscal_quarter:
            fiscal_period += f" Q{filing.fiscal_quarter}"

        context = {
            "ticker": filing.ticker,
            "company_name": filing.company_name,
            "filing_type": filing.filing_type,
            "fiscal_period": fiscal_period,
            "tier": tier,
            "tier_guidance": TIER_GUIDANCE.get(tier, TIER_GUIDANCE["core"]),
        }
        return await self._extract(
            text=text,
            source_type="sec_filing",
            source_id=filing.filing_id,
            domain=domain,
            context=context,
        )

    async def extract_from_arxiv(
        self, paper: Paper, domain: str = "quantum"
    ) -> CaseStudyExtractionResult:
        """Extract a case study from an ArXiv paper abstract."""
        text = paper.abstract or ""
        if not text.strip():
            return CaseStudyExtractionResult(
                source_type="arxiv", source_id=paper.arxiv_id,
                success=False, error_message="No abstract",
            )

        context = {
            "title": paper.title,
            "authors": ", ".join(paper.authors[:5]) if paper.authors else "Unknown",
            "categories": ", ".join(paper.categories) if paper.categories else "",
        }
        return await self._extract(
            text=text,
            source_type="arxiv",
            source_id=paper.arxiv_id,
            domain=domain,
            context=context,
        )

    # =========================================================================
    # Core extraction logic
    # =========================================================================

    async def _extract(
        self,
        text: str,
        source_type: str,
        source_id: str,
        domain: str,
        context: Dict[str, Any],
    ) -> CaseStudyExtractionResult:
        """Core extraction: prompt selection, chunking, LLM call, parsing."""
        start_time = time.time()
        result = CaseStudyExtractionResult(
            source_type=source_type,
            source_id=source_id,
            source_length=len(text),
            extraction_model=self.model,
        )

        try:
            # Truncate if needed
            max_chars = self.config.max_source_chars
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.info(
                    f"[CASE_STUDY] Truncated {source_type} {source_id} to {max_chars:,} chars"
                )

            # Get prompt
            prompt = self._get_prompt(domain, source_type, context)

            # Chunk if needed
            chunks = self._chunk_text(text)
            all_studies: List[CaseStudy] = []
            total_cost = 0.0

            for i, chunk in enumerate(chunks):
                chunk_label = f"chunk {i+1}/{len(chunks)}" if len(chunks) > 1 else "full"
                logger.info(
                    f"[CASE_STUDY] Extracting from {source_type} {source_id} ({chunk_label}, "
                    f"{len(chunk):,} chars)"
                )

                studies, cost = await self._extract_from_chunk(
                    prompt=prompt,
                    text=chunk,
                    source_type=source_type,
                    source_id=source_id,
                    domain=domain,
                    context=context,
                )
                all_studies.extend(studies)
                total_cost += cost

            # Dedup across chunks
            if len(chunks) > 1:
                before = len(all_studies)
                all_studies = self._deduplicate(all_studies)
                if len(all_studies) < before:
                    logger.info(
                        f"[CASE_STUDY] Deduped {before} → {len(all_studies)} case studies"
                    )

            # Cap per source
            max_per_source = self.config.max_case_studies_per_source
            if len(all_studies) > max_per_source:
                all_studies.sort(key=lambda cs: cs.relevance_score, reverse=True)
                all_studies = all_studies[:max_per_source]

            result.case_studies = all_studies
            result.success = True
            result.extraction_cost_usd = total_cost
            result.compute_statistics()

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"[CASE_STUDY] Extraction error for {source_type} {source_id}: {e}")

        result.extraction_time_seconds = time.time() - start_time
        return result

    async def _extract_from_chunk(
        self,
        prompt: str,
        text: str,
        source_type: str,
        source_id: str,
        domain: str,
        context: Dict[str, Any],
    ) -> Tuple[List[CaseStudy], float]:
        """Extract case studies from a single chunk of text. Returns (studies, cost_usd)."""
        client = await self._get_client()

        try:
            response = await client.messages_create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=prompt,
                messages=[{"role": "user", "content": f"SOURCE CONTENT:\n\n{text}"}],
                temperature=self.temperature,
            )

            response_text = client.extract_text(response)

            # Calculate cost
            cost = 0.0
            if hasattr(response, "usage"):
                from utils.llm_client import calculate_cost
                cost = calculate_cost(
                    self.model,
                    getattr(response.usage, "input_tokens", 0),
                    getattr(response.usage, "output_tokens", 0),
                )

            # Parse JSON response
            raw_studies = self._parse_json_array(response_text)
            if raw_studies is None:
                logger.warning(f"[CASE_STUDY] Failed to parse JSON from {source_type} {source_id}")
                return [], cost

            # Convert to CaseStudy objects
            studies = []
            for raw in raw_studies:
                try:
                    cs = self._raw_to_case_study(
                        raw, source_type, source_id, domain, context
                    )
                    studies.append(cs)
                except Exception as e:
                    logger.warning(f"[CASE_STUDY] Skipping malformed case study: {e}")

            logger.info(
                f"[CASE_STUDY] Extracted {len(studies)} case studies from {source_type} "
                f"{source_id} (cost: ${cost:.4f})"
            )
            return studies, cost

        except Exception as e:
            logger.error(f"[CASE_STUDY] LLM call error: {e}")
            return [], 0.0

    # =========================================================================
    # Prompt construction
    # =========================================================================

    def _get_prompt(self, domain: str, source_type: str, context: Dict[str, Any]) -> str:
        """Get and format the appropriate prompt for domain + source type."""
        key = (domain, source_type)
        template = DOMAIN_SOURCE_PROMPTS.get(key)
        if not template:
            raise ValueError(f"No prompt template for domain={domain}, source_type={source_type}")

        # Format with context (safe — ignores extra keys, skips missing ones)
        try:
            return template.format(**context)
        except KeyError:
            # Some templates don't use all context keys — that's fine
            return template

    # =========================================================================
    # Chunking
    # =========================================================================

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap. Tries to break at paragraph/sentence boundaries."""
        if len(text) <= self.CHUNK_SIZE:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))

            # Try to break at paragraph boundary
            if end < len(text):
                para_break = text.rfind("\n\n", start + self.CHUNK_SIZE // 2, end)
                if para_break > start:
                    end = para_break + 2
                else:
                    # Try sentence boundary
                    sent_break = text.rfind(". ", start + self.CHUNK_SIZE // 2, end)
                    if sent_break > start:
                        end = sent_break + 2

            chunks.append(text[start:end])
            start = end - self.CHUNK_OVERLAP if end < len(text) else len(text)

        return chunks

    # =========================================================================
    # Deduplication
    # =========================================================================

    def _deduplicate(self, studies: List[CaseStudy]) -> List[CaseStudy]:
        """Remove near-duplicate case studies (from chunk overlap)."""
        if not studies:
            return studies

        unique: List[CaseStudy] = []
        for cs in studies:
            is_dup = False
            for existing in unique:
                sim = self._text_similarity(cs.grounding_quote, existing.grounding_quote)
                if sim > self.DEDUP_SIMILARITY:
                    # Keep the one with higher relevance
                    if cs.relevance_score > existing.relevance_score:
                        unique.remove(existing)
                        unique.append(cs)
                    is_dup = True
                    break
            if not is_dup:
                unique.append(cs)

        return unique

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Simple word-overlap Jaccard similarity."""
        if not a or not b:
            return 0.0
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    # =========================================================================
    # JSON parsing with truncation recovery
    # =========================================================================

    def _parse_json_array(self, text: str) -> Optional[List[dict]]:
        """Parse JSON array from LLM response, with recovery for truncated output."""
        if not text:
            return None

        # Try 1: Direct parse
        try:
            data = json.loads(text.strip())
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass

        # Try 2: Extract from markdown code block
        if "```" in text:
            start = text.find("```")
            # Skip language tag (e.g., ```json)
            newline = text.find("\n", start)
            if newline > 0:
                end = text.find("```", newline)
                if end > newline:
                    block = text[newline:end].strip()
                    try:
                        data = json.loads(block)
                        if isinstance(data, list):
                            return data
                        if isinstance(data, dict):
                            return [data]
                    except json.JSONDecodeError:
                        pass

        # Try 3: Find array brackets
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end + 1])
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Try 4: Truncated JSON recovery — find last complete object
        if start >= 0:
            json_text = text[start:]
            last_brace = json_text.rfind("}")
            if last_brace > 0:
                truncated = json_text[:last_brace + 1] + "]"
                try:
                    data = json.loads(truncated)
                    if isinstance(data, list):
                        logger.info("[CASE_STUDY] Recovered truncated JSON response")
                        return data
                except json.JSONDecodeError:
                    # Try removing the last incomplete object
                    last_comma = json_text.rfind(",", 0, last_brace)
                    if last_comma > 0:
                        truncated = json_text[:last_comma] + "]"
                        try:
                            data = json.loads(truncated)
                            if isinstance(data, list):
                                logger.info("[CASE_STUDY] Recovered truncated JSON (removed last object)")
                                return data
                        except json.JSONDecodeError:
                            pass

        logger.warning(f"[CASE_STUDY] Could not parse JSON from response ({len(text)} chars)")
        return None

    # =========================================================================
    # Raw dict → CaseStudy conversion
    # =========================================================================

    def _raw_to_case_study(
        self,
        raw: dict,
        source_type: str,
        source_id: str,
        domain: str,
        context: Dict[str, Any],
    ) -> CaseStudy:
        """Convert a raw dict from LLM response to a CaseStudy object."""
        now = datetime.now(timezone.utc)

        return CaseStudy(
            case_study_id=str(uuid.uuid4()),
            source_type=source_type,
            source_id=source_id,
            domain=domain,
            grounding_quote=raw.get("grounding_quote", ""),
            context_text=raw.get("context_text"),
            use_case_title=raw.get("use_case_title", "Untitled"),
            use_case_summary=raw.get("use_case_summary", ""),
            company=raw.get("company", ""),
            industry=raw.get("industry", ""),
            technology_stack=self._ensure_list(raw.get("technology_stack")),
            department=raw.get("department"),
            implementation_detail=raw.get("implementation_detail"),
            teams_impacted=self._ensure_list(raw.get("teams_impacted")),
            scale=raw.get("scale"),
            timeline=raw.get("timeline"),
            readiness_level=raw.get("readiness_level", "announced"),
            outcome_metric=raw.get("outcome_metric"),
            outcome_type=raw.get("outcome_type"),
            outcome_quantified=bool(raw.get("outcome_quantified", False)),
            speaker=raw.get("speaker"),
            speaker_role=raw.get("speaker_role"),
            speaker_company=raw.get("speaker_company"),
            companies_mentioned=self._ensure_list(raw.get("companies_mentioned")),
            technologies_mentioned=self._ensure_list(raw.get("technologies_mentioned")),
            people_mentioned=self._ensure_list(raw.get("people_mentioned")),
            competitors_mentioned=self._ensure_list(raw.get("competitors_mentioned")),
            # Quantum-specific
            qubit_type=raw.get("qubit_type"),
            gate_fidelity=raw.get("gate_fidelity"),
            commercial_viability=raw.get("commercial_viability"),
            scientific_significance=raw.get("scientific_significance"),
            # AI-specific
            ai_model_used=raw.get("ai_model_used"),
            roi_metric=raw.get("roi_metric"),
            deployment_type=raw.get("deployment_type"),
            # Quality
            relevance_score=float(raw.get("relevance_score", 0.5)),
            confidence=float(raw.get("confidence", 0.8)),
            # Metadata — store any extra fields from context
            metadata={
                k: v for k, v in context.items()
                if k not in ("tier_guidance",)  # Don't store prompt text
            },
            # Audit
            extracted_at=now,
            extraction_model=self.model,
            extraction_confidence=float(raw.get("confidence", 0.8)),
        )

    @staticmethod
    def _ensure_list(val) -> List[str]:
        """Ensure a value is a list of strings."""
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x) for x in val if x]
        if isinstance(val, str):
            return [x.strip() for x in val.split(",") if x.strip()]
        return []
