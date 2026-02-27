"""
ChromaDB Embeddings Store
=========================

Local vector search using ChromaDB + sentence-transformers.
For semantic search over articles, SEC nuggets, earnings quotes, and podcast quotes.

Supports multiple content types via the content_type parameter.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .embeddings_config import CONTENT_TYPE_CONFIG, VALID_CONTENT_TYPES

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class SearchResult:
    """A single search result."""
    item_id: str
    title: str
    url: str
    summary: str
    score: float  # similarity score (higher = more similar)
    source_type: str = "articles"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResults:
    """Collection of search results."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total: int = 0


class EmbeddingsStore:
    """
    ChromaDB-based vector store for semantic search.

    Indexes content for semantic retrieval using sentence-transformers
    for local embedding generation.

    Supports multiple content types via the content_type parameter:
    - "articles" (default): quantum_articles collection
    - "sec_nuggets": quantum_sec_nuggets collection
    - "earnings_quotes": quantum_earnings_quotes collection
    - "podcast_quotes": quantum_podcast_quotes collection
    """

    def __init__(
        self,
        persist_directory: str = "data/embeddings",
        collection_name: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        content_type: str = "articles",
    ):
        if not HAS_CHROMADB:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(
                f"Unknown content type: {content_type}. "
                f"Valid types: {VALID_CONTENT_TYPES}"
            )

        # Content type configuration
        self.content_type = content_type
        self._config = CONTENT_TYPE_CONFIG[content_type]
        self._id_field = self._config["id_field"]
        self._source_type = self._config["source_type"]

        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Use explicit collection_name if provided, otherwise from config
        resolved_collection = collection_name or self._config["chromadb_collection"]

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=resolved_collection,
            metadata={"hnsw:space": "cosine"},
        )

        # Lazy-load embedding model
        self._model = None
        self._model_name = model_name

    @property
    def model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            if not HAS_SENTENCE_TRANSFORMERS:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self._model_name)
            logger.info(f"[EMBEDDINGS] Loaded model: {self._model_name}")
        return self._model

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    # =========================================================================
    # Content-type-aware helpers
    # =========================================================================

    def _get_item_id(self, item: Any) -> str:
        """Extract the unique ID from an item based on content type."""
        if self.content_type == "articles":
            return getattr(item, "id", getattr(item, "url", ""))
        return getattr(item, self._id_field, "")

    def _build_document_text(self, item: Any) -> str:
        """Build the text string to embed, based on content type."""
        if self.content_type == "articles":
            parts = [item.title]
            if hasattr(item, "ai_summary") and item.ai_summary:
                parts.append(item.ai_summary)
            elif hasattr(item, "summary") and item.summary:
                parts.append(item.summary)
            if hasattr(item, "key_takeaway") and item.key_takeaway:
                parts.append(item.key_takeaway)
            return " | ".join(parts)

        elif self.content_type == "sec_nuggets":
            parts = [item.nugget_text]
            if item.context_text:
                parts.append(item.context_text)
            return " | ".join(parts)

        elif self.content_type in ("earnings_quotes", "podcast_quotes"):
            parts = []
            ctx_before = getattr(item, "context_before", None)
            if ctx_before:
                parts.append(ctx_before)
            parts.append(item.quote_text)
            ctx_after = getattr(item, "context_after", None)
            if ctx_after:
                parts.append(ctx_after)
            return " | ".join(parts)

        elif self.content_type == "case_studies":
            parts = [item.use_case_title]
            if item.use_case_summary:
                parts.append(item.use_case_summary)
            if item.grounding_quote:
                parts.append(item.grounding_quote)
            if item.outcome_metric:
                parts.append(item.outcome_metric)
            return " | ".join(parts)

        return ""

    def _build_metadata(self, item: Any) -> Dict[str, Any]:
        """Build metadata dict for the item, based on content type."""
        def _enum_val(v):
            """Safely extract .value from enum or return string as-is."""
            return v.value if hasattr(v, "value") else str(v)

        if self.content_type == "articles":
            return {
                "title": getattr(item, "title", "")[:200],
                "url": getattr(item, "url", ""),
                "source_name": getattr(item, "source_name", ""),
                "primary_category": getattr(item, "primary_category", ""),
                "priority": getattr(item, "priority", "medium"),
                "relevance_score": float(getattr(item, "relevance_score", 0.5)),
                "domain": getattr(item, "domain", "quantum"),
                "published_at": (
                    item.published_at.strftime("%Y-%m-%d")
                    if getattr(item, "published_at", None) else ""
                ),
            }

        elif self.content_type == "sec_nuggets":
            themes = item.themes
            if isinstance(themes, list):
                themes = ",".join(themes)
            return {
                "ticker": item.ticker,
                "company_name": item.company_name,
                "filing_type": _enum_val(item.filing_type),
                "nugget_type": _enum_val(item.nugget_type),
                "themes": themes,
                "signal_strength": _enum_val(item.signal_strength),
                "risk_level": item.risk_level,
                "relevance_score": float(item.relevance_score),
                "domain": getattr(item, "domain", "quantum"),
                "filing_date": (
                    item.filing_date.strftime("%Y-%m-%d")
                    if getattr(item, "filing_date", None) else ""
                ),
            }

        elif self.content_type == "earnings_quotes":
            themes = item.themes
            if isinstance(themes, list):
                themes = ",".join(themes)
            return {
                "ticker": item.ticker,
                "company_name": item.company_name,
                "speaker_name": item.speaker_name,
                "speaker_role": _enum_val(item.speaker_role),
                "quote_type": _enum_val(item.quote_type),
                "themes": themes,
                "sentiment": item.sentiment,
                "relevance_score": float(item.relevance_score),
                "domain": getattr(item, "domain", "quantum"),
                "year": item.year,
                "quarter": item.quarter,
            }

        elif self.content_type == "podcast_quotes":
            themes = item.themes
            if isinstance(themes, list):
                themes = ",".join(themes)
            return {
                "podcast_name": item.podcast_name,
                "episode_title": item.episode_title,
                "speaker_name": item.speaker_name,
                "speaker_role": item.speaker_role,
                "quote_type": item.quote_type,
                "themes": themes,
                "sentiment": item.sentiment,
                "relevance_score": float(item.relevance_score),
                "published_at": item.published_at if isinstance(item.published_at, str) else (
                    item.published_at.strftime("%Y-%m-%d") if getattr(item, "published_at", None) else ""
                ),
            }

        elif self.content_type == "case_studies":
            tech_stack = item.technology_stack
            if isinstance(tech_stack, list):
                tech_stack = ",".join(tech_stack)
            return {
                "case_study_id": item.case_study_id,
                "source_type": item.source_type,
                "company": item.company or "",
                "industry": item.industry or "",
                "use_case_title": item.use_case_title or "",
                "outcome_type": item.outcome_type or "",
                "readiness_level": item.readiness_level or "",
                "technology_stack": tech_stack,
                "relevance_score": float(item.relevance_score),
                "domain": getattr(item, "domain", "quantum"),
            }

        return {}

    # =========================================================================
    # Core methods
    # =========================================================================

    async def index_items(self, items: List[Any]) -> int:
        """
        Index items for semantic search.

        Content-type-aware: builds text and metadata based on self.content_type.

        Returns:
            Number of items indexed.
        """
        ids = []
        documents = []
        metadatas = []

        for item in items:
            doc_text = self._build_document_text(item)
            if not doc_text.strip():
                continue

            item_id = self._get_item_id(item)
            ids.append(item_id)
            documents.append(doc_text)
            metadatas.append(self._build_metadata(item))

        if not ids:
            return 0

        # Generate embeddings
        embeddings = self._embed(documents)

        # Upsert to ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"[EMBEDDINGS] Indexed {len(ids)} {self.content_type}")
        return len(ids)

    async def index_articles(self, articles: List[Any]) -> int:
        """Backward-compatible alias for index_items."""
        return await self.index_items(articles)

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> SearchResults:
        """
        Semantic search over indexed content.

        Args:
            query: Search query text
            n_results: Maximum results to return
            filters: Optional ChromaDB where clause filters

        Returns:
            SearchResults with ranked results
        """
        query_embedding = self._embed([query])[0]

        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self.collection.count() or 1),
        }
        if filters:
            search_kwargs["where"] = filters

        try:
            results = self.collection.query(**search_kwargs)
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Search error: {e}")
            return SearchResults(query=query)

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0

                # Build display title based on content type
                if self.content_type == "articles":
                    title = metadata.get("title", "")
                elif self.content_type == "sec_nuggets":
                    ticker = metadata.get("ticker", "")
                    ntype = metadata.get("nugget_type", "")
                    title = f"{ticker} SEC: {ntype}" if ticker else ntype
                elif self.content_type == "earnings_quotes":
                    speaker = metadata.get("speaker_name", "")
                    ticker = metadata.get("ticker", "")
                    title = f"{speaker} ({ticker})" if speaker else ticker
                elif self.content_type == "podcast_quotes":
                    speaker = metadata.get("speaker_name", "")
                    podcast = metadata.get("podcast_name", "")
                    title = f"{speaker} on {podcast}" if speaker else podcast
                else:
                    title = ""

                url = metadata.get("url", "")

                search_results.append(SearchResult(
                    item_id=doc_id,
                    title=title,
                    url=url,
                    summary=results["documents"][0][i] if results["documents"] else "",
                    score=1.0 - distance,  # Convert distance to similarity
                    source_type=self._source_type,
                    metadata=metadata,
                ))

        return SearchResults(
            query=query,
            results=search_results,
            total=len(search_results),
        )

    def count(self) -> int:
        """Get total number of indexed documents."""
        return self.collection.count()


def get_chromadb_store(
    persist_directory: str = "data/embeddings",
    collection_name: Optional[str] = None,
    content_type: str = "articles",
) -> EmbeddingsStore:
    """Factory function for ChromaDB embeddings store."""
    return EmbeddingsStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
        content_type=content_type,
    )
