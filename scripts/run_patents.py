import asyncio
import argparse
import sys
import os

# Add project root to PYTHONPATH if run standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.patents import GooglePatentsFetcher
from storage.bigquery import BigQueryStorage
from storage.sqlite import SQLiteStorage
from config.settings import IngestionConfig
from utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Fetch and ingest patent data from Google Patents.")
    parser.add_argument("--domain", type=str, default="quantum", choices=["quantum", "ai"],
                        help="The domain to fetch patents for (determines company list).")
    parser.add_argument("--storage", type=str, default="bigquery", choices=["sqlite", "bigquery"],
                        help="Storage backend to use.")
    
    args = parser.parse_args()
    config = IngestionConfig()
    
    # Initialize storage
    if args.storage == "bigquery":
        project_id = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0436975498")
        dataset_id = os.environ.get("BQ_DATASET_ID", "quantum_ai_hub")
        storage = BigQueryStorage(project_id=project_id, dataset_id=dataset_id)
    else:
        storage = SQLiteStorage(config)
        
    # Configure companies based on domain
    if args.domain == "quantum":
        companies = ["Rigetti", "IonQ", "D-Wave", "IBM", "Google LLC", "Microsoft", "Quantinuum", "PsiQuantum", "Alice & Bob", "Pasqal", "QuEra"]
    else:
        companies = ["OpenAI", "Anthropic", "Mistral", "Google LLC", "Microsoft", "Meta Platforms", "xAI", "NVIDIA", "AMD"]

    logger.info(f"Starting patent ingestion for domain: {args.domain} (searching {len(companies)} companies)")
    
    fetcher = GooglePatentsFetcher(config, companies=companies, domain=args.domain)
    
    try:
        # Fetch patents
        patents = await fetcher.fetch_all(limit_per_company=10)
        logger.info(f"Fetched {len(patents)} total patents across all companies.")
        
        # Save to database
        if patents:
            saved_count = await storage.save_patents(patents)
            logger.info(f"Successfully saved {saved_count} new patents to the database.")
        else:
            logger.info("No patents found to save.")
            
    except Exception as e:
        logger.error(f"Error during patent ingestion: {e}", exc_info=True)
    finally:
        await storage.close()

if __name__ == "__main__":
    asyncio.run(main())
