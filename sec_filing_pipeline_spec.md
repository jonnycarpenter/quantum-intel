# SEC Filing Nugget Extraction Pipeline - Recreation Spec

> **Purpose**: Complete specification to recreate the SEC filing ingestion and LLM-based "nugget" extraction pipeline. This pipeline collects SEC filings (10-K, 10-Q, 8-K), stores them in BigQuery, extracts strategic intelligence nuggets using Claude, embeds them for semantic search, and surfaces them via API/agent tools.

---

## Architecture Overview

```
                         ┌─────────────────────┐
                         │   SEC-API.io         │
                         │ (Full-Text Search    │
                         │  Filing Extractor)   │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  1. SEC Filing Collector        │
                    │  (app/tools/sec_filings/)       │
                    │  - Query filings by ticker      │
                    │  - Extract sections (10-K/Q)    │
                    │  - Download full text (8-K)     │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  2. Ingestion Orchestrator      │
                    │  (app/ingestion/orchestrator.py)│
                    │  - Stores raw filings to BQ     │
                    │    `sec_filings` table          │
                    │  - Converts to RawArticle       │
                    │    for general `articles` table  │
                    │  - Triggers nugget extraction    │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  3. Nugget Extractor (LLM)     │
                    │  (app/ingestion/sec_filings/)   │
                    │  - Claude Sonnet 4.5            │
                    │  - Extracts 15-30 nuggets/filing│
                    │  - Rich classification taxonomy │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  4. BigQuery Storage + Embeddings│
                    │  (app/db/gcp_storage.py)         │
                    │  - `sec_filing_nuggets` table    │
                    │  - Vertex AI embeddings          │
                    │    (text-embedding-004)          │
                    └───────────────┬────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────▼─────────┐ ┌────────▼────────┐ ┌──────────▼──────────┐
    │ 5a. MCP Agent Tool │ │ 5b. REST API    │ │ 5c. Semantic Search │
    │ search_sec_nuggets │ │ /financial-feed │ │ (vector search)     │
    │ get_sec_nugget_stats│ │ (FastAPI)       │ │ ML.DISTANCE cosine  │
    └────────────────────┘ └─────────────────┘ └─────────────────────┘
```

---

## Layer 1: Data Collection (`app/tools/sec_filings/`)

### Files

| File | Purpose |
|------|---------|
| `models.py` | Pydantic models: `SECFiling`, `FilingMetadata` |
| `sec_client.py` | HTTP client wrapping sec-api.io endpoints |
| `extractor.py` | Section extractor (pulls specific 10-K/Q sections) |
| `collector.py` | Orchestrates collection for tracked companies |

### External API: sec-api.io

Three endpoints are used:

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Full-Text Search | `https://api.sec-api.io` | Query filings by ticker, form type, date range |
| Section Extractor | `https://api.sec-api.io/extractor` | Extract specific sections (Item 1, 1A, 7, 7A) from 10-K/Q |
| Archive/Render | `https://archive.sec-api.io` | Download full filing text (used for 8-K) |

**Authentication**: API key passed as `Authorization` header (search/extractor) or `?token=` query param (archive).

**Config** (in `settings.py`):
```python
sec_api_key: str  # env var: SEC_IO_KEY or SEC_IO_API_KEY
sec_filing_types: list = ["10-K", "10-Q", "8-K"]
sec_extract_sections: list = ["1", "1A", "7", "7A"]
```

### SECClient (`sec_client.py`)

```python
class SECClient:
    QUERY_URL = "https://api.sec-api.io"
    EXTRACTOR_URL = "https://api.sec-api.io/extractor"
    RENDER_URL = "https://archive.sec-api.io"
    MIN_REQUEST_INTERVAL = 0.5  # Rate limiting

    def query_filings(ticker, cik, form_types, filed_after, filed_before, size) -> List[FilingMetadata]
    def extract_section(filing_url, section) -> Optional[str]
    def download_filing(filing_url) -> Optional[str]
```

**Key behaviors**:
- Rate limiting: 500ms minimum between requests
- Retry with exponential backoff on 429 (rate limit) responses: 2s, 4s, 8s
- Query payload uses Lucene-style query syntax: `ticker:RPM AND formType:("10-K" OR "10-Q")`
- Results sorted by `filedAt` descending
- Uses `httpx.Client` (sync) with 60s timeout

### SectionExtractor (`extractor.py`)

Maps SEC section numbers to human-readable names:
```python
SECTION_NAMES = {
    "1": "business",
    "1A": "risk_factors",
    "7": "mda",
    "7A": "market_risk_disclosures",
}
```

Calls `sec_client.extract_section()` for each configured section, returns `Dict[str, str]` of `section_name -> content`.

### SECFilingCollector (`collector.py`)

```python
class SECFilingCollector:
    def collect_for_company(company_id, ticker, since) -> List[SECFiling]
```

**Logic per filing type**:
- **10-K / 10-Q**: Extract individual sections (risk_factors, mda, business, market_risk)
- **8-K**: Download full text (no section extraction)
- Skips filings already in `existing_ids` set (deduplication by accession number)
- Returns up to 5 filings per company per run

### Data Models (`models.py`)

```python
class FilingMetadata(BaseModel):
    accession_no: str      # Unique SEC filing identifier
    cik: str               # SEC Central Index Key
    ticker: str
    company_name: str
    form_type: str         # "10-K", "10-Q", "8-K"
    filed_at: datetime
    filing_url: str

class SECFiling(BaseModel):
    id: str                # = accession_no
    company_id: str
    ticker: str
    cik: str
    company_name: str
    form_type: str
    filed_at: datetime
    filing_url: str
    sections: Optional[Dict[str, str]]  # For 10-K/Q: {"risk_factors": "...", "mda": "..."}
    full_text: Optional[str]            # For 8-K
    collected_at: datetime
```

---

## Layer 2: Ingestion Orchestrator Integration

The orchestrator (`app/ingestion/orchestrator.py`) does three things with SEC filings:

### 2a. Store raw filings in dedicated `sec_filings` BigQuery table

```python
sec_bq_rows = [{
    "filing_id": filing.id,           # accession number
    "company_id": company_id,
    "ticker": filing.ticker,
    "cik": filing.cik,
    "company_name": filing.company_name,
    "form_type": filing.form_type,
    "filed_at": filing.filed_at.isoformat(),
    "filing_url": filing.filing_url,
    "sections_json": json.dumps(filing.sections),  # JSON string
    "full_text": filing.full_text,
    "collected_at": datetime.utcnow().isoformat(),
}]
await storage.store_sec_filings(sec_bq_rows)
```

### 2b. Convert to RawArticle for general articles table

SEC filings are also stored in the generic `articles` table with `source_type="sec_filing"`. This allows them to appear in general search/feed alongside news articles.

Important: SEC filings are **excluded from vector store** chunking (their dedicated nuggets table serves that purpose instead).

```python
if article.source_type not in ("earnings_transcript", "sec_filing"):
    vector_docs.append(corpus_item)  # Skip SEC for vector store
```

### 2c. Trigger nugget extraction post-ingestion

After storing, the orchestrator runs nugget extraction inline:

```python
from app.ingestion.sec_filings.nugget_extractor import SecNuggetExtractor

extractor = SecNuggetExtractor()
for article, classification in classified:
    if article.source_type != "sec_filing":
        continue
    result = await extractor.extract_nuggets(filing_data)
    if result.success and result.nuggets:
        bq_rows = [n.to_bq_row() for n in result.nuggets]
        await storage.store_sec_filing_nuggets(bq_rows)
```

---

## Layer 3: LLM Nugget Extraction (`app/ingestion/sec_filings/`)

This is the core intelligence extraction layer. It uses an LLM to read SEC filing content and extract structured "nuggets" of strategic intelligence.

### Files

| File | Purpose |
|------|---------|
| `models.py` | Pydantic models, enums, BigQuery serialization |
| `nugget_extractor.py` | LLM extraction engine |
| `__init__.py` | Package exports |

### SecNuggetExtractor (`nugget_extractor.py`)

```python
class SecNuggetExtractor:
    def __init__(
        model="claude-sonnet-4-5",   # LLM model for extraction
        max_tokens=16000,            # Max response tokens
        temperature=0.2,             # Low temp for consistency
        max_content_chars=150000,    # Truncate filings beyond this
    )

    async def extract_nuggets(filing_data: Dict) -> SecNuggetExtractionResult
```

**Input** (`filing_data` dict):
```python
{
    "id": "0000091142-24-000042",      # accession number
    "ticker": "RPM",
    "company_name": "RPM International",
    "cik": "91142",
    "filing_type": "10-K",
    "fiscal_year": 2024,
    "fiscal_quarter": None,            # None for annual filings
    "filing_date": "2024-07-25",
    "sections": {                      # Parsed sections (preferred)
        "risk_factors": "...",
        "mda": "...",
        "business": "...",
    },
    "sections_json": "{...}",          # JSON string fallback
    "full_text": "...",                # Raw text fallback
}
```

**Content preparation** (`_prepare_content`):
- Prioritizes key sections in order: `risk_factors`, `mda`, `business`, `legal_proceedings`, `market_risk`
- Falls back to `full_text` if no sections available
- Truncates at `max_content_chars` (150k chars)

**LLM call**:
- Uses resilient async client (Anthropic primary, Gemini fallback)
- 120s timeout via `asyncio.wait_for()`
- Returns JSON array of nugget objects

**Response parsing** (`_parse_response`):
- Handles markdown code fences (```json)
- Regex fallback to find JSON arrays
- Truncated JSON recovery: finds last complete `}` and closes the array
- Returns `List[Dict]` of raw nugget data

### Extraction Prompt (RPM_NUGGET_EXTRACTION_PROMPT)

The prompt is the heart of the pipeline. It provides:

1. **Filing metadata** (company, ticker, filing type, fiscal year, date)
2. **Filing content** (the actual SEC text)
3. **Business context** specific to the target company (segments, products, markets)
4. **Six high-value nugget categories**:
   - Competitive Disclosures (highest value - companies must disclose material threats)
   - Risk Admissions (material risks, new risks, raw material costs)
   - Forward Guidance (strategic initiatives, capital allocation, expansion)
   - Regulatory Exposure (EPA, VOC, building codes, environmental remediation)
   - Material Changes (leadership, M&A, restructuring - especially 8-K)
   - Market Conditions (construction outlook, housing, infrastructure)
5. **Critical instructions**: Extract exact quotes, flag new/buried disclosures, score relevance
6. **Output schema**: Detailed JSON format specification for each nugget field

The prompt asks for 15-30 nuggets per filing.

**Adapting for another company/industry**: Replace the "RPM BUSINESS CONTEXT" section and `SecFilingTheme` enum with your target company's segments, products, competitors, and market dynamics. The nugget categories (competitive disclosure, risk admission, etc.) are universal SEC concepts.

### Data Models (`models.py`)

#### Enums (Taxonomy)

```python
class FilingType(str, Enum):
    FORM_10K, FORM_10Q, FORM_8K, FORM_S1, FORM_DEF14A, FORM_20F, FORM_6K, OTHER

class FilingSection(str, Enum):
    RISK_FACTORS, BUSINESS, MDA, LEGAL_PROCEEDINGS, MARKET_RISK,
    PROPERTIES, EXHIBITS, FORWARD_LOOKING, EXECUTIVE_COMPENSATION, UNKNOWN

class NuggetType(str, Enum):
    COMPETITIVE_DISCLOSURE    # Named competitors in legally mandated disclosures
    RISK_ADMISSION            # Material risk acknowledgments
    MARKET_POSITION           # Market share/positioning statements
    FORWARD_GUIDANCE          # Forward-looking statements
    REGULATORY_EXPOSURE       # Regulatory risk/compliance
    LITIGATION_DISCLOSURE     # Legal proceedings
    MATERIAL_CHANGE           # 8-K triggered events
    STRATEGIC_INITIATIVE      # Strategy announcements
    SUPPLY_CHAIN              # Supply chain disclosures
    RAW_MATERIALS             # Raw material cost/availability
    FINANCIAL_METRIC          # Key financial data points
    ESG_DISCLOSURE            # ESG/sustainability
    ACQUISITION               # M&A activity

class DisclosureSignalStrength(str, Enum):
    EXPLICIT    # Direct, clear disclosure
    STANDARD    # Routine disclosure language
    HEDGED      # Heavy legal caveats
    BURIED      # Deep in filing, potentially hidden
    NEW         # First-time disclosure (highest value)

class SecFilingTheme(str, Enum):
    # ~30 themes organized into categories:
    # Business Segments, Construction Markets, Product Categories,
    # Competitive Dynamics, Operations & Finance, External Factors, Channels
    # (Customize these per your target industry)
```

#### ExtractedSecNugget

The core data model for a single extracted insight:

```python
class ExtractedSecNugget(BaseModel):
    # Identity
    nugget_id: str              # UUID
    filing_id: str              # Links back to source filing

    # The nugget
    nugget_text: str            # 1-3 sentence insight (exact quote when possible)
    context_text: Optional[str] # Surrounding context

    # Filing context
    filing_type: FilingType
    section: FilingSection      # Which section it came from

    # Classification
    nugget_type: NuggetType
    themes: List[SecFilingTheme]
    signal_strength: DisclosureSignalStrength

    # Entity references
    companies_mentioned: List[str]
    brands_mentioned: List[str]
    competitors_named: List[str]   # CRITICAL - named competitors
    regulators_mentioned: List[str]

    # Risk & relevance
    risk_level: str                # "high", "medium", "low"
    is_new_disclosure: bool        # First-time disclosure (gold)
    strategic_relevance: str       # "high", "medium", "low"
    relevance_score: float         # 0.0-1.0 industry relevance
    is_actionable: bool            # Contains actionable intelligence
    actionability_reason: Optional[str]
    business_segment: Optional[str]

    # Source
    ticker: str
    company_name: str
    cik: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    filing_date: Optional[str]

    # Audit
    extracted_at: str              # ISO timestamp
    extraction_model: str          # e.g. "claude-sonnet-4-6"

    def to_bq_row() -> Dict       # Serialize for BigQuery insert
    def to_display_dict() -> Dict  # Serialize for API responses
```

#### SecNuggetExtractionResult

Wraps the output of a single filing extraction:

```python
class SecNuggetExtractionResult(BaseModel):
    filing_id: str
    ticker: str
    company_name: str
    filing_type: FilingType
    fiscal_year: int

    nuggets: List[ExtractedSecNugget]
    total_nuggets: int
    actionable_count: int
    new_disclosure_count: int

    nuggets_by_section: Dict[str, int]
    nuggets_by_type: Dict[str, int]

    success: bool
    error_message: Optional[str]
    extraction_model: str
    extraction_time_seconds: float
    filing_length: int

    def compute_statistics()  # Populates counts from nuggets list
```

---

## Layer 4: BigQuery Storage (`app/db/gcp_storage.py`)

### Table: `sec_filings` (raw filing storage)

```sql
CREATE TABLE sec_filings (
    filing_id STRING NOT NULL,          -- accession number
    company_id STRING,
    ticker STRING NOT NULL,
    cik STRING,
    company_name STRING,
    form_type STRING NOT NULL,          -- "10-K", "10-Q", "8-K"
    filed_at TIMESTAMP,
    filing_url STRING,
    sections_json STRING,               -- JSON dict: {"risk_factors": "...", "mda": "..."}
    full_text STRING,                   -- For 8-K or fallback
    collected_at TIMESTAMP NOT NULL
)
PARTITION BY MONTH(filed_at)
CLUSTER BY ticker, form_type;
```

### Table: `sec_filing_nuggets` (extracted intelligence)

```sql
CREATE TABLE sec_filing_nuggets (
    nugget_id STRING NOT NULL,
    filing_id STRING NOT NULL,          -- FK to sec_filings
    nugget_text STRING NOT NULL,
    context_text STRING,
    filing_type STRING,
    section STRING,
    nugget_type STRING,
    themes STRING,                      -- JSON array
    signal_strength STRING,
    companies_mentioned STRING,         -- JSON array
    brands_mentioned STRING,            -- JSON array
    competitors_named STRING,           -- JSON array
    regulators_mentioned STRING,        -- JSON array
    risk_level STRING,
    is_new_disclosure BOOLEAN,
    strategic_relevance STRING,
    relevance_score FLOAT64,
    is_actionable BOOLEAN,
    actionability_reason STRING,
    business_segment STRING,
    ticker STRING NOT NULL,
    company_name STRING,
    cik STRING,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    filing_date STRING,
    extracted_at TIMESTAMP NOT NULL,
    extraction_model STRING,
    embedding FLOAT64 REPEATED,         -- Vertex AI vector embedding
    embedding_model STRING              -- e.g. "text-embedding-004"
)
PARTITION BY MONTH(extracted_at)
CLUSTER BY ticker, nugget_type;
```

### Storage Methods

```python
# Raw filing storage
async def store_sec_filings(filings: List[Dict]) -> int
async def get_sec_filing_ids() -> set                        # For dedup
async def get_sec_filing_stats() -> Dict

# Nugget extraction pipeline
async def get_sec_filings_for_nugget_extraction(
    limit=50,
    include_already_extracted=False   # True for re-extraction
) -> List[Dict]

# Nugget storage (with auto-embedding)
async def store_sec_filing_nuggets(nuggets: List[Dict]) -> int
    # Automatically generates Vertex AI embeddings before insert

# Nugget querying (LIKE-based fallback)
async def get_sec_filing_nuggets(
    ticker, search_query, nugget_type, themes, section,
    signal_strength, fiscal_year, actionable_only,
    new_disclosures_only, min_relevance, limit
) -> List[Dict]

# Maintenance
async def delete_all_sec_filing_nuggets() -> int             # For re-extraction
async def get_sec_filing_nugget_stats() -> Dict
```

### Embedding Generation

When storing nuggets, embeddings are automatically generated:

```python
from app.db.semantic_search import get_semantic_searcher
searcher = await get_semantic_searcher()
texts = [searcher.build_embed_text_for_sec(n) for n in nuggets]
embeddings = await searcher.embed_texts(texts)
# Each embedding is appended to the nugget row before BQ insert
```

Uses Google Vertex AI `text-embedding-004` model (768-dimensional vectors).

---

## Layer 5: Search & API Access

### 5a. MCP Agent Tool (`app/mcp/tools/sec_nuggets.py`)

Two LangChain `@tool` functions for AI agent access:

```python
@tool
async def search_sec_nuggets(
    query: str,
    ticker: Optional[str] = None,
    nugget_type: Optional[str] = None,
    section: Optional[str] = None,
    signal_strength: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    actionable_only: bool = False,
    new_disclosures_only: bool = False,
    limit: int = 15,
) -> str:
    """Search pre-extracted strategic insights from SEC filings."""

@tool
async def get_sec_nugget_stats() -> str:
    """Get statistics about the SEC filing nugget extraction database."""
```

**Theme auto-detection**: The search tool maps query keywords to theme filters:
```python
theme_keywords = {
    "coating": "protective_coatings",
    "waterproof": "waterproofing",
    "sherwin": "sherwin_williams",
    "raw material": "raw_material_costs",
    "tio2": "raw_material_costs",
    "pricing": "pricing_strategy",
    # ... ~20 keyword mappings
}
```

**Search strategy**:
1. Try semantic vector search (cosine distance via `ML.DISTANCE` in BigQuery)
2. Fall back to LIKE-based text search if vector search unavailable

### 5b. REST API (`app/api/routes/financial_feed.py`)

```
GET /api/v1/financial-feed
    ?search=<text>
    &source_type=sec|earnings|all
    &ticker=RPM
    &type_filter=competitive_disclosure
    &themes=raw_material_costs,supply_chain
    &sort_by=newest|relevance
    &limit=40
    &offset=0
```

Returns a combined feed of SEC nuggets and earnings quotes with a `source_type` discriminator. Each item includes full classification metadata.

### 5c. Semantic Vector Search (`app/db/semantic_search.py`)

```python
async def search_sec_nuggets(
    query, ticker, nugget_type, section, signal_strength,
    fiscal_year, themes, actionable_only, new_disclosures_only,
    min_relevance, limit
) -> List[Dict]:
    """Semantic search over sec_filing_nuggets using vector embeddings."""
```

Uses BigQuery ML.DISTANCE with cosine similarity:
```sql
SELECT *, ML.DISTANCE(base.embedding, query.embedding, 'COSINE') AS distance
FROM sec_filing_nuggets base
CROSS JOIN query_embedding query
WHERE <filters>
ORDER BY distance ASC
LIMIT <n>
```

---

## Layer 6: Backfill & Operations

### Backfill Script (`scripts/operations/backfill_sec_nuggets.py`)

For processing existing filings that haven't been nugget-extracted yet, or re-extracting with a new/upgraded model.

```bash
# Default: process up to 50 new filings
python scripts/operations/backfill_sec_nuggets.py

# Limit batch size
python scripts/operations/backfill_sec_nuggets.py --limit 20

# Re-extract ALL (deletes existing nuggets first)
python scripts/operations/backfill_sec_nuggets.py --reextract

# Preview without extracting
python scripts/operations/backfill_sec_nuggets.py --dry-run

# Show current stats
python scripts/operations/backfill_sec_nuggets.py --stats
```

**Re-extract flow**:
1. Delete all existing nuggets via `DELETE FROM sec_filing_nuggets WHERE TRUE`
2. Query all filings from `sec_filings` table
3. Run extraction on each filing
4. Store new nuggets with fresh embeddings
5. 1-second rate limit between LLM calls

---

## Dependencies

### Python Packages
```
pydantic          # Data models
httpx             # SEC API HTTP client
anthropic         # Claude LLM (primary)
google-cloud-bigquery  # BigQuery storage
google-cloud-aiplatform  # Vertex AI embeddings
langchain-core    # @tool decorator for MCP tools
fastapi           # REST API
```

### External Services
| Service | Purpose | Auth |
|---------|---------|------|
| sec-api.io | SEC filing search, section extraction, full text | API key |
| Anthropic Claude | Nugget extraction (Claude Sonnet) | API key |
| Google Vertex AI | Embedding generation (text-embedding-004) | Service account |
| Google BigQuery | Storage and vector search | Service account |

### Environment Variables
```
SEC_IO_KEY          # sec-api.io API key
ANTHROPIC_API_KEY   # Claude API key
GEMINI_API_KEY      # Gemini fallback (optional)
GCP_PROJECT_ID      # BigQuery project
```

---

## Key Design Decisions

1. **Two-table design**: Raw filings stored separately from extracted nuggets. This allows re-extraction with upgraded models without re-collecting from sec-api.io.

2. **Inline extraction during ingestion**: Nuggets are extracted immediately after filing collection, not as a separate batch job. This keeps intelligence fresh.

3. **Backfill script for catch-up**: When upgrading extraction models or fixing issues, the backfill script can re-process all historical filings.

4. **Vector embeddings at storage time**: Embeddings are generated when nuggets are stored, not at query time. This makes search fast.

5. **Dual search path**: Semantic vector search is preferred, with LIKE-based fallback. This ensures availability even if embedding generation fails.

6. **SEC filings excluded from general vector store**: Their large size would slow down general article search. Instead, they have their own dedicated nugget search.

7. **JSON arrays in STRING columns**: BigQuery doesn't natively support arrays of strings well for filtering. Themes, companies, competitors are stored as JSON strings and searched with LIKE patterns.

8. **Rate limiting throughout**: SEC API (500ms between requests), LLM calls (1s between extractions in backfill), all with exponential backoff on 429s.

9. **Resilient LLM wrapper**: Primary Anthropic with automatic Gemini fallback on API failures. Configurable per the `app/utils/resilient_llm.py` module.

10. **Industry-specific prompt**: The extraction prompt is deeply customized for the target industry. When adapting, the prompt and `SecFilingTheme` enum are the two things that need to change.

---

## Adaptation Checklist (for a new project)

1. **Update `SecFilingTheme` enum** in `models.py` - Replace RPM-specific themes with your industry's themes (segments, competitors, product categories, markets)

2. **Rewrite `RPM_NUGGET_EXTRACTION_PROMPT`** in `nugget_extractor.py` - Replace the "RPM BUSINESS CONTEXT" section with your target company's segments, products, and competitive landscape. Keep the nugget categories (they're universal SEC concepts).

3. **Update theme keyword mappings** in `sec_nuggets.py` MCP tool - Map new query keywords to your updated theme enum values

4. **Configure tracked companies** - The orchestrator iterates over tracked companies from the `companies` table. Add your target tickers/CIKs.

5. **Set up BigQuery tables** - Both tables auto-create on first use via the `_create_*_table()` methods. Just ensure GCP project/dataset are configured.

6. **Set up sec-api.io account** - Get an API key at https://sec-api.io. Free tier may suffice for small company lists; paid tier for higher volume.

7. **Configure embedding model** - If using Vertex AI, ensure the `text-embedding-004` model is available in your GCP project. Or swap for another embedding provider.

8. **Test extraction** - Use the backfill script with `--dry-run` first, then `--limit 1` to test a single filing before bulk extraction.

---

## Cost Estimates

| Operation | Model | Est. Cost |
|-----------|-------|-----------|
| Nugget extraction per 10-K | Claude Sonnet 4.5 | ~$0.20-0.60 |
| Nugget extraction per 8-K | Claude Sonnet 4.5 | ~$0.05-0.15 |
| Embedding per nugget | Vertex AI text-embedding-004 | ~$0.0001 |
| sec-api.io per filing query | - | Per plan pricing |
| BigQuery storage | - | ~$0.02/GB/month |
| BigQuery queries | - | ~$5/TB scanned |
