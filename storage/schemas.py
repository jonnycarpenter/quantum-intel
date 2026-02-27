"""
SQLite Table Schemas
====================

Table creation SQL for the Quantum Intelligence Hub.
"""

ARTICLES_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_name TEXT,
    source_url TEXT,
    source_type TEXT DEFAULT 'rss',
    published_at TEXT,
    date_confidence TEXT DEFAULT 'fetched',
    fetched_at TEXT NOT NULL,
    summary TEXT,
    full_text TEXT,
    author TEXT,
    tags TEXT DEFAULT '[]',

    -- Classification
    primary_category TEXT DEFAULT 'market_analysis',
    priority TEXT DEFAULT 'medium',
    relevance_score REAL DEFAULT 0.5,
    ai_summary TEXT,
    key_takeaway TEXT,
    companies_mentioned TEXT DEFAULT '[]',
    technologies_mentioned TEXT DEFAULT '[]',
    people_mentioned TEXT DEFAULT '[]',
    use_case_domains TEXT DEFAULT '[]',
    sentiment TEXT DEFAULT 'neutral',
    confidence REAL DEFAULT 0.8,
    classifier_model TEXT,
    classified_at TEXT,

    -- Digest
    digest_priority TEXT DEFAULT 'medium',
    feed_eligible INTEGER DEFAULT 1,

    -- Dedup
    content_hash TEXT,
    coverage_count INTEGER DEFAULT 1,
    duplicate_urls TEXT DEFAULT '[]',

    -- Metadata
    metadata TEXT DEFAULT '{}',

    -- Domain
    domain TEXT DEFAULT 'quantum'
);
"""

ARTICLES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(primary_category);",
    "CREATE INDEX IF NOT EXISTS idx_articles_priority ON articles(priority);",
    "CREATE INDEX IF NOT EXISTS idx_articles_source_type ON articles(source_type);",
    "CREATE INDEX IF NOT EXISTS idx_articles_relevance ON articles(relevance_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_articles_domain ON articles(domain);",
]

DIGESTS_TABLE = """
CREATE TABLE IF NOT EXISTS digests (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    period_hours INTEGER DEFAULT 72,
    executive_summary TEXT,
    content TEXT,
    total_items INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0
);
"""

# Paper and Stock tables (Phase 2)
PAPERS_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT DEFAULT '[]',
    abstract TEXT,
    categories TEXT DEFAULT '[]',
    published_at TEXT,
    updated_at TEXT,
    ingested_at TEXT,
    pdf_url TEXT,

    -- LLM-generated
    relevance_score REAL,
    paper_type TEXT,
    use_case_category TEXT,
    commercial_readiness TEXT,
    significance_summary TEXT
);
"""

STOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS stocks (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    change_percent REAL,
    market_cap REAL,
    sma_20 REAL,
    sma_50 REAL,
    PRIMARY KEY (ticker, date)
);
"""

PAPERS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_papers_published_at ON papers(published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_papers_ingested_at ON papers(ingested_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_papers_relevance ON papers(relevance_score DESC);",
]

STOCKS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_stocks_date ON stocks(date DESC);",
]

# ============================================================================
# Earnings Pipeline Tables (Phase 4A)
# ============================================================================

EARNINGS_TRANSCRIPTS_TABLE = """
CREATE TABLE IF NOT EXISTS earnings_transcripts (
    transcript_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    transcript_text TEXT,
    call_date TEXT,
    participants TEXT DEFAULT '[]',
    fiscal_period TEXT,
    ingested_at TEXT NOT NULL,
    char_count INTEGER DEFAULT 0,
    domain TEXT DEFAULT 'quantum',
    UNIQUE(ticker, year, quarter)
);
"""

EARNINGS_QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS earnings_quotes (
    quote_id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    quote_text TEXT NOT NULL,
    context_before TEXT,
    context_after TEXT,

    -- Speaker attribution
    speaker_name TEXT NOT NULL,
    speaker_role TEXT DEFAULT 'unknown',
    speaker_title TEXT,
    speaker_company TEXT,
    speaker_firm TEXT,

    -- Classification
    quote_type TEXT DEFAULT 'strategy',
    themes TEXT DEFAULT '',
    sentiment TEXT DEFAULT 'neutral',
    confidence_level TEXT DEFAULT 'cautious',

    -- Entities
    companies_mentioned TEXT DEFAULT '',
    technologies_mentioned TEXT DEFAULT '',
    competitors_mentioned TEXT DEFAULT '',
    metrics_mentioned TEXT DEFAULT '',

    -- Relevance
    relevance_score REAL DEFAULT 0.5,
    is_quotable INTEGER DEFAULT 0,
    quotability_reason TEXT,

    -- Source context
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    call_date TEXT,
    section TEXT DEFAULT 'unknown',
    position_in_section INTEGER DEFAULT 0,

    -- Audit
    extracted_at TEXT NOT NULL,
    extraction_model TEXT,
    extraction_confidence REAL DEFAULT 0.8,
    domain TEXT DEFAULT 'quantum',

    FOREIGN KEY (transcript_id) REFERENCES earnings_transcripts(transcript_id)
);
"""

EARNINGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_transcripts_ticker ON earnings_transcripts(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_transcripts_year_quarter ON earnings_transcripts(year, quarter);",
    "CREATE INDEX IF NOT EXISTS idx_transcripts_ingested ON earnings_transcripts(ingested_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_transcript ON earnings_quotes(transcript_id);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_ticker ON earnings_quotes(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_type ON earnings_quotes(quote_type);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_relevance ON earnings_quotes(relevance_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_quotable ON earnings_quotes(is_quotable);",
    "CREATE INDEX IF NOT EXISTS idx_transcripts_domain ON earnings_transcripts(domain);",
    "CREATE INDEX IF NOT EXISTS idx_quotes_domain ON earnings_quotes(domain);",
]

# ============================================================================
# SEC Pipeline Tables (Phase 4A)
# ============================================================================

SEC_FILINGS_TABLE = """
CREATE TABLE IF NOT EXISTS sec_filings (
    filing_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    cik TEXT NOT NULL,
    accession_number TEXT,
    filing_type TEXT NOT NULL,
    filing_date TEXT,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    primary_document TEXT,
    filing_url TEXT,
    raw_content TEXT,
    sections TEXT,
    ingested_at TEXT NOT NULL,
    char_count INTEGER DEFAULT 0,
    domain TEXT DEFAULT 'quantum',
    UNIQUE(ticker, filing_type, fiscal_year, fiscal_quarter)
);
"""

SEC_NUGGETS_TABLE = """
CREATE TABLE IF NOT EXISTS sec_nuggets (
    nugget_id TEXT PRIMARY KEY,
    filing_id TEXT NOT NULL,
    nugget_text TEXT NOT NULL,
    context_text TEXT,

    -- Filing context
    filing_type TEXT DEFAULT '10-K',
    section TEXT DEFAULT 'unknown',

    -- Classification
    nugget_type TEXT DEFAULT 'risk_admission',
    themes TEXT DEFAULT '',
    signal_strength TEXT DEFAULT 'standard',

    -- Entities
    companies_mentioned TEXT DEFAULT '',
    technologies_mentioned TEXT DEFAULT '',
    competitors_named TEXT DEFAULT '',
    regulators_mentioned TEXT DEFAULT '',

    -- Risk/Opportunity
    risk_level TEXT DEFAULT 'medium',
    is_new_disclosure INTEGER DEFAULT 0,
    is_actionable INTEGER DEFAULT 0,
    actionability_reason TEXT,

    -- Relevance
    relevance_score REAL DEFAULT 0.5,

    -- Source context
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    cik TEXT,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    filing_date TEXT,
    accession_number TEXT,

    -- Audit
    extracted_at TEXT NOT NULL,
    extraction_model TEXT,
    extraction_confidence REAL DEFAULT 0.8,
    domain TEXT DEFAULT 'quantum',

    FOREIGN KEY (filing_id) REFERENCES sec_filings(filing_id)
);
"""

SEC_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_filings_ticker ON sec_filings(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_filings_type ON sec_filings(filing_type);",
    "CREATE INDEX IF NOT EXISTS idx_filings_year ON sec_filings(fiscal_year);",
    "CREATE INDEX IF NOT EXISTS idx_filings_ingested ON sec_filings(ingested_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_filing ON sec_nuggets(filing_id);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_ticker ON sec_nuggets(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_type ON sec_nuggets(nugget_type);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_relevance ON sec_nuggets(relevance_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_new ON sec_nuggets(is_new_disclosure);",
    "CREATE INDEX IF NOT EXISTS idx_filings_domain ON sec_filings(domain);",
    "CREATE INDEX IF NOT EXISTS idx_nuggets_domain ON sec_nuggets(domain);",
]

# ============================================================================
# Podcast Pipeline Tables (Phase 4B)
# ============================================================================

PODCAST_TRANSCRIPTS_TABLE = """
CREATE TABLE IF NOT EXISTS podcast_transcripts (
    transcript_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    podcast_id TEXT NOT NULL,
    podcast_name TEXT NOT NULL,
    episode_title TEXT NOT NULL,
    episode_url TEXT,
    audio_url TEXT,

    -- Content
    full_text TEXT,
    formatted_text TEXT,
    char_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    duration_seconds INTEGER,

    -- Speakers
    hosts TEXT DEFAULT '[]',
    guest_name TEXT,
    guest_title TEXT,
    guest_company TEXT,
    speaker_count INTEGER DEFAULT 0,

    -- Source & status
    transcript_source TEXT DEFAULT 'assemblyai',
    status TEXT DEFAULT 'pending',
    published_at TEXT,
    ingested_at TEXT NOT NULL,
    transcribed_at TEXT,
    transcription_cost_usd REAL DEFAULT 0.0,

    UNIQUE(podcast_id, episode_id)
);
"""

PODCAST_QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS podcast_quotes (
    quote_id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    quote_text TEXT NOT NULL,
    context_before TEXT,
    context_after TEXT,

    -- Speaker attribution
    speaker_name TEXT NOT NULL,
    speaker_role TEXT DEFAULT 'guest',
    speaker_title TEXT,
    speaker_company TEXT,

    -- Classification
    quote_type TEXT DEFAULT 'technical_insight',
    themes TEXT DEFAULT '',
    sentiment TEXT DEFAULT 'neutral',

    -- Entities
    companies_mentioned TEXT DEFAULT '',
    technologies_mentioned TEXT DEFAULT '',
    people_mentioned TEXT DEFAULT '',

    -- Relevance
    relevance_score REAL DEFAULT 0.5,
    is_quotable INTEGER DEFAULT 0,
    quotability_reason TEXT,

    -- Source context
    podcast_id TEXT NOT NULL,
    podcast_name TEXT NOT NULL,
    episode_title TEXT NOT NULL,
    published_at TEXT,

    -- Audit
    extracted_at TEXT NOT NULL,
    extraction_model TEXT,
    extraction_confidence REAL DEFAULT 0.8,

    FOREIGN KEY (transcript_id) REFERENCES podcast_transcripts(transcript_id)
);
"""

PODCAST_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_podcast_trans_podcast ON podcast_transcripts(podcast_id);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_trans_status ON podcast_transcripts(status);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_trans_published ON podcast_transcripts(published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_trans_ingested ON podcast_transcripts(ingested_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_transcript ON podcast_quotes(transcript_id);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_podcast ON podcast_quotes(podcast_id);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_type ON podcast_quotes(quote_type);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_relevance ON podcast_quotes(relevance_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_quotable ON podcast_quotes(is_quotable);",
    "CREATE INDEX IF NOT EXISTS idx_podcast_quotes_speaker ON podcast_quotes(speaker_name);",
]

# ============================================================================
# Weekly Briefing Table (Phase 4C)
# ============================================================================

WEEKLY_BRIEFINGS_TABLE = """
CREATE TABLE IF NOT EXISTS weekly_briefings (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL DEFAULT 'quantum',
    week_of TEXT NOT NULL,
    created_at TEXT NOT NULL,

    -- Serialized JSON blobs
    sections TEXT DEFAULT '[]',
    market_movers TEXT DEFAULT '[]',
    research_papers TEXT DEFAULT '[]',

    -- Metadata
    articles_analyzed INTEGER DEFAULT 0,
    sections_active INTEGER DEFAULT 0,
    sections_total INTEGER DEFAULT 7,
    generation_cost_usd REAL DEFAULT 0.0,
    pre_brief_id TEXT,

    UNIQUE(domain, week_of)
);
"""

WEEKLY_BRIEFINGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wb_domain ON weekly_briefings(domain);",
    "CREATE INDEX IF NOT EXISTS idx_wb_week ON weekly_briefings(week_of DESC);",
    "CREATE INDEX IF NOT EXISTS idx_wb_created ON weekly_briefings(created_at DESC);",
]

# ============================================================================
# Case Studies Table (Phase 6)
# ============================================================================

CASE_STUDIES_TABLE = """
CREATE TABLE IF NOT EXISTS case_studies (
    case_study_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    domain TEXT DEFAULT 'quantum',

    -- Grounding
    grounding_quote TEXT NOT NULL,
    context_text TEXT,

    -- Core fields
    use_case_title TEXT NOT NULL,
    use_case_summary TEXT,
    company TEXT,
    industry TEXT,
    technology_stack TEXT DEFAULT '',

    -- Implementation
    department TEXT,
    implementation_detail TEXT,
    teams_impacted TEXT DEFAULT '',
    scale TEXT,
    timeline TEXT,
    readiness_level TEXT DEFAULT 'announced',

    -- Outcome
    outcome_metric TEXT,
    outcome_type TEXT,
    outcome_quantified INTEGER DEFAULT 0,

    -- Speaker (podcast/earnings)
    speaker TEXT,
    speaker_role TEXT,
    speaker_company TEXT,

    -- Entities
    companies_mentioned TEXT DEFAULT '',
    technologies_mentioned TEXT DEFAULT '',
    people_mentioned TEXT DEFAULT '',
    competitors_mentioned TEXT DEFAULT '',

    -- Quantum-specific
    qubit_type TEXT,
    gate_fidelity TEXT,
    commercial_viability TEXT,
    scientific_significance TEXT,

    -- AI-specific
    ai_model_used TEXT,
    roi_metric TEXT,
    deployment_type TEXT,

    -- Relevance
    relevance_score REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.8,

    -- Metadata overflow
    metadata TEXT DEFAULT '{}',

    -- Audit
    extracted_at TEXT NOT NULL,
    extraction_model TEXT,
    extraction_confidence REAL DEFAULT 0.8
);
"""

CASE_STUDIES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cs_source_type ON case_studies(source_type);",
    "CREATE INDEX IF NOT EXISTS idx_cs_source_id ON case_studies(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_cs_domain ON case_studies(domain);",
    "CREATE INDEX IF NOT EXISTS idx_cs_company ON case_studies(company);",
    "CREATE INDEX IF NOT EXISTS idx_cs_industry ON case_studies(industry);",
    "CREATE INDEX IF NOT EXISTS idx_cs_outcome_type ON case_studies(outcome_type);",
    "CREATE INDEX IF NOT EXISTS idx_cs_relevance ON case_studies(relevance_score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_cs_readiness ON case_studies(readiness_level);",
    "CREATE INDEX IF NOT EXISTS idx_cs_extracted_at ON case_studies(extracted_at DESC);",
]

ALL_TABLES = [
    ARTICLES_TABLE, DIGESTS_TABLE, PAPERS_TABLE, STOCKS_TABLE,
    EARNINGS_TRANSCRIPTS_TABLE, EARNINGS_QUOTES_TABLE,
    SEC_FILINGS_TABLE, SEC_NUGGETS_TABLE,
    PODCAST_TRANSCRIPTS_TABLE, PODCAST_QUOTES_TABLE,
    WEEKLY_BRIEFINGS_TABLE,
    CASE_STUDIES_TABLE,
]
ALL_INDEXES = ARTICLES_INDEXES + PAPERS_INDEXES + STOCKS_INDEXES + EARNINGS_INDEXES + SEC_INDEXES + PODCAST_INDEXES + WEEKLY_BRIEFINGS_INDEXES + CASE_STUDIES_INDEXES
