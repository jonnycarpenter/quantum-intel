# Deep Research Workflow — Recreation Spec

> **Purpose**: Step-by-step blueprint for recreating the Deep Research multi-agent engine in a new Quantum Computing & AI Intelligence Hub. Derived from the production C1 Intelligence Hub codebase.

---

## 1. What It Does

Deep Research is an **on-demand, multi-agent research pipeline** that takes a user's natural-language question (e.g., "What's the outlook for quantum error correction?") and produces an **executive-ready research report** with citations, metrics, visuals, and quotes — all in ~60–90 seconds.

**End-user experience:**
1. User types a question in the UI
2. Real-time progress streams to the frontend (SSE) — tool calls, thinking, agent transitions
3. A rich, block-based report appears: paragraphs, metric grids, quote callouts, inline charts
4. Reports are cached and saved for future reference

---

## 2. Architecture Overview

The system is a **6-node directed acyclic graph (DAG)** built on **LangGraph** with parallel fan-out:

```
                          ┌─────────────────┐
                     ┌───►│   Financial     │───┐
                     │    │   Research      │   │
┌─────────────┐     │    └─────────────────┘   │    ┌─────────────┐
│   Groomer   │─────┼───►┌─────────────────┐   ├───►│ Synthesizer │
│   (Query)   │     │    │   Industry      │   │    │  (Report)   │
└─────────────┘     │    │   Research      │   │    └──────┬──────┘
                    │    └─────────────────┘   │           │
                    │    ┌─────────────────┐   │           ▼
                    └───►│    Visual       │───┘    ┌─────────────┐
                         │   Research      │        │  Validator  │
                         └─────────────────┘        │  (QA Gate)  │
                                                    └──────┬──────┘
                                                           │
                                                           ▼
                                                    [Final Report]
```

**Key principle**: Financial, Industry, and Visual agents run **in parallel** using LangGraph's `Send` API, then fan-in to the Synthesizer. This cuts research time by ~60%.

---

## 3. Node-by-Node Breakdown

### Node 1: Groomer (`groomer.py`)

**Purpose**: Query interpretation and sub-query generation.

**What it does:**
- Parses the user's natural-language question
- Generates targeted sub-queries for Financial and Industry agents
- Identifies entities to track (companies, products, technologies)
- Sets research timeframe and scope
- Injects context from prior related research (from BigQuery)

**Model**: Light/cheap model (Claude Haiku or equivalent) — speed matters here.

**Key output** — `ResearchBrief` schema:
```python
class ResearchBrief(BaseModel):
    status: QueryStatus                         # READY or NEEDS_CLARIFICATION
    clarifying_question: Optional[ClarifyingQuestion]
    original_query: Optional[str]
    clarified_intent: Optional[str]
    timeframe: Optional[str]
    financial_agent_queries: Optional[List[str]] # Sub-queries for Financial agent
    industry_agent_queries: Optional[List[str]]  # Sub-queries for Industry agent
    entities_to_track: Optional[List[str]]       # Companies/products to focus on
    domain_context: Optional[str]
    priority_sources: Optional[Dict[str, List[str]]]
    exclusions: Optional[List[str]]
```

**Clarification flow**: If the query is ambiguous, groomer can request clarification (max 2 rounds, then forces research).

**Context injection**: Before the LLM call, groomer fetches related prior research from BigQuery and injects it into the system prompt. This prevents redundant research.

**Implementation detail**: Empty messages must be filtered before calling the LLM API (prevents Anthropic "empty message content" errors).

---

### Node 2: Financial Research (`financial.py`)

**Purpose**: Financial data, corporate intelligence, and executive quotes.

**Conditional tool gating** — only fetches expensive data when relevant:

| Query Type                    | Corpus Query | Earnings Quotes | SEC Nuggets | Company News |
|-------------------------------|:---:|:---:|:---:|:---:|
| Generic ("quantum trends")    | ✅ | ❌ | ❌ | ❌ |
| Company-specific ("deep dive on IonQ") | ✅ | ✅ | ✅ | ✅ |
| Exploratory ("who's leading in QC?") | ✅ | ✅ (if tickers found) | ✅ (if tickers found) | ✅ |

**Tools to build:**
1. `query_corpus` — Semantic search over your pre-ingested article vector store (**always runs**)
2. `search_earnings_quotes` — Pre-extracted, speaker-attributed earnings quotes from BigQuery (**conditional**)
3. `search_sec_nuggets` — Pre-extracted SEC filing insights with signal strength (**conditional**)
4. `get_company_news` — Recent company news by ticker
5. `get_analyst_ratings` — Upgrades, downgrades, price targets
6. `get_sentiment_summary` — Aggregated news sentiment

**Output schema** — `FinancialAgentOutput`:
```python
class FinancialAgentOutput(BaseModel):
    status: str
    queries_executed: List[str]
    sources_searched: int
    sources_with_results: int
    execution_time_seconds: float
    findings: List[FinancialFinding]     # Each has citation, confidence, metrics
    key_metrics_summary: Optional[Dict]
    failed_sources: List[Dict]
    data_gaps: List[str]
    warnings: List[str]
```

Each `FinancialFinding` includes:
- `finding` (text), `finding_type`, `confidence` (HIGH/MEDIUM/LOW)
- `citation` with `source_type`, `source_title`, `source_url`, `direct_quote`
- `entities_mentioned`, `metrics`

**Model**: Heavy/capable model (Claude Opus or equivalent) — quality matters here.

---

### Node 3: Industry Research (`industry.py`)

**Purpose**: Market intelligence, competitive landscape, demand signals.

**Tools to build:**
1. `query_corpus` — Semantic search over pre-ingested articles (**always runs**)
2. `search_podcast_quotes` — Expert insights from industry podcasts (**conditional**)
3. `news_search` / `web_search` — External semantic search (e.g., Exa.ai, Tavily)
4. `get_market_signals` — Aggregated market indicators
5. `get_google_trends` — Demand signal validation

**Output schema** — `IndustryAgentOutput`:
```python
class IndustryAgentOutput(BaseModel):
    status: str
    queries_executed: List[str]
    findings: List[IndustryFinding]
    demand_signals: Optional[Dict]
    competitive_landscape_shifts: List[str]
    data_gaps: List[str]
    warnings: List[str]
```

Each `IndustryFinding` includes `sentiment` (POSITIVE/NEUTRAL/NEGATIVE), `event_type`, `is_historical`, `importance`.

---

### Node 4: Visual Research (`visual.py`)

**Purpose**: Surface relevant charts, graphs, and visual data from a pre-classified image corpus.

**Why a separate agent?**
1. **Zero added latency** — runs in parallel, usually finishes first (~15s vs ~30s for research agents)
2. **Separation of concerns** — Financial thinks earnings, Industry thinks news, Visual thinks charts
3. **Future expansion** — can add chart generation from trend data

**How it works:**
1. Analyzes the research brief to identify visual needs
2. Queries `article_images` BigQuery table (classified images from ingestion)
3. Uses LLM reasoning to rank and select 3–8 most impactful visuals
4. Generates contextual captions tied to research findings
5. Falls back to heuristic selection if LLM ranking fails

**Output schema** — `VisualAgentOutput`:
```python
class VisualAgentOutput(BaseModel):
    status: str = "success"
    visuals_found: int = 0
    searches_executed: List[str] = []
    supporting_visuals: List[SupportingVisual] = []  # image_url, caption, placement
    data_gaps: List[str] = []
    warnings: List[str] = []
```

---

### Node 5: Synthesizer (`synthesizer.py`)

**Purpose**: Merge all findings into a dynamic, block-based executive report.

This is the **most complex node** and the heart of the system.

**Block-based output system (V3)**:
Instead of flat text, the synthesizer constructs reports using a library of UI blocks:

| Block Type | Description |
|---|---|
| `paragraph` | Standard analysis text with inline citation pills |
| `metric_grid` | Horizontal row of key metrics (e.g., Revenue $1.2B \| YoY +12%) |
| `visual_split` | Side-by-side layout: analysis text + chart from Visual agent |
| `quote` | Styled verbatim callout with speaker attribution and source_type |
| `table` | Structured data comparison |

**Quote surfacing pipeline**:
1. `_condense_findings()` preserves `direct_quote`, `source_type`, `sentiment`, `metrics` from agent outputs
2. `_extract_quotable_findings()` categorizes into `executive_quotes`, `sec_nuggets`, `podcast_quotes`
3. `_build_quotes_section()` presents them explicitly so the LLM creates `quote` blocks

**Source-type styling** (frontend):
- **Earnings**: amber accent + `TrendingUp` icon
- **Podcast**: purple accent + `Mic` icon
- **SEC Filing**: blue accent + `FileText` icon

**Design principles**:
- 12-word max headlines — lead with the insight
- 2–3 sections max — ruthlessly prioritize
- Visual agency — the LLM chooses *where* to place visuals
- Graceful degradation — text-only fallback if no visuals available

**Model**: Heavy model with **Extended Thinking** enabled (~16K thinking budget tokens).

**Output schema** — `SynthesisAgentOutput`:
```python
class SynthesisAgentOutput(BaseModel):
    report_title: str
    executive_summary: ExecutiveSummary   # headline, key_points, key_metrics, citations
    sections: List[ReportSection]         # Each has header + blocks[]
    companies_with_logos: List[CompanyWithLogo]
    thinking_content: Optional[str]       # Claude's reasoning process
    confidence: str
    data_completeness: DataCompletenessLevel
    sources_used: List[Citation]
```

---

### Node 6: Validator (`validator.py`)

**Purpose**: Citation verification and quality gate.

**Checks**:
- Citation completeness (every claim has a source)
- Citation quality (URLs, dates, proper attribution)
- Unsubstantiated claims detection
- Confidence level alignment with data quality

**Output**:
```python
class ValidatorOutput(BaseModel):
    validation_passed: bool
    citation_issues: List[str]
    confidence_adjustments: List[str]
    warnings: List[str]
```

**Model**: Light model (Haiku) — fast and sufficient for this structured check.

---

## 4. Workflow Graph (LangGraph Implementation)

```python
from langgraph.graph import StateGraph, END
from langgraph.types import Send

def create_research_workflow():
    workflow = StateGraph(DeepResearchState)
    
    # Add nodes
    workflow.add_node("groom", query_grooming_node)
    workflow.add_node("financial_research", financial_research_node)
    workflow.add_node("industry_research", industry_research_node)
    workflow.add_node("visual_research", visual_research_node)
    workflow.add_node("synthesize", synthesis_node)
    workflow.add_node("validate", validator_node)
    
    # Entry point
    workflow.set_entry_point("groom")
    
    # Conditional routing: fan-out or end (if clarification needed)
    workflow.add_conditional_edges(
        "groom",
        route_after_groom,    # Returns List[Send] for parallel or END
        { END: END }
    )
    
    # Fan-in: all 3 research nodes → synthesize
    workflow.add_edge("financial_research", "synthesize")
    workflow.add_edge("industry_research", "synthesize")
    workflow.add_edge("visual_research", "synthesize")
    
    # Sequential post-synthesis
    workflow.add_edge("synthesize", "validate")
    workflow.add_edge("validate", END)
    
    return workflow.compile()
```

**Routing function** (`route_after_groom`):
```python
def route_after_groom(state):
    brief = state.get("research_brief")
    if not brief:
        return END  # Grooming failed
    
    if brief.status == QueryStatus.NEEDS_CLARIFICATION:
        if state.get("clarification_count", 0) >= 2:
            pass  # Force research after 2 attempts
        else:
            return END  # Wait for user input
    
    # Fan-out to all 3 agents in parallel
    return [
        Send("financial_research", state),
        Send("industry_research", state),
        Send("visual_research", state),
    ]
```

---

## 5. State Schema with Parallel Reducers

Parallel execution requires **reducer annotations** for safe state merging:

```python
from typing import TypedDict, Annotated

class DeepResearchState(TypedDict):
    # Immutable fields — set early, never overwritten
    user_query: Annotated[str, _keep_first]
    conversation_history: Annotated[List[BaseMessage], _keep_first]
    research_brief: Annotated[Optional[ResearchBrief], _keep_first]
    clarification_count: Annotated[int, _keep_first]
    
    # Mutable outputs — each agent updates its own field
    financial_output: Annotated[Optional[FinancialAgentOutput], _keep_last]
    industry_output: Annotated[Optional[IndustryAgentOutput], _keep_last]
    visual_output: Annotated[Optional[VisualAgentOutput], _keep_last]
    final_report: Annotated[Optional[SynthesisAgentOutput], _keep_last]
    validator_output: Annotated[Optional[ValidatorOutput], _keep_last]
    current_status: Annotated[str, _keep_last]
    
    # Merged from parallel branches
    errors: Annotated[List[Dict[str, Any]], _merge_errors]
```

**Reducer functions:**
```python
def _keep_first(a, b):
    """Keep original value (immutable fields)."""
    return a if (a is not None and a != "") else b

def _keep_last(a, b):
    """Keep latest value (mutable outputs)."""
    return b if b is not None else a

def _merge_errors(a, b):
    """Combine error lists from parallel branches."""
    return (a or []) + (b or [])
```

> **Why Annotated?** LangGraph's `Send` API passes full state to each branch. When branches return, their states must be merged. Without reducers, duplicate keys cause `InvalidUpdateError`.

---

## 6. Real-Time SSE Streaming

### Progress Emission Architecture

Agents emit progress events via an async queue:

```python
class ToolProgress(BaseModel):
    tool_name: str
    message: str
    ticker: Optional[str] = None
    status: str  # "running", "complete", "failed"

# Usage in agent code:
emit_progress_sync(ToolProgress(
    tool_name="sec_filings",
    message="Fetching SEC 10-K for IonQ",
    ticker="IONQ",
    status="running"
))
```

**SSE Event Types:**
- `stage` — Phase transitions (planning → researching → synthesizing)
- `plan` — Research brief with objectives and entities
- `agent_start` / `agent_complete` — Per-agent progress
- `tool_progress` — Individual tool calls within agents
- `thinking` — Claude's extended thinking content (collapsible in UI)
- `complete` — Final report payload
- `timeout` — Timeout with completed/active node details

### Streaming Implementation (Critical Bug Fix)

**Never** use `asyncio.wait_for()` on a shared async iterator without `asyncio.shield()`:

```python
# WRONG — cancels the entire workflow!
event = await asyncio.wait_for(event_iterator.__anext__(), timeout=0.1)

# CORRECT — protects from cancellation
if pending_task is None:
    pending_task = asyncio.create_task(event_iterator.__anext__())
event = await asyncio.wait_for(asyncio.shield(pending_task), timeout=0.5)
```

The API route polls the progress queue every 100ms, streaming events immediately instead of waiting for LangGraph lifecycle events.

---

## 7. Caching & Persistence

### Two-Tier Caching

**Tier 1: In-Memory Cache**
- TTL: 1 hour
- Key: SHA256 of normalized (lowercase, trimmed) query
- Fastest retrieval for recent/repeated queries

**Tier 2: BigQuery Persistence**
- TTL: 24 hours (configurable)
- Table: `deep_research_reports`
- Survives server restarts
- Enables report history and search

### Research Memory Service

```python
memory = await get_research_memory()

# Check cache first
cached = await memory.get_cached_report(query)

# Find related past research for context injection
related = await memory.find_related_research(
    query=query,
    companies=["IonQ", "Rigetti"],
    industries=["quantum_computing"]
)

# Store completed report
await memory.store_report(report_id, query, state)
```

---

## 8. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/research/start` | POST | Start deep research workflow |
| `/api/research/stream/{id}` | GET | Stream research progress (SSE) |
| `/api/research/reports` | GET | List saved reports (paginated) |
| `/api/research/reports/{id}` | GET | Get full report by ID |
| `/api/research/reports/search/related` | GET | Find related past research |
| `/api/research/cache/stats` | GET | View cache statistics |
| `/api/research/cache/clear` | DELETE | Clear in-memory cache |

---

## 9. Timeout & Resilience Configuration

```python
# Timeout settings
deep_research_workflow_timeout = 600   # 10 min overall
deep_research_tool_timeout = 60        # 60s per external tool
deep_research_llm_timeout = 240        # 240s for LLM calls

# Extended Thinking
deep_research_thinking_enabled = True
deep_research_thinking_budget_tokens = 16000
```

**Typical timing**: Groom (~10s) + Parallel research (~60s) + Synthesizer with thinking (~120–240s) + Validator (~15s) = ~200–325s total

**Graceful degradation**: If 1 of 3 analyst agents fails, the Synthesizer proceeds with partial data rather than failing the entire session.

**LLM resilience**: Use a resilient wrapper with automatic Gemini fallback:
```python
llm = create_resilient_llm_with_gemini_fallback(
    primary_model="claude-opus-4-5",
    anthropic_api_key=settings.anthropic_api_key,
    gemini_api_key=settings.gemini_api_key,
)
```

---

## 10. Model Selection Guide

| Node | Recommended Model | Rationale |
|---|---|---|
| Groomer | Haiku (cheapest) | Speed important, simple task |
| Financial Agent | Opus (most capable) | Complex multi-tool reasoning |
| Industry Agent | Opus (most capable) | Complex multi-tool reasoning |
| Visual Agent | Sonnet (mid-tier) | Ranking task, not creative |
| Synthesizer | Opus + Extended Thinking | Report quality is paramount |
| Validator | Haiku (cheapest) | Structured checking, fast |

---

## 11. Quantum/AI Domain Adaptation Checklist

To adapt this for quantum computing and AI intelligence:

- [ ] **Corpus**: Ingest articles from quantum/AI sources (arXiv, QC industry pubs, AI newsletters, etc.)
- [ ] **Entities**: Replace composites industry entities with QC/AI companies (IonQ, Rigetti, IBM Quantum, Google DeepMind, NVIDIA, etc.)
- [ ] **Groomer prompt**: Update domain context to quantum computing and AI
- [ ] **Financial tools**: Wire up SEC/earnings for QC/AI tickers (IONQ, RGTI, IBM, GOOG, NVDA, etc.)
- [ ] **Industry tools**: Configure Exa/Tavily queries for QC/AI topics
- [ ] **Podcast quotes**: Ingest QC/AI podcasts (Quantum Computing Now, AI podcasts, etc.)
- [ ] **Visual agent**: Build image corpus from QC/AI articles (roadmaps, benchmark charts, etc.)
- [ ] **Synthesizer prompt**: Update to reason about qubits, error correction, AI architectures, etc.

---

## 12. File Organization Summary

```
backend/
├── app/
│   ├── agents/research/
│   │   ├── groomer.py          # Node 1: Query interpretation
│   │   ├── financial.py        # Node 2: Financial research
│   │   ├── industry.py         # Node 3: Industry research
│   │   ├── visual.py           # Node 4: Visual research
│   │   ├── synthesizer.py      # Node 5: Report synthesis
│   │   ├── validator.py        # Node 6: Citation QA
│   │   ├── state.py            # Pydantic schemas + TypedDict state + reducers
│   │   ├── progress.py         # SSE progress emission
│   │   └── memory.py           # Research memory (BigQuery persistence)
│   ├── graph/
│   │   └── research_workflow.py # LangGraph DAG definition
│   └── api/routes/
│       └── deep_research.py     # SSE streaming endpoint
```

---

## 13. Observability

- **LangSmith**: Tracing for every workflow run (cost, latency, errors)
- **Cloud Run log prefixes**: `[GROOMER]`, `[FINANCIAL_RESEARCH]`, `[INDUSTRY_RESEARCH]`, `[VISUAL_RESEARCH]`, `[SYNTHESIZER]`, `[ROUTE_AFTER_GROOM]`
- **START/COMPLETE pairs**: Log timing for all async operations
- **Token tracking**: Per-call token counts and estimated cost in BigQuery

---

## 14. Common Pitfalls & Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `InvalidUpdateError: Can receive only one value per step` | State field missing reducer annotation | Add `Annotated[Type, reducer]` to `state.py` |
| Pydantic validation errors | LLM output doesn't match schema | Add explicit JSON schema to extraction prompt |
| `empty message content` error | Empty messages in conversation history | Filter messages before LLM call |
| Research cancelled immediately | SSE cancellation bug | Use `asyncio.shield()` when polling iterator |
| Research hangs/times out | External API slow | Use `sync_tool_with_timeout` decorator |
