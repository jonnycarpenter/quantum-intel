"""
Platform Knowledge Base Tool
============================

Searches the BigQuery Vector Database for internal platform guides
and help documentation (e.g. how the feed works, what the brevity score is).
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PlatformKnowledgeTool:
    """Tool to query internal platform documentation via Vertex AI embeddings."""

    def __init__(self):
        self._embeddings = None

    def _ensure_initialized(self) -> None:
        """Lazy-initialize the specific platform guides embedding store."""
        if self._embeddings is None:
            try:
                from storage import get_embeddings_store
                # Special content type routing to the platform_guides vector table
                self._embeddings = get_embeddings_store(content_type="platform_guides")
            except Exception as e:
                logger.warning(f"[TOOL] Vector store not available: {e}")
                self._embeddings = None

    async def execute(
        self,
        query: str,
        limit: int = 3,
    ) -> str:
        """
        Search the platform knowledge base and return results.

        Args:
            query: User's question about the platform (e.g. "How do I use the pipeline?")
            limit: Maximum chunks to return

        Returns:
            JSON string with semantic search results
        """
        self._ensure_initialized()
        
        if not self._embeddings:
            return json.dumps({
                "status": "error",
                "message": "Vector store connection failed. Cannot query the platform knowledge base."
            })

        logger.info(f"[TOOL] platform_knowledge: query='{query}' limit={limit}")

        try:
            search_results = await self._embeddings.search(
                query=query,
                n_results=limit,
            )
            
            # Format results for the LLM
            formatted_results = []
            for r in search_results.results:
                formatted_results.append({
                    "title": r.title,
                    "content": r.summary,  # For knowledge base, summary acts as the chunk text
                    "relevance_score": round(r.score, 3) if r.score else 0.0,
                    "source_file": r.metadata.get("source_file", "unknown") if r.metadata else "unknown"
                })
                
            if not formatted_results:
                return json.dumps({
                    "status": "success",
                    "results": [],
                    "message": "No relevant documentation found for that query in the platform guides."
                })

            return json.dumps({
                "status": "success",
                "results": formatted_results,
                "total_found": len(formatted_results),
                "query": query,
            })

        except Exception as e:
            logger.error(f"[TOOL] platform_knowledge error: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Platform Knowledge search failed: {type(e).__name__}: {e}"
            })
