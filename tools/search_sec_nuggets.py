import json
import logging
from typing import Optional

from tools.base import BaseTool
from storage import get_storage

logger = logging.getLogger(__name__)


class SearchSecNuggetsTool(BaseTool):
    """
    Tool for searching historically extracted SEC nuggets.
    """

    name = "search_sec_nuggets"
    description = (
        "Search the database of historical SEC filing risk factors, MD&A insights, and nuggets. "
        "Useful for understanding official company disclosures, risk factors, or strategic statements."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or keyword to search for in nuggets.",
            },
            "ticker": {
                "type": "string",
                "description": "Optional stock ticker symbol to narrow search down to a specific company.",
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
        ticker: Optional[str] = None,
        limit: int = 5,
        **kwargs,
    ) -> str:
        """Execute the SEC nugget search."""
        try:
            logger.info(f"[TOOL] Executing search_sec_nuggets for: '{query}'")
            storage = get_storage()
            results = await storage.search_sec_nuggets(
                query=query, ticker=ticker, limit=limit
            )

            if not results:
                return json.dumps({
                    "query": query,
                    "ticker": ticker,
                    "results": [],
                    "message": "No matching SEC nuggets found.",
                })

            output = []
            for item in results:
                output.append({
                    "company_name": item.company_name,
                    "ticker": item.ticker,
                    "filing_info": f"{item.filing_type} ({item.filing_date})",
                    "nugget_text": item.nugget_text,
                    "themes": item.themes,
                    "relevance_score": item.relevance_score,
                })

            return json.dumps({"query": query, "ticker": ticker, "results": output})

        except Exception as e:
            logger.error(f"[TOOL] search_sec_nuggets failed: {e}")
            return json.dumps({"error": f"Search failed: {str(e)}"})
