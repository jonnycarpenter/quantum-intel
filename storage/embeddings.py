"""
ChromaDB Embeddings Store
=========================

Local vector search using ChromaDB + sentence-transformers.
For semantic search over articles and paper abstracts.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

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
    article_id: str
    title: str
    url: str
    summary: str
    score: float  # similarity score (lower = more similar in ChromaDB)
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

    Indexes article summaries and paper abstracts for semantic retrieval.
    Uses sentence-transformers for local embedding generation.
    """

    def __init__(
        self,
        persist_directory: str = "data/embeddings",
        collection_name: str = "quantum_articles",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        if not HAS_CHROMADB:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
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

    async def index_articles(self, articles: List[Any]) -> int:
        """
        Index articles for semantic search.

        Args:
            articles: List of ClassifiedArticle objects

        Returns:
            Number of chunks indexed
        """
        ids = []
        documents = []
        metadatas = []

        for article in articles:
            # Build searchable text from article
            text_parts = [article.title]
            if hasattr(article, "ai_summary") and article.ai_summary:
                text_parts.append(article.ai_summary)
            elif hasattr(article, "summary") and article.summary:
                text_parts.append(article.summary)
            if hasattr(article, "key_takeaway") and article.key_takeaway:
                text_parts.append(article.key_takeaway)

            doc_text = " | ".join(text_parts)
            if not doc_text.strip():
                continue

            article_id = getattr(article, "id", getattr(article, "url", ""))
            ids.append(article_id)
            documents.append(doc_text)
            metadatas.append({
                "title": article.title[:200],
                "url": getattr(article, "url", ""),
                "source_name": getattr(article, "source_name", ""),
                "primary_category": getattr(article, "primary_category", ""),
                "priority": getattr(article, "priority", "medium"),
                "relevance_score": float(getattr(article, "relevance_score", 0.5)),
                "domain": getattr(article, "domain", "quantum"),
                "published_at": (
                    article.published_at.strftime("%Y-%m-%d")
                    if getattr(article, "published_at", None) else ""
                ),
            })

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

        logger.info(f"[EMBEDDINGS] Indexed {len(ids)} articles")
        return len(ids)

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> SearchResults:
        """
        Semantic search over indexed articles.

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

                search_results.append(SearchResult(
                    article_id=doc_id,
                    title=metadata.get("title", ""),
                    url=metadata.get("url", ""),
                    summary=results["documents"][0][i] if results["documents"] else "",
                    score=1.0 - distance,  # Convert distance to similarity
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
    collection_name: str = "quantum_articles",
) -> EmbeddingsStore:
    """Factory function for ChromaDB embeddings store."""
    return EmbeddingsStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
