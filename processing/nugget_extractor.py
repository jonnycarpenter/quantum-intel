"""
SEC Nugget Extractor
====================

LLM-based extraction of key nuggets from SEC filings.
Uses Claude Sonnet for high-quality, structured nugget extraction with
filing context, classification, and entity extraction.
"""

import json
import os
import re
from typing import Optional, List
from datetime import datetime, timezone

from models.sec_filing import (
    SecFiling,
    SecNugget,
    NuggetExtractionResult,
    FilingType,
    FilingSection,
    NuggetType,
    SignalStrength,
)
from config.settings import SecConfig
from config.earnings_tickers import CORE_TICKERS as QUANTUM_CORE_TICKERS
from config.ai_earnings_tickers import AI_CORE_TICKERS
from utils.llm_client import get_resilient_async_client
from utils.logger import get_logger

logger = get_logger(__name__)


NUGGET_EXTRACTION_PROMPT = """You are an expert SEC filing analyst specializing in the quantum computing industry.

## QUANTUM COMPUTING BUSINESS CONTEXT

The quantum computing industry spans several technology platforms and market segments:

**Hardware Platforms**: Trapped ion (IonQ), superconducting (IBM, Google, Rigetti), quantum annealing (D-Wave), photonic (PsiQuantum, Xanadu), neutral atom (QuEra), topological (Microsoft)

**Key Competitive Dimensions**:
- Qubit count and quality (gate fidelity, coherence times)
- Quantum error correction progress (#AQ, logical qubits)
- Quantum volume and circuit depth benchmarks
- Cloud access models (QCaaS, hybrid classical-quantum)
- Government and defense contracts (DOE, DARPA, NSA, DOD)
- Enterprise customer wins and revenue per customer
- Patent portfolio breadth

**Market Segments**: Quantum computing hardware, quantum software/algorithms, quantum networking/communications, quantum sensing, post-quantum cryptography (PQC), quantum-safe security

**Revenue Drivers**: Cloud quantum computing access (QCaaS), on-premise systems, government R&D contracts, consulting/professional services, quantum-safe encryption products

**Critical Risks**: Technology obsolescence (platform risk), path to fault tolerance, cash burn rate, dilution, ITAR/export controls on quantum tech, customer concentration

## NUGGET CATEGORIES (alphabetical)

Extract nuggets in these high-value categories:

1. **Competitive Disclosures** (HIGHEST VALUE): Named competitors in legally mandated disclosures. SEC filings MUST disclose material competitive threats — these are verified, legal statements about competitive positioning.
2. **Forward Guidance**: Quantum roadmap milestones, revenue targets, backlog, customer pipeline, go-to-market plans, capacity expansion.
3. **Government & Defense**: DOE/DARPA/DOD contracts, classified programs (mentioned obliquely), ITAR compliance, export controls.
4. **Material Changes** (especially 8-K): Leadership changes, M&A activity, major partnerships, restructuring, going-concern language.
5. **Regulatory & Export Risk**: Export controls on quantum technology, ITAR, EAR, CFIUS review, NIST PQC standards compliance.
6. **Risk Admissions**: Going-concern warnings, cash runway, technology risk, platform obsolescence, customer concentration, dilution warnings.
7. **Technology Investment**: R&D spending, qubit roadmap progress, error correction milestones, new system benchmarks, patent filings.

## EXTRACTION RULES

1. Nuggets MUST be verbatim excerpts or very close paraphrases — do NOT editorialize
2. Rate relevance 0.0–1.0 (1.0 = directly about quantum computing technology or business)
3. Flag first-time disclosures as is_new_disclosure=true — these are the most valuable
4. Flag actionable items as is_actionable=true (investment decisions should flow from this)
5. For {tier} tickers, {tier_guidance}
6. Prioritize "buried" disclosures — important facts deep in risk factors or footnotes
7. Note signal strength: "strong" = explicit disclosure, "standard" = routine language, "weak" = vague/hedged, "noise" = boilerplate

## FILING METADATA

TICKER: {ticker}
COMPANY: {company_name}
FILING TYPE: {filing_type}
FISCAL PERIOD: {fiscal_period}
FILING DATE: {filing_date}

## OUTPUT FORMAT

Respond with ONLY a JSON array of nugget objects:
```json
[
  {{
    "nugget_text": "verbatim excerpt or close paraphrase from filing",
    "context_text": "surrounding paragraph providing context",
    "section": "risk_factors|business_overview|mda|financial_statements|notes|legal_proceedings|controls|exhibits|signatures|cover_page|unknown",
    "nugget_type": "competitive_disclosure|risk_admission|technology_investment|ip_patent|regulatory_compliance|forward_guidance|material_change|quantum_readiness",
    "themes": ["error_correction", "government_contracts"],
    "signal_strength": "strong|standard|weak|noise",
    "companies_mentioned": ["IBM", "Google"],
    "technologies_mentioned": ["trapped ion", "error correction"],
    "competitors_named": ["IBM Quantum"],
    "regulators_mentioned": ["DOE"],
    "risk_level": "critical|high|medium|low",
    "is_new_disclosure": true,
    "is_actionable": true,
    "actionability_reason": "First disclosure of logical qubit milestone — validates roadmap",
    "relevance_score": 0.95
  }}
]
```

Extract 5–15 of the most significant nuggets. Prioritize competitive disclosures, risk admissions, and technology milestones over boilerplate language."""


AI_NUGGET_EXTRACTION_PROMPT = """You are an expert SEC filing analyst specializing in the artificial intelligence industry.

## AI INDUSTRY BUSINESS CONTEXT

The AI industry spans several layers and market segments:

**Compute & Infrastructure**: GPU/accelerator design (NVIDIA, AMD, Broadcom custom XPUs), AI chip manufacturing (TSMC), AI server systems (Super Micro, Dell), AI cloud infrastructure (CoreWeave, Lambda), data center power & cooling (Vertiv, Eaton)

**Foundation Model Providers**: OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Cohere, xAI — competing on model capabilities, safety, and enterprise readiness

**AI Platforms & Applications**: Enterprise AI (Palantir, C3.ai, Snowflake Cortex), AI automation (UiPath, ServiceNow Now Assist), conversational AI (SoundHound), AI-powered ad tech (AppLovin), decision intelligence (BigBear.ai)

**Key Competitive Dimensions**:
- GPU/accelerator performance (FLOPS, memory bandwidth, interconnect)
- Model capabilities (benchmarks, context windows, multimodality, reasoning)
- AI revenue and monetization metrics (AI ARR, AI bookings, AI inference volume)
- Cloud AI market share (AWS vs Azure vs GCP)
- Enterprise customer wins and deployment scale
- AI inference cost efficiency and total cost of ownership
- AI safety and responsible AI practices
- Custom silicon programs (Google TPU, Amazon Trainium, Microsoft Maia)

**Revenue Drivers**: AI cloud services (inference API, fine-tuning), AI hardware (GPUs, AI servers, networking), AI software platforms (enterprise licenses, consumption-based), AI-powered features within existing products (Copilot, Gemini, Meta AI)

**Critical Risks**: GPU supply constraints, customer concentration risk, AI regulation (EU AI Act, US executive orders), data center power availability, model commoditization, open-source disruption, AI safety incidents, massive capital expenditure requirements

## NUGGET CATEGORIES (alphabetical)

Extract nuggets in these high-value categories:

1. **AI Capex & Infrastructure** (HIGHEST VALUE): GPU spend, data center build-out, power procurement, custom silicon investments, capacity commitments.
2. **AI Revenue & Monetization**: AI-specific revenue breakdowns, AI ARR, inference volume metrics, AI product adoption rates, consumption-based growth.
3. **Competitive Disclosures**: Named competitors in legally mandated disclosures. SEC filings MUST disclose material competitive threats — these are verified, legal statements.
4. **Forward Guidance & Roadmap**: AI product roadmap, model launches, performance targets, capacity expansion timelines, customer pipeline.
5. **Model & Technology Milestones**: Benchmark results, new model releases, inference speed improvements, multimodal capabilities, reasoning advances.
6. **Regulatory & Compliance Risk**: AI regulation (EU AI Act, US state laws), content moderation liability, copyright/IP lawsuits, responsible AI governance, export controls on AI chips.
7. **Risk Admissions**: AI investment uncertainty, competition from open-source, customer concentration, technology commoditization risk, talent attrition, going-concern warnings.
8. **Strategic Partnerships & M&A**: AI partnerships, custom silicon deals, AI startup acquisitions, joint ventures, licensing agreements.

## EXTRACTION RULES

1. Nuggets MUST be verbatim excerpts or very close paraphrases — do NOT editorialize
2. Rate relevance 0.0–1.0 (1.0 = directly about AI technology, AI revenue, or AI competitive positioning)
3. Flag first-time disclosures as is_new_disclosure=true — these are the most valuable
4. Flag actionable items as is_actionable=true (investment decisions should flow from this)
5. For {tier} tickers, {tier_guidance}
6. Prioritize "buried" disclosures — important facts deep in risk factors or footnotes
7. Note signal strength: "strong" = explicit disclosure, "standard" = routine language, "weak" = vague/hedged, "noise" = boilerplate

## FILING METADATA

TICKER: {ticker}
COMPANY: {company_name}
FILING TYPE: {filing_type}
FISCAL PERIOD: {fiscal_period}
FILING DATE: {filing_date}

## OUTPUT FORMAT

Respond with ONLY a JSON array of nugget objects:
```json
[
  {{
    "nugget_text": "verbatim excerpt or close paraphrase from filing",
    "context_text": "surrounding paragraph providing context",
    "section": "risk_factors|business_overview|mda|financial_statements|notes|legal_proceedings|controls|exhibits|signatures|cover_page|unknown",
    "nugget_type": "competitive_disclosure|risk_admission|technology_investment|ip_patent|regulatory_compliance|forward_guidance|material_change|quantum_readiness",
    "themes": ["ai_infrastructure", "gpu_supply"],
    "signal_strength": "strong|standard|weak|noise",
    "companies_mentioned": ["NVIDIA", "OpenAI"],
    "technologies_mentioned": ["H100", "custom ASIC", "inference optimization"],
    "competitors_named": ["AWS", "Azure"],
    "regulators_mentioned": ["EU", "FTC"],
    "risk_level": "critical|high|medium|low",
    "is_new_disclosure": true,
    "is_actionable": true,
    "actionability_reason": "First disclosure of AI-specific revenue breakdown — validates AI monetization trajectory",
    "relevance_score": 0.95
  }}
]
```

Extract 5–15 of the most significant nuggets. Prioritize AI capex disclosures, competitive dynamics, and revenue/monetization metrics over boilerplate language."""


# Map domain to prompt template
DOMAIN_NUGGET_PROMPTS = {
    "quantum": NUGGET_EXTRACTION_PROMPT,
    "ai": AI_NUGGET_EXTRACTION_PROMPT,
}

# Map domain to core tickers list
DOMAIN_CORE_TICKERS = {
    "quantum": QUANTUM_CORE_TICKERS,
    "ai": AI_CORE_TICKERS,
}


class NuggetExtractor:
    """
    LLM-based extractor for SEC filing nuggets.

    Uses Claude Sonnet to extract key disclosures with filing context,
    classification, and entity extraction.
    """

    def __init__(self, config: Optional[SecConfig] = None):
        self.config = config or SecConfig()

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("[NUGGET_EXTRACTOR] No ANTHROPIC_API_KEY set")

        self.client = get_resilient_async_client(
            anthropic_api_key=api_key, timeout=180.0
        )
        self.model = self.config.extraction_model
        self.temperature = self.config.extraction_temperature
        self.max_tokens = self.config.extraction_max_tokens

    async def extract_nuggets(self, filing: SecFiling, domain: str = "quantum") -> NuggetExtractionResult:
        """
        Extract nuggets from an SEC filing.

        Args:
            filing: SecFiling with raw_content populated
            domain: "quantum" or "ai" — selects extraction prompt and core ticker list

        Returns:
            NuggetExtractionResult with extracted nuggets
        """
        logger.info(
            f"[NUGGET_EXTRACTOR] Extracting from {filing.unique_key} "
            f"(domain={domain}, {filing.char_count:,} chars)"
        )

        # Select domain-specific prompt and core tickers
        prompt_template = DOMAIN_NUGGET_PROMPTS.get(domain, NUGGET_EXTRACTION_PROMPT)
        core_tickers = DOMAIN_CORE_TICKERS.get(domain, QUANTUM_CORE_TICKERS)

        # Determine tier-specific guidance
        is_core = filing.ticker in core_tickers
        tier = "core" if is_core else "secondary"
        domain_label = "AI" if domain == "ai" else "quantum"
        tier_guidance = (
            f"extract ALL {domain_label}-relevant nuggets — this is a core {domain_label} company"
            if is_core
            else f"only extract nuggets specifically mentioning {domain_label} technology, "
            f"{domain_label}-related initiatives, or {domain_label} competitive positioning"
        )

        # Use sections if available (more targeted), otherwise full content
        content = ""
        if filing.sections:
            for section_name, section_text in filing.sections.items():
                content += f"\n\n--- {section_name.upper()} ---\n\n{section_text}"
        else:
            content = filing.raw_content or ""

        # Truncate if needed
        max_chars = self.config.max_filing_chars
        if len(content) > max_chars:
            logger.info(
                f"[NUGGET_EXTRACTOR] Truncating content from {len(content):,} "
                f"to {max_chars:,} chars"
            )
            content = content[:max_chars]

        fiscal_period = f"FY{filing.fiscal_year}"
        if filing.fiscal_quarter:
            fiscal_period += f" Q{filing.fiscal_quarter}"

        prompt = prompt_template.format(
            ticker=filing.ticker,
            company_name=filing.company_name,
            filing_type=filing.filing_type,
            fiscal_period=fiscal_period,
            filing_date=(
                filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else "N/A"
            ),
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
                        "content": f"FILING CONTENT:\n\n{content}",
                    }
                ],
                temperature=self.temperature,
            )

            response_text = self.client.extract_text(response)
            nuggets = self._parse_nuggets(response_text, filing, domain=domain)

            result = NuggetExtractionResult(
                filing_id=filing.filing_id,
                ticker=filing.ticker,
                company_name=filing.company_name,
                nuggets=nuggets,
                total_nuggets=len(nuggets),
                extraction_model=self.model,
            )

            logger.info(
                f"[NUGGET_EXTRACTOR] Extracted {len(nuggets)} nuggets from "
                f"{filing.unique_key}"
            )
            return result

        except Exception as e:
            logger.error(
                f"[NUGGET_EXTRACTOR] Extraction error for {filing.unique_key}: {e}"
            )
            return NuggetExtractionResult(
                filing_id=filing.filing_id,
                ticker=filing.ticker,
                company_name=filing.company_name,
                nuggets=[],
                total_nuggets=0,
                extraction_model=self.model,
            )

    def _parse_nuggets(
        self, text: str, filing: SecFiling, domain: str = "quantum"
    ) -> List[SecNugget]:
        """Parse LLM response into SecNugget objects."""
        parsed = self._parse_json_array(text)
        if not parsed:
            return []

        nuggets: List[SecNugget] = []
        for i, item in enumerate(parsed):
            try:
                nugget = SecNugget(
                    filing_id=filing.filing_id,
                    nugget_text=item.get("nugget_text", ""),
                    context_text=item.get("context_text", ""),
                    filing_type=filing.filing_type,
                    section=self._parse_enum(
                        FilingSection, item.get("section", "unknown")
                    ),
                    nugget_type=self._parse_enum(
                        NuggetType, item.get("nugget_type", "risk_admission")
                    ),
                    themes=item.get("themes", []),
                    signal_strength=self._parse_enum(
                        SignalStrength, item.get("signal_strength", "standard")
                    ),
                    companies_mentioned=item.get("companies_mentioned", []),
                    technologies_mentioned=item.get("technologies_mentioned", []),
                    competitors_named=item.get("competitors_named", []),
                    regulators_mentioned=item.get("regulators_mentioned", []),
                    risk_level=item.get("risk_level", "medium"),
                    is_new_disclosure=bool(item.get("is_new_disclosure", False)),
                    is_actionable=bool(item.get("is_actionable", False)),
                    actionability_reason=item.get("actionability_reason", ""),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    ticker=filing.ticker,
                    company_name=filing.company_name,
                    cik=filing.cik,
                    fiscal_year=filing.fiscal_year,
                    fiscal_quarter=filing.fiscal_quarter,
                    filing_date=filing.filing_date,
                    accession_number=filing.accession_number,
                    extraction_model=self.model,
                    domain=domain,
                )
                nuggets.append(nugget)
            except Exception as e:
                logger.warning(f"[NUGGET_EXTRACTOR] Parse error on nugget #{i}: {e}")
                continue

        return nuggets

    def _parse_enum(self, enum_class, value):
        """Safely parse an enum value."""
        try:
            return enum_class(value)
        except (ValueError, KeyError):
            return list(enum_class)[0]

    def _parse_json_array(self, text: str) -> Optional[List[dict]]:
        """Parse a JSON array from LLM response, with truncated JSON recovery."""
        # Try direct parse
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Try code fence extraction
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Try to find any JSON array in the text
        bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
        if bracket_match:
            try:
                data = json.loads(bracket_match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Truncated JSON recovery: find the last complete object and close the array
        # This handles cases where max_tokens cuts off the response mid-JSON
        bracket_start = text.find("[")
        if bracket_start >= 0:
            json_text = text[bracket_start:]
            # Find the last complete "}" that closes a nugget object
            last_brace = json_text.rfind("}")
            if last_brace > 0:
                truncated = json_text[: last_brace + 1] + "]"
                try:
                    data = json.loads(truncated)
                    if isinstance(data, list):
                        logger.info(
                            f"[NUGGET_EXTRACTOR] Recovered {len(data)} nuggets "
                            f"from truncated JSON"
                        )
                        return data
                except json.JSONDecodeError:
                    pass

        logger.warning(
            f"[NUGGET_EXTRACTOR] Failed to parse JSON from response "
            f"(length={len(text)}, preview={text[:200]})"
        )
        return None

