"""
ArXiv Paper Fetcher
===================

Async ArXiv API client for quantum computing research papers.
Uses the ArXiv Atom API with XML parsing (no external arxiv package needed).
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set

import aiohttp

from config.settings import IngestionConfig
from config.arxiv_queries import (
    ARXIV_QUERIES,
    ARXIV_GENERAL_QUERY,
    ARXIV_API_BASE_URL,
    ARXIV_RATE_LIMIT_SECONDS,
    ARXIV_MAX_RESULTS,
)
from models.article import RawArticle, SourceType
from models.paper import Paper
from utils.logger import get_logger

logger = get_logger(__name__)

# ArXiv Atom XML namespaces
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArXivFetcher:
    """
    Fetches papers from the ArXiv API.

    Features:
    - Use-case focused queries + optional general query
    - Dual output: RawArticle (for classification pipeline) + Paper (for papers table)
    - Client-side date filtering (ArXiv API date filtering is unreliable)
    - 3-second rate limit between requests (ArXiv TOS compliance)
    - Cross-query dedup by arxiv_id
    - Domain-aware: accepts injected queries for quantum or AI domains
    """

    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        queries: Optional[List[Dict[str, Any]]] = None,
        general_query: Optional[str] = None,
    ):
        self.config = config or IngestionConfig()
        self.rate_limit_seconds = self.config.arxiv_rate_limit_seconds
        self.max_results = self.config.arxiv_max_results_per_query
        self.max_article_age_days = self.config.max_article_age_days
        self.api_base_url = ARXIV_API_BASE_URL
        self._queries = queries if queries is not None else ARXIV_QUERIES
        self._general_query = general_query if general_query is not None else ARXIV_GENERAL_QUERY

    async def fetch_all_queries(
        self,
        include_general: bool = False,
    ) -> Tuple[List[RawArticle], List[Paper]]:
        """
        Run all ArXiv queries and return both RawArticles and Papers.

        Args:
            include_general: Whether to include the general catch-all query

        Returns:
            Tuple of (RawArticle list for classification, Paper list for papers table)
        """
        queries_to_run = list(self._queries)
        if include_general:
            queries_to_run.append({
                "name": "general",
                "query": self._general_query,
                "use_case": "general",
            })

        logger.info(f"[FETCHER] ArXiv: running {len(queries_to_run)} queries")

        all_articles: List[RawArticle] = []
        all_papers: List[Paper] = []
        seen_arxiv_ids: Set[str] = set()
        success_count = 0
        error_count = 0

        async with aiohttp.ClientSession() as session:
            for i, query_config in enumerate(queries_to_run, 1):
                try:
                    entries = await self._fetch_query(session, query_config["query"])
                    query_new = 0

                    for entry_data in entries:
                        arxiv_id = entry_data.get("arxiv_id", "")
                        if not arxiv_id or arxiv_id in seen_arxiv_ids:
                            continue

                        seen_arxiv_ids.add(arxiv_id)

                        # Create Paper
                        paper = Paper.from_arxiv_entry(entry_data)
                        all_papers.append(paper)

                        # Create RawArticle for classification pipeline
                        raw_article = paper.to_raw_article(
                            query_metadata={
                                "arxiv_query_name": query_config["name"],
                                "arxiv_use_case": query_config.get("use_case", ""),
                            }
                        )
                        all_articles.append(raw_article)
                        query_new += 1

                    success_count += 1
                    logger.debug(
                        f"[FETCHER] ArXiv [{i}/{len(queries_to_run)}] "
                        f"'{query_config['name']}' -> {len(entries)} results, "
                        f"{query_new} new"
                    )

                except Exception as e:
                    error_count += 1
                    logger.warning(
                        f"[FETCHER] ArXiv query error ({query_config.get('name', '?')}): {e}"
                    )

                # Rate limit: 3 seconds between requests (ArXiv TOS)
                if i < len(queries_to_run):
                    await asyncio.sleep(self.rate_limit_seconds)

        logger.info(
            f"[FETCHER] ArXiv total: {len(all_articles)} unique papers "
            f"from {success_count} queries ({error_count} errors)"
        )
        return all_articles, all_papers

    async def _fetch_query(
        self,
        session: aiohttp.ClientSession,
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Execute a single ArXiv API query.

        Args:
            session: aiohttp client session
            query: ArXiv search query string

        Returns:
            List of parsed entry dicts
        """
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        async with session.get(self.api_base_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                raise RuntimeError(f"ArXiv API returned status {response.status}")
            xml_text = await response.text()

        return self._parse_atom_response(xml_text)

    def _parse_atom_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse ArXiv Atom XML response into entry dicts."""
        entries = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_article_age_days)

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.warning(f"[FETCHER] ArXiv XML parse error: {e}")
            return []

        for entry in root.findall(f"{ATOM_NS}entry"):
            parsed = self._parse_entry(entry, cutoff)
            if parsed is not None:
                entries.append(parsed)

        return entries

    def _parse_entry(
        self,
        entry: ET.Element,
        cutoff: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single <entry> element from the ArXiv Atom response.

        Returns None if the entry is too old or missing required fields.
        """
        # Extract arxiv_id from <id> tag
        # Format: http://arxiv.org/abs/2301.12345v1
        id_elem = entry.find(f"{ATOM_NS}id")
        if id_elem is None or id_elem.text is None:
            return None

        raw_id = id_elem.text.strip()
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
        # Remove version suffix (v1, v2, etc.)
        if arxiv_id and arxiv_id[-2] == "v" and arxiv_id[-1].isdigit():
            arxiv_id = arxiv_id[:-2]

        # Title
        title_elem = entry.find(f"{ATOM_NS}title")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
        if not title:
            return None
        # Clean up multi-line titles
        title = " ".join(title.split())

        # Published date
        published_elem = entry.find(f"{ATOM_NS}published")
        published_at = None
        if published_elem is not None and published_elem.text:
            try:
                published_at = datetime.fromisoformat(
                    published_elem.text.strip().replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Date filtering
        if published_at and published_at < cutoff:
            return None

        # Updated date
        updated_elem = entry.find(f"{ATOM_NS}updated")
        updated_at = None
        if updated_elem is not None and updated_elem.text:
            try:
                updated_at = datetime.fromisoformat(
                    updated_elem.text.strip().replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Abstract (summary)
        summary_elem = entry.find(f"{ATOM_NS}summary")
        abstract = ""
        if summary_elem is not None and summary_elem.text:
            abstract = " ".join(summary_elem.text.strip().split())

        # Authors
        authors = []
        for author_elem in entry.findall(f"{ATOM_NS}author"):
            name_elem = author_elem.find(f"{ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        # Categories
        categories = []
        for cat_elem in entry.findall(f"{ATOM_NS}category"):
            term = cat_elem.get("term", "")
            if term:
                categories.append(term)

        # PDF URL
        pdf_url = None
        for link_elem in entry.findall(f"{ATOM_NS}link"):
            if link_elem.get("type") == "application/pdf":
                pdf_url = link_elem.get("href")
                break
            # Fallback: link with title="pdf"
            if link_elem.get("title") == "pdf":
                pdf_url = link_elem.get("href")
                break

        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "published": published_at.isoformat() if published_at else None,
            "updated": updated_at.isoformat() if updated_at else None,
            "pdf_url": pdf_url,
        }
