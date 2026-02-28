"""
Create BigQuery Vector Indexes
================================

Creates IVF vector indexes on all embedding tables for faster
VECTOR_SEARCH queries. Safe to re-run (uses IF NOT EXISTS).

Requires:
    - GCP_PROJECT_ID set in .env
    - Embedding tables already created (via bigquery_schemas.py)

Usage:
    python scripts/create_vector_indexes.py
    python scripts/create_vector_indexes.py --dry-run
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.bigquery_schemas import get_vector_index_ddl
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create vector indexes on BigQuery embedding tables",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print DDL statements without executing",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    gcp_project = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("BQ_DATASET_ID", "quantum_ai_hub")
    full_dataset = f"{gcp_project}.{dataset_id}"

    if not gcp_project and not args.dry_run:
        logger.error("GCP_PROJECT_ID not set. Use --dry-run to preview DDL.")
        return

    ddl_statements = get_vector_index_ddl(full_dataset)

    if args.dry_run:
        logger.info("[DRY RUN] Vector index DDL statements:\n")
        for ddl in ddl_statements:
            print(ddl)
            print()
        logger.info(f"Total: {len(ddl_statements)} indexes")
        return

    # Execute DDL
    from google.cloud import bigquery
    client = bigquery.Client(project=gcp_project)

    created = 0
    for ddl in ddl_statements:
        try:
            logger.info(f"Creating index: {ddl.split(chr(10))[0]}...")
            client.query(ddl).result()
            created += 1
            logger.info("  ✓ Done")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("  ⊘ Already exists")
                created += 1
            else:
                logger.error(f"  ✗ Error: {e}")

    logger.info(f"\n{created}/{len(ddl_statements)} vector indexes ready.")
    client.close()


if __name__ == "__main__":
    main()
