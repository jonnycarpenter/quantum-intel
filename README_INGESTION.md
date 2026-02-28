# Core Ingestion Pipeline

Fetches, deduplicates, classifies, and stores quantum computing intelligence from multiple sources.

## Architecture

```
RSS / Exa / ArXiv / StockNews  →  Dedup  →  Classify (Claude)  →  SQLite + Embeddings
```

| Stage | Module | Description |
|-------|--------|-------------|
| Fetch | `fetchers/rss.py` | 20+ tiered RSS feeds |
| Fetch | `fetchers/exa.py` | 52 Exa queries across 9 themes |
| Fetch | `fetchers/arxiv.py` | Quantum computing paper search |
| Fetch | `fetchers/stocknews.py` | Stock market news for quantum tickers |
| Fetch | `fetchers/stocks.py` | Price data via yfinance (20 tickers) |
| Filter | `processing/deduplication.py` | SimHash + URL dedup with article aggregation |
| Classify | `processing/classifier.py` | Claude-powered category, priority, relevance scoring |
| Persist | `storage/sqlite.py` | SQLite (local) or BigQuery (prod) |
| Embed | `storage/` | ChromaDB (local) or Vertex AI (prod) |

## Configuration

| File | Purpose |
|------|---------|
| `config/rss_sources.py` | Quantum RSS feeds (4 tiers) |
| `config/ai_rss_sources.py` | AI domain RSS feeds (4 tiers, for AI pipeline) |
| `config/exa_queries.py` | Quantum Exa search queries |
| `config/ai_exa_queries.py` | AI Exa search queries (for AI pipeline) |
| `config/arxiv_queries.py` | ArXiv categories and search terms |
| `config/tickers.py` | Stock tickers to track |
| `config/settings.py` | `IngestionConfig` dataclass |
| `config/prompts.py` | LLM classification prompts |

## Running

```bash
# Full ingestion (all sources)
python scripts/run_ingestion.py

# Specific sources only
python scripts/run_ingestion.py --sources rss exa

# Quick test (5 articles max)
python scripts/run_ingestion.py --sources rss --max-classify 5

# Generate digest from recent articles
python scripts/run_digest.py
```

## Orchestrator Flow

The pipeline is coordinated by `orchestrator.py`:

1. **Fetch** — Pull articles from enabled sources (RSS, Exa, ArXiv, StockNews)
2. **Filter** — Remove blocked sources/domains
3. **Dedup** — URL-based + title similarity deduplication
4. **Classify** — Claude classifies: category, priority, relevance, entities, sentiment
5. **Persist** — Save classified articles to storage
6. **Embed** — Generate vector embeddings for semantic search

## Storage

- **Local:** SQLite (`data/quantum_intel.db`) + ChromaDB (`data/embeddings/`)
- **Production:** BigQuery + Vertex AI Vector Search
- **Auto-select:** `storage.get_storage()` picks backend based on `GCP_PROJECT_ID` env var

## Scheduling

Core ingestion runs on a recurring Cloud Run Job schedule. See `CLAUDE.md` for environment variable configuration.

## AI News Pipeline (In Progress)

The same pipeline architecture is being extended for AI-domain intelligence:
- `config/ai_rss_sources.py` — 22 AI RSS feeds across 4 tiers (dedicated → vendor → academic → general tech)
- `config/ai_exa_queries.py` — AI-focused search queries
- Uses the same orchestrator pattern with `domain="ai"` parameter
