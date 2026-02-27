"""
Embeddings Content Type Configuration
======================================

Registry of content types supported by the embeddings stores.
Shared between ChromaDB (embeddings.py) and Vertex AI (vertex_embeddings.py).
"""

from typing import Dict


CONTENT_TYPE_CONFIG: Dict[str, Dict[str, str]] = {
    "articles": {
        "bq_table": "article_embeddings",
        "chromadb_collection": "quantum_articles",
        "id_field": "article_id",
        "source_type": "articles",
    },
    "sec_nuggets": {
        "bq_table": "sec_nugget_embeddings",
        "chromadb_collection": "quantum_sec_nuggets",
        "id_field": "nugget_id",
        "source_type": "sec_nuggets",
    },
    "earnings_quotes": {
        "bq_table": "earnings_quote_embeddings",
        "chromadb_collection": "quantum_earnings_quotes",
        "id_field": "quote_id",
        "source_type": "earnings_quotes",
    },
    "podcast_quotes": {
        "bq_table": "podcast_quote_embeddings",
        "chromadb_collection": "quantum_podcast_quotes",
        "id_field": "quote_id",
        "source_type": "podcast_quotes",
    },
    "case_studies": {
        "bq_table": "case_study_embeddings",
        "chromadb_collection": "quantum_case_studies",
        "id_field": "case_study_id",
        "source_type": "case_studies",
    },
}

VALID_CONTENT_TYPES = set(CONTENT_TYPE_CONFIG.keys())
