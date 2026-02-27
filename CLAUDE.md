# Quantum + AI Intelligence Hub

Multi-agent AI system monitoring the quantum computing and AI ecosystems.

## Project Conventions

### Architecture
- **Local-first:** SQLite + ChromaDB for development; BigQuery + Vertex AI for production
- **Storage factory pattern:** `storage.get_storage()` auto-selects backend based on environment
- **Orchestrator pattern:** fetch → filter → dedup → classify → persist → embed
- **Domain-aware pipeline:** Single codebase serves both "quantum" and "ai" domains via `--domain` flag
- **Async everywhere:** All I/O operations use async/await (fetchers, storage, LLM calls)

### Code Style
- **Models:** Python dataclasses (not Pydantic)
- **Type hints:** On all function signatures
- **Logging:** Structured with module prefixes: `[FETCHER]`, `[CLASSIFIER]`, `[STORAGE]`, `[ORCHESTRATOR]`
- **Imports:** Use `from quantum_intel.module import X` pattern

### Module Layout
```
config/       - Configuration constants (feeds, queries, tickers, prompts)
models/       - Dataclasses for articles, papers, stocks, earnings, SEC filings, case studies
fetchers/     - Data source clients (RSS, Tavily, ArXiv, yfinance, StockNews, SEC EDGAR, API Ninjas)
processing/   - Classification, dedup, scoring, quote extraction, nugget extraction, case study extraction
storage/      - SQLite/BigQuery backends + ChromaDB/Vertex embeddings
utils/        - Logger, LLM client, date utilities
agents/       - Intelligence + router agents (Phase 3)
tools/        - Agent tools: corpus search, web search, stock data (Phase 3)
scripts/      - CLI entry points (run_ingestion, run_digest, run_earnings, run_sec, run_case_studies)
deploy/       - GCP deploy scripts (setup_infra, cloud_run_jobs, setup_scheduler)
tests/        - pytest tests per module
```

### Environment Variables
Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude API (classification + agents)
- `TAVILY_API_KEY` — Web search (Phase 2)

Optional:
- `API_NINJA_API_KEY` — Earnings transcripts (Phase 4A)
- `STOCKNEWS_API_KEY` — Stock news articles (Phase 4A)
- `SECIO_API_KEY` — SEC.io enhanced filing access (Phase 4A, optional)
- `SEC_USER_AGENT` — Required for EDGAR API (Phase 4A)
- `OPENAI_API_KEY` — Whisper transcription (Phase 4)
- `GCP_PROJECT_ID` — Triggers BigQuery/Vertex backends (Phase 5)
- `GCP_REGION` — GCP region (default: us-central1)
- `BQ_DATASET_ID` — BigQuery dataset name (default: quantum_ai_hub)
- `STORAGE_BACKEND` — Force "sqlite" or "bigquery" (default: auto)
- `EMBEDDINGS_BACKEND` — Force "chromadb" or "vertex" (default: auto)
- `SQLITE_DB_PATH` — Override SQLite path (default: data/quantum_intel.db)
- `EMBEDDINGS_PATH` — Override ChromaDB path (default: data/embeddings)

### Testing
- Framework: pytest
- Each module gets a corresponding test file in `tests/`
- Run: `python -m pytest tests/`
- CLI smoke tests:
  - Quantum: `python scripts/run_ingestion.py --sources rss --max-classify 5`
  - AI: `python scripts/run_ingestion.py --domain ai --sources rss --max-classify 5`
  - AI Tavily: `python scripts/run_ingestion.py --domain ai --sources tavily --tavily-themes industry_retail --max-classify 5`
  - AI ArXiv: `python scripts/run_ingestion.py --domain ai --sources arxiv --max-classify 5`

### Key Domain Constants
- 29 content categories: 11 quantum-specific + 8 shared business + 10 AI-specific
- 4 priority levels: critical, high, medium, low
- 7 entity types: company, technology, product, person, institution, standard, use_case_domain
- **Quantum:** 18 RSS feeds, 52 Tavily queries (9 themes), 6 ArXiv queries
- **AI:** 19 RSS feeds, 198 Tavily queries (34 themes), 8 ArXiv queries
- 20 stock tickers (pure-play quantum + major tech + ETF)
- 14 earnings tickers with CIK mappings (core + secondary)
- SEC filing types: 10-K, 10-Q, 8-K
- `domain` field on articles table: `"quantum"` (default) or `"ai"`

### Reference Implementation
The `ingestion_REFERENCE_template/` folder contains a proven CPG intelligence hub.
Key patterns to follow:
- `orchestrator.py` — pipeline coordination
- `storage/base.py` — StorageBackend ABC
- `storage/__init__.py` — factory functions
- `processing/classifier.py` — LLM classification with JSON parsing
- `processing/deduplication.py` — SimHash + URL dedup
- `utils/llm_client.py` — resilient async Anthropic client

### Phase 4A: Voice Pipelines
- Earnings: `fetchers/earnings.py` → `processing/quote_extractor.py` → storage backend
- SEC: `fetchers/sec.py` → `processing/nugget_extractor.py` → storage backend
- Podcasts: `fetchers/podcast.py` → `processing/podcast_quote_extractor.py` → storage backend
- StockNews: `fetchers/stocknews.py` → existing article classify pipeline
- Run standalone: `python scripts/run_earnings.py`, `python scripts/run_sec.py`, `python scripts/run_podcast.py`

### Phase 6: Case Study Extraction
- **Model:** `models/case_study.py` — CaseStudy dataclass with ~40 fields, enums (SourceType, OutcomeType, ReadinessLevel)
- **Extractor:** `processing/case_study_extractor.py` — 10 domain+source prompt combinations (2 domains × 5 source types)
- **Config:** `config/settings.py` → `CaseStudyConfig` (model, temperature, chunking, dedup thresholds)
- **Storage:** `case_studies` table in SQLite/BigQuery, 5 methods on StorageBackend ABC
- **Embeddings:** `case_study_embeddings` table, registered in `storage/embeddings_config.py`
- **Run standalone:** `python scripts/run_case_studies.py --domain ai --sources articles,sec,earnings --max-items 10`
- Extracts structured narratives (company, industry, implementation, quantified outcomes) from already-ingested content
- Polymorphic FK: `source_type` + `source_id` links to articles, transcripts, filings, papers
- Standalone batch script — does not modify existing ingestion pipelines

### Phase 5: GCP Production Backend
- **BigQuery storage:** `storage/bigquery.py` — implements StorageBackend ABC with BigQuery
- **BigQuery schemas:** `storage/bigquery_schemas.py` — DDL for all 17 BigQuery tables (incl. case_studies + case_study_embeddings)
- **Vertex AI embeddings:** `storage/vertex_embeddings.py` — text-embedding-005 + VECTOR_SEARCH
- **Factory routing:** `storage/__init__.py` — auto-selects backend based on `GCP_PROJECT_ID`
- **Docker:** Single `Dockerfile`, different entrypoints per Cloud Run Job
- **CI/CD:** Push to `master` on GitHub triggers Cloud Build → builds image → updates all jobs
- **Cloud Build config:** `cloudbuild.yaml` — build, push, update 10 Cloud Run Jobs
- **Deploy scripts:** `deploy/setup_infra.sh`, `deploy/cloud_run_jobs.sh`, `deploy/setup_scheduler.sh`
- **10 Cloud Run Jobs** with Cloud Scheduler (see `README_GCP_DEPLOYMENT.md`)
- **GitHub repo:** `jonnycarpenter/quantum-intel` (public)

### Dependencies
- **`requirements.txt`** — Production-only (slim, no PyTorch/CUDA/ChromaDB/Streamlit)
- **`requirements-local.txt`** — All deps including local dev (ChromaDB, Streamlit, pytest)

### Documentation Convention
Every core pipeline must have its own README. These live at the project root:

| README | Covers |
|--------|--------|
| `README_INGESTION.md` | Core data ingestion (RSS, Tavily, ArXiv, StockNews) |
| `README_PODCASTS.md` | Podcast pipeline (discovery, transcription, quote extraction) |
| `README_SEC_EARNINGS.md` | SEC EDGAR filings + earnings call transcripts |
| `README_GCP_DEPLOYMENT.md` | GCP deployment: BigQuery, Vertex AI, Cloud Run, Scheduler |

When adding a new pipeline or major functionality area, create a corresponding `README_<NAME>.md` at the project root.
