# Multi-Agent Weekly Briefing — Recreation Spec

> **Purpose**: Step-by-step blueprint for recreating the weekly executive briefing pipeline in a new Quantum Computing & AI Intelligence Hub. Derived from the production C1 Intelligence Hub codebase (both V1 2-agent and V2 3-agent architectures).

---

## 1. What It Does

The Multi-Agent Briefing is an **automated, scheduled pipeline** that ingests the past 14 days of intelligence, distills it into a strategic executive briefing with citations, voice enrichment, and story arc tracking, and then converts it into a podcast-style audio episode.

**End-user experience:**
- Every **Monday morning**, a new briefing appears in the UI
- Contains BLUF (Bottom Line Up Front), 2–4 deep-dive sections, and source citations
- Each section tagged as `net_new` or `continuing` relative to prior weeks
- Company logos rendered inline via `[[Company Name]]` tags
- Playable podcast audio (4–6 minutes, two-voice conversation)
- Conversational AI assistant for follow-up questions about the briefing

---

## 2. Architecture Overview

Two production architectures exist. Both are documented here.

### V1: 2-Agent Pipeline (Simpler — Good Starting Point)

```
Agent 1 (Pre-Brief)              Agent 2 (Synthesis)           Podcast Generation
claude-sonnet                     claude-opus                   ElevenLabs TTS
        │                               │                            │
        ▼                               ▼                            ▼
┌─────────────────┐            ┌─────────────────┐         ┌─────────────────┐
│ Analyze ALL     │            │ Compare against │         │ Convert to      │
│ priority items  │ ────────►  │ historical ctx  │ ─────►  │ natural speech  │
│ from 14 days    │            │ + voice enrich  │         │ Upload to GCS   │
└─────────────────┘            │ + Exa search    │         └─────────────────┘
        │                      └─────────────────┘                  │
        ▼                               │                            ▼
  Pre-Brief JSON              Final Briefing JSON           podcast.mp3
  (observations,              (sections, BLUF,              (4-6 min audio)
   signal_types)               source_articles)
```

### V2: 3-Agent Pipeline (Production-Grade — Recommended)

```
Data Ingestion → BigQuery Articles
       ↓
Research Agent (Sonnet) — corpus search, story arc extraction, Tavily gap detection
       ↓
Research Package (intermediate snapshot → BigQuery)
       ↓
Briefing Agent (Opus) — executive synthesis, narrative weighting, voice integration
       ↓
Briefing Draft (intermediate snapshot → BigQuery)
       ↓
Quality Reviewer (Sonnet) — strategy alignment, gap-checking, confidence scoring
       ↓
Final Briefing JSON + Podcast Generation (ElevenLabs)
```

**V2 adds:**
- Dedicated Research Agent with tool access
- Quality Reviewer with confidence scoring and revision loop
- Intermediate pipeline snapshotting for white-box auditing
- Story arc tracking via past briefings tool
- Priority-mapped themes (tied to strategic priorities YAML)

---

## 3. Agent-by-Agent Breakdown

### Agent 1 / Research Agent: Pre-Brief Generator

**Purpose**: Analyze all recent priority articles and produce structured observations.

**Responsibilities:**
1. Fetch ALL Medium/High/Critical priority digest items from last 14 days
2. Process in batches (40 items per batch to prevent context rot)
3. Produce structured observations with signal types
4. Track article IDs for citation mapping

**How article fetching works:**
```python
class PreBriefGenerator:
    BATCH_SIZE = 40  # Max articles per LLM batch
    
    async def _get_priority_items(self, days=14, start_date=None, end_date=None):
        """Fetch from digest_items table (has AI-assigned priority, category,
        topics, companies, digest_summary) instead of raw articles."""
        # Tiered ordering: Critical > High > Medium, then recency
```

**Batched processing** — prevents context rot:
```python
async def generate_pre_brief(self, days=14, start_date=None, end_date=None):
    items, period_start, period_end = await self._get_priority_items(days)
    
    batches = [items[i:i+BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    batch_results = []
    for i, batch in enumerate(batches):
        result = await self._analyze_batch(batch, i+1, len(batches), ...)
        batch_results.append(result)
    
    merged = self._merge_batch_results(batch_results, len(items))
    # Save to BigQuery pre_briefings table
```

**Pre-Brief output structure:**
```json
{
  "observations": [
    {
      "topic": "Quantum Error Correction Breakthrough",
      "signal_type": "market_shift",
      "companies_mentioned": ["IonQ", "Google"],
      "article_ids": ["uuid-1", "uuid-2"],
      "summary": "..."
    }
  ],
  "article_count": 47,
  "article_ids": ["uuid-1", "uuid-2", ...],
  "period_start": "2026-02-08T00:00:00Z",
  "period_end": "2026-02-22T00:00:00Z"
}
```

**V2 Research Agent additions:**
- **Tool access**: Corpus search, Tavily web search, voice search, past briefings reader
- **Story arc extraction**: Uses `PastBriefingsTool` to identify continuing themes
- **Search budget**: ~10–16 Tavily searches per run

**Model**: Sonnet (fast, cheap) — this is raw analysis, not creative synthesis.

---

### Agent 2 / Briefing Agent: Executive Synthesizer

**Purpose**: Transform the pre-brief into a polished executive briefing.

**Inputs:**
1. Pre-brief data from Agent 1
2. Historical context (last 2–4 weekly briefings from BigQuery)
3. Voice enrichment (SEC nuggets, earnings quotes, podcast quotes)
4. Peripheral intelligence (Exa search results)
5. Full article texts for citation linking

**Historical context retrieval:**
```python
async def _get_historical_context(self, limit=2):
    """Get BLUF, headlines, companies, and overall trend
    from prior briefings for differential analysis."""
    # Enables accurate net_new vs continuing classification
```

**Voice enrichment pipeline:**
```python
async def _fetch_voice_enrichment(self, pre_brief_data):
    """Search BigQuery for authoritative voice data to ground analysis."""
    # Sources:
    #   1. sec_filing_nuggets — legally mandated disclosures, risk factors
    #   2. earnings_quotes — executive quotes from Q&A sessions
    #   3. podcast_quotes — practitioner insights, technology adoption
    
    # Extract topics and companies from pre-brief
    # Query each table with targeted keyword search (top 10 each)
    # Format into <enrichment_context> block for synthesis prompt
    # Each fetch wrapped in try/except (single failure doesn't break pipeline)
```

**Voice attribution guidelines:**
- Only include quotes that genuinely reinforce a strategic theme
- Do NOT force-fit quotes — if nothing is relevant, proceed without
- Attribute clearly: "As [Speaker], [Role] at [Company] noted in [Source]..."

**Exa peripheral search:**
```python
# Agent 2 can search for adjacent intelligence
search_peripheral_intelligence()
# - Validates high-conviction claims
# - Fills gaps in coverage
# - Up to 5 iterations (search loop with scratchpad notes)
```

**Output structure — V1:**
```json
{
  "id": "uuid",
  "briefing_type": "weekly_executive",
  "briefing_title": "Executive Briefing: Week of Feb 17",
  "bluf": "Single sentence high-level summary",
  "sections": [
    {
      "header": "Strategic Theme Header",
      "headline": {
        "text": "Critical development [[IonQ]] [1]",
        "status": "net_new",
        "companies_mentioned": ["IonQ"]
      },
      "insights": [...],
      "source_articles": [
        {
          "article_number": 1,
          "id": "article-uuid",
          "title": "Article Title",
          "url": "https://...",
          "source_name": "Nature",
          "published_at": "2026-02-15T..."
        }
      ],
      "companies_with_logos": [
        {"name": "IonQ", "domain": "ionq.com", "logo_url": "..."}
      ]
    }
  ],
  "key_topics_this_week": ["Topic 1", "Topic 2"],
  "overall_trend": "Detailed trend analysis",
  "podcast_url": "https://storage.googleapis.com/.../podcast.mp3",
  "podcast_duration_seconds": 245
}
```

**Output structure — V2:** Split into `strategic_priority_themes` (mapped to client priority IDs) and `additional_market_insights` (AI-discovered findings).

**Model**: Opus (most capable) — quality of strategic synthesis is paramount.

---

### Quality Reviewer (V2 Only)

**Purpose**: Strategy alignment verification and paranoid gap-checking.

**Checks:**
1. BLUF accuracy — does the summary match the data?
2. Contradiction check — conflicting claims between sections?
3. Staleness check — is the data within the requested lookback?
4. Priority alignment — are strategic priorities adequately covered?

**Output:**
```json
{
  "confidence_score": 87,
  "flags": [
    {"severity": "WARNING", "message": "No coverage found for priority P3"}
  ],
  "approved": true
}
```

**Revision loop**: Max 2 revision attempts if QA identifies critical gaps.

---

## 4. Citation System

### Citation Flow
1. Agent 1 numbers articles `[1]` through `[N]`
2. Agent 2 references these: `[1]`, `[2]`, etc.
3. Exa peripheral results get separate namespace: `[Exa:1]`, `[Exa:2]`
4. Post-processing normalizes all to sequential `[1]`, `[2]`, etc.

### Citation cleanup logic:
```python
def _clean_citation_text(self, text, max_pre_brief_articles, exa_id_to_unified):
    """Normalize citations in final output:
    - [37] → renumbered to sequential [1], [2], etc.
    - [Exa:6] → same renumbering (Exa prefix stripped)
    - [37, Exa:6] → split and renumbered (handles mixed citations)
    """
```

### Frontend UX:
- **Hover** on citation number → shows publication domain (e.g., `nature.com`)
- **Click** → opens source URL in new tab
- **Sources footer** → grouped by domain with citation numbers

---

## 5. Story Arc Tracking

### What It Is
Story arc tracking identifies whether a topic is **new** or **continuing** from prior weeks, and how it's evolving.

### Status Labels
| Status | Meaning |
|---|---|
| `net_new` / `New` | First appearance of this theme |
| `Emerging` | Building momentum |
| `Heating Up` | Intensifying focus |
| `Cooling` | Declining attention |
| `Resolved` | Story concluded |
| `continuing` / `Developing` | Legacy: topic from prior weeks with updates |

### How It Works
1. **Past Briefings Tool** reads last 4 weeks of briefings from BigQuery
2. Identifies potential arcs by tracking:
   - Specific companies mentioned across 3+ distinct weeks
   - Topic/theme overlap within consecutive sections
   - Status transitions
3. Research Agent receives "Potential Arcs" as context
4. LLM verifies arcs by searching for specific updates

### Narrative Continuity via Overlap
- **Lookback window**: 14 days (2 weeks)
- **Generation frequency**: Every 7 days (weekly)
- **Overlap**: Each briefing shares 50% of context with predecessor
- **Effect**: Natural noise filter — transient stories don't persist, genuine shifts are reinforced

---

## 6. Podcast Generation Pipeline

### 3-Step Process

**Step 1: Scaffold** (`_build_podcast_dialogue`)
- Deterministic extraction of briefing content into host/analyst turns
- Voice-enriched insights (SEC, earnings, podcast attribution markers) get special analyst delivery and host reactions

**Step 2: Naturalize** (`_naturalize_dialogue`)
- Claude Sonnet rewrites scaffold into natural conversation
- Adds reactions, interjections, varied energy
- Preserves executive/expert quotes verbatim ("the CFO actually said, and I quote...")
- Falls back to original scaffold on failure

**Step 3: TTS** (`_generate_podcast`)
- ElevenLabs Text-to-Dialogue API generates multi-voice audio
- Two voices: **Host** (Rachel) + **Analyst** (Josh)
- ~4–6 minutes for typical 3-section briefing

### Text Formatting for Speech
```python
def _format_text_for_speech(text):
    # Remove citations: [1], [Exa:2] → removed
    # Remove company tags: [[IonQ]] → "IonQ"
    # Expand currency: $2.4B → "2.4 billion dollars"
    # Expand percentages: 40% → "40 percent"
```

### Storage & Access
- GCS bucket with public access prevention
- Stream through backend API: `/api/podcast/briefing/{briefing_id}`
- Supports HTTP Range requests (206 Partial Content) for seeking

### Configuration
```python
elevenlabs_api_key = "..."             # In Secret Manager
elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel (host)
elevenlabs_model = "eleven_monolingual_v1"
elevenlabs_voice_stability = 0.5
elevenlabs_voice_similarity_boost = 0.75
```

---

## 7. Inline Company Logos

`[[Company Name]]` tags in briefing text are rendered with logos from Logo.dev:
- Applies to: section headlines, insight text, BLUF, and `overall_trend`
- Backend enriches `companies_with_logos` per section:
  ```json
  {"name": "IonQ", "domain": "ionq.com", "logo_url": "https://logo.dev/..."}
  ```
- `{{Entity Name}}` double-curly braces for non-company entities → renders as **bold text** (no logo)

---

## 8. Strategic Priorities System (V2)

Define client focus areas in a YAML configuration file:

```yaml
# inputs/strategic_priorities.yaml
priorities:
  - id: P1
    name: "Quantum Error Correction Progress"
    description: "Track advances in QEC across hardware platforms"
  - id: P2
    name: "AI Hardware Race"
    description: "Monitor custom AI chip development and GPU competition"
  - id: P3
    name: "Quantum Cloud Access"
    description: "Cloud-based quantum computing platforms and adoption"
```

The Research Agent scans for each priority. The Briefing Agent maps sections to priority IDs. The Quality Reviewer flags uncovered priorities.

---

## 9. Scheduling & Automation

| Component | Details |
|---|---|
| **Schedule** | Monday 8:30 AM CST via Cloud Scheduler |
| **Job** | `weekly-executive-briefing` |
| **Trigger** | POST to `/api/v1/scheduler/briefing` |
| **Cadence** | Weekly — do NOT generate out-of-band (fragements story arcs) |

### Manual Trigger
```bash
curl -X POST https://<CLOUD_RUN_URL>/api/v1/scheduler/briefing
```

### Historical Backfill
Essential for bootstrapping the story arc context chain:
```bash
cd backend
python scripts/operations/backfill_briefings.py           # All weeks
python scripts/operations/backfill_briefings.py --week 1   # Single week
python scripts/operations/backfill_briefings.py --verify    # Check results
python scripts/operations/backfill_briefings.py --with-podcast  # Include audio
```

**Backfill order must be chronological** (oldest first) — each briefing's Past Briefings Tool needs prior entries to establish arcs.

---

## 10. Data Storage

### BigQuery Tables

| Table | Purpose |
|---|---|
| `articles` | Raw ingested articles (source of truth) |
| `digest_items` | Classified articles with AI-assigned priority, category, summary |
| `pre_briefings` | Agent 1 intermediate output |
| `weekly_briefings` | Final briefing JSON |
| `briefing_v2_research_packages` | (V2) Research Agent intermediate snapshot |
| `briefing_v2_drafts` | (V2) Pre-QA briefing draft snapshot |
| `sec_filing_nuggets` | Pre-extracted SEC filing insights |
| `earnings_quotes` | Pre-extracted, speaker-attributed earnings quotes |
| `podcast_quotes` | Pre-extracted industry podcast quotes |

### GCS Storage
- Podcast audio: `<PROJECT_ID>-hub-data/podcasts/{briefing_id}.mp3`

---

## 11. Intermediate Pipeline Snapshotting (V2)

For white-box auditing of the 3-agent pipeline:

| Stage | Data Object | Persistence Target | Purpose |
|---|---|---|---|
| Research | `ResearchPackage` | `briefing_v2_research_packages` | Inspect evidence before synthesis |
| Synthesis | `BriefingDraft` | `briefing_v2_drafts` | Compare pre-QA draft with final |

**Linkage**: Records saved immediately after agent completion, then linked via `briefing_id` after final save.

---

## 12. Conversational Follow-Up (V2)

After a briefing is generated, an **inline AI assistant** allows follow-up questions:

**Tools available to the assistant:**

| Tool | Capability | Source |
|---|---|---|
| `get_current_briefing` | Full briefing content retrieval | Internal JSON |
| `corpus_search` | Supporting evidence discovery | BigQuery / Vector search |
| `podcast_insights` | Expert practitioner perspectives | BigQuery (Podcasts) |

- Streams via SSE for near-instant feedback
- Displays inline tool-usage badges ("Consulting Industry Experts")
- Maintains briefing context for the entire session

---

## 13. Week Date & Title Logic

```python
def _get_this_weeks_monday(self):
    """Get the Monday of the current week (most recent Monday).
    Ensures briefings always reference the same week regardless of run day.
    Convention: 'Week of [Monday date]'"""
```

**Forced title override**: The LLM sometimes generates wrong dates. The title is force-overridden after LLM response:
```python
# Title is always: "Weekly Briefing: Week of {target_monday_formatted}"
# LLM-generated title is ignored
```

---

## 14. Resilience Patterns

- **LLM resilience**: Anthropic primary with Gemini fallback (auto-failover)
- **Voice enrichment resilience**: Each enrichment fetch wrapped in try/except — single source failure doesn't break pipeline
- **Podcast resilience**: Pipeline continues to "Complete" even if audio generation fails — text briefings always available
- **Truncated JSON repair**: `_repair_truncated_json()` recovers from max_tokens cutoffs
- **Grounding hygiene**: Test data in source tables will bleed into briefings — always sanitize before generation

---

## 15. Model Selection Guide

| Agent | Recommended Model | Rationale |
|---|---|---|
| Pre-Brief / Research | Sonnet (mid-tier) | Fast, cheap — raw analysis |
| Executive Synthesizer | Opus (most capable) | Strategic nuance, "Big Picture" coherence |
| Quality Reviewer | Sonnet (mid-tier) | Structured checking |
| Podcast Naturalization | Sonnet (mid-tier) | Creative but bounded |

**Estimated cost per briefing**: ~$2.16 USD (Research $0.22, Synthesis $1.80, QA $0.14)

---

## 16. Observability

### Log Prefixes
| Prefix | Component |
|---|---|
| `[BQ_SAVE]` | BigQuery save operations |
| `[SAVE]` | Briefing save path |
| `Agent 2:` | Executive synthesizer LLM calls |
| `[RESEARCH-AGENT]` | V2 Research Agent scans |
| `[BRIEFING-AGENT]` | V2 Briefing Agent synthesis |
| `[BRIEFING_V2]` | V2 stage transitions |

### Monitoring Table (V2)
`monitoring_briefing_v2_runs` tracks:
- Status & duration
- Per-agent success bits
- Search activity (Tavily, voice, corpus)
- Output stats (themes, word count, QA approval)
- LLM token usage and estimated cost

---

## 17. Quantum/AI Domain Adaptation Checklist

- [ ] **Strategic priorities**: Define 3–5 QC/AI focus areas in YAML
- [ ] **Data sources**: Configure ingestion for QC/AI news, arXiv, industry blogs
- [ ] **Voice enrichment**: Ingest QC/AI earnings calls, podcasts, SEC filings
- [ ] **Company mappings**: IonQ, Rigetti, IBM, Google, NVIDIA, D-Wave, Quantinuum, etc.
- [ ] **Prompt tuning**: Update Agent 1 and Agent 2 prompts for QC/AI domain language
- [ ] **Podcast voices**: Choose ElevenLabs voices for your brand
- [ ] **Scheduling**: Set up Cloud Scheduler for Monday morning runs
- [ ] **Backfill**: Generate 3 historical briefings to bootstrap story arc context
- [ ] **Logo sources**: Ensure QC/AI company domains resolve in Logo.dev

---

## 18. File Organization Summary

```
backend/
├── app/
│   ├── ingestion/generators/
│   │   ├── pre_briefing.py        # Agent 1: Article analysis
│   │   ├── weekly_briefing.py     # Agent 2: Executive synthesis + podcast
│   │   ├── bulletin_board.py      # Priority spotlight bullets
│   │   └── digest.py              # Digest item generation
│   ├── config/
│   │   └── settings.py            # Model configs, ElevenLabs, timeouts
│   ├── db/
│   │   └── gcp_storage.py         # BigQuery persistence
│   └── api/routes/
│       ├── briefing.py            # Briefing API endpoints
│       └── podcast.py             # Podcast streaming endpoint
├── inputs/
│   └── strategic_priorities.yaml  # Client focus areas (V2)
└── scripts/
    └── operations/
        └── backfill_briefings.py  # Historical backfill CLI
```

---

## 19. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/scheduler/briefing` | POST | Trigger full pipeline |
| `/api/briefing/v2/generate` | POST | Trigger async V2 generation |
| `/api/briefing/v2/status/{job_id}` | GET | Poll progress (0–100%) |
| `/api/briefing/v2/result/{job_id}` | GET | Get final JSON |
| `/api/briefing/v2/latest` | GET | Get most recent briefing |
| `/api/podcast/briefing/{briefing_id}` | GET | Stream podcast audio |
| `/api/briefing/chat/stream` | POST | Conversational follow-up |

---

## 20. Quick Start Implementation Order

1. **Set up data ingestion** — articles into BigQuery with priority classification
2. **Build Agent 1 / Research Agent** — batch processing of priority articles
3. **Build Agent 2 / Briefing Agent** — synthesis with historical context
4. **Add citation system** — article linking and cleanup
5. **Add voice enrichment** — SEC, earnings, podcast quote integration
6. **Add quality reviewer** (V2) — confidence scoring and revision loop
7. **Add podcast generation** — ElevenLabs TTS pipeline
8. **Set up scheduling** — Cloud Scheduler for Monday runs
9. **Backfill 3 weeks** — Bootstrap story arc context chain
10. **Build frontend** — BLUF, sections, citations, podcast player, conversational assistant
