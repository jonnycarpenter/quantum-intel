"""
Weekly Briefing Pipeline
========================

Two-agent pipeline for generating weekly intelligence briefings.

  Research Agent (Sonnet) → structured observations mapped to priorities
  Briefing Agent (Opus)   → narrative synthesis with voice enrichment & citations

Usage:
    pipeline = WeeklyBriefingPipeline(config, storage)
    briefing = await pipeline.generate(domain="quantum")
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

from config.settings import WeeklyBriefingConfig
from config.strategic_priorities import (
    DOMAIN_PRIORITIES,
    format_priorities_block,
)
from config.prompts import RESEARCH_AGENT_PROMPTS, BRIEFING_AGENT_PROMPTS
from config.tickers import ALL_TICKERS
from config.earnings_tickers import ALL_EARNINGS_TICKERS
from models.weekly_briefing import (
    WeeklyBriefing, BriefingSection, VoiceQuote, Citation,
    MarketMover, ResearchPaper, PreBrief, PreBriefObservation,
)
from storage.base import StorageBackend, ClassifiedArticle
from utils.llm_client import get_resilient_async_client, calculate_cost
from utils.logger import get_logger

logger = get_logger(__name__)

# Priority levels to include (medium and above)
INCLUDED_PRIORITIES = {"critical", "high", "medium"}


class WeeklyBriefingPipeline:
    """Orchestrates the 2-agent weekly briefing pipeline."""

    def __init__(
        self,
        config: Optional[WeeklyBriefingConfig] = None,
        storage: Optional[StorageBackend] = None,
    ):
        self.config = config or WeeklyBriefingConfig()
        self.storage = storage

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.client = get_resilient_async_client(api_key, timeout=300.0)
        self.total_cost = 0.0

    async def generate(self, domain: str = "quantum", days: Optional[int] = None) -> WeeklyBriefing:
        """Full pipeline: fetch -> research agent -> voice enrichment -> briefing agent -> assemble."""
        lookback = days or self.config.lookback_days
        logger.info(f"[WEEKLY-BRIEFING] Starting {domain} briefing (lookback={lookback}d)")

        # Step 1: Fetch articles
        articles = await self._fetch_articles(domain, lookback)
        logger.info(f"[WEEKLY-BRIEFING] Fetched {len(articles)} articles (medium+ priority)")

        if not articles:
            logger.warning(f"[WEEKLY-BRIEFING] No articles found for {domain}")
            return self._empty_briefing(domain)

        # Build article lookup for citation resolution
        self._article_lookup: Dict[str, ClassifiedArticle] = {a.id: a for a in articles}

        # Step 2: Research Agent — produce pre-brief
        pre_brief = await self._run_research_agent(articles, domain)
        logger.info(
            f"[RESEARCH-AGENT] Produced {len(pre_brief.observations)} observations "
            f"from {pre_brief.article_count} articles in {pre_brief.batch_count} batches"
        )

        # Step 3: Fetch voice enrichment
        voice_data = await self._fetch_voice_enrichment(pre_brief, domain)

        # Step 4: Fetch market mover candidates
        market_candidates = await self._fetch_market_movers()

        # Step 5: Fetch research papers
        papers = await self._fetch_papers(lookback)

        # Step 6: Briefing Agent — synthesize
        briefing = await self._run_briefing_agent(
            pre_brief, voice_data, market_candidates, papers, domain
        )

        briefing.articles_analyzed = len(articles)
        briefing.generation_cost_usd = self.total_cost
        briefing.pre_brief_id = pre_brief.pre_brief_id

        logger.info(
            f"[WEEKLY-BRIEFING] Complete: {briefing.sections_active}/{briefing.sections_total} "
            f"sections active, cost=${self.total_cost:.4f}"
        )

        return briefing

    # =========================================================================
    # Step 1: Fetch Articles
    # =========================================================================

    async def _fetch_articles(self, domain: str, days: int) -> List[ClassifiedArticle]:
        """Fetch recent articles filtered to medium/high/critical priority."""
        hours = days * 24
        all_articles = await self.storage.get_recent_articles(
            hours=hours, limit=self.config.max_articles, domain=domain
        )
        # Filter to medium+ priority
        filtered = [
            a for a in all_articles
            if a.priority in INCLUDED_PRIORITIES
        ]
        return filtered

    # =========================================================================
    # Step 2: Research Agent
    # =========================================================================

    async def _run_research_agent(self, articles: List[ClassifiedArticle], domain: str) -> PreBrief:
        """Batch-process articles through the Research Agent (Sonnet)."""
        batch_size = self.config.research_batch_size
        batches = [articles[i:i + batch_size] for i in range(0, len(articles), batch_size)]

        all_observations: List[PreBriefObservation] = []

        for i, batch in enumerate(batches):
            logger.info(f"[RESEARCH-AGENT] Processing batch {i + 1}/{len(batches)} ({len(batch)} articles)")
            observations = await self._analyze_batch(batch, i + 1, len(batches), domain)
            all_observations.extend(observations)

        # Determine period
        dates = [a.published_at for a in articles if a.published_at]
        period_start = min(dates) if dates else None
        period_end = max(dates) if dates else None

        return PreBrief(
            domain=domain,
            observations=all_observations,
            article_count=len(articles),
            period_start=period_start,
            period_end=period_end,
            batch_count=len(batches),
        )

    async def _analyze_batch(
        self, batch: List[ClassifiedArticle], batch_num: int, total_batches: int, domain: str
    ) -> List[PreBriefObservation]:
        """Analyze a single batch of articles with the Research Agent."""
        # Format articles for the prompt
        articles_text = self._format_articles_for_research(batch)

        # Build system prompt with priorities
        priorities_block = format_priorities_block(domain)
        system_template = RESEARCH_AGENT_PROMPTS.get(domain, RESEARCH_AGENT_PROMPTS["quantum"])
        system_prompt = system_template.format(priorities_block=priorities_block)

        user_message = f"BATCH {batch_num} of {total_batches}\n\nARTICLES:\n\n{articles_text}"

        try:
            response = await self.client.messages_create(
                model=self.config.research_model,
                max_tokens=self.config.research_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=self.config.research_temperature,
            )

            # Track cost
            if hasattr(response, "usage"):
                cost = calculate_cost(
                    self.config.research_model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                self.total_cost += cost

            text = self.client.extract_text(response)
            parsed = self._parse_json_robust(text)

            if not parsed or not isinstance(parsed, list):
                logger.warning(f"[RESEARCH-AGENT] Batch {batch_num}: failed to parse JSON")
                return []

            observations = []
            for item in parsed:
                obs = PreBriefObservation(
                    topic=item.get("topic", ""),
                    priority_tag=item.get("priority_tag", "unmatched"),
                    signal_type=item.get("signal_type", "development"),
                    companies=item.get("companies", []),
                    technologies=item.get("technologies", []),
                    article_ids=item.get("article_ids", []),
                    summary=item.get("summary", ""),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                )
                observations.append(obs)

            logger.info(f"[RESEARCH-AGENT] Batch {batch_num}: {len(observations)} observations")
            return observations

        except Exception as e:
            logger.error(f"[RESEARCH-AGENT] Batch {batch_num} error: {e}")
            return []

    def _format_articles_for_research(self, articles: List[ClassifiedArticle]) -> str:
        """Format articles as structured text for the Research Agent."""
        lines = []
        for a in articles:
            pub = a.published_at.strftime("%Y-%m-%d") if a.published_at else "unknown"
            companies = ", ".join(a.companies_mentioned[:5]) if a.companies_mentioned else "none"
            techs = ", ".join(a.technologies_mentioned[:5]) if a.technologies_mentioned else "none"
            summary = (a.ai_summary or a.summary or "")[:300]
            lines.append(
                f"---\n"
                f"ID: {a.id}\n"
                f"Title: {a.title}\n"
                f"Source: {a.source_name} | Published: {pub}\n"
                f"Category: {a.primary_category} | Priority: {a.priority}\n"
                f"Companies: {companies}\n"
                f"Technologies: {techs}\n"
                f"Summary: {summary}\n"
            )
        return "\n".join(lines)

    # =========================================================================
    # Step 3: Voice Enrichment
    # =========================================================================

    async def _fetch_voice_enrichment(self, pre_brief: PreBrief, domain: str) -> Dict[str, Any]:
        """Fetch earnings quotes, SEC nuggets, and podcast quotes relevant to pre-brief topics."""
        enrichment = {"earnings_quotes": [], "sec_nuggets": [], "podcast_quotes": []}

        # Extract unique companies/tickers from observations
        mentioned_companies = set()
        keywords = set()
        for obs in pre_brief.observations:
            for c in obs.companies:
                mentioned_companies.add(c)
            keywords.add(obs.topic)
            for t in obs.technologies:
                keywords.add(t)

        # Map company names to tickers
        from config.earnings_tickers import EARNINGS_COMPANIES
        ticker_map = {c["company"].lower(): c["ticker"] for c in EARNINGS_COMPANIES}
        relevant_tickers = set()
        for company in mentioned_companies:
            company_lower = company.lower()
            for name, ticker in ticker_map.items():
                if company_lower in name or name in company_lower:
                    relevant_tickers.add(ticker)

        # Also include all tracked tickers for completeness
        for ticker in ALL_EARNINGS_TICKERS[:7]:  # Core tickers
            relevant_tickers.add(ticker)

        # Fetch earnings quotes
        for ticker in relevant_tickers:
            try:
                quotes = await self.storage.get_quotes_by_ticker(
                    ticker, limit=self.config.max_quotes_per_ticker
                )
                for q in quotes:
                    enrichment["earnings_quotes"].append({
                        "text": q.quote_text,
                        "speaker": q.speaker_name,
                        "role": q.speaker_role.value if hasattr(q.speaker_role, "value") else q.speaker_role,
                        "company": q.company_name,
                        "ticker": q.ticker,
                        "quarter": f"Q{q.quarter} {q.year}",
                        "quote_type": q.quote_type.value if hasattr(q.quote_type, "value") else q.quote_type,
                        "relevance_score": q.relevance_score,
                    })
            except Exception as e:
                logger.warning(f"[WEEKLY-BRIEFING] Error fetching quotes for {ticker}: {e}")

        # Fetch SEC nuggets
        for ticker in relevant_tickers:
            try:
                nuggets = await self.storage.get_nuggets_by_ticker(
                    ticker, limit=self.config.max_nuggets_per_ticker
                )
                for n in nuggets:
                    enrichment["sec_nuggets"].append({
                        "text": n.nugget_text,
                        "company": n.company_name,
                        "ticker": n.ticker,
                        "filing_type": n.filing_type,
                        "fiscal_year": n.fiscal_year,
                        "nugget_type": n.nugget_type.value if hasattr(n.nugget_type, "value") else str(n.nugget_type),
                        "is_new_disclosure": n.is_new_disclosure,
                        "relevance_score": n.relevance_score,
                    })
            except Exception as e:
                logger.warning(f"[WEEKLY-BRIEFING] Error fetching nuggets for {ticker}: {e}")

        # Fetch podcast quotes (keyword search)
        search_terms = list(keywords)[:5]  # Top 5 keywords
        for term in search_terms:
            try:
                quotes = await self.storage.search_podcast_quotes(
                    term, limit=self.config.max_podcast_quotes
                )
                for pq in quotes:
                    enrichment["podcast_quotes"].append({
                        "text": pq.quote_text,
                        "speaker": pq.speaker_name,
                        "role": pq.speaker_role,
                        "company": pq.speaker_company or "",
                        "title": pq.speaker_title or "",
                        "podcast": pq.podcast_name,
                        "episode": pq.episode_title,
                        "published_at": pq.published_at if isinstance(pq.published_at, str) else "",
                        "relevance_score": pq.relevance_score,
                    })
            except Exception as e:
                logger.warning(f"[WEEKLY-BRIEFING] Error searching podcast quotes for '{term}': {e}")

        # Deduplicate podcast quotes by text
        seen_texts = set()
        deduped_podcast = []
        for pq in enrichment["podcast_quotes"]:
            text_key = pq["text"][:100]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduped_podcast.append(pq)
        enrichment["podcast_quotes"] = deduped_podcast[:self.config.max_podcast_quotes]

        logger.info(
            f"[WEEKLY-BRIEFING] Voice enrichment: "
            f"{len(enrichment['earnings_quotes'])} earnings quotes, "
            f"{len(enrichment['sec_nuggets'])} SEC nuggets, "
            f"{len(enrichment['podcast_quotes'])} podcast quotes"
        )

        return enrichment

    # =========================================================================
    # Step 4: Market Movers
    # =========================================================================

    async def _fetch_market_movers(self) -> List[Dict[str, Any]]:
        """Find tickers with >threshold% weekly change."""
        movers = []
        for ticker in ALL_TICKERS:
            try:
                snapshots = await self.storage.get_stock_data(
                    ticker, days=self.config.stock_lookback_days
                )
                if len(snapshots) < 2:
                    continue

                # snapshots are DESC by date — [0] is latest, [-1] is oldest
                latest = snapshots[0]
                oldest = snapshots[-1]

                if oldest.close and oldest.close > 0 and latest.close:
                    change_pct = ((latest.close - oldest.close) / oldest.close) * 100
                    if abs(change_pct) >= self.config.market_mover_threshold_pct:
                        movers.append({
                            "ticker": ticker,
                            "company_name": latest.ticker,  # Will be enriched by briefing agent
                            "close": latest.close,
                            "change_pct": round(change_pct, 1),
                        })
            except Exception as e:
                logger.warning(f"[WEEKLY-BRIEFING] Error fetching stock data for {ticker}: {e}")

        # Sort by absolute change descending
        movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
        logger.info(f"[WEEKLY-BRIEFING] Market movers: {len(movers)} tickers with >{self.config.market_mover_threshold_pct}% change")
        return movers

    # =========================================================================
    # Step 5: Fetch Papers
    # =========================================================================

    async def _fetch_papers(self, days: int) -> List[Dict[str, Any]]:
        """Fetch recent ArXiv papers."""
        papers = await self.storage.get_recent_papers(days=days, limit=10)
        result = []
        for p in papers:
            result.append({
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors[:3] if p.authors else [],
                "abstract": (p.abstract or "")[:500],
                "commercial_readiness": p.commercial_readiness,
                "relevance_score": p.relevance_score,
                "significance_summary": p.significance_summary or "",
                "abs_url": f"https://arxiv.org/abs/{p.arxiv_id}",
            })
        logger.info(f"[WEEKLY-BRIEFING] Paper candidates: {len(result)}")
        return result

    # =========================================================================
    # Step 6: Briefing Agent
    # =========================================================================

    async def _run_briefing_agent(
        self,
        pre_brief: PreBrief,
        voice_data: Dict[str, Any],
        market_candidates: List[Dict[str, Any]],
        papers: List[Dict[str, Any]],
        domain: str,
    ) -> WeeklyBriefing:
        """Synthesize observations into a narrative briefing with the Briefing Agent (Opus)."""

        # Build the comprehensive user message
        user_message = self._build_briefing_prompt(
            pre_brief, voice_data, market_candidates, papers, domain
        )

        # Build system prompt
        priorities_block = format_priorities_block(domain)
        system_template = BRIEFING_AGENT_PROMPTS.get(domain, BRIEFING_AGENT_PROMPTS["quantum"])
        system_prompt = system_template.format(priorities_block=priorities_block)

        logger.info(f"[BRIEFING-AGENT] Sending to {self.config.briefing_model} ({len(user_message)} chars)")

        try:
            response = await self.client.messages_create(
                model=self.config.briefing_model,
                max_tokens=self.config.briefing_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=self.config.briefing_temperature,
            )

            # Track cost
            if hasattr(response, "usage"):
                cost = calculate_cost(
                    self.config.briefing_model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                self.total_cost += cost
                logger.info(f"[BRIEFING-AGENT] Opus cost: ${cost:.4f}")

            text = self.client.extract_text(response)
            parsed = self._parse_json_robust(text)

            if not parsed or not isinstance(parsed, dict):
                logger.error("[BRIEFING-AGENT] Failed to parse briefing JSON")
                return self._empty_briefing(domain)

            return self._assemble_briefing(parsed, domain)

        except Exception as e:
            logger.error(f"[BRIEFING-AGENT] Error: {e}")
            return self._empty_briefing(domain)

    def _build_briefing_prompt(
        self,
        pre_brief: PreBrief,
        voice_data: Dict[str, Any],
        market_candidates: List[Dict[str, Any]],
        papers: List[Dict[str, Any]],
        domain: str,
    ) -> str:
        """Assemble the comprehensive user message for the Briefing Agent."""
        parts = []

        # Section 1: Pre-brief observations grouped by priority
        parts.append("=" * 60)
        parts.append("PRE-BRIEF OBSERVATIONS (from Research Agent)")
        parts.append("=" * 60)

        priorities = DOMAIN_PRIORITIES.get(domain, [])
        priority_tags = [p.tag for p in priorities] + ["market", "research", "unmatched"]

        for tag in priority_tags:
            obs_for_tag = [o for o in pre_brief.observations if o.priority_tag == tag]
            if not obs_for_tag:
                continue
            label = next((p.label for p in priorities if p.tag == tag), tag.upper())
            parts.append(f"\n--- {tag}: {label} ({len(obs_for_tag)} observations) ---")
            for obs in obs_for_tag:
                parts.append(f"\nTopic: {obs.topic}")
                parts.append(f"Signal: {obs.signal_type} | Relevance: {obs.relevance_score}")
                parts.append(f"Companies: {', '.join(obs.companies)}")
                parts.append(f"Article IDs: {', '.join(obs.article_ids)}")
                parts.append(f"Summary: {obs.summary}")

        # Section 2: Voice enrichment
        parts.append("\n" + "=" * 60)
        parts.append("VOICE ENRICHMENT DATA")
        parts.append("=" * 60)

        if voice_data.get("earnings_quotes"):
            parts.append(f"\n--- Earnings Quotes ({len(voice_data['earnings_quotes'])}) ---")
            for eq in voice_data["earnings_quotes"]:
                parts.append(
                    f'\n"{eq["text"]}"\n'
                    f'  — {eq["speaker"]}, {eq["role"]} at {eq["company"]} ({eq["quarter"]})\n'
                    f'  Type: {eq["quote_type"]} | Relevance: {eq["relevance_score"]}'
                )

        if voice_data.get("sec_nuggets"):
            parts.append(f"\n--- SEC Nuggets ({len(voice_data['sec_nuggets'])}) ---")
            for sn in voice_data["sec_nuggets"]:
                parts.append(
                    f'\n"{sn["text"]}"\n'
                    f'  — {sn["company"]} {sn["filing_type"]} FY{sn["fiscal_year"]}\n'
                    f'  Type: {sn["nugget_type"]} | New disclosure: {sn["is_new_disclosure"]}'
                )

        if voice_data.get("podcast_quotes"):
            parts.append(f"\n--- Podcast Quotes ({len(voice_data['podcast_quotes'])}) ---")
            for pq in voice_data["podcast_quotes"]:
                parts.append(
                    f'\n"{pq["text"]}"\n'
                    f'  — {pq["speaker"]}, {pq.get("title", "")} at {pq.get("company", "")}\n'
                    f'  Podcast: {pq["podcast"]} — {pq["episode"]}\n'
                    f'  Relevance: {pq["relevance_score"]}'
                )

        # Section 3: Market mover candidates
        if market_candidates:
            parts.append("\n" + "=" * 60)
            parts.append("MARKET MOVER CANDIDATES")
            parts.append("=" * 60)
            for m in market_candidates:
                sign = "+" if m["change_pct"] >= 0 else ""
                parts.append(f'{m["ticker"]}: ${m["close"]:.2f} ({sign}{m["change_pct"]}% weekly)')

        # Section 4: Paper candidates
        if papers:
            parts.append("\n" + "=" * 60)
            parts.append("RESEARCH PAPER CANDIDATES")
            parts.append("=" * 60)
            for p in papers:
                parts.append(
                    f'\nTitle: {p["title"]}\n'
                    f'ArXiv: {p["arxiv_id"]} | Authors: {", ".join(p["authors"])}\n'
                    f'Readiness: {p["commercial_readiness"]} | Relevance: {p["relevance_score"]}\n'
                    f'Summary: {p["significance_summary"][:200]}\n'
                    f'URL: {p["abs_url"]}'
                )

        # Section 5: Article lookup table
        parts.append("\n" + "=" * 60)
        parts.append("ARTICLE LOOKUP TABLE (for citation resolution)")
        parts.append("=" * 60)
        for article_id, a in self._article_lookup.items():
            pub = a.published_at.strftime("%Y-%m-%d") if a.published_at else ""
            parts.append(
                f'ID: {a.id} | Title: {a.title[:100]} | '
                f'Source: {a.source_name} | URL: {a.url} | Published: {pub}'
            )

        return "\n".join(parts)

    def _assemble_briefing(self, parsed: Dict[str, Any], domain: str) -> WeeklyBriefing:
        """Assemble WeeklyBriefing from parsed Briefing Agent JSON output."""
        # Parse sections
        sections = []
        for s_data in parsed.get("sections", []):
            voice_quotes = [VoiceQuote.from_dict(vq) for vq in s_data.get("voice_quotes", [])]
            citations = [Citation.from_dict(c) for c in s_data.get("citations", [])]
            section = BriefingSection(
                header=s_data.get("header", ""),
                priority_tag=s_data.get("priority_tag", ""),
                priority_label=s_data.get("priority_label", ""),
                narrative=s_data.get("narrative", ""),
                voice_quotes=voice_quotes,
                citations=citations,
                has_content=bool(s_data.get("has_content", False)),
            )
            sections.append(section)

        # Ensure all 5 priority sections exist (even if empty)
        existing_tags = {s.priority_tag for s in sections}
        for p in DOMAIN_PRIORITIES.get(domain, []):
            if p.tag not in existing_tags:
                sections.append(BriefingSection(
                    header=p.label,
                    priority_tag=p.tag,
                    priority_label=p.label,
                    has_content=False,
                ))

        # Sort sections by priority tag
        tag_order = {f"P{i}": i for i in range(1, 6)}
        sections.sort(key=lambda s: tag_order.get(s.priority_tag, 99))

        # Parse market movers
        market_movers = [MarketMover.from_dict(m) for m in parsed.get("market_movers", [])]

        # Parse research papers
        research_papers = [ResearchPaper.from_dict(p) for p in parsed.get("research_papers", [])]

        # Compute week_of (Monday of current week)
        today = datetime.now(timezone.utc).date()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        sections_active = sum(1 for s in sections if s.has_content)
        sections_total = len(DOMAIN_PRIORITIES.get(domain, [])) + 2  # +2 for market + research

        # Count market/research as active if they have content
        if market_movers:
            sections_active += 1
        if research_papers:
            sections_active += 1

        return WeeklyBriefing(
            domain=domain,
            week_of=monday.isoformat(),
            sections=sections,
            market_movers=market_movers,
            research_papers=research_papers,
            sections_active=sections_active,
            sections_total=sections_total,
        )

    # =========================================================================
    # Utilities
    # =========================================================================

    def _parse_json_robust(self, text: str) -> Any:
        """
        4-tier resilient JSON parser.
        Copied from quote_extractor.py pattern — handles LLM output quirks.
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # Tier 1: Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Tier 2: Extract from ```json code block
        json_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Tier 3: Find any JSON object or array in text
        for pattern in [r'(\{[\s\S]*\})', r'(\[[\s\S]*\])']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        # Tier 4: Truncated JSON recovery — find last closing brace/bracket
        for closer, opener in [("}", "{"), ("]", "[")]:
            last_close = text.rfind(closer)
            first_open = text.find(opener)
            if first_open >= 0 and last_close > first_open:
                candidate = text[first_open:last_close + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    # Try adding missing closers
                    for suffix in ["]", "}", "]}",  "}]"]:
                        try:
                            return json.loads(candidate + suffix)
                        except json.JSONDecodeError:
                            continue

        logger.warning(f"[WEEKLY-BRIEFING] JSON parse failed on {len(text)} chars")
        return None

    def _empty_briefing(self, domain: str) -> WeeklyBriefing:
        """Return an empty briefing for when no data is available."""
        today = datetime.now(timezone.utc).date()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        sections = []
        for p in DOMAIN_PRIORITIES.get(domain, []):
            sections.append(BriefingSection(
                header=p.label,
                priority_tag=p.tag,
                priority_label=p.label,
                has_content=False,
            ))

        return WeeklyBriefing(
            domain=domain,
            week_of=monday.isoformat(),
            sections=sections,
            sections_active=0,
            sections_total=len(sections) + 2,
        )
