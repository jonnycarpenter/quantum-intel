"""
Vertex AI Embeddings Store
===========================

GCP production vector search using Vertex AI text-embedding-005
and BigQuery VECTOR_SEARCH for semantic retrieval.

Mirrors the EmbeddingsStore interface from embeddings.py (ChromaDB).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from google.cloud import bigquery

logger = logging.getLogger(__name__)

try:
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False


@dataclass
class SearchResult:
    """A single search result."""
    article_id: str
    title: str
    url: str
    summary: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResults:
    """Collection of search results."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total: int = 0


class VertexEmbeddingsStore:
    """
    Vertex AI + BigQuery Vector Search embeddings store.

    Uses text-embedding-005 (768 dimensions) via Vertex AI API.
    Stores vectors in BigQuery `article_embeddings` table.
    Queries via BigQuery VECTOR_SEARCH function.
    """

    EMBEDDING_MODEL = "text-embedding-005"
    EMBEDDING_DIM = 768
    BATCH_SIZE = 250  # Vertex AI batch limit

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "quantum_ai_hub",
        location: str = "us-central1",
    ):
        if not HAS_VERTEX:
            raise ImportError(
                "google-cloud-aiplatform not installed. "
                "Run: pip install google-cloud-aiplatform"
            )

        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.full_dataset = f"{project_id}.{dataset_id}"
        self.bq_client = bigquery.Client(project=project_id)
        aiplatform.init(project=project_id, location=location)
        self._model = None

    @property
    def model(self):
        """Lazy-load the Vertex AI embedding model."""
        if self._model is None:
            self._model = TextEmbeddingModel.from_pretrained(self.EMBEDDING_MODEL)
            logger.info(f"[EMBEDDINGS] Loaded Vertex AI model: {self.EMBEDDING_MODEL}")
        return self._model

    def _table(self, name: str) -> str:
        return f"`{self.full_dataset}.{name}`"

    def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings via Vertex AI API in batches."""
        all_embeddings = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            results = self.model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in results])
        return all_embeddings

    async def index_articles(self, articles: List[Any]) -> int:
        """
        Index articles for semantic search.

        Generates embeddings via Vertex AI and stores in BigQuery
        article_embeddings table.

        Returns:
            Number of articles indexed.
        """
        ids = []
        documents = []
        article_data = []

        for article in articles:
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
            article_data.append({
                "article_id": article_id,
                "title": getattr(article, "title", "")[:200],
                "url": getattr(article, "url", ""),
                "source_name": getattr(article, "source_name", ""),
                "primary_category": getattr(article, "primary_category", ""),
                "priority": getattr(article, "priority", "medium"),
                "relevance_score": float(getattr(article, "relevance_score", 0.5)),
                "domain": getattr(article, "domain", "quantum"),
                "published_at": (
                    article.published_at.isoformat()
                    if getattr(article, "published_at", None) else None
                ),
                "document_text": doc_text,
            })

        if not ids:
            return 0

        # Generate embeddings
        embeddings = await self._run_sync(self._embed, documents)

        # Build rows with embeddings
        rows = []
        for i, data in enumerate(article_data):
            data["embedding"] = embeddings[i]
            rows.append(data)

        # Check which article_ids already exist
        existing_query = (
            f"SELECT article_id FROM {self._table('article_embeddings')} "
            f"WHERE article_id IN UNNEST(@ids)"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", ids)]
        )
        existing_rows = await self._run_sync(
            lambda: list(self.bq_client.query(existing_query, job_config=job_config).result())
        )
        existing_ids = {r["article_id"] for r in existing_rows}

        # Filter to new rows only
        new_rows = [r for r in rows if r["article_id"] not in existing_ids]
        if not new_rows:
            logger.info(f"[EMBEDDINGS] All {len(ids)} articles already indexed")
            return 0

        # Insert new rows
        table_ref = f"{self.full_dataset}.article_embeddings"
        errors = await self._run_sync(
            lambda: self.bq_client.insert_rows_json(table_ref, new_rows)
        )

        if errors:
            logger.warning(f"[EMBEDDINGS] Insert errors: {errors[:3]}")
            return 0

        logger.info(f"[EMBEDDINGS] Indexed {len(new_rows)} articles via Vertex AI")
        return len(new_rows)

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> SearchResults:
        """
        Semantic search using BigQuery VECTOR_SEARCH.

        Args:
            query: Search query text
            n_results: Maximum results to return
            filters: Optional filters (e.g., {"domain": "quantum"})

        Returns:
            SearchResults with ranked results
        """
        # Generate query embedding
        query_embedding = await self._run_sync(
            lambda: self._embed([query])[0]
        )

        # Build the VECTOR_SEARCH query
        embedding_literal = "[" + ", ".join(str(v) for v in query_embedding) + "]"

        where_clause = ""
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"base.{key} = '{value}'")
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"""
SELECT
    base.article_id,
    base.title,
    base.url,
    base.document_text,
    base.source_name,
    base.primary_category,
    base.priority,
    base.relevance_score,
    base.domain,
    base.published_at,
    distance
FROM VECTOR_SEARCH(
    TABLE {self._table('article_embeddings')},
    'embedding',
    (SELECT {embedding_literal} AS embedding),
    top_k => {n_results},
    distance_type => 'COSINE'
)
{where_clause}
ORDER BY distance ASC
LIMIT {n_results}
"""

        try:
            rows = await self._run_sync(
                lambda: list(self.bq_client.query(sql).result())
            )
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Vector search error: {e}")
            return SearchResults(query=query)

        search_results = []
        for row in rows:
            row_dict = dict(row)
            distance = row_dict.get("distance", 1.0)
            search_results.append(SearchResult(
                article_id=row_dict.get("article_id", ""),
                title=row_dict.get("title", ""),
                url=row_dict.get("url", ""),
                summary=row_dict.get("document_text", ""),
                score=1.0 - distance,  # Convert distance to similarity
                metadata={
                    "source_name": row_dict.get("source_name", ""),
                    "primary_category": row_dict.get("primary_category", ""),
                    "priority": row_dict.get("priority", ""),
                    "relevance_score": row_dict.get("relevance_score", 0.5),
                    "domain": row_dict.get("domain", ""),
                    "published_at": str(row_dict.get("published_at", "")),
                },
            ))

        return SearchResults(
            query=query,
            results=search_results,
            total=len(search_results),
        )

    def count(self) -> int:
        """Get total number of indexed documents."""
        query = f"SELECT COUNT(*) as cnt FROM {self._table('article_embeddings')}"
        result = list(self.bq_client.query(query).result())
        return result[0]["cnt"] if result else 0
