from typing import List, Dict, Any, Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, BackgroundTasks
import asyncio

from config.settings import IngestionConfig
from storage.bigquery import BigQueryStorage
from scripts.run_radar_aggregation import run_radar_aggregation
from utils.logger import get_logger
import os

logger = get_logger(__name__)
router = APIRouter()

def _get_storage() -> BigQueryStorage:
    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0436975498")
    dataset_id = os.getenv("BQ_DATASET_ID", "quantum_ai_hub")
    return BigQueryStorage(project_id=project_id, dataset_id=dataset_id)

@router.get("/metrics/{domain}")
async def get_radar_metrics(domain: str) -> Dict[str, Any]:
    """
    Fetch the latest maturity radar metrics for a given domain ('quantum' or 'ai').
    Used to populate the frontend Recharts Radar graph.
    """
    if domain not in ["quantum", "ai"]:
        raise HTTPException(status_code=400, detail="Domain must be 'quantum' or 'ai'")
        
    storage = _get_storage()
    
    query = f"""
    SELECT 
        category_name,
        signal_score,
        article_count,
        paper_count,
        avg_relevance
    FROM `{storage.full_dataset}.maturity_radar_metrics`
    WHERE domain = @domain
        AND calculated_date = (
            SELECT MAX(calculated_date) 
            FROM `{storage.full_dataset}.maturity_radar_metrics`
            WHERE domain = @domain
        )
    ORDER BY signal_score DESC
    """
    
    job_config = storage.client.job_config = type("JobConfig", (), {})()
    from google.cloud import bigquery
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("domain", "STRING", domain)
        ]
    )
    
    try:
        results = await storage._run_sync(
            lambda: list(storage.client.query(query, job_config=job_config).result())
        )
        
        metrics = []
        for r in results:
            metrics.append({
                "subject": r.category_name,
                "A": r.signal_score,       # For the main radar polygon
                "fullMark": 100,           # Max scale of radar
                "articles": r.article_count,
                "papers": r.paper_count,
                "relevance": r.avg_relevance
            })
            
        return {
            "status": "success",
            "domain": domain,
            "data": metrics
        }
    except Exception as e:
        logger.error(f"[API] Error fetching radar metrics for {domain}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch radar metrics")

@router.post("/trigger")
async def trigger_radar_aggregation(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Manually trigger the background calculation of the Maturity Radar metrics.
    """
    background_tasks.add_task(asyncio.run, run_radar_aggregation())
    return {
        "status": "success",
        "message": "Radar aggregation started in the background."
    }
