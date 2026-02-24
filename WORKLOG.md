# Quantum + AI Intel Hub — Work Log

## Completed

### Sessions 1-2 (Feb 2026)
- Built core ingestion pipeline: RSS, Tavily, ArXiv, StockNews
- Built SEC/EDGAR pipeline: 10-K, 10-Q, 8-K with nugget extraction
- Built earnings transcript pipeline with quote extraction
- Built podcast pipeline: transcription (AssemblyAI) + quote extraction
- Fixed LLM client for Claude Code proxy (HTTP/1.1, SSE parsing, temperature exclusion)
- Fixed SEC section item codes for 10-Q and 8-K
- Fixed `_salvage_json` to handle mid-object JSON truncation
- Fixed episode dedup (deterministic MD5 episode_id from audio_url)
- **Data in DB:** 356 podcast quotes (21 transcripts, 9 podcasts), 319 SEC nuggets (11 tickers)

### Session 3 (Feb 2026)
- Diagnosed earnings quote extraction failure: `EarningsConfig.extraction_max_tokens` was 4096 — JSON truncated mid-array causing all parses to fail silently
- Fixed: raised `extraction_max_tokens` to 16,000 in `config/settings.py` (matches SEC extractor)
- Added `--re-extract` CLI flag to `scripts/run_earnings.py` for re-running extraction on saved transcripts without quotes
- Added `get_transcripts_without_quotes()` method to `SQLiteStorage`
- Confirmed stocks pipeline: 900 snapshots saved (yfinance, 20 tickers, 60 days)
- Confirmed StockNews pipeline: 50 articles per run, all API keys present
- Populated earnings DB: 14 transcripts (7 core quantum tickers, Q2–Q4 2025), ~280+ quotes extracted
- **All pipelines now operational:** RSS, StockNews, Stocks, SEC, Podcasts, Earnings

### Session 4 (Feb 2026) — GCP Migration
- Implemented BigQuery storage backend (`storage/bigquery.py`) — all 45+ StorageBackend ABC methods
- Created BigQuery table schemas (`storage/bigquery_schemas.py`) — 12 tables with ARRAY, TIMESTAMP, JSON types
- Implemented Vertex AI embeddings store (`storage/vertex_embeddings.py`) — text-embedding-005 + VECTOR_SEARCH
- Updated storage factory (`storage/__init__.py`) — auto-routes to BigQuery/Vertex when `GCP_PROJECT_ID` is set
- Fixed 3 scripts (`run_earnings.py`, `run_sec.py`, `run_podcast.py`) to use `get_storage()` factory instead of hardcoded `SQLiteStorage`
- Created `Dockerfile` + `.dockerignore` for Cloud Run Jobs
- Created deploy scripts: `deploy/setup_infra.sh` (GCP APIs, dataset, secrets, IAM), `deploy/cloud_run_jobs.sh` (9 jobs), `deploy/setup_scheduler.sh` (9 cron schedules)
- Added GCP dependencies to `requirements.txt`
- Created `README_GCP_DEPLOYMENT.md` with full deployment guide
- Local SQLite path preserved — factory pattern switches based on environment

---

## Next Session

### Deploy to GCP
1. Run `deploy/setup_infra.sh` to create infrastructure
2. Populate secrets in Secret Manager
3. Run `deploy/cloud_run_jobs.sh` to create Cloud Run Jobs
4. Run `deploy/setup_scheduler.sh` to create cron triggers
5. Test: `gcloud run jobs execute quantum-rss-ingestion --region us-central1`
6. Optional: Run `scripts/migrate_sqlite_to_bigquery.py` to backfill existing data

### Remaining Work
- Write `tests/test_bigquery_storage.py` and `tests/test_vertex_embeddings.py`
- Write `scripts/migrate_sqlite_to_bigquery.py` for one-time data migration
- Create BigQuery vector index on `article_embeddings.embedding` column
- Monitor costs and tune Cloud Run Job resource limits
