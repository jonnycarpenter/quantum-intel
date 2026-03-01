import json
import logging
from typing import Optional

from tools.base import BaseTool
from storage import get_storage

logger = logging.getLogger(__name__)


class SearchCaseStudiesTool(BaseTool):
    """
    Tool for searching parsed case studies.
    """

    name = "search_case_studies"
    description = (
        "Search explicitly through parsed case studies. "
        "Useful for understanding how companies or industries are deploying technology, "
        "their specific use cases, blockers, metrics, and outcomes."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or topics to search for within case cases.",
            },
            "domain": {
                "type": "string",
                "description": "Domain to filter by, typically 'quantum' or 'ai'.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return. Default 5.",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
        **kwargs,
    ) -> str:
        """Execute the case study search."""
        try:
            logger.info(f"[TOOL] Executing search_case_studies for: '{query}'")
            storage = get_storage()
            results = await storage.search_case_studies(
                query=query, domain=domain, limit=limit
            )

            if not results:
                return json.dumps({
                    "query": query,
                    "results": [],
                    "message": "No matching case studies found.",
                })

            output = []
            for item in results:
                output.append({
                    "company_name": item.company_name,
                    "industry": item.industry,
                    "use_case_summary": item.use_case_summary,
                    "metrics_observed": item.metrics_observed,
                    "technical_blockers": item.technical_blockers,
                    "url": item.url,
                    "relevance_score": item.relevance_score,
                })

            return json.dumps({"query": query, "results": output})

        except Exception as e:
            logger.error(f"[TOOL] search_case_studies failed: {e}")
            return json.dumps({"error": f"Search failed: {str(e)}"})
