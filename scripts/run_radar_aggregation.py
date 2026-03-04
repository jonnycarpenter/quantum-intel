import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime
import json

from config.settings import IngestionConfig
from storage.bigquery import BigQueryStorage
from utils.logger import get_logger

logger = get_logger(__name__)

async def run_radar_aggregation():
    """
    Calculates Maturity Radar metrics based on the last 30 days of data
    from articles and papers, then stores them in the maturity_radar_metrics table.
    """
    # Assuming GCP_PROJECT_ID and BQ_DATASET_ID are in the env
    config = IngestionConfig()
    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0436975498")
    dataset_id = os.getenv("BQ_DATASET_ID", "quantum_ai_hub")

    # BigQueryStorage expects explicit kwargs
    storage = BigQueryStorage(project_id=project_id, dataset_id=dataset_id)
    # _initialize_dataset() is called synchronously in BigQueryStorage.__init__
    
    # 1. Define the categories we want on the radar for Quantum & AI
    quantum_categories = [
        ("Hardware & Error Correction", "hardware_error_correction"),
        ("Financial Services", "financial_services"),
        ("Drug Discovery & Health", "drug_discovery_healthcare"),
        ("Cybersecurity & PQC", "cybersecurity_pqc"),
        ("Supply Chain & Logistics", "supply_chain_optimization"),
        ("Energy & Materials", "energy_climate_materials")
    ]
    
    ai_categories = [
        ("Models & Products", "models_products"),
        ("Enterprise Architecture", "enterprise_architecture"),
        ("Infrastructure & Hardware", "infrastructure_hardware"),
        ("Safety & Alignment", "safety_alignment"),
        ("Research & Open Source", "research_open_source")
    ]
    
    # 2. Extract 30 day velocity metrics using BigQuery
    today = datetime.now().date()
    
    query = """
    WITH BinnedArticles AS (
      SELECT 
        CASE
          -- Quantum Binning
          WHEN primary_category IN ('hardware_milestone', 'error_correction', 'algorithm_research') THEN 'hardware_error_correction'
          WHEN primary_category IN ('use_case_drug_discovery', 'use_case_healthcare') THEN 'drug_discovery_healthcare'
          WHEN primary_category IN ('use_case_finance', 'market_analysis') THEN 'financial_services'
          WHEN primary_category IN ('use_case_cybersecurity', 'policy_regulation', 'geopolitics') THEN 'cybersecurity_pqc'
          WHEN primary_category IN ('use_case_optimization', 'use_case_supply_chain') THEN 'supply_chain_optimization'
          WHEN primary_category IN ('use_case_energy_materials', 'use_case_climate') THEN 'energy_climate_materials'
          -- AI Binning
          WHEN primary_category IN ('ai_model_release', 'ai_product_launch') THEN 'models_products'
          WHEN primary_category IN ('ai_use_case_enterprise', 'ai_use_case_finance', 'use_case_ai_ml') THEN 'enterprise_architecture'
          WHEN primary_category IN ('ai_infrastructure', 'hardware_milestone') THEN 'infrastructure_hardware'
          WHEN primary_category IN ('ai_safety_alignment', 'policy_regulation', 'geopolitics') THEN 'safety_alignment'
          WHEN primary_category IN ('ai_research_breakthrough', 'ai_open_source') THEN 'research_open_source'
          ELSE NULL
        END as radar_category,
        domain,
        id,
        relevance_score
      FROM `gen-lang-client-0436975498.quantum_ai_hub.articles`
      WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    ),
    BinnedPapers AS (
      SELECT
        CASE
          WHEN use_case_category IN ('hardware_milestone', 'error_correction', 'algorithm_research') THEN 'hardware_error_correction'
          WHEN use_case_category IN ('use_case_drug_discovery', 'use_case_healthcare') THEN 'drug_discovery_healthcare'
          WHEN use_case_category IN ('use_case_finance', 'market_analysis') THEN 'financial_services'
          WHEN use_case_category IN ('use_case_cybersecurity', 'policy_regulation', 'geopolitics') THEN 'cybersecurity_pqc'
          WHEN use_case_category IN ('use_case_optimization', 'use_case_supply_chain') THEN 'supply_chain_optimization'
          WHEN use_case_category IN ('use_case_energy_materials', 'use_case_climate') THEN 'energy_climate_materials'
          ELSE NULL
        END as radar_category,
        'quantum' as domain,
        arxiv_id,
        relevance_score
      FROM `gen-lang-client-0436975498.quantum_ai_hub.papers`
      WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    ),
    AggArticles AS (
      SELECT 
        radar_category as primary_category,
        domain,
        COUNT(id) as article_count,
        AVG(relevance_score) as avg_article_relevance
      FROM BinnedArticles
      WHERE radar_category IS NOT NULL
      GROUP BY radar_category, domain
    ),
    AggPapers AS (
      SELECT 
        radar_category as primary_category,
        domain,
        COUNT(arxiv_id) as paper_count,
        AVG(relevance_score) as avg_paper_relevance
      FROM BinnedPapers
      WHERE radar_category IS NOT NULL
      GROUP BY radar_category, domain
    )
    SELECT
      COALESCE(a.primary_category, p.primary_category) as category_id,
      COALESCE(a.domain, p.domain) as domain,
      COALESCE(a.article_count, 0) as article_count,
      COALESCE(p.paper_count, 0) as paper_count,
      COALESCE(a.avg_article_relevance, 0.0) as avg_article_relevance,
      COALESCE(p.avg_paper_relevance, 0.0) as avg_paper_relevance
    FROM AggArticles a
    FULL OUTER JOIN AggPapers p 
      ON a.primary_category = p.primary_category AND a.domain = p.domain
    """
    
    try:
        from google.cloud import bigquery
        client = storage.client
        job = client.query(query)
        results = job.result()
        
        # 3. Process into final metrics dictionary
        metrics_by_cat = {}
        for row in results:
            cat_id = row.category_id
            domain = row.domain
            key = f"{domain}_{cat_id}"
            
            # Simple scoring metric: combine volume + relevance
            # (Weight papers slightly higher for true "maturity" signal)
            total_volume = row.article_count + (row.paper_count * 1.5)
            avg_rel = max(row.avg_article_relevance, row.avg_paper_relevance)
            
            # Normalize to a 0-100 scale (heuristic max volume of ~50 per month)
            normalized_volume = min(100.0, (total_volume / 50.0) * 100.0)
            
            # Final score = 70% volume/traction + 30% relevance density
            signal_score = (normalized_volume * 0.7) + (avg_rel * 0.3)
            
            metrics_by_cat[key] = {
                "article_count": row.article_count,
                "paper_count": row.paper_count,
                "avg_relevance": avg_rel,
                "signal_score": min(100.0, round(signal_score, 1))
            }
            
        # 4. Write results to the BQ maturity_radar_metrics table.
        # Strategy: Truncate the table first (metadata op, not DML — bypasses streaming buffer),
        # then insert fresh rows via the streaming API.
        rows_to_insert = []
        
        # Helper to generate rows
        def build_rows(category_list, domain_name):
            for display_name, cat_id in category_list:
                key = f"{domain_name}_{cat_id}"
                data = metrics_by_cat.get(key, {
                    "article_count": 0, "paper_count": 0, 
                    "avg_relevance": 0.0, "signal_score": 10.0 # Baseline 10
                })
                
                rows_to_insert.append({
                    "calculated_date": today.isoformat(),
                    "domain": domain_name,
                    "category_name": display_name,
                    "signal_score": max(10.0, data["signal_score"]), # Never completely zero on radar
                    "article_count": data["article_count"],
                    "paper_count": data["paper_count"],
                    "avg_relevance": data["avg_relevance"],
                    "velocity_trend": 0.0 # Placeholder for future MoM % growth logic
                })
                
        build_rows(quantum_categories, "quantum")
        build_rows(ai_categories, "ai")
        
        # Truncate the metrics table using the BigQuery Jobs API (CREATE OR REPLACE)
        # This bypasses the streaming buffer limitation that blocks DML operations.
        from storage.bigquery_schemas import BQ_MATURITY_RADAR_METRICS_DDL
        fq_table = f"{project_id}.{dataset_id}.maturity_radar_metrics"
        truncate_ddl = BQ_MATURITY_RADAR_METRICS_DDL.replace(
            "CREATE TABLE IF NOT EXISTS", "CREATE OR REPLACE TABLE"
        ).format(table=fq_table)
        client.query(truncate_ddl).result()
        logger.info("[RADAR] Truncated maturity_radar_metrics table")
        
        # Insert fresh metrics via streaming API
        errors = client.insert_rows_json(fq_table, rows_to_insert)
        
        if errors:
            logger.error(f"Error inserting radar metrics: {errors}")
        else:
            logger.info(f"Successfully calculated and inserted {len(rows_to_insert)} radar metrics for {today.isoformat()}")

    except Exception as e:
        logger.error(f"Failed to calculate radar metrics: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_radar_aggregation())
