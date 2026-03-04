"""Check the state of podcast data in BigQuery and test the pipeline."""
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from google.cloud import bigquery

project = os.environ.get('GCP_PROJECT_ID')
dataset = os.environ.get('BQ_DATASET_ID', 'quantum_ai_hub')
client = bigquery.Client(project=project)

print("=== BigQuery Table Counts ===")
for t in ['podcast_transcripts', 'podcast_quotes', 'case_studies', 'case_study_embeddings']:
    q = f"SELECT COUNT(*) as cnt FROM `{project}.{dataset}.{t}`"
    result = list(client.query(q).result())
    print(f"  {t}: {result[0].cnt} rows")

print("\n=== Podcast Quotes - Date Range ===")
q = f"""
SELECT 
    MIN(extracted_at) as earliest, 
    MAX(extracted_at) as latest,
    COUNT(DISTINCT podcast_name) as podcasts,
    COUNT(DISTINCT episode_title) as episodes
FROM `{project}.{dataset}.podcast_quotes`
"""
for row in client.query(q).result():
    print(f"  Earliest: {row.earliest}")
    print(f"  Latest: {row.latest}")
    print(f"  Podcasts: {row.podcasts}, Episodes: {row.episodes}")

print("\n=== Podcast Quotes by Podcast ===")
q = f"""
SELECT podcast_name, COUNT(*) as quote_count, MAX(extracted_at) as latest_extract
FROM `{project}.{dataset}.podcast_quotes`
GROUP BY podcast_name
ORDER BY quote_count DESC
"""
for row in client.query(q).result():
    print(f"  {row.podcast_name}: {row.quote_count} quotes (latest: {row.latest_extract})")

print("\n=== Test: Can we discover new podcast episodes? ===")
try:
    import sys
    sys.path.insert(0, '.')
    from config.podcast_sources import PODCAST_SOURCES, AI_PODCAST_SOURCES
    from fetchers.podcast import PodcastFetcher
    
    fetcher = PodcastFetcher()
    
    # Try discovering from one quantum + one AI podcast
    test_sources = [PODCAST_SOURCES[0], AI_PODCAST_SOURCES[0]]
    for src in test_sources:
        print(f"\n  Testing: {src.name} ({src.domain})")
        print(f"    RSS: {src.rss_url}")
        episodes = asyncio.run(fetcher.discover_episodes(src, max_episodes=1))
        if episodes:
            ep = episodes[0]
            print(f"    Found: {ep.title[:60]}")
            print(f"    Audio URL: {ep.audio_url[:80] if ep.audio_url else 'None'}")
            print(f"    Published: {ep.published_at}")
        else:
            print(f"    No episodes found!")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
