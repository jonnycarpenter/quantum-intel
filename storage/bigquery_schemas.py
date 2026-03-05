"""
BigQuery Table Schemas
======================

BigQuery DDL for the Quantum + AI Intelligence Hub.
Parallel to schemas.py (SQLite), adapted for BigQuery types:
  - ARRAY<STRING> for list fields
  - TIMESTAMP for datetimes
  - BOOL for booleans
  - JSON for metadata/sections blobs
  - No UNIQUE constraints (enforced via MERGE upserts)
"""


def _table(dataset: str, name: str, ddl: str) -> str:
    """Format DDL with fully-qualified table name."""
    return ddl.format(dataset=dataset, table=f"{dataset}.{name}")


# ============================================================================
# Articles
# ============================================================================

BQ_ARTICLES_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id STRING NOT NULL,
  url STRING NOT NULL,
  title STRING NOT NULL,
  source_name STRING,
  source_url STRING,
  source_type STRING,
  published_at TIMESTAMP,
  date_confidence STRING,
  fetched_at TIMESTAMP NOT NULL,
  summary STRING,
  full_text STRING,
  author STRING,
  tags ARRAY<STRING>,

  primary_category STRING,
  priority STRING,
  relevance_score FLOAT64,
  ai_summary STRING,
  key_takeaway STRING,
  companies_mentioned ARRAY<STRING>,
  technologies_mentioned ARRAY<STRING>,
  people_mentioned ARRAY<STRING>,
  use_case_domains ARRAY<STRING>,
  sentiment STRING,
  confidence FLOAT64,
  time_to_market_impact STRING,
  disrupted_industries STRING,
  investment_signal STRING,
  classifier_model STRING,
  classified_at TIMESTAMP,

  digest_priority STRING,
  feed_eligible BOOL,

  content_hash STRING,
  coverage_count INT64,
  duplicate_urls ARRAY<STRING>,

  metadata JSON,
  domain STRING
)
"""

# ============================================================================
# Digests
# ============================================================================

BQ_DIGESTS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  period_hours INT64,
  executive_summary STRING,
  content JSON,
  total_items INT64,
  critical_count INT64,
  high_count INT64,
  medium_count INT64,
  low_count INT64
)
"""

# ============================================================================
# Papers (ArXiv)
# ============================================================================

BQ_PAPERS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  arxiv_id STRING NOT NULL,
  title STRING NOT NULL,
  authors ARRAY<STRING>,
  abstract STRING,
  categories ARRAY<STRING>,
  published_at TIMESTAMP,
  updated_at TIMESTAMP,
  ingested_at TIMESTAMP,
  pdf_url STRING,

  relevance_score FLOAT64,
  paper_type STRING,
  use_case_category STRING,
  commercial_readiness STRING,
  significance_summary STRING
)
"""

# ============================================================================
# Stocks
# ============================================================================

BQ_STOCKS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  ticker STRING NOT NULL,
  date STRING NOT NULL,
  open FLOAT64,
  high FLOAT64,
  low FLOAT64,
  close FLOAT64,
  volume INT64,
  change_percent FLOAT64,
  market_cap FLOAT64,
  sma_20 FLOAT64,
  sma_50 FLOAT64
)
"""

# ============================================================================
# Earnings Transcripts
# ============================================================================

BQ_EARNINGS_TRANSCRIPTS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  transcript_id STRING NOT NULL,
  ticker STRING NOT NULL,
  company_name STRING NOT NULL,
  year INT64 NOT NULL,
  quarter INT64 NOT NULL,
  transcript_text STRING,
  call_date TIMESTAMP,
  participants JSON,
  fiscal_period STRING,
  ingested_at TIMESTAMP NOT NULL,
  char_count INT64,
  domain STRING
)
"""

# ============================================================================
# Earnings Quotes
# ============================================================================

BQ_EARNINGS_QUOTES_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  quote_id STRING NOT NULL,
  transcript_id STRING NOT NULL,
  quote_text STRING NOT NULL,
  context_before STRING,
  context_after STRING,

  speaker_name STRING NOT NULL,
  speaker_role STRING,
  speaker_title STRING,
  speaker_company STRING,
  speaker_firm STRING,

  quote_type STRING,
  themes STRING,
  sentiment STRING,
  confidence_level STRING,

  companies_mentioned STRING,
  technologies_mentioned STRING,
  competitors_mentioned STRING,
  metrics_mentioned STRING,

  relevance_score FLOAT64,
  is_quotable BOOL,
  quotability_reason STRING,

  ticker STRING NOT NULL,
  company_name STRING NOT NULL,
  year INT64 NOT NULL,
  quarter INT64 NOT NULL,
  call_date TIMESTAMP,
  section STRING,
  position_in_section INT64,

  extracted_at TIMESTAMP NOT NULL,
  extraction_model STRING,
  extraction_confidence FLOAT64,
  domain STRING
)
"""

# ============================================================================
# SEC Filings
# ============================================================================

BQ_SEC_FILINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  filing_id STRING NOT NULL,
  ticker STRING NOT NULL,
  company_name STRING NOT NULL,
  cik STRING NOT NULL,
  accession_number STRING,
  filing_type STRING NOT NULL,
  filing_date TIMESTAMP,
  fiscal_year INT64 NOT NULL,
  fiscal_quarter INT64,
  primary_document STRING,
  filing_url STRING,
  raw_content STRING,
  sections JSON,
  ingested_at TIMESTAMP NOT NULL,
  char_count INT64,
  domain STRING
)
"""

# ============================================================================
# SEC Nuggets
# ============================================================================

BQ_SEC_NUGGETS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  nugget_id STRING NOT NULL,
  filing_id STRING NOT NULL,
  nugget_text STRING NOT NULL,
  context_text STRING,

  filing_type STRING,
  section STRING,

  nugget_type STRING,
  themes STRING,
  signal_strength STRING,

  companies_mentioned STRING,
  technologies_mentioned STRING,
  competitors_named STRING,
  regulators_mentioned STRING,

  risk_level STRING,
  is_new_disclosure BOOL,
  is_actionable BOOL,
  actionability_reason STRING,

  relevance_score FLOAT64,

  ticker STRING NOT NULL,
  company_name STRING NOT NULL,
  cik STRING,
  fiscal_year INT64 NOT NULL,
  fiscal_quarter INT64,
  filing_date TIMESTAMP,
  accession_number STRING,

  extracted_at TIMESTAMP NOT NULL,
  extraction_model STRING,
  extraction_confidence FLOAT64,
  domain STRING
)
"""

# ============================================================================
# Podcast Transcripts
# ============================================================================

BQ_PODCAST_TRANSCRIPTS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  transcript_id STRING NOT NULL,
  episode_id STRING NOT NULL,
  podcast_id STRING NOT NULL,
  podcast_name STRING NOT NULL,
  episode_title STRING NOT NULL,
  episode_url STRING,
  audio_url STRING,

  full_text STRING,
  formatted_text STRING,
  char_count INT64,
  word_count INT64,
  duration_seconds INT64,

  hosts ARRAY<STRING>,
  guest_name STRING,
  guest_title STRING,
  guest_company STRING,
  speaker_count INT64,

  transcript_source STRING,
  status STRING,
  published_at TIMESTAMP,
  ingested_at TIMESTAMP NOT NULL,
  transcribed_at TIMESTAMP,
  transcription_cost_usd FLOAT64
)
"""

# ============================================================================
# Podcast Quotes
# ============================================================================

BQ_PODCAST_QUOTES_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  quote_id STRING NOT NULL,
  transcript_id STRING NOT NULL,
  episode_id STRING NOT NULL,
  quote_text STRING NOT NULL,
  context_before STRING,
  context_after STRING,

  speaker_name STRING NOT NULL,
  speaker_role STRING,
  speaker_title STRING,
  speaker_company STRING,

  quote_type STRING,
  themes STRING,
  sentiment STRING,

  companies_mentioned STRING,
  technologies_mentioned STRING,
  people_mentioned STRING,

  relevance_score FLOAT64,
  is_quotable BOOL,
  quotability_reason STRING,

  podcast_id STRING NOT NULL,
  podcast_name STRING NOT NULL,
  episode_title STRING NOT NULL,
  published_at TIMESTAMP,

  extracted_at TIMESTAMP NOT NULL,
  extraction_model STRING,
  extraction_confidence FLOAT64
)
"""

# ============================================================================
# Weekly Briefings
# ============================================================================

BQ_WEEKLY_BRIEFINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id STRING NOT NULL,
  domain STRING NOT NULL,
  week_of STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,

  sections JSON,
  market_movers JSON,
  research_papers JSON,

  articles_analyzed INT64,
  sections_active INT64,
  sections_total INT64,
  generation_cost_usd FLOAT64,
  pre_brief_id STRING
)
"""

# ============================================================================
# Article Embeddings (for Vertex AI vector search)
# ============================================================================

BQ_ARTICLE_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  article_id STRING NOT NULL,
  title STRING,
  url STRING,
  source_name STRING,
  primary_category STRING,
  priority STRING,
  relevance_score FLOAT64,
  domain STRING,
  published_at TIMESTAMP,
  document_text STRING,
  embedding ARRAY<FLOAT64>
)
"""

# ============================================================================
# SEC Nugget Embeddings (for Vertex AI vector search)
# ============================================================================

BQ_SEC_NUGGET_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  nugget_id STRING NOT NULL,
  ticker STRING,
  company_name STRING,
  filing_type STRING,
  nugget_type STRING,
  themes STRING,
  signal_strength STRING,
  risk_level STRING,
  relevance_score FLOAT64,
  domain STRING,
  filing_date TIMESTAMP,
  document_text STRING,
  embedding ARRAY<FLOAT64>
)
"""

# ============================================================================
# Earnings Quote Embeddings (for Vertex AI vector search)
# ============================================================================

BQ_EARNINGS_QUOTE_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  quote_id STRING NOT NULL,
  ticker STRING,
  company_name STRING,
  speaker_name STRING,
  speaker_role STRING,
  quote_type STRING,
  themes STRING,
  sentiment STRING,
  relevance_score FLOAT64,
  domain STRING,
  year INT64,
  quarter INT64,
  document_text STRING,
  embedding ARRAY<FLOAT64>
)
"""

# ============================================================================
# Podcast Quote Embeddings (for Vertex AI vector search)
# ============================================================================

BQ_PODCAST_QUOTE_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  quote_id STRING NOT NULL,
  podcast_name STRING,
  episode_title STRING,
  speaker_name STRING,
  speaker_role STRING,
  quote_type STRING,
  themes STRING,
  sentiment STRING,
  relevance_score FLOAT64,
  published_at TIMESTAMP,
  document_text STRING,
  embedding ARRAY<FLOAT64>
)
"""

# ============================================================================
# Case Studies (Phase 6)
# ============================================================================

BQ_CASE_STUDIES_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  case_study_id STRING NOT NULL,
  source_type STRING NOT NULL,
  source_id STRING NOT NULL,
  domain STRING,

  grounding_quote STRING NOT NULL,
  context_text STRING,

  use_case_title STRING NOT NULL,
  use_case_summary STRING,
  company STRING,
  industry STRING,
  technology_stack ARRAY<STRING>,

  department STRING,
  implementation_detail STRING,
  teams_impacted ARRAY<STRING>,
  scale STRING,
  timeline STRING,
  readiness_level STRING,

  outcome_metric STRING,
  outcome_type STRING,
  outcome_quantified BOOL,

  speaker STRING,
  speaker_role STRING,
  speaker_company STRING,

  companies_mentioned ARRAY<STRING>,
  technologies_mentioned ARRAY<STRING>,
  people_mentioned ARRAY<STRING>,
  competitors_mentioned ARRAY<STRING>,

  qubit_type STRING,
  gate_fidelity STRING,
  commercial_viability STRING,
  scientific_significance STRING,

  ai_model_used STRING,
  roi_metric STRING,
  deployment_type STRING,

  relevance_score FLOAT64,
  confidence FLOAT64,

  metadata JSON,

  extracted_at TIMESTAMP NOT NULL,
  extraction_model STRING,
  extraction_confidence FLOAT64
)
"""

# ============================================================================
# Case Study Embeddings (for Vertex AI vector search)
# ============================================================================

BQ_CASE_STUDY_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  case_study_id STRING NOT NULL,
  source_type STRING,
  company STRING,
  industry STRING,
  use_case_title STRING,
  outcome_type STRING,
  readiness_level STRING,
  relevance_score FLOAT64,
  technology_stack STRING,
  domain STRING,
  extracted_at TIMESTAMP,
  document_text STRING,
  embedding ARRAY<FLOAT64>
)
"""

# ============================================================================
# Funding Events (Phase 3)
# ============================================================================

BQ_FUNDING_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id STRING NOT NULL,
  article_id STRING NOT NULL,
  article_url STRING NOT NULL,
  domain STRING,

  startup_name STRING NOT NULL,
  funding_round STRING,
  funding_amount STRING,
  valuation STRING,
  lead_investors ARRAY<STRING>,
  other_investors ARRAY<STRING>,

  investment_thesis STRING,
  known_technologies ARRAY<STRING>,
  use_of_funds STRING,

  extracted_at TIMESTAMP NOT NULL,
  confidence_score FLOAT64,
  grounding_quote STRING NOT NULL
)
"""

# ============================================================================
# API Keys (Proxy Storage)
# ============================================================================

BQ_API_KEYS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  api_key STRING NOT NULL,
  client_name STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  last_used_at TIMESTAMP,
  is_active BOOL NOT NULL,
  tier STRING,
  permissions ARRAY<STRING>,
  allowed_domains ARRAY<STRING>
)
"""

# ============================================================================
# Maturity Radar Metrics
# ============================================================================

BQ_MATURITY_RADAR_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  calculated_date DATE NOT NULL,
  domain STRING NOT NULL,
  category_name STRING NOT NULL,
  signal_score FLOAT64 NOT NULL,
  article_count INT64 NOT NULL,
  paper_count INT64 NOT NULL,
  avg_relevance FLOAT64 NOT NULL,
  velocity_trend FLOAT64
)
"""

# ============================================================================
# Patents (Phase 9)
# ============================================================================

BQ_PATENTS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id STRING NOT NULL,
  title STRING NOT NULL,
  abstract STRING,
  assignee STRING,
  inventors ARRAY<STRING>,
  filing_date STRING,
  publication_date STRING,
  patent_url STRING,
  domain STRING,
  relevance_score FLOAT64,
  innovation_category STRING,
  created_at TIMESTAMP NOT NULL
)
"""


# ============================================================================
# Table registry — maps logical name to DDL template
# ============================================================================

BQ_TABLE_REGISTRY = {
    "articles": BQ_ARTICLES_DDL,
    "digests": BQ_DIGESTS_DDL,
    "papers": BQ_PAPERS_DDL,
    "stocks": BQ_STOCKS_DDL,
    "earnings_transcripts": BQ_EARNINGS_TRANSCRIPTS_DDL,
    "earnings_quotes": BQ_EARNINGS_QUOTES_DDL,
    "sec_filings": BQ_SEC_FILINGS_DDL,
    "sec_nuggets": BQ_SEC_NUGGETS_DDL,
    "podcast_transcripts": BQ_PODCAST_TRANSCRIPTS_DDL,
    "podcast_quotes": BQ_PODCAST_QUOTES_DDL,
    "weekly_briefings": BQ_WEEKLY_BRIEFINGS_DDL,
    "article_embeddings": BQ_ARTICLE_EMBEDDINGS_DDL,
    "sec_nugget_embeddings": BQ_SEC_NUGGET_EMBEDDINGS_DDL,
    "earnings_quote_embeddings": BQ_EARNINGS_QUOTE_EMBEDDINGS_DDL,
    "podcast_quote_embeddings": BQ_PODCAST_QUOTE_EMBEDDINGS_DDL,
    "case_studies": BQ_CASE_STUDIES_DDL,
    "case_study_embeddings": BQ_CASE_STUDY_EMBEDDINGS_DDL,
    "funding_events": BQ_FUNDING_EVENTS_DDL,
    "api_keys": BQ_API_KEYS_DDL,
    "maturity_radar_metrics": BQ_MATURITY_RADAR_METRICS_DDL,
    "patents": BQ_PATENTS_DDL,
}


def get_all_create_ddl(dataset: str) -> list[str]:
    """Return list of CREATE TABLE IF NOT EXISTS statements for all tables."""
    return [
        ddl.format(table=f"{dataset}.{name}")
        for name, ddl in BQ_TABLE_REGISTRY.items()
    ]


# ============================================================================
# Vector Indexes
# ============================================================================

# Tables with embedding columns that need vector indexes
VECTOR_INDEX_TABLES = [
    "article_embeddings",
    "sec_nugget_embeddings",
    "earnings_quote_embeddings",
    "podcast_quote_embeddings",
    "case_study_embeddings",
]


def get_vector_index_ddl(dataset: str) -> list[str]:
    """
    Return CREATE VECTOR INDEX IF NOT EXISTS statements for all embedding tables.

    Uses IVF index type with COSINE distance metric — the standard for
    BigQuery vector search with text-embedding-005 (768 dimensions).

    These indexes improve VECTOR_SEARCH performance on large embedding tables.
    """
    ddl_statements = []
    for table_name in VECTOR_INDEX_TABLES:
        index_name = f"idx_{table_name}_vec"
        ddl = (
            f"CREATE VECTOR INDEX IF NOT EXISTS `{index_name}`\n"
            f"ON `{dataset}.{table_name}`(embedding)\n"
            f"OPTIONS(index_type='IVF', distance_type='COSINE', ivf_options='{{\"num_lists\": 100}}')"
        )
        ddl_statements.append(ddl)

    return ddl_statements
