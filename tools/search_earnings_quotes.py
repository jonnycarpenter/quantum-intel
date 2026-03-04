import json
import logging
from typing import Optional

from storage import get_storage

logger = logging.getLogger(__name__)


class SearchEarningsQuotesTool:
    """
    Tool for searching historically extracted earnings quotes.
    """

    name = "search_earnings_quotes"
    description = (
        "Search the database of historical earnings quotes. "
        "Useful for finding out exactly what a company (or overall industry) has said "
        "about a specific topic (e.g. 'GPU CapEx', 'deployment blockers') during earnings."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or keyword to search for in quotes, themes, tech mentioned, etc.",
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
        """Execute the earnings quote search."""
        try:
            logger.info(f"[TOOL] Executing search_earnings_quotes for: '{query}'")
            storage = get_storage()
            results = await storage.search_earnings_quotes(
                query=query, ticker=ticker, limit=limit
            )

            if not results:
                return json.dumps({
                    "query": query,
                    "ticker": ticker,
                    "results": [],
                    "message": "No matching earnings quotes found.",
                })

            output = []
            for item in results:
                output.append({
                    "company_name": item.company_name,
                    "ticker": item.ticker,
                    "year_quarter": f"{item.year} Q{item.quarter}",
                    "speaker": f"{item.speaker_name} ({item.speaker_role})",
                    "quote_text": item.quote_text,
                    "themes": item.themes,
                    "relevance_score": item.relevance_score,
                })

            return json.dumps({"query": query, "ticker": ticker, "results": output})

        except Exception as e:
            logger.error(f"[TOOL] search_earnings_quotes failed: {e}")
            return json.dumps({"error": f"Search failed: {str(e)}"})
