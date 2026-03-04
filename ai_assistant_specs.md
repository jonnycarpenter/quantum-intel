# AI Assistant (Side Panel) — Architecture Spec

> **Purpose**: Reference spec for replicating the Intelligence Hub's AI assistant side panel in another project. Covers backend agent system, API layer, frontend hook + UI components, and advanced features.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Tech Stack](#2-tech-stack)
3. [Backend: Agent System](#3-backend-agent-system)
   - [3.1 Data Models (Session, Messages, Scratchpad)](#31-data-models)
   - [3.2 Identity / System Prompt](#32-identity--system-prompt)
   - [3.3 Agent Runner (Orchestration)](#33-agent-runner-orchestration)
   - [3.4 Tool System (Surface-Aware)](#34-tool-system-surface-aware)
   - [3.5 Context Compaction Engine](#35-context-compaction-engine)
   - [3.6 Decision Anchors](#36-decision-anchors)
   - [3.7 Semantic Memory (Cross-Session)](#37-semantic-memory-cross-session)
   - [3.8 Session Store](#38-session-store)
4. [API Layer](#4-api-layer)
   - [4.1 Endpoints](#41-endpoints)
   - [4.2 SSE Streaming Protocol](#42-sse-streaming-protocol)
   - [4.3 Request/Response Schemas](#43-requestresponse-schemas)
5. [Frontend: React Integration](#5-frontend-react-integration)
   - [5.1 React Hook (`useChalk`)](#51-react-hook-usechalk)
   - [5.2 Context Provider (`ChalkProvider`)](#52-context-provider-chalkprovider)
   - [5.3 Panel Component (`ChalkPanel`)](#53-panel-component-chalkpanel)
   - [5.4 Supporting Components](#54-supporting-components)
6. [File Structure](#6-file-structure)
7. [Implementation Checklist](#7-implementation-checklist)

---

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React / Next.js)               │
│                                                                  │
│  ChalkProvider (Context)                                         │
│   ├── useChalk hook (state + API calls + SSE streaming)          │
│   ├── ChalkPanel (slide-in side panel)                           │
│   ├── ContextIndicator (context window usage bar)                │
│   └── ScratchpadPanel (pinned notes that survive compaction)     │
│                                                                  │
│  Trigger: Header button opens side panel                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼───────────────────────────────────────┐
│                         API LAYER (FastAPI)                       │
│                                                                  │
│  POST /api/agent/chat          (sync chat)                       │
│  GET  /api/agent/chat/stream   (SSE streaming)                   │
│  GET  /api/agent/scratchpad/*  (scratchpad CRUD)                 │
│  POST /api/agent/scratchpad/*                                    │
│  GET  /api/agent/session/*     (session info)                    │
│  GET  /api/agent/anchors/*     (decision anchors)                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                     AGENT RUNNER (Orchestration)                  │
│                                                                  │
│  1. Session get/create                                           │
│  2. Context compaction check                                     │
│  3. Semantic memory retrieval                                    │
│  4. Build identity prompt (system prompt + scratchpad + anchors) │
│  5. Get surface-specific tools                                   │
│  6. Build message array                                          │
│  7. LLM call with iterative tool loop (max 10 iterations)       │
│  8. Save session state                                           │
│  9. Return response / yield SSE events                           │
│                                                                  │
│  Dependencies: Anthropic SDK, Session Store, Tool Executor       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **LLM** | Anthropic Claude (Sonnet 4) | Via `anthropic` Python SDK (async) |
| **Backend** | FastAPI (Python) | Async endpoints, SSE via `StreamingResponse` |
| **Frontend** | React 18 + Next.js 15 | App Router, TypeScript |
| **Session Store** | In-memory (Python dict) | Abstracted behind `SessionStore` ABC for Redis swap |
| **Vector Memory** | ChromaDB + sentence-transformers | Cross-session semantic memory (`all-MiniLM-L6-v2`) |
| **Streaming** | Server-Sent Events (SSE) | `text/event-stream` via FastAPI `StreamingResponse` |
| **Markdown Rendering** | `react-markdown` + `remark-gfm` | For assistant responses |

---

## 3. Backend: Agent System

### 3.1 Data Models

**File**: `api/agent/models/session.py`

#### `Message`
```python
class Message(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    surface: str              # Which surface/tab this message came from
    timestamp: datetime
    token_count: Optional[int]
    is_compacted: bool        # True if this is a summary, not original
```

#### `ScratchpadItem`
```python
class ScratchpadItem(BaseModel):
    id: UUID
    content: str
    added_by: Literal["user", "chalk"]  # Who added it
    surface: str
    timestamp: datetime
    pinned: bool              # Pinned items survive aggressive compaction
    source_type: Optional[str]  # e.g., "deep_research_bluf", "user_note"
```

#### `Scratchpad`
```python
class Scratchpad(BaseModel):
    items: list[ScratchpadItem]
    max_items: int = 10       # Hard limit
    max_tokens: int = 1000    # Soft cap on total size
    
    def add(...) -> ScratchpadItem   # Auto-evicts oldest non-pinned if full
    def remove(id) -> bool
```

#### `DecisionAnchor`
```python
class DecisionAnchor(BaseModel):
    id: UUID
    content: str
    decision_type: Literal["correction", "directive", "preference"]
    surface: str
    timestamp: datetime
    original_context: Optional[str]
    confidence: float         # 0.0-1.0, threshold is 0.8+
```

#### `ChalkSession` (main session state)
```python
class ChalkSession(BaseModel):
    id: UUID
    messages: list[Message]
    scratchpad: Scratchpad
    decision_anchors: list[DecisionAnchor]
    current_surface: str
    surfaces_visited: list[str]
    compaction_count: int
    created_at: datetime
    last_activity: datetime
    ttl_hours: int = 4        # Session expiration
```

#### `Surface` enum
```python
class Surface(str, Enum):
    MARKET_INTEL = "market_intel"
    NEED_TO_KNOW = "need_to_know"
    DEEP_RESEARCH = "deep_research"
    NEWS_FEED = "news_feed"
```

**Key design decisions:**
- Messages track which surface/tab they originated from → enables cross-surface context
- Scratchpad has both user-added and agent-added items
- Decision anchors are extracted during compaction and never removed
- Session has a TTL (default 4 hours)

---

### 3.2 Identity / System Prompt

**File**: `api/agent/identity/chalk_identity.py`

The identity system builds a dynamic system prompt for every LLM call:

```python
def build_identity_prompt(session: ChalkSession, client_flavor: str) -> str:
```

**Prompt structure:**
1. **Personality & mission** — Who the agent is, communication style
2. **Domain knowledge** — Category-specific context (optional, per client flavor)
3. **Vendor name blocklist** — Names the agent must NEVER mention (e.g., API providers)
4. **Capabilities list** — What the agent can do on each surface
5. **Session context** (dynamic):
   - Current surface
   - Session start time
   - Surfaces visited so far
6. **Scratchpad contents** (dynamic) — Verbatim pinned items
7. **Decision anchors** (dynamic) — "User-Defined Constraints & Preferences"
8. **Relevant past insights** (dynamic) — From semantic memory, with timestamps

**Client flavors** — Template per client (`"base"`, `"sprite"`), selectable at runner init:
```python
class ClientFlavor(str, Enum):
    BASE = "base"
    SPRITE = "sprite"
```

**Knowledge base** — External markdown file loaded at build time:
- Path: `inputs/GUIDE_KNOWLEDGE.md`
- Contains tab explanations, feature walkthroughs, data source info
- Referenced in the prompt so the agent can answer platform questions

---

### 3.3 Agent Runner (Orchestration)

**File**: `api/agent/runner.py`

The `AgentRunner` class is the main orchestration layer. It provides two methods:

#### Synchronous: `chat(message, surface, session_id) -> AgentResponse`

```
1. Get or create session (via SessionStore)
2. Check & perform compaction if context usage exceeds thresholds
3. Retrieve relevant semantic memories (top 2, min relevance 0.4)
4. Build identity prompt (system prompt + scratchpad + anchors + memories)
5. Get surface-specific tool definitions (Anthropic format)
6. Build messages array (from session history)
7. Call LLM with iterative tool loop:
   - If stop_reason == "tool_use" → execute tools, append results, loop
   - If stop_reason == "end_turn" → extract text, break
   - Max 10 iterations (prevents infinite loops)
8. Save session (add user + assistant messages)
9. Return AgentResponse
```

#### Streaming: `chat_stream(message, surface, session_id) -> AsyncGenerator[StreamEvent]`

Same flow but uses `client.messages.stream()` and yields SSE events:
```
session → thinking → tool_call → tool_result → text_delta (chunks) → complete
```

**Configuration:**
```python
DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_TOOL_ITERATIONS = 10
```

**Singleton pattern:**
```python
_runner: Optional[AgentRunner] = None

def get_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner
```

---

### 3.4 Tool System (Surface-Aware)

**File**: `api/agent/services/tools.py`

Tools are defined in **Anthropic tool-calling format** (JSON schema). The system routes different tools to different surfaces/tabs.

#### Tool routing:
```python
# Each surface gets base tools + specialized tools
SURFACE_TOOL_NAMES = {
    "market_intel": BASE + ["exa_search", "practitioner_quotes", "get_category_signals"],
    "need_to_know": BASE + ["podcast_insights", "get_briefing", "get_momentum_scores"],
    "deep_research": BASE + ["run_deep_research_v2"],
    "news_feed": BASE + ["get_recent_articles", "filter_by_category", "get_article_detail"],
}

BASE_TOOL_NAMES = ["corpus_search", "add_to_scratchpad", "remove_from_scratchpad", "view_scratchpad"]
```

#### Demo mode:
A `DEMO_MODE = True/False` flag restricts all surfaces to only scratchpad tools (no external API calls). Useful for demos where reliability matters.

#### Tool execution:
The `ToolExecutor` class maps tool names to implementations:
```python
class ToolExecutor:
    def __init__(self, session: ChalkSession):
        self.session = session
    
    async def execute(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "add_to_scratchpad":
            return await self._add_to_scratchpad(tool_input)
        elif tool_name == "corpus_search":
            return await self._corpus_search(tool_input)
        # ...etc
```

**Tool definition format (Anthropic):**
```python
{
    "name": "corpus_search",
    "description": "Search the article corpus...",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language search query"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["query"]
    }
}
```

---

### 3.5 Context Compaction Engine

**File**: `api/agent/services/compaction.py`

Manages conversation length by summarizing old messages when context gets full.

#### Thresholds:
| Level | Context Usage | Action |
|-------|:------------:|--------|
| Monitor | 40% | Start tracking |
| Soft | 55% | Compact oldest 33% of messages |
| Warn | 70% | Compact oldest 50% |
| Hard | 85% | Compact oldest 75% |
| Emergency | 95% | Keep only last few turns |

#### How it works:
1. Before each LLM call, `check_and_compact(session, llm_client)` checks usage
2. If threshold exceeded, selects old messages for summarization
3. Uses LLM (same client) to generate a structured summary
4. Replaces original messages with a single `is_compacted=True` summary message
5. **Preserves**: scratchpad items, decision anchors, research reports
6. Extracts decision anchors from compacted messages (via `decision_extraction.py`)
7. Stores compacted summary in semantic memory for cross-session recall
8. Increments `session.compaction_count`

#### Summary prompt structure:
```
MUST PRESERVE: Decisions, key findings with data, corrections, action items
SUMMARIZE: Topics explored, tools used, analysis chains
DISCARD: Routine confirmations, repeated info, dead ends
```

---

### 3.6 Decision Anchors

**File**: `api/agent/services/decision_extraction.py`

Critical user decisions that are **never compacted away**.

#### Types:
- **Correction**: "No, Celsius is Tier 1, not Tier 4"
- **Directive**: "Always prioritize practitioner insights"
- **Preference**: "Focus on functional beverage space"

#### Extraction:
1. **LLM extraction** (primary): Uses Claude Haiku for speed/cost. Analyzes conversation segments during compaction. Confidence threshold: 0.8+.
2. **Rule-based fallback**: Pattern matching for corrections ("No,", "Actually,", "That's wrong"), directives ("Always", "Focus on", "Prioritize"), preferences ("I prefer", "Don't show me").

#### Injection:
Decision anchors are formatted and injected into every system prompt:
```
[CORRECTION] Celsius is Tier 1 competitor
[DIRECTIVE] Always prioritize practitioner insights
[PREFERENCE] Focus on functional beverage space
```

---

### 3.7 Semantic Memory (Cross-Session)

**File**: `api/agent/services/semantic_memory.py`

Enables the agent to recall insights from previous sessions.

#### Storage:
- **Vector DB**: ChromaDB with persistent storage (`data/agent_memory/`)
- **Embedding model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Collection**: `agent_memory_{client_name}` (per-client isolation)
- **Cosine similarity** for retrieval

#### Lifecycle:
1. After compaction, the summary is embedded and stored
2. Before each new query, top 2 relevant memories retrieved (min relevance 0.4)
3. Injected into system prompt as "Relevant Past Insights" with timestamps
4. 30-day retention with auto-cleanup

#### Data model:
```python
@dataclass
class MemoryChunk:
    content: str
    session_id: str
    surface: str
    timestamp: datetime
    relevance_score: float  # 0-1
    has_anchors: bool
```

---

### 3.8 Session Store

**File**: `api/agent/services/session_store.py`

Abstract interface with in-memory implementation:

```python
class SessionStore(ABC):
    async def get(session_id) -> Optional[ChalkSession]
    async def get_or_create(session_id, surface) -> ChalkSession
    async def save(session) -> None
    async def delete(session_id) -> bool
    async def cleanup_expired() -> int
    async def count() -> int

class InMemorySessionStore(SessionStore):
    # Dict-based, thread-safe via asyncio locks
    # Sessions lost on restart
    # Ready to swap to RedisSessionStore for production
```

---

## 4. API Layer

### 4.1 Endpoints

**File**: `api/routers/agent.py` — Prefix: `/api/agent`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Agent health check |
| `POST` | `/chat` | Synchronous chat (full response) |
| `GET` | `/chat/stream` | SSE streaming chat |
| `GET` | `/session/{session_id}` | Session metadata |
| `GET` | `/scratchpad/{session_id}` | Get scratchpad items |
| `POST` | `/scratchpad/add` | Add scratchpad item |
| `DELETE` | `/scratchpad/{session_id}/{item_id}` | Remove scratchpad item |
| `POST` | `/scratchpad/{session_id}/{item_id}/toggle-pin` | Toggle pin status |
| `GET` | `/anchors/{session_id}` | Get decision anchors |

### 4.2 SSE Streaming Protocol

**Endpoint**: `GET /api/agent/chat/stream?message=...&surface=...&session_id=...`

**Event types:**
```
event: session
data: {"session_id": "uuid", "surface": "market_intel", "is_new": true}

event: thinking
data: {"iteration": 1}

event: tool_call
data: {"tool": "corpus_search", "input": {"query": "..."}}

event: tool_result
data: {"tool": "corpus_search", "result_preview": "Found 5 results..."}

event: text_delta
data: {"text": "Based on recent "}  (many of these, one per chunk)

event: compaction
data: {"compaction_count": 1, "context_usage": 0.42}

event: complete
data: {"session_id": "uuid", "message": "...", "tools_called": [...], "context_usage": 0.42, ...}

event: error
data: {"error": "Something failed", "session_id": "uuid"}
```

**Response headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### 4.3 Request/Response Schemas

#### Chat Request (POST /chat)
```json
{
  "message": "What is Olipop doing lately?",
  "surface": "market_intel",
  "session_id": "uuid-or-null"
}
```

#### Chat Response
```json
{
  "message": "Based on recent market intelligence...",
  "session_id": "uuid",
  "surface": "market_intel",
  "tools_called": ["corpus_search", "exa_search"],
  "context_usage": 0.42,
  "compaction_count": 0,
  "scratchpad_count": 2,
  "model_used": "claude-sonnet-4-6",
  "duration_ms": 3200,
  "error": null
}
```

#### Scratchpad Add Request
```json
{
  "content": "Key finding: Starry CVS deal is $2M",
  "surface": "market_intel",
  "session_id": "uuid",
  "pinned": true
}
```

---

## 5. Frontend: React Integration

### 5.1 React Hook (`useChalk`)

**File**: `frontend/src/hooks/useChalk.ts`

Core state management hook. Returns state + actions for the entire agent interaction.

#### State:
```typescript
interface ChalkState {
  sessionId: string | null
  messages: ChalkMessage[]
  isLoading: boolean
  contextUsage: number       // 0-1 decimal
  compactionCount: number
  scratchpad: ScratchpadItem[]
  currentSurface: Surface
  error: string | null
}
```

#### Types:
```typescript
type Surface = 'market_intel' | 'need_to_know' | 'deep_research' | 'news_feed'

interface ChalkMessage {
  role: 'user' | 'assistant'
  content: string
  surface: Surface
  timestamp: string
  toolsCalled?: string[]
}

interface ScratchpadItem {
  id: string
  content: string
  added_by: 'user' | 'chalk'
  surface: string
  timestamp: string
  pinned: boolean
  source_type?: string
}
```

#### Actions:
```typescript
interface UseChalkReturn extends ChalkState {
  sendMessage: (message: string) => Promise<void>           // Sync chat
  sendMessageStreaming: (message: string) => Promise<void>   // SSE streaming
  switchSurface: (surface: Surface) => void
  addToScratchpad: (content: string, pinned?: boolean) => Promise<void>
  removeFromScratchpad: (itemId: string) => Promise<void>
  clearSession: () => void
  refreshScratchpad: () => Promise<void>
  isStreaming: boolean
  hasSession: boolean
}
```

#### Sync chat flow:
1. Add user message to state immediately (optimistic)
2. `POST /api/agent/chat` with `{message, surface, session_id}`
3. On response: add assistant message, update `contextUsage`, `compactionCount`
4. Refresh scratchpad (may have been updated by agent)

#### SSE streaming flow:
1. Add user message + empty assistant message to state
2. `fetch('/api/agent/chat/stream?...')` — read body as stream
3. Parse SSE events from chunked response
4. Handle event types:
   - `session` → store session_id
   - `text` / `text_delta` → append text to last assistant message
   - `tool_start` → add to `toolsCalled` on last message
   - `context_update` → update `contextUsage`
   - `complete` → finalize
   - `error` → set error state
5. On complete: refresh scratchpad

**Key implementation detail**: The SSE consumer uses `fetch()` + `ReadableStream`, NOT `EventSource`. This allows aborting via `AbortController` and better error handling.

---

### 5.2 Context Provider (`ChalkProvider`)

**File**: `frontend/src/components/agent/ChalkContext.tsx`

Wraps the app so any component can access the agent:

```typescript
function ChalkProvider({ children, currentMode }: ChalkProviderProps) {
  const [isOpen, setIsOpen] = useState(false)
  const chalk = useChalk(initialSurface)

  // Auto-sync surface when user switches tabs
  useEffect(() => {
    const newSurface = modeToSurface(currentMode)
    if (newSurface !== chalk.currentSurface) {
      chalk.switchSurface(newSurface)
    }
  }, [currentMode])

  // Helper to open panel and optionally pre-fill a message
  const openWithMessage = useCallback((message?: string) => {
    setIsOpen(true)
    if (message) setTimeout(() => chalk.sendMessage(message), 100)
  }, [chalk])

  return (
    <ChalkContext.Provider value={{ ...chalk, isOpen, setIsOpen, openWithMessage }}>
      {children}
    </ChalkContext.Provider>
  )
}
```

**Mode-to-surface mapping:**
```typescript
function modeToSurface(mode: Mode): Surface {
  switch (mode) {
    case 'briefing':       return 'market_intel'
    case 'deep-research':  return 'deep_research'
    case 'feed':           return 'news_feed'
    default:               return 'market_intel'
  }
}
```

**Consuming from any component:**
```typescript
const chalk = useChalkContext()       // Required (throws if no provider)
const chalk = useChalkContextOptional() // Optional (returns null)
```

---

### 5.3 Panel Component (`ChalkPanel`)

**File**: `frontend/src/components/agent/ChalkPanel.tsx`

A **fixed right-side slide-in panel** (420px wide) with:

#### Layout structure:
```
┌────────────────────────────────────┐
│ HEADER                             │
│ [Icon] Intelligence Hub Guide      │
│ [ContextIndicator] [Reset] [Close] │
├────────────────────────────────────┤
│ MESSAGES AREA (scrollable)         │
│                                    │
│ Empty state: suggestions grid      │
│ - "What does this platform do?"    │
│ - "How is this different from..."  │
│ - "What would I use this for?"     │
│                                    │
│ [User bubble]  [Assistant bubble]  │
│ [Loading spinner]  [Error banner]  │
│                                    │
├────────────────────────────────────┤
│ SCRATCHPAD (collapsible, if items) │
│ 📌 Key finding: ...               │
│ 📌 Research BLUF: ...             │
├────────────────────────────────────┤
│ INPUT AREA                         │
│ [textarea] [Send button]           │
│ Enter to send, Shift+Enter newline │
└────────────────────────────────────┘
```

#### Key features:
- **Backdrop overlay** — Semi-transparent black, click to close
- **Quick suggestions** — Per-surface suggested questions when empty
- **Auto-scroll** — Scrolls to bottom on new messages
- **Auto-focus** — Input field focuses when panel opens
- **Markdown rendering** — Assistant responses rendered with `react-markdown` + `remark-gfm`
- **Tool usage indicator** — Shows which tools were called per message
- **Keyboard shortcuts** — Enter to send, Shift+Enter for newline

#### Message bubble component:
- User messages: Right-aligned, gray background
- Assistant messages: Left-aligned, accent color background, rendered as markdown
- Avatar icons: User icon vs Bot icon (lucide-react)
- Tools called shown below assistant messages as small text

---

### 5.4 Supporting Components

#### `ContextIndicator`
**File**: `frontend/src/components/agent/ContextIndicator.tsx`

Visual progress bar showing context window usage:

| Range | Color | Label |
|-------|-------|-------|
| < 50% | Green | Fresh |
| 50-70% | Yellow | Active |
| 70-85% | Orange | Dense |
| > 85% | Red | Near limit |

Shows compaction count with a ⚡ icon. Has compact and full display modes.

#### `ScratchpadPanel`
**File**: `frontend/src/components/agent/ScratchpadPanel.tsx`

Collapsible panel within the chat panel:
- Shows pinned items with 📌 icon
- Items labeled as `[USER]` or `[CHALK]`
- "Add note" button → inline text input
- Delete button per item
- Max 10 items with counter display

---

## 6. File Structure

### Backend
```
api/
├── agent/
│   ├── __init__.py
│   ├── runner.py                      # AgentRunner class (chat + chat_stream)
│   ├── identity/
│   │   ├── __init__.py
│   │   └── chalk_identity.py          # System prompt templates + builder
│   ├── models/
│   │   ├── __init__.py
│   │   └── session.py                 # Session, Message, Scratchpad, DecisionAnchor
│   ├── services/
│   │   ├── __init__.py                # Re-exports all services
│   │   ├── session_store.py           # SessionStore ABC + InMemorySessionStore
│   │   ├── compaction.py              # Compaction engine (thresholds, summarization)
│   │   ├── tools.py                   # Tool definitions + surface routing
│   │   ├── decision_extraction.py     # LLM + rule-based anchor extraction
│   │   └── semantic_memory.py         # ChromaDB cross-session vector memory
│   └── tests/                         # 213+ passing tests
├── routers/
│   └── agent.py                       # FastAPI router (all /api/agent/* endpoints)
└── main.py                            # App entry, includes agent router
```

### Frontend
```
frontend/src/
├── hooks/
│   └── useChalk.ts                    # Core hook (state, sync chat, SSE, scratchpad)
├── components/
│   └── agent/
│       ├── index.ts                   # Barrel exports
│       ├── ChalkContext.tsx            # React Context provider
│       ├── ChalkPanel.tsx             # Side panel UI
│       ├── ContextIndicator.tsx       # Context usage bar
│       └── ScratchpadPanel.tsx        # Pinned notes panel
```

---

## 7. Implementation Checklist

### Phase 1: Core Data Models
- [ ] `Session` model (id, messages, surfaces, timestamps, TTL)
- [ ] `Message` model (role, content, surface, token estimation)
- [ ] `Scratchpad` model (items, add/remove/evict, max limits)
- [ ] `Surface` enum (your app's tabs/views)

### Phase 2: Session Store
- [ ] `SessionStore` abstract interface
- [ ] `InMemorySessionStore` implementation
- [ ] Session expiration / cleanup

### Phase 3: Identity System
- [ ] System prompt template with personality
- [ ] Dynamic context injection (surface, scratchpad, timestamps)
- [ ] Client flavor support (optional)
- [ ] Knowledge base loading from external file

### Phase 4: Tool System
- [ ] Define tools in Anthropic JSON schema format
- [ ] Surface-to-tool mapping
- [ ] `ToolExecutor` class mapping names to implementations
- [ ] Scratchpad tools (add/remove/view) — built-in, no external deps
- [ ] Demo mode toggle (tools on/off)

### Phase 5: Agent Runner
- [ ] `AgentRunner` class with Anthropic async client
- [ ] `chat()` sync method (tool loop, max iterations)
- [ ] `chat_stream()` SSE generator method
- [ ] Singleton `get_runner()` pattern

### Phase 6: API Endpoints
- [ ] `POST /chat` — sync chat
- [ ] `GET /chat/stream` — SSE streaming
- [ ] `GET /session/{id}` — session info
- [ ] Scratchpad CRUD endpoints
- [ ] SSE response headers (no-cache, keep-alive, no buffering)

### Phase 7: Frontend Hook
- [ ] `useAssistant` hook with state management
- [ ] Sync `sendMessage` method (fetch POST)
- [ ] Streaming `sendMessageStreaming` method (fetch + ReadableStream SSE parser)
- [ ] Surface switching
- [ ] Scratchpad operations
- [ ] Session clear
- [ ] AbortController for stream cancellation

### Phase 8: Frontend Context
- [ ] `AssistantProvider` wrapping the app
- [ ] Mode-to-surface mapping for your tabs
- [ ] `openWithMessage()` helper
- [ ] Auto-sync surface on tab change

### Phase 9: Frontend UI
- [ ] Slide-in side panel (fixed right, 420px)
- [ ] Header with title, context indicator, reset, close
- [ ] Message list with auto-scroll
- [ ] Empty state with per-surface suggestions
- [ ] User/assistant message bubbles with avatars
- [ ] Markdown rendering for assistant messages
- [ ] Loading state (spinner)
- [ ] Error state (banner)
- [ ] Scratchpad panel (collapsible)
- [ ] Text input with Enter-to-send

### Phase 10: Advanced Features (Optional)
- [ ] Context compaction engine (multi-threshold summarization)
- [ ] Decision anchor extraction (LLM + rule-based)
- [ ] Semantic memory (ChromaDB cross-session recall)
- [ ] Metrics/observability logging

---

> **Minimum viable implementation**: Phases 1-9 give you a fully functional AI assistant side panel. Phase 10 adds long-conversation and cross-session intelligence.
