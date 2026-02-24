# Weekly Briefing Pipeline

Synthesized weekly intelligence briefings powered by a 2-agent LLM pipeline. Produces narrative sections mapped to strategic priorities, enriched with executive voice quotes and inline citations. Generates separate briefings for quantum computing and AI domains.

## Architecture

```
Articles (SQLite)  ─┐
Earnings Quotes    ─┤
SEC Nuggets        ─┤──→  Research Agent (Sonnet)  ──→  Briefing Agent (Opus)  ──→  WeeklyBriefing
Podcast Quotes     ─┤          batch analysis              narrative synthesis
Stock Data         ─┤          → observations               → sections with voice
ArXiv Papers       ─┘                                         & citations
```

| Stage | Module | Description |
|-------|--------|-------------|
| Config | `config/strategic_priorities.py` | 5 priorities per domain (P1-P5) with category mappings |
| Config | `config/settings.py` | `WeeklyBriefingConfig` — models, batch sizes, thresholds |
| Config | `config/prompts.py` | Domain-specific prompts for both agents |
| Models | `models/weekly_briefing.py` | All dataclasses (PreBrief, BriefingSection, VoiceQuote, etc.) |
| Pipeline | `processing/weekly_briefing.py` | `WeeklyBriefingPipeline` — full orchestration |
| Storage | `storage/sqlite.py` | `weekly_briefings` table with JSON-serialized sections |
| CLI | `scripts/run_weekly_briefing.py` | CLI entry point with pretty-print and JSON output |
| API | `api/routes/digest.py` | `GET /digest/weekly-briefing` endpoint |
| Frontend | `frontend-react/src/pages/BriefingPage.tsx` | Narrative sections, voice quotes, market movers, papers |

## Pipeline Steps

1. **Fetch Articles** — Pull 14 days of articles from SQLite, filter to medium/high/critical priority
2. **Research Agent (Sonnet)** — Batch-process articles (40/batch) into structured observations mapped to priority tags
3. **Voice Enrichment** — Query earnings quotes, SEC nuggets, and podcast quotes for companies mentioned in observations
4. **Market Movers** — Identify tickers with >5% weekly change from stock data
5. **Research Papers** — Pull recent ArXiv papers for the research frontier section
6. **Briefing Agent (Opus)** — Synthesize all inputs into narrative sections with inline citations and voice quotes

## Strategic Priorities

### Quantum

| Tag | Label | Maps From |
|-----|-------|-----------|
| P1 | Quantum Advantage | Use case categories (drug discovery, finance, optimization, etc.) |
| P2 | Error Correction & Logical Qubits | `error_correction`, `algorithm_research` |
| P3 | Hardware Race | `hardware_milestone` |
| P4 | Commercial & Contracts | `company_earnings`, `funding_ipo`, `partnership_contract`, etc. |
| P5 | Government & Defense | `policy_regulation`, `geopolitics`, `use_case_cybersecurity` |

### AI

| Tag | Label | Maps From |
|-----|-------|-----------|
| P1 | Enterprise AI & ROI | `ai_use_case_enterprise`, `ai_use_case_healthcare`, etc. |
| P2 | Frontier Models & Capabilities | `ai_model_release`, `ai_product_launch`, `ai_research_breakthrough` |
| P3 | Safety & Regulation | `ai_safety_alignment`, `policy_regulation` |
| P4 | Infrastructure & Compute | `ai_infrastructure` |
| P5 | Open Source Dynamics | `ai_open_source` |

Sections only render when the Briefing Agent finds enough signal for that priority. Weeks with no activity in a priority simply omit the section.

## Running

```bash
# Generate quantum briefing (14-day lookback)
python scripts/run_weekly_briefing.py --domain quantum

# Generate AI briefing, save to database
python scripts/run_weekly_briefing.py --domain ai --save

# Custom lookback window, JSON output
python scripts/run_weekly_briefing.py --domain quantum --days 21 --json

# Override database path
python scripts/run_weekly_briefing.py --domain quantum --db-path data/prod.db --save
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--domain` | `quantum` | `quantum` or `ai` |
| `--days` | `14` | Lookback window in days |
| `--save` | off | Persist briefing to SQLite |
| `--json` | off | Output raw JSON instead of pretty-print |
| `--db-path` | auto | Override SQLite database path |

## Configuration

Key settings in `WeeklyBriefingConfig` (`config/settings.py`):

| Setting | Default | Description |
|---------|---------|-------------|
| `research_model` | `claude-sonnet-4-6` | Research Agent model |
| `research_batch_size` | 40 | Articles per LLM batch |
| `research_max_tokens` | 4096 | Max tokens for research response |
| `briefing_model` | `claude-opus-4-6` | Briefing Agent model |
| `briefing_max_tokens` | 16000 | Max tokens for briefing response |
| `lookback_days` | 14 | Default article lookback |
| `min_priority` | `medium` | Minimum priority to include |
| `max_articles` | 500 | Max articles to fetch |
| `market_mover_threshold_pct` | 5.0 | Minimum % change for market movers |
| `max_quotes_per_ticker` | 3 | Earnings quotes per ticker for enrichment |
| `max_nuggets_per_ticker` | 3 | SEC nuggets per ticker for enrichment |
| `max_podcast_quotes` | 10 | Total podcast quotes for enrichment |

## Voice Enrichment

The pipeline dynamically queries voice data based on companies discovered by the Research Agent:

- **Earnings Quotes** — Executive statements from quarterly earnings calls (via `storage.get_quotes_by_ticker()`)
- **SEC Nuggets** — Key disclosures from 10-K, 10-Q, 8-K filings (via `storage.get_nuggets_by_ticker()`)
- **Podcast Quotes** — Expert commentary from quantum/AI podcasts (via `storage.search_podcast_quotes()`)

For AI briefings, podcast quotes carry heavier weight (practitioners discussing real deployments). For quantum briefings, earnings and SEC data are primary (public company disclosures about quantum programs).

## API

```
GET /api/digest/weekly-briefing?domain=quantum
GET /api/digest/weekly-briefing?domain=ai&week=2026-02-17
```

Returns `{ "briefing": WeeklyBriefingData | null }` with full sections, market movers, and research papers.

## Output Structure

```
WeeklyBriefing
├── domain: "quantum" | "ai"
├── week_of: "2026-02-17"
├── sections: BriefingSection[]
│   ├── priority_tag: "P1"
│   ├── header: "Quantum Advantage Breakthroughs"
│   ├── narrative: "IonQ demonstrated a 100x speedup [1]..."
│   ├── voice_quotes: VoiceQuote[]
│   │   └── { text, speaker, role, company, source_type, source_context }
│   ├── citations: Citation[]
│   │   └── { number, title, url, source_name }
│   └── has_content: true
├── market_movers: MarketMover[]
│   └── { ticker, close, change_pct, context_text }
├── research_papers: ResearchPaper[]
│   └── { arxiv_id, title, authors, why_it_matters, commercial_readiness }
├── articles_analyzed: 150
├── sections_active: 3
└── generation_cost_usd: 0.45
```

## Cost Estimates

| Component | Model | Typical Cost |
|-----------|-------|-------------|
| Research Agent | Sonnet (per batch of 40) | ~$0.02-0.04 |
| Briefing Agent | Opus (single call) | ~$0.30-0.50 |
| **Total per briefing** | | **~$0.35-0.60** |

Costs are tracked per-run and stored in the `generation_cost_usd` field.

## Re-run Behavior

- Uses `INSERT OR REPLACE` keyed on `(domain, week_of)` — re-running for the same week overwrites the previous briefing
- Safe to run multiple times; only the latest generation is kept
- The `week_of` is computed as the Monday of the current week

## Scheduling

Intended to run weekly (e.g., Sunday evening) for each domain:

```bash
# Cron: Sunday 8pm — generate and save both briefings
0 20 * * 0 cd /path/to/quantum-intel && python scripts/run_weekly_briefing.py --domain quantum --save
15 20 * * 0 cd /path/to/quantum-intel && python scripts/run_weekly_briefing.py --domain ai --save
```

## Tests

```bash
python -m pytest tests/test_weekly_briefing.py -v
```

28 tests covering:
- Model round-trip serialization (8 tests)
- Strategic priorities structure and category mapping (10 tests)
- JSON parser tiers — direct, code block, embedded, empty, garbage (5 tests)
- Storage round-trip — save, retrieve latest, retrieve by week, domain isolation (1 test)
- Pipeline internals — empty briefing structure, market mover threshold, config defaults (4 tests)
