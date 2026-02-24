# SEC & Earnings Pipeline

Fetches SEC EDGAR filings and earnings call transcripts, then extracts strategic nuggets and executive quotes.

## Architecture

```
Earnings:  API Ninjas  →  Transcripts  →  Quote Extraction (Claude)  →  SQLite
SEC:       EDGAR API   →  Filings      →  Nugget Extraction (Claude)  →  SQLite
```

### Earnings Pipeline

| Stage | Module | Description |
|-------|--------|-------------|
| Config | `config/earnings_tickers.py` | 14 tickers with CIK mappings |
| Fetch | `fetchers/earnings.py` | API Ninjas earnings transcripts |
| Extract | `processing/quote_extractor.py` | Claude-powered executive quote extraction |
| Store | `storage/sqlite.py` | `earnings_transcripts` + `earnings_quotes` tables |

### SEC Pipeline

| Stage | Module | Description |
|-------|--------|-------------|
| Config | `config/earnings_tickers.py` | CIK mappings for EDGAR lookups |
| Fetch | `fetchers/sec.py` | SEC EDGAR API (10-K, 10-Q, 8-K filings) |
| Extract | `processing/nugget_extractor.py` | Strategic nugget extraction via Claude |
| Store | `storage/sqlite.py` | `sec_filings` + `sec_nuggets` tables |

## Running

```bash
# Earnings pipeline
python scripts/run_earnings.py

# Specific ticker
python scripts/run_earnings.py --tickers IONQ RGTI

# SEC pipeline
python scripts/run_sec.py

# Specific ticker + filing type
python scripts/run_sec.py --tickers IONQ --filing-types 10-K 10-Q
```

## Tracked Tickers

### Core Quantum (Primary)
| Ticker | Company | CIK |
|--------|---------|-----|
| IONQ | IonQ | 0001811856 |
| RGTI | Rigetti Computing | 0001838359 |
| QBTS | D-Wave Quantum | 0001907982 |
| ARQQ | Arqit Quantum | 0001859690 |
| QUBT | Quantum Computing Inc | 0001758009 |

### Secondary Coverage
IBM, GOOG, MSFT, INTC, HPE, NVDA, AMD, HON, BABA

## Configuration

All tickers and CIK mappings in `config/earnings_tickers.py`:
- `EARNINGS_TICKERS` — Full list with company names and CIK numbers
- `CORE_EARNINGS_TICKERS` — Primary quantum companies only

## What Gets Extracted

### Earnings Quotes
- Speaker attribution (name, role, title, company)
- Quote type: strategy, guidance, risk, technology, competitive
- Themes, sentiment, companies/technologies mentioned
- Relevance scoring and quotability assessment

### SEC Nuggets
- Filing context (type, section, fiscal year/quarter)
- Nugget type: risk_admission, strategic_shift, competitive_intelligence, technology_bet
- Signal strength, risk level, actionability
- Companies, technologies, competitors, regulators mentioned

## Database Tables

### Earnings
- **`earnings_transcripts`** — Raw transcript text, participants, fiscal period
- **`earnings_quotes`** — Individual quotes with full speaker attribution and classification

### SEC
- **`sec_filings`** — Filing metadata, raw content, sections
- **`sec_nuggets`** — Strategic nuggets with classification and entity extraction

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude for extraction |
| `API_NINJA_API_KEY` | Yes | Earnings transcript API |
| `SEC_USER_AGENT` | Yes | Required for EDGAR API (format: `Name email@example.com`) |
| `SECIO_API_KEY` | No | SEC.io enhanced access (optional) |
