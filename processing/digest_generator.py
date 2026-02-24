"""
Digest Generator
================

Compiles classified articles into a structured daily intelligence digest.
Follows the format from spec §7.1.
"""

import os
from datetime import datetime, timezone
from typing import List, Optional

from models.article import Digest, DigestItem, Priority
from config.prompts import DIGEST_SYSTEM_PROMPT, AI_DIGEST_SYSTEM_PROMPT
from config.settings import IngestionConfig
from storage.base import ClassifiedArticle
from utils.llm_client import get_resilient_async_client
from utils.logger import get_logger

logger = get_logger(__name__)


class DigestGenerator:
    """
    Generates daily intelligence digests from classified articles.

    Can generate digests in two modes:
    1. Template mode: Structured markdown from article data (no LLM needed)
    2. LLM mode: Claude-generated executive summary + curated digest
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()

        api_key = self.config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            self.client = get_resilient_async_client(
                anthropic_api_key=api_key, timeout=180.0
            )
        else:
            self.client = None

    async def generate(
        self,
        articles: List[ClassifiedArticle],
        hours: int = 72,
        use_llm: bool = False,
        domain: str = "quantum",
    ) -> Digest:
        """
        Generate a digest from classified articles.

        Args:
            articles: List of ClassifiedArticle objects
            hours: Time period covered
            use_llm: Whether to use Claude for executive summary

        Returns:
            Digest object
        """
        # Sort by relevance score descending
        sorted_articles = sorted(
            articles, key=lambda a: a.relevance_score, reverse=True
        )

        # Build digest items
        items = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for article in sorted_articles[:self.config.digest_max_items]:
            priority_str = article.priority or "medium"
            try:
                priority = Priority(priority_str)
            except ValueError:
                priority = Priority.MEDIUM

            if priority_str == "critical":
                critical_count += 1
            elif priority_str == "high":
                high_count += 1
            elif priority_str == "medium":
                medium_count += 1
            else:
                low_count += 1

            items.append(DigestItem(
                title=article.title,
                source_name=article.source_name,
                url=article.url,
                summary=article.ai_summary or article.summary,
                category=article.primary_category,
                priority=priority,
                relevance_score=article.relevance_score,
                published_at=article.published_at,
                companies_mentioned=article.companies_mentioned,
                technologies_mentioned=article.technologies_mentioned,
            ))

        # Generate executive summary
        executive_summary = ""
        if use_llm and self.client and items:
            executive_summary = await self._generate_llm_summary(items, domain=domain)
        else:
            if domain == "ai":
                executive_summary = self._generate_ai_template_summary(items)
            else:
                executive_summary = self._generate_template_summary(items)

        digest = Digest(
            created_at=datetime.now(timezone.utc),
            period_hours=hours,
            executive_summary=executive_summary,
            items=items,
            total_items=len(items),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )

        logger.info(
            f"[DIGEST] Generated digest: {len(items)} items "
            f"(critical: {critical_count}, high: {high_count}, "
            f"medium: {medium_count}, low: {low_count})"
        )

        return digest

    def _generate_template_summary(self, items: List[DigestItem]) -> str:
        """Generate a structured summary without LLM."""
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        lines = [f"QUANTUM INTELLIGENCE DIGEST: {today}", ""]

        # Critical items
        critical_items = [i for i in items if i.priority == Priority.CRITICAL]
        if critical_items:
            lines.append("CRITICAL:")
            for item in critical_items:
                lines.append(f"  * [{item.source_name}] {item.title}")
                if item.summary:
                    lines.append(f"    {item.summary[:150]}")
            lines.append("")

        # Group by category
        categories = {}
        for item in items:
            cat = item.category or "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        # Company news
        company_cats = ["company_earnings", "funding_ipo", "partnership_contract", "personnel_leadership"]
        company_items = [i for i in items if i.category in company_cats]
        if company_items:
            lines.append("COMPANY NEWS:")
            for item in company_items[:5]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Research & milestones
        research_cats = ["hardware_milestone", "error_correction", "algorithm_research"]
        research_items = [i for i in items if i.category in research_cats]
        if research_items:
            lines.append("RESEARCH & MILESTONES:")
            for item in research_items[:4]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Use cases
        use_case_cats = [c for c in categories if c.startswith("use_case_")]
        use_case_items = [i for i in items if i.category in use_case_cats]
        if use_case_items:
            lines.append("USE CASES & DEPLOYMENTS:")
            for item in use_case_items[:3]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Cybersecurity
        cyber_items = [i for i in items if i.category == "use_case_cybersecurity"]
        if cyber_items:
            lines.append("CYBERSECURITY & PQC:")
            for item in cyber_items[:2]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        return "\n".join(lines)

    def _generate_ai_template_summary(self, items: List[DigestItem]) -> str:
        """Generate a structured AI digest summary without LLM."""
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        lines = [f"AI INTELLIGENCE DIGEST: {today}", ""]

        # Critical items
        critical_items = [i for i in items if i.priority == Priority.CRITICAL]
        if critical_items:
            lines.append("CRITICAL:")
            for item in critical_items:
                lines.append(f"  * [{item.source_name}] {item.title}")
                if item.summary:
                    lines.append(f"    {item.summary[:150]}")
            lines.append("")

        # Model & product launches
        model_cats = ["ai_model_release", "ai_product_launch"]
        model_items = [i for i in items if i.category in model_cats]
        if model_items:
            lines.append("MODEL & PRODUCT LAUNCHES:")
            for item in model_items[:5]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Enterprise AI & use cases
        use_case_cats = ["ai_use_case_enterprise", "ai_use_case_healthcare", "ai_use_case_finance", "ai_use_case_other"]
        use_case_items = [i for i in items if i.category in use_case_cats]
        if use_case_items:
            lines.append("ENTERPRISE AI & USE CASES:")
            for item in use_case_items[:5]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Infrastructure & compute
        infra_items = [i for i in items if i.category == "ai_infrastructure"]
        if infra_items:
            lines.append("INFRASTRUCTURE & COMPUTE:")
            for item in infra_items[:3]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Safety & regulation
        safety_cats = ["ai_safety_alignment", "policy_regulation"]
        safety_items = [i for i in items if i.category in safety_cats]
        if safety_items:
            lines.append("SAFETY & REGULATION:")
            for item in safety_items[:3]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Funding & market
        market_cats = ["company_earnings", "funding_ipo", "market_analysis"]
        market_items = [i for i in items if i.category in market_cats]
        if market_items:
            lines.append("FUNDING & MARKET:")
            for item in market_items[:3]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Research highlights
        research_items = [i for i in items if i.category == "ai_research_breakthrough"]
        if research_items:
            lines.append("RESEARCH HIGHLIGHTS:")
            for item in research_items[:3]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Open source
        oss_items = [i for i in items if i.category == "ai_open_source"]
        if oss_items:
            lines.append("OPEN SOURCE:")
            for item in oss_items[:2]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        # Remaining (partnership, personnel, geopolitics, skepticism)
        shown_cats = set(model_cats + use_case_cats + safety_cats + market_cats + ["ai_infrastructure", "ai_research_breakthrough", "ai_open_source"])
        remaining = [i for i in items if i.category not in shown_cats and i.priority != Priority.CRITICAL]
        if remaining:
            lines.append("OTHER NOTABLE:")
            for item in remaining[:5]:
                lines.append(f"  * [{item.source_name}] {item.title}")
            lines.append("")

        return "\n".join(lines)

    async def _generate_llm_summary(self, items: List[DigestItem], domain: str = "quantum") -> str:
        """Generate executive summary using Claude."""
        # Build article list for LLM
        article_summaries = []
        for item in items[:30]:
            priority_val = item.priority.value if isinstance(item.priority, Priority) else item.priority
            article_summaries.append(
                f"[{priority_val.upper()}] [{item.category}] [{item.source_name}] "
                f"{item.title}\n  {item.summary[:200]}"
            )

        if domain == "ai":
            digest_label = "AI Intelligence Digest"
            system_prompt = AI_DIGEST_SYSTEM_PROMPT
        else:
            digest_label = "Quantum Intelligence Digest"
            system_prompt = DIGEST_SYSTEM_PROMPT

        user_message = (
            f"Here are {len(article_summaries)} classified articles from the past "
            f"24-72 hours. Generate a {digest_label}.\n\n"
            + "\n\n".join(article_summaries)
        )

        try:
            response = await self.client.messages_create(
                model=self.config.digest_model,
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
            )
            return self.client.extract_text(response)
        except Exception as e:
            logger.warning(f"[DIGEST] LLM summary failed, using template: {e}")
            if domain == "ai":
                return self._generate_ai_template_summary(items)
            return self._generate_template_summary(items)
