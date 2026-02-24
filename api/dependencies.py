"""
FastAPI Dependencies
====================

Shared dependencies: storage instance, embeddings store.
"""

import os
import sys
from functools import lru_cache

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from storage import get_storage, StorageBackend


@lru_cache()
def get_db() -> StorageBackend:
    """Get singleton storage backend."""
    return get_storage()
