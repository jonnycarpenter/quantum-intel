# Core Ingestion Pipeline

Fetches, deduplicates, classifies, and stores quantum computing intelligence from multiple sources.

## Architecture

```
RSS / Exa / ArXiv / StockNews  →  Dedup  →  Classify (Claude)  →  BigQuery + Vertex AI Embeddings
```

| Stage | Module | Description |
|-------|--------|-------------|
| Fetch | `fetchers/rss.py` | 20+ tiered RSS feeds |
| Fetch | `fetchers/exa.py` | 57 quantum queries (10 themes) + 203 AI queries (35 themes) |
| Fetch | `fetchers/arxiv.py` | Quantum computing paper search |
| Fetch | `fetchers/stocknews.py` | Stock market news for quantum tickers |
| Fetch | `fetchers/stocks.py` | Price data via yfinance (20 tickers) |
| Filter | `processing/deduplication.py` | SimHash + URL dedup with article aggregation |
| Classify | `processing/classifier.py` | Claude-powered category, priority, relevance scoring |
| Persist | `storage/bigquery.py` | BigQuery storage |
| Embed | `storage/vertex_embeddings.py` | Vertex AI text-embedding-005 |

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

- **BigQuery** (`quantum_ai_hub` dataset) for all structured data
- **Vertex AI** text-embedding-005 for vector embeddings + VECTOR_SEARCH

## Scheduling

Core ingestion runs on a recurring Cloud Run Job schedule. See `CLAUDE.md` for environment variable configuration.

## Dual-Domain Pipeline

Both quantum and AI domains use identical pipeline architecture with different config:

| Domain | RSS Feeds | Exa Queries | ArXiv Queries | Cloud Run Jobs |
|--------|-----------|-------------|---------------|----------------|
| Quantum | 18 feeds (4 tiers) | 57 queries (10 themes) | 6 queries | `quantum-rss-ingestion`, `quantum-exa-ingestion`, `quantum-arxiv-ingestion` |
| AI | 19 feeds (4 tiers) | 203 queries (35 themes) | 8 queries | `ai-rss-ingestion`, `ai-exa-ingestion`, `ai-arxiv-ingestion` |

Switch domain with `--domain ai` or `--domain quantum` on any script.
