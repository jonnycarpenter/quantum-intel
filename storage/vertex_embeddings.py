"""
Vertex AI Embeddings Store
===========================

GCP production vector search using Vertex AI text-embedding-005
and BigQuery VECTOR_SEARCH for semantic retrieval.

Supports multiple content types: articles, sec_nuggets, earnings_quotes, podcast_quotes.
Mirrors the EmbeddingsStore interface from embeddings.py (ChromaDB).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from google.cloud import bigquery

from .embeddings_config import CONTENT_TYPE_CONFIG, VALID_CONTENT_TYPES

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
    item_id: str
    title: str
    url: str
    summary: str
    score: float
    source_type: str = "articles"
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
    Stores vectors in BigQuery embedding tables.
    Queries via BigQuery VECTOR_SEARCH function.

    Supports multiple content types via the content_type parameter:
    - "articles" (default): article_embeddings table
    - "sec_nuggets": sec_nugget_embeddings table
    - "earnings_quotes": earnings_quote_embeddings table
    - "podcast_quotes": podcast_quote_embeddings table
    """

    EMBEDDING_MODEL = "text-embedding-005"
    EMBEDDING_DIM = 768
    BATCH_SIZE = 250  # Vertex AI batch limit

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "quantum_ai_hub",
        location: str = "us-central1",
        content_type: str = "articles",
    ):
        if not HAS_VERTEX:
            raise ImportError(
                "google-cloud-aiplatform not installed. "
                "Run: pip install google-cloud-aiplatform"
            )

        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(
                f"Unknown content type: {content_type}. "
                f"Valid types: {VALID_CONTENT_TYPES}"
            )

        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.full_dataset = f"{project_id}.{dataset_id}"
        self.bq_client = bigquery.Client(project=project_id)
        aiplatform.init(project=project_id, location=location)
        self._model = None

        # Content type configuration
        self.content_type = content_type
        self._config = CONTENT_TYPE_CONFIG[content_type]
        self._bq_table_name = self._config["bq_table"]
        self._id_field = self._config["id_field"]
        self._source_type = self._config["source_type"]

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
                "article_id": getattr(item, "id", getattr(item, "url", "")),
                "title": getattr(item, "title", "")[:200],
                "url": getattr(item, "url", ""),
                "source_name": getattr(item, "source_name", ""),
                "primary_category": getattr(item, "primary_category", ""),
                "priority": getattr(item, "priority", "medium"),
                "relevance_score": float(getattr(item, "relevance_score", 0.5)),
                "domain": getattr(item, "domain", "quantum"),
                "published_at": (
                    item.published_at.isoformat()
                    if getattr(item, "published_at", None) else None
                ),
            }

        elif self.content_type == "sec_nuggets":
            themes = item.themes
            if isinstance(themes, list):
                themes = ",".join(themes)
            return {
                "nugget_id": item.nugget_id,
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
                    item.filing_date.isoformat()
                    if getattr(item, "filing_date", None) else None
                ),
            }

        elif self.content_type == "earnings_quotes":
            themes = item.themes
            if isinstance(themes, list):
                themes = ",".join(themes)
            return {
                "quote_id": item.quote_id,
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
                "quote_id": item.quote_id,
                "podcast_name": item.podcast_name,
                "episode_title": item.episode_title,
                "speaker_name": item.speaker_name,
                "speaker_role": item.speaker_role,
                "quote_type": item.quote_type,
                "themes": themes,
                "sentiment": item.sentiment,
                "relevance_score": float(item.relevance_score),
                "published_at": item.published_at if isinstance(item.published_at, str) else (
                    item.published_at.isoformat() if getattr(item, "published_at", None) else None
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
                "extracted_at": (
                    item.extracted_at.isoformat()
                    if getattr(item, "extracted_at", None) else None
                ),
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
        item_data = []

        for item in items:
            doc_text = self._build_document_text(item)
            if not doc_text.strip():
                continue

            item_id = self._get_item_id(item)
            ids.append(item_id)
            documents.append(doc_text)

            metadata = self._build_metadata(item)
            metadata["document_text"] = doc_text
            item_data.append(metadata)

        if not ids:
            return 0

        # Generate embeddings
        embeddings = await self._run_sync(self._embed, documents)

        # Build rows with embeddings
        rows = []
        for i, data in enumerate(item_data):
            data["embedding"] = embeddings[i]
            rows.append(data)

        # Check which IDs already exist
        existing_query = (
            f"SELECT {self._id_field} FROM {self._table(self._bq_table_name)} "
            f"WHERE {self._id_field} IN UNNEST(@ids)"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", ids)]
        )
        existing_rows = await self._run_sync(
            lambda: list(self.bq_client.query(existing_query, job_config=job_config).result())
        )
        existing_ids = {r[self._id_field] for r in existing_rows}

        # Filter to new rows only
        new_rows = [r for r in rows if r[self._id_field] not in existing_ids]
        if not new_rows:
            logger.info(f"[EMBEDDINGS] All {len(ids)} {self.content_type} already indexed")
            return 0

        # Insert new rows
        table_ref = f"{self.full_dataset}.{self._bq_table_name}"
        errors = await self._run_sync(
            lambda: self.bq_client.insert_rows_json(table_ref, new_rows)
        )

        if errors:
            logger.warning(f"[EMBEDDINGS] Insert errors: {errors[:3]}")
            return 0

        logger.info(f"[EMBEDDINGS] Indexed {len(new_rows)} {self.content_type} via Vertex AI")
        return len(new_rows)

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
SELECT base.*, distance
FROM VECTOR_SEARCH(
    TABLE {self._table(self._bq_table_name)},
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

            # Build display title based on content type
            if self.content_type == "articles":
                title = row_dict.get("title", "")
            elif self.content_type == "sec_nuggets":
                ticker = row_dict.get("ticker", "")
                ntype = row_dict.get("nugget_type", "")
                title = f"{ticker} SEC: {ntype}" if ticker else ntype
            elif self.content_type == "earnings_quotes":
                speaker = row_dict.get("speaker_name", "")
                ticker = row_dict.get("ticker", "")
                title = f"{speaker} ({ticker})" if speaker else ticker
            elif self.content_type == "podcast_quotes":
                speaker = row_dict.get("speaker_name", "")
                podcast = row_dict.get("podcast_name", "")
                title = f"{speaker} on {podcast}" if speaker else podcast
            else:
                title = ""

            url = row_dict.get("url", "")

            # Build metadata (exclude embedding, distance, and document_text)
            metadata = {
                k: v for k, v in row_dict.items()
                if k not in ("embedding", "distance", "document_text")
            }

            search_results.append(SearchResult(
                item_id=row_dict.get(self._id_field, ""),
                title=title,
                url=url,
                summary=row_dict.get("document_text", ""),
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
        query = f"SELECT COUNT(*) as cnt FROM {self._table(self._bq_table_name)}"
        result = list(self.bq_client.query(query).result())
        return result[0]["cnt"] if result else 0
