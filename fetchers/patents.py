import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from utils.logger import get_logger
from models.patent import Patent
from config.settings import IngestionConfig

logger = get_logger(__name__)

class PatentsViewFetcher:
    """
    Fetches recent patent grants assigned to specific companies
    using the USPTO PatentsView API (https://patentsview.org).
    
    No API key required. Free and publicly accessible.
    """

    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        companies: Optional[List[str]] = None,
        domain: str = "quantum"
    ):
        self.config = config or IngestionConfig()
        self.companies = companies or [
            "Rigetti", "IonQ", "D-Wave", "IBM", "Google LLC",
            "Microsoft", "Quantinuum", "PsiQuantum"
        ]
        self.domain = domain
        self.base_url = "https://search.patentsview.org/api/v1/patent/"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "QuantumIntelHub/1.0 (patent-monitoring)",
        }
        self.max_retries = 3

    async def fetch_all(self, limit_per_company: int = 20) -> List[Patent]:
        """Fetch patents for all configured companies."""
        all_patents = []
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for company in self.companies:
                try:
                    patents = await self._fetch_for_company(session, company, limit_per_company)
                    all_patents.extend(patents)
                    await asyncio.sleep(1)  # Polite rate limiting
                except Exception as e:
                    logger.error(f"[PATENT_FETCHER] Failed to fetch for {company}: {e}")
                    
        return all_patents

    async def _fetch_for_company(
        self, session: aiohttp.ClientSession, company: str, limit: int
    ) -> List[Patent]:
        """Fetch the most recent patents for a single company assignee."""
        
        # PatentsView API query: search by assignee organization name
        # Use _contains for partial matching (e.g., "Rigetti" matches "Rigetti Computing, Inc.")
        # Limit results to patents from the last 2 years for relevance
        two_years_ago = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        
        payload = {
            "q": {
                "_and": [
                    {"_or": [
                        {"assignees.assignee_organization": {"_contains": company}},
                    ]},
                    {"patent_date": {"_gte": two_years_ago}}
                ]
            },
            "f": [
                "patent_id",
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "patent_type",
                "assignees.assignee_organization",
                "inventors.inventor_first_name",
                "inventors.inventor_last_name",
                "application.filing_date",
            ],
            "o": {
                "per_page": limit,
                "page": 1,
            },
            "s": [{"patent_date": "desc"}]
        }
        
        logger.info(f"[PATENT_FETCHER] Searching PatentsView for: {company}")
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except Exception as e:
                            logger.error(f"[PATENT_FETCHER] Failed to parse JSON for {company}: {e}")
                            return []
                        
                        patents_data = data.get("patents", [])
                        if not patents_data:
                            logger.info(f"[PATENT_FETCHER] No patents found for {company}")
                            return []
                        
                        patents = []
                        for doc in patents_data:
                            p = self._parse_document(doc, company)
                            if p:
                                patents.append(p)
                        
                        total = data.get("total_patent_count", len(patents))
                        logger.info(
                            f"[PATENT_FETCHER] Extracted {len(patents)} patents for {company} "
                            f"(total available: {total})"
                        )
                        return patents
                        
                    elif response.status == 429:
                        # Rate limited
                        wait = 10 * (attempt + 1)
                        logger.warning(
                            f"[PATENT_FETCHER] Rate limited for {company}, "
                            f"retrying in {wait}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait)
                        continue
                    elif response.status >= 500 and attempt < self.max_retries - 1:
                        wait = 5 * (attempt + 1)
                        logger.warning(
                            f"[PATENT_FETCHER] Server error {response.status} for {company}, "
                            f"retrying in {wait}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait)
                        continue
                    else:
                        body = await response.text()
                        logger.error(
                            f"[PATENT_FETCHER] API returned {response.status} for {company}: {body[:200]}"
                        )
                        return []
            except aiohttp.ClientError as e:
                logger.error(f"[PATENT_FETCHER] Connection error for {company}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                return []
        
        return []

    def _parse_document(self, doc: Dict[str, Any], search_company: str) -> Optional[Patent]:
        """Parse a PatentsView API result into a Patent dataclass."""
        try:
            patent_id = doc.get("patent_id") or doc.get("patent_number", "")
            if not patent_id:
                return None
            
            title = doc.get("patent_title", "").strip()
            if not title:
                return None
            
            abstract = (doc.get("patent_abstract") or "").strip()
            
            # Extract assignee organization
            assignees = doc.get("assignees", [])
            if assignees and isinstance(assignees, list):
                assignee = assignees[0].get("assignee_organization", search_company) or search_company
            else:
                assignee = search_company
            
            # Extract inventors
            inventors_raw = doc.get("inventors", [])
            inventors = []
            if inventors_raw and isinstance(inventors_raw, list):
                for inv in inventors_raw:
                    first = inv.get("inventor_first_name", "")
                    last = inv.get("inventor_last_name", "")
                    name = f"{first} {last}".strip()
                    if name:
                        inventors.append(name)
            
            # Dates
            patent_date = doc.get("patent_date", "")  # Grant/publication date
            
            # Filing date from application sub-object
            application = doc.get("application", {})
            if isinstance(application, list) and application:
                filing_date = application[0].get("filing_date", "")
            elif isinstance(application, dict):
                filing_date = application.get("filing_date", "")
            else:
                filing_date = ""
            
            # Build patent URL (Google Patents is a good viewer even if the XHR is blocked)
            patent_url = f"https://patents.google.com/patent/US{patent_id}"
            
            return Patent(
                id=f"US{patent_id}",
                title=title,
                abstract=abstract,
                assignee=assignee,
                inventors=inventors,
                filing_date=filing_date or "",
                publication_date=patent_date or "",
                patent_url=patent_url,
                domain=self.domain,
                relevance_score=0.8,
                innovation_category="General Intellectual Property"
            )
        except Exception as e:
            logger.warning(f"[PATENT_FETCHER] Error parsing document {doc.get('patent_id', 'unknown')}: {e}")
            return None


# Backwards-compatible alias
GooglePatentsFetcher = PatentsViewFetcher
