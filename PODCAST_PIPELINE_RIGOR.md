# Podcast Pipeline Rigor: Production Hardening Plan

> **Created**: 2026-01-26  
> **Status**: Ready for Execution  
> **Session**: Next fresh session

---

## Executive Summary

The podcast pipeline has 16 episodes fully transcribed via AssemblyAI, but **zero quotes were extracted** due to a syntax error in `quotes_bigquery.py`. Additionally, transcripts are currently stored only in local ChromaDB, not in BigQuery for production use.

**This document outlines the complete remediation and hardening plan.**

---

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| Transcripts (16 episodes) | ✅ Stored | ChromaDB (`data/embeddings/podcast_transcripts/`) |
| Quotes | ❌ Only 2 test rows | BigQuery `sprite_intelligence.podcast_quotes` |
| Transcript Table | ❌ Does not exist | BigQuery |
| Quote Extractor | ✅ Fixed | Sonnet 4.6 + chunking |
| BigQuery Quote Storage | ✅ Fixed | Syntax error resolved |

### Episodes Completed (from `podcast_state.db`)
```
config_startup-cpg:        6 episodes (AssemblyAI)
config_cpg-insiders:       2 episodes (AssemblyAI)
config_cpg-guys:           6 episodes (AssemblyAI)
config_at-your-convenience: 2 episodes (AssemblyAI)
```

---

## Phase 1: Backfill Quote Extraction

**Goal**: Extract quotes from all 16 existing transcripts and store in BigQuery.

### 1.1 Create Backfill Script

**File**: `scripts/backfill_podcast_quotes.py`

```python
"""
Backfill script to extract quotes from existing ChromaDB transcripts.
Uses the fixed QuoteExtractor (Sonnet 4.6 + chunking).
"""

Steps:
1. Connect to ChromaDB collection: podcast_transcripts
2. Query all stored transcripts with metadata
3. For each transcript:
   a. Skip if quotes already exist in BigQuery for this episode_id
   b. Call QuoteExtractor.extract_quotes()
   c. Store results via BigQueryQuoteStorage
   d. Log progress and cost
4. Report summary: quotes extracted, total cost, any failures
```

### 1.2 Expected Output

- **Quotes per episode**: 10-25 (depending on content richness)
- **Total expected**: 160-400 quotes across 16 episodes
- **Cost estimate**: ~$0.15/episode × 16 = **~$2.50 total**
- **Runtime**: ~2-3 minutes per episode, ~30-45 min total

### 1.3 Verification Steps

```sql
-- Verify quotes were stored
SELECT 
    podcast_name,
    COUNT(*) as quote_count,
    AVG(relevance_score) as avg_relevance
FROM sprite_intelligence.podcast_quotes
WHERE podcast_name != 'Test Podcast'
GROUP BY podcast_name
ORDER BY quote_count DESC;

-- Check speaker attribution quality
SELECT 
    speaker_name,
    speaker_role,
    COUNT(*) as cnt
FROM sprite_intelligence.podcast_quotes
WHERE podcast_name != 'Test Podcast'
GROUP BY speaker_name, speaker_role
ORDER BY cnt DESC;
```

---

## Phase 2: Create BigQuery Transcripts Table

**Goal**: Create production storage for full transcripts in BigQuery.

### 2.1 Schema Design

**Table**: `sprite_intelligence.podcast_transcripts`

```sql
CREATE TABLE sprite_intelligence.podcast_transcripts (
    transcript_id STRING NOT NULL,
    episode_id STRING NOT NULL,
    podcast_name STRING NOT NULL,
    episode_title STRING NOT NULL,
    episode_url STRING,
    published_date DATE,
    
    -- Transcript content
    full_text STRING NOT NULL,  -- Raw transcript text
    formatted_text STRING,       -- Speaker-labeled version
    word_count INT64,
    duration_seconds INT64,
    
    -- Speaker diarization metadata
    has_speaker_labels BOOLEAN DEFAULT FALSE,
    speaker_count INT64,
    speakers ARRAY<STRUCT<
        label STRING,
        name STRING,
        role STRING
    >>,
    
    -- Resolution metadata
    resolver_used STRING,        -- 'assemblyai', 'youtube_transcript', 'site_transcript'
    resolution_confidence FLOAT64,
    transcription_cost_usd FLOAT64,
    
    -- Guest/host metadata
    guest_name STRING,
    guest_title STRING,
    guest_company STRING,
    hosts ARRAY<STRING>,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP
)
PARTITION BY published_date
CLUSTER BY podcast_name, resolver_used;
```

### 2.2 Implementation

**File**: `ingestion_template/podcast_pipeline/storage/transcripts_bigquery.py`

Create `BigQueryTranscriptStorage` class with methods:
- `store_transcript(transcript, episode_metadata) -> str`
- `get_transcript(episode_id) -> Optional[Transcript]`
- `get_transcripts_by_podcast(podcast_name, limit) -> List[Transcript]`
- `search_transcripts(query, limit) -> List[Transcript]`
- `transcript_exists(episode_id) -> bool`
- `count() -> int`

### 2.3 Update Factory

**File**: `ingestion_template/podcast_pipeline/storage/__init__.py`

Update `get_transcript_storage()` to return `BigQueryTranscriptStorage` when `GCP_PROJECT_ID` is set.

```python
def get_transcript_storage() -> TranscriptStorage:
    if get_secret("GCP_PROJECT_ID"):
        from .transcripts_bigquery import BigQueryTranscriptStorage
        return BigQueryTranscriptStorage()
    
    # Local fallback
    from .transcripts_chromadb import ChromaDBTranscriptStorage
    return ChromaDBTranscriptStorage()
```

---

## Phase 3: Migrate Existing Transcripts

**Goal**: Copy all 16 transcripts from ChromaDB to the new BigQuery table.

### 3.1 Migration Script

**File**: `scripts/migrate_transcripts_to_bigquery.py`

```python
"""
One-time migration of ChromaDB transcripts to BigQuery.
"""

Steps:
1. Connect to ChromaDB collection
2. Retrieve all transcript documents with metadata
3. For each transcript:
   a. Parse metadata (episode_id, podcast_name, etc.)
   b. Reconstruct Transcript object
   c. Store in BigQueryTranscriptStorage
4. Verify counts match
5. (Optional) Mark ChromaDB collection as archived
```

### 3.2 Data Mapping

| ChromaDB Field | BigQuery Column |
|---------------|-----------------|
| document | full_text |
| metadata.episode_id | episode_id |
| metadata.podcast_name | podcast_name |
| metadata.episode_title | episode_title |
| metadata.episode_url | episode_url |
| metadata.published_at | published_date |
| metadata.guest_name | guest_name |
| metadata.guest_title | guest_title |
| metadata.guest_company | guest_company |

### 3.3 Verification

```sql
-- Verify migration
SELECT COUNT(*) FROM sprite_intelligence.podcast_transcripts;
-- Should return 16

-- Compare with state DB
-- podcast_state.db should show 16 completed episodes
```

---

## Phase 4: Update Pipeline for Production

**Goal**: Ensure new episodes automatically store transcripts in BigQuery.

### 4.1 Pipeline Changes

The pipeline (`pipeline.py`) already calls `transcript_storage.store_transcript()`. After updating the factory, new episodes will automatically go to BigQuery.

**Verification**: Run pipeline with `--dry-run` to confirm storage selection:

```bash
python -m ingestion_template.podcast_pipeline.cli run --industry cpg --days 7 --dry-run
```

Check logs for:
```
[PIPELINE] Transcript storage: BigQueryTranscriptStorage
```

### 4.2 API Integration

Ensure the API endpoints query BigQuery for transcripts:

**File**: `api/routes/podcast.py`

- `/api/podcast/transcripts` - List transcripts
- `/api/podcast/transcripts/{episode_id}` - Get specific transcript
- `/api/podcast/search` - Search across quotes AND transcripts

---

## Execution Checklist

### Session Tasks

- [ ] **Phase 1**: Backfill Quote Extraction
  - [ ] Create `scripts/backfill_podcast_quotes.py`
  - [ ] Run backfill (expect ~$2.50 Anthropic cost)
  - [ ] Verify 150+ quotes in BigQuery
  - [ ] Check speaker attribution quality

- [ ] **Phase 2**: Create BigQuery Transcripts Table
  - [ ] Create `transcripts_bigquery.py` with schema
  - [ ] Add table creation logic
  - [ ] Update storage factory

- [ ] **Phase 3**: Migrate Existing Transcripts
  - [ ] Create `scripts/migrate_transcripts_to_bigquery.py`
  - [ ] Run migration
  - [ ] Verify 16 transcripts in BigQuery

- [ ] **Phase 4**: Verify Production Pipeline
  - [ ] Test pipeline with dry-run
  - [ ] Confirm BigQuery storage selection
  - [ ] Run one real episode to verify end-to-end

- [ ] **Cleanup**
  - [ ] Delete test quotes from BigQuery
  - [ ] Update podcast pipeline README
  - [ ] Commit all changes

---

## Cost Summary

| Item | Estimated Cost |
|------|---------------|
| Quote backfill (16 episodes × $0.15) | ~$2.50 |
| BigQuery storage (minimal) | ~$0.01/mo |
| **Total one-time cost** | **~$2.50** |

---

## Files to Create/Modify

| Action | File |
|--------|------|
| CREATE | `scripts/backfill_podcast_quotes.py` |
| CREATE | `scripts/migrate_transcripts_to_bigquery.py` |
| CREATE | `ingestion_template/podcast_pipeline/storage/transcripts_bigquery.py` |
| MODIFY | `ingestion_template/podcast_pipeline/storage/__init__.py` |
| MODIFY | `ingestion_template/podcast_pipeline/README.md` |
| DELETE | `scripts/_verify_podcast_pipeline.py` (temp script) |
| DELETE | `scripts/_investigate_quotes.py` (temp script) |

---

## Success Criteria

1. **Quotes**: 150+ real quotes in BigQuery with proper speaker attribution
2. **Transcripts**: 16 transcripts in BigQuery with full metadata
3. **Pipeline**: New episodes auto-store to BigQuery
4. **API**: `/api/podcast/search` returns real quotes
5. **No Test Data**: "Test Podcast" rows deleted from BigQuery
