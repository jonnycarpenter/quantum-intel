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

### Session 5 (Feb 2026) — GCP Deployment Complete
- Deployed full infrastructure to GCP: Cloud Run Jobs, Cloud Scheduler, BigQuery, Vertex AI
- Set up Cloud Build CI/CD (push to `master` triggers build → deploy)
- Configured `min-instances: 1` for warm starts
- All 10 Cloud Run Jobs operational with cron schedules
- Verified end-to-end: ingestion, SEC, earnings, podcasts running in production
### Session 6 (Feb 2026) — Weekly Briefings + Page-Level Domain Selectors
- Added `ai-weekly-briefing` Cloud Run Job (separate from quantum)
- Staggered Monday scheduling: AI at 12:00 UTC, Quantum at 12:45 UTC
- Updated `cloudbuild.yaml`, `cloud_run_jobs.sh`, `setup_scheduler.sh`
- Created reusable `DomainToggle` component for page-level domain switching
- Migrated domain toggle from App header into each page (Briefing, Explore, Markets, Research, Filings)
- Each page now manages its own domain state independently
- Generated and saved manual briefings for both quantum and AI domains
- TypeScript compiles cleanly with all changes

### Session 7 (Feb 2026) — Phase 6 Case Study Extraction
- Implemented full case study extraction layer (`models/case_study.py`, `processing/case_study_extractor.py`)
- 10 domain+source LLM prompt combinations (2 domains x 5 source types)
- Added `CaseStudyConfig` to `config/settings.py` (model, temperature, chunking, dedup thresholds)
- Extended StorageBackend ABC with 5 case study methods, implemented in SQLite + BigQuery
- Added `case_studies` + `case_study_embeddings` tables to BigQuery schemas
- Registered case study embeddings in `storage/embeddings_config.py`
- Created `scripts/run_case_studies.py` — standalone batch script with `--domain`, `--sources`, `--max-items`
- ArXiv: abstract-only extraction (no PDF ingestion)

### Session 8 (Feb 2026) — Case Studies Tab + Frontend Reskin
- Built Case Studies frontend page (`CaseStudiesPage.tsx`) with stats dashboard, filters (source, readiness, outcome), search
- Added backend API endpoints for case studies (`api/routes/case_studies.py`)
- Added Case Studies nav item to App.tsx
- Reskinned entire frontend from dark mode to light mode matching ketzerointelligence.ai
  - Swapped `@theme` palette: charcoal → off-white/white backgrounds, dark text
  - Adjusted badge opacity values across all pages for visibility on light backgrounds
  - Teal-branded chat bubbles
- Fixed `EARNINGS_TICKERS` → `EARNINGS_COMPANIES` import in `api/routes/earnings.py` and `api/routes/sec.py`

### Session 9 (Feb 2026) — Tests, Migration Script, Vector Index
- Wrote `tests/test_bigquery_storage.py` — 37 mock-based tests covering helpers, row conversion, all entity operations
- Wrote `tests/test_vertex_embeddings.py` — 22 mock-based tests covering all 5 content types, indexing, search, count
- All 59 new tests passing (no GCP credentials required)
- Created `scripts/migrate_sqlite_to_bigquery.py` — one-time migration across 12 tables, supports `--dry-run`, `--tables`, `--batch-size`
- Added `get_vector_index_ddl()` to `storage/bigquery_schemas.py` — IVF + COSINE indexes for all 5 embedding tables
- Created `scripts/create_vector_indexes.py` — standalone script to apply vector indexes, supports `--dry-run`

### Session 10 (Feb 2026) — Tavily → Exa Search Swap
- Full replacement of Tavily with Exa search API for better `published_date` reliability
- Created `fetchers/exa.py` — ExaFetcher using `search_and_contents()` with ISO 8601 date filtering
- Renamed config files: `tavily_queries.py` → `exa_queries.py`, `ai_tavily_queries.py` → `exa_ai_queries.py`
- Updated all variable names: `TAVILY_QUERIES` → `EXA_QUERIES`, `AI_TAVILY_QUERIES` → `AI_EXA_QUERIES`
- Updated `config/settings.py`: `tavily_api_key` → `exa_api_key`, added `exa_max_characters`
- Updated `orchestrator.py`, `scripts/run_ingestion.py`, `tools/web_search.py`, `api/routes/stats.py`
- Updated deploy: `cloudbuild.yaml`, `cloud_run_jobs.sh`, `setup_scheduler.sh`, `setup_infra.sh`
- Created `tests/test_exa.py` — 12 mock-based tests, all passing
- Deleted `fetchers/tavily.py`, `tests/test_tavily.py`, root-level `exa.py` (reference template leftover)
- Updated docs: `CLAUDE.md`, `README_INGESTION.md`, `.env.example`
- Swapped dependency: `tavily-python` → `exa-py` in `requirements.txt`
- **237 tests passing** (2 pre-existing failures in corpus_search.py unrelated to swap)

---

## Next Up

### Remaining Work
- Monitor costs and tune Cloud Run Job resource limits
- Add `EXA_API_KEY` to GCP Secret Manager and `.env`
