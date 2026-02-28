"""
Stats API Routes
================

Endpoints for system stats and health.
Powers the Settings page and status bar.
"""

import os
from fastapi import APIRouter

from api.dependencies import get_db

router = APIRouter()


@router.get("")
async def get_system_stats():
    """
    Get system-wide statistics for the status bar and settings page.
    """
    storage = get_db()

    # Core stats
    stats = await storage.get_stats(hours=720)  # 30 days

    # Embeddings count
    embeddings_count = 0
    try:
        from storage import get_embeddings_store
        emb = get_embeddings_store()
        if emb:
            embeddings_count = emb.count()
    except Exception:
        pass

    # API key status (masked)
    api_keys = {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "exa": bool(os.getenv("EXA_API_KEY")),
        "api_ninjas": bool(os.getenv("API_NINJA_API_KEY")),
        "stocknews": bool(os.getenv("STOCKNEWS_API_KEY")),
    }

    return {
        "stats": stats,
        "embeddings_count": embeddings_count,
        "api_keys": api_keys,
        "storage_backend": os.getenv("STORAGE_BACKEND", "sqlite"),
        "db_path": os.getenv("SQLITE_DB_PATH", "data/quantum_intel.db"),
    }
