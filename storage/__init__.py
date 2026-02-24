"""
Storage Module
==============

Provides storage abstraction for development (SQLite/ChromaDB) and production (BigQuery/Vertex AI).

STORAGE BACKENDS:
- SQLite: Local development (default)
- BigQuery: GCP production (when GCP_PROJECT_ID is set)

EMBEDDINGS BACKENDS:
- ChromaDB + sentence-transformers: Local development (default)
- BigQuery Vector Search + Vertex AI: GCP production (when GCP_PROJECT_ID is set)

Usage:
    from storage import get_storage, ClassifiedArticle
    storage = get_storage()
    await storage.save_articles(articles)
"""

import os
import logging
from typing import Optional

from .base import StorageBackend, ClassifiedArticle
from .sqlite import SQLiteStorage

logger = logging.getLogger(__name__)

__all__ = [
    "get_storage",
    "close_storage",
    "StorageBackend",
    "ClassifiedArticle",
    "SQLiteStorage",
    "get_embeddings_store",
]

# Singleton instances
_storage_instance: Optional[StorageBackend] = None


def get_storage(
    db_path: Optional[str] = None,
    force_new: bool = False,
    backend: Optional[str] = None,
) -> StorageBackend:
    """
    Factory function to get storage backend.

    Selects backend based on environment:
    - If GCP_PROJECT_ID is set -> BigQuery
    - Otherwise -> SQLite

    Args:
        db_path: Override SQLite database path
        force_new: Force create new instance (ignore singleton)
        backend: Force specific backend ("sqlite", "bigquery", "auto")

    Returns:
        StorageBackend instance
    """
    global _storage_instance

    if _storage_instance is not None and not force_new:
        return _storage_instance

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    backend = backend or os.getenv("STORAGE_BACKEND", "auto")
    gcp_project = os.getenv("GCP_PROJECT_ID")

    if backend == "auto":
        use_bigquery = bool(gcp_project)
    elif backend == "bigquery":
        use_bigquery = True
    elif backend == "sqlite":
        use_bigquery = False
    else:
        raise ValueError(f"Unknown storage backend: {backend}")

    if use_bigquery:
        from .bigquery import BigQueryStorage
        _storage_instance = BigQueryStorage(
            project_id=gcp_project,
            dataset_id=os.getenv("BQ_DATASET_ID", "quantum_ai_hub"),
            location=os.getenv("GCP_REGION", "us-central1"),
        )
        logger.info(f"[STORAGE] Using BigQuery: {gcp_project}")
        return _storage_instance

    # SQLite for development
    path = db_path or os.getenv("SQLITE_DB_PATH", "data/quantum_intel.db")
    _storage_instance = SQLiteStorage(db_path=path)
    logger.info(f"[STORAGE] Using SQLite: {path}")

    return _storage_instance


async def close_storage() -> None:
    """Close the global storage instance."""
    global _storage_instance
    if _storage_instance:
        await _storage_instance.close()
        _storage_instance = None
        logger.info("[STORAGE] Storage connection closed")


# Embeddings store singleton
_embeddings_instance = None


def get_embeddings_store(
    persist_directory: Optional[str] = None,
    force_new: bool = False,
):
    """
    Factory function to get embeddings/vector store.

    Selects backend based on environment:
    - If GCP_PROJECT_ID is set -> Vertex AI + BigQuery Vector Search
    - Otherwise -> ChromaDB + sentence-transformers (local)
    """
    global _embeddings_instance

    if _embeddings_instance is not None and not force_new:
        return _embeddings_instance

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    gcp_project = os.getenv("GCP_PROJECT_ID")
    embeddings_backend = os.getenv("EMBEDDINGS_BACKEND", "auto")

    use_vertex = (
        (embeddings_backend == "auto" and bool(gcp_project))
        or embeddings_backend == "vertex"
    )

    if use_vertex:
        from .vertex_embeddings import VertexEmbeddingsStore
        _embeddings_instance = VertexEmbeddingsStore(
            project_id=gcp_project,
            dataset_id=os.getenv("BQ_DATASET_ID", "quantum_ai_hub"),
            location=os.getenv("GCP_REGION", "us-central1"),
        )
        logger.info("[EMBEDDINGS] Using Vertex AI + BigQuery Vector Search")
    else:
        path = persist_directory or os.getenv("EMBEDDINGS_PATH", "data/embeddings")
        from .embeddings import get_chromadb_store
        _embeddings_instance = get_chromadb_store(persist_directory=path)
        logger.info(f"[EMBEDDINGS] Using ChromaDB: {path}")

    return _embeddings_instance
