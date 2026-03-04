"""Quick check of BigQuery table row counts."""
import os
from dotenv import load_dotenv
load_dotenv()

from google.cloud import bigquery

project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET_ID', 'quantum_ai_hub')
print(f'Project: {project}, Dataset: {dataset}')

client = bigquery.Client(project=project)

tables = [
    'case_studies', 'case_study_embeddings',
    'podcast_quotes', 'podcast_transcripts',
    'articles', 'papers', 'sec_nuggets', 'earnings_quotes',
]

for t in tables:
    try:
        q = f"SELECT COUNT(*) as cnt FROM `{project}.{dataset}.{t}`"
        result = list(client.query(q).result())
        print(f"  {t}: {result[0].cnt} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

# Check if podcast_quotes has any empty-string published_at
print("\n--- Podcast quotes with empty published_at ---")
try:
    q = f"SELECT COUNT(*) as cnt FROM `{project}.{dataset}.podcast_quotes` WHERE published_at IS NULL"
    result = list(client.query(q).result())
    print(f"  NULL published_at: {result[0].cnt}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check latest podcast_quotes
print("\n--- Latest 5 podcast quotes ---")
try:
    q = f"SELECT quote_id, podcast_name, episode_title, published_at, extracted_at FROM `{project}.{dataset}.podcast_quotes` ORDER BY extracted_at DESC LIMIT 5"
    for row in client.query(q).result():
        print(f"  {row.podcast_name} | {row.episode_title[:40]} | pub={row.published_at} | ext={row.extracted_at}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check latest podcast_transcripts
print("\n--- Latest 5 podcast transcripts ---")
try:
    q = f"SELECT transcript_id, podcast_name, episode_title, published_at, ingested_at FROM `{project}.{dataset}.podcast_transcripts` ORDER BY ingested_at DESC LIMIT 5"
    for row in client.query(q).result():
        print(f"  {row.podcast_name} | {row.episode_title[:40]} | pub={row.published_at} | ing={row.ingested_at}")
except Exception as e:
    print(f"  ERROR: {e}")
