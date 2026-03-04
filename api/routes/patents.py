from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any, List

from config.settings import IngestionConfig
from storage.bigquery import BigQueryStorage
from storage.sqlite import SQLiteStorage

router = APIRouter()

def get_storage() -> Any:
    import os
    config = IngestionConfig()
    if os.environ.get("STORAGE_BACKEND", "bigquery") == "bigquery":
        project_id = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0436975498")
        dataset_id = os.environ.get("BQ_DATASET_ID", "quantum_ai_hub")
        return BigQueryStorage(project_id=project_id, dataset_id=dataset_id)
    return SQLiteStorage(config)

@router.get("/recent/{domain}")
async def get_recent_patents(
    domain: str,
    limit: int = Query(50, ge=1, le=100),
    storage: Any = Depends(get_storage)
) -> Dict[str, Any]:
    """Get recent patent filings for a specific domain."""
    try:
        if domain not in ["quantum", "ai"]:
            raise HTTPException(status_code=400, detail="Invalid domain. Must be 'quantum' or 'ai'")
            
        patents = await storage.get_recent_patents(domain=domain, limit=limit)
        
        # Convert dataclasses to dicts for JSON serialization, or assume pydantic/dataclass serialization works
        # Data objects from DB might be models.patent.Patent
        patents_dict = [p.to_dict() if hasattr(p, 'to_dict') else p for p in patents]
        
        return {
            "status": "success",
            "domain": domain,
            "data": patents_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await storage.close()
