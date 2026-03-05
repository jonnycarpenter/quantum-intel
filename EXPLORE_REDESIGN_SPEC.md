# Explore Tab Redesign Spec

> **Session 14 — March 4, 2026**
> Planning doc for Explore page transformation + tab consolidation.
> To be implemented in a fresh session.

---

## 1. Design Philosophy

The core value proposition of Ket Zero Intelligence is:

> **"Here are the advancements (quantum or AI) — and here is how they're actually being used in the real world."**

The app serves business-oriented users who need to:
- Stay current on quantum/AI developments
- Extract themes and talking points for strategy meetings
- Understand real-world deployment patterns (case studies)
- Track market/investment signals

---

## 2. Tab Structure — Before & After

### Current (7 tabs + Settings)
| Tab | Content | Verdict |
|-----|---------|---------|
| Briefing | Weekly briefing | **Keep** — landing page, executive summary |
| Explore | Articles only | **Redesign** — becomes the unified exploration hub |
| Markets | Stock data | **Keep standalone** — will be built out further |
| Research | ArXiv papers | **Fold into Explore** |
| Case Studies | Case studies | **Keep standalone** — core value prop |
| Filings | SEC + Earnings | **Fold into Explore** |
| Patents | Patent filings | **Fold into Explore** |

### Proposed (5 tabs + Settings)
| Tab | Icon | Content |
|-----|------|---------|
| **Briefing** | `Newspaper` | Weekly briefing (unchanged) |
| **Explore** | `Compass` | Unified feed: articles, research papers, voice quotes (podcast + earnings), SEC nuggets, patents — plus analytics and insight-building tools |
| **Case Studies** | `Lightbulb` | Case studies (unchanged — standalone, core value prop) |
| **Markets** | `TrendingUp` | Stock data (unchanged — standalone, will be expanded) |
| **Settings** | `Settings` | System stats (header gear icon) |

**Net change:** Remove Research, Filings, and Patents as standalone tabs. Their content moves into Explore with content-type filtering.

---

## 3. Explore Page — New Layout

### 3A. Split-Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Explore                                   [Quantum] [AI]   │
├───────────────────────────┬─────────────────────────────────┤
│                           │                                 │
│  LEFT PANEL (60%)         │  RIGHT PANEL (40%)              │
│  ════════════════         │  ═════════════════              │
│                           │                                 │
│  [Analytics Bar]          │  "Insight Builder"              │
│   • Category breakdown    │                                 │
│   • Trend sparklines      │  Saved clips / highlights       │
│   • Concept cloud         │  from the left panel.           │
│                           │                                 │
│  [Content Type Tabs]      │  User can pin articles,         │
│  Articles | Voice Quotes  │  quotes, nuggets to build       │
│  | Research | SEC/Patents │  a custom briefing.             │
│                           │                                 │
│  [Filters]                │  [Export as PDF / Markdown]     │
│  Category · Priority ·    │                                 │
│  Time Range · Search      │  ───────────────────────        │
│                           │  When empty, shows:             │
│  ┌──────────────────────┐ │  "Pin items from the feed       │
│  │ Content Card         │ │   to build your briefing"       │
│  │ [📌 Pin] [🔗 Link]  │ │                                 │
│  └──────────────────────┘ │                                 │
│  ┌──────────────────────┐ │                                 │
│  │ Content Card         │ │                                 │
│  │ [📌 Pin]             │ │                                 │
│  └──────────────────────┘ │                                 │
│  ...scrollable feed...    │                                 │
│                           │                                 │
├───────────────────────────┴─────────────────────────────────┤
│  Status Bar                                                 │
└─────────────────────────────────────────────────────────────┘
```

**Responsive behavior:**
- On smaller screens, the Insight Builder collapses to a floating action button that opens a drawer/modal
- Split can be toggled off (full-width feed mode) via a toggle icon

### 3B. Left Panel — Feed + Analytics

#### Analytics Bar (top of left panel)

Three collapsible/expandable visualization widgets:

**1. Category Breakdown Chart**
- Horizontal bar chart or donut chart showing article count by `primary_category`
- Clickable — clicking a category filters the feed
- Responds to domain toggle and time range
- Data source: `GET /api/articles/categories` (already exists)

**2. Trend Over Time**
- Small multi-line sparkline chart showing how topic categories trend over time
- X-axis: time (7d/30d/90d matching time range selector)
- Y-axis: article count per day/week
- Lines: top 5 most active categories (color-coded)
- New API needed: `GET /api/articles/trends?domain=quantum&days=30`
- Returns: `{ category: string, data: { date: string, count: number }[] }[]`

**3. Concept Cloud**
- Word/concept cloud generated from article titles + summaries + entities
- Size = frequency, color = category/sentiment
- Changes dynamically with domain toggle and time range
- Clickable — clicking a term triggers search filter
- New API needed: `GET /api/articles/concept-cloud?domain=quantum&hours=168`
- Returns: `{ terms: { text: string, weight: number, category?: string }[] }`
- Backend: Extract terms from `technologies_mentioned`, `companies_mentioned`, `key_takeaway` fields; weighted by frequency + recency

**Analytics bar behavior:**
- Collapsed by default on mobile, expanded on desktop
- Toggle: "Show Analytics" / "Hide Analytics" with a small chevron
- Animations: smooth height transition

#### Content Type Tabs

Horizontal tabs below analytics bar:

| Tab | Data Source | Content |
|-----|-----------|---------|
| **All** | Mixed feed | Everything, reverse-chronological |
| **Articles** | `GET /api/articles` | News articles (existing ArticleCard) |
| **Voice Quotes** | `GET /api/podcasts` (new) + `GET /api/earnings` | Podcast quotes + earnings quotes merged, sorted by date |
| **Research** | `GET /api/papers` | ArXiv papers (moved from standalone tab) |
| **Filings & IP** | `GET /api/sec` + `GET /api/patents` | SEC nuggets + patents merged |

**"All" tab logic:**
- Fetches from all sources in parallel
- Merges into single reverse-chronological feed
- Each card shows a small source-type badge (Article / Podcast / Earnings / SEC / Paper / Patent)
- Requires a new unified feed API or client-side merge of multiple queries

**Filter persistence:**
- Filters apply across all content type tabs where applicable
- Domain toggle, time range, and search are universal
- Category filter only applies to Articles tab
- Quote type filter only applies to Voice Quotes tab
- etc.

#### Content Cards

Each content type gets its own card component, all with a **pin button** (📌) for the Insight Builder:

| Content Type | Card Design | Key Fields |
|---|---|---|
| **Article** | Existing `ArticleCard` + pin button | title, summary, source, category, priority, companies, relevance |
| **Podcast Quote** | NEW `PodcastQuoteCard` | quote text (large italic), speaker + role, podcast name, episode, quote_type badge, themes, sentiment |
| **Earnings Quote** | Existing style from FilingsPage | quote text, speaker + role, company + ticker, quarter, quote_type, confidence |
| **SEC Nugget** | Existing style from FilingsPage | nugget text, company + ticker, filing source, nugget_type, risk_level, NEW badge |
| **Paper** | Existing style from ResearchPage | title, authors, significance, type badge, readiness, relevance, arXiv link |
| **Patent** | Existing style from PatentsPage | title, assignee, inventors, filing date, abstract |

All cards share:
- Pin button (📌) — adds to Insight Builder
- External link icon (🔗) — opens source
- Consistent border-left color coding by content type:
  - Article: teal
  - Podcast: cyan
  - Earnings: purple
  - SEC: orange
  - Paper: blue
  - Patent: gray

### 3C. Right Panel — Insight Builder

The Insight Builder is the "workspace" side of the split screen. Users build custom briefings by pinning content from the feed.

**States:**

1. **Empty state**: 
   - Illustration + "Pin items from the feed to build your briefing"
   - Suggested prompts: "Try pinning a few articles and voice quotes, then export as a briefing"

2. **Has pinned items**:
   - Draggable/reorderable list of pinned items (compact card view)
   - Each pinned item shows: content type badge, title/quote snippet, remove button (✕)
   - "Add a note" — inline text area to add user annotations between items
   - Section dividers the user can insert ("---" or named headers)

3. **Export options** (bottom bar):
   - **Export PDF** — generates a formatted PDF briefing from pinned items
   - **Export Markdown** — downloads .md file
   - **Send to Chat** — sends pinned content to the AI chat as context for deeper analysis
   - **Clear all** — resets the builder

**Technical approach:**
- Pinned items stored in React state (or localStorage for persistence across page navigations)
- No backend needed initially — purely client-side
- Export uses existing `AdHocModal` pattern (markdown → ReactMarkdown rendering → print)
- "Send to Chat" composes a message like: "Analyze these {N} items I've collected: [summaries]" and sends to ChatPanel

**Future enhancement:** Save/load named briefing collections server-side.

---

## 4. New Backend API Endpoints

### 4A. Podcast Quotes API (new file: `api/routes/podcasts.py`)

```
GET /api/podcasts
  ?domain=quantum|ai
  &quote_type=opinion|technical_insight|prediction|...
  &speaker=<name>
  &podcast=<name>
  &search=<text>
  &limit=50

Response: {
  quotes: PodcastQuote[],
  total: number
}
```

Storage methods already exist:
- `storage.get_podcast_quotes(domain, limit)`
- `storage.search_podcast_quotes(query, limit)`

Need to add optional `quote_type` and `speaker` filtering in the storage layer or route.

### 4B. Article Trends API (new endpoint on existing articles route)

```
GET /api/articles/trends
  ?domain=quantum|ai
  &days=30
  &top_n=5

Response: {
  trends: [
    { category: "hardware_milestone", data: [{ date: "2026-02-01", count: 5 }, ...] },
    { category: "partnership_contract", data: [{ date: "2026-02-01", count: 3 }, ...] },
    ...
  ]
}
```

Backend: BigQuery query grouping articles by `primary_category` and `DATE(published_at)`, limited to top N categories by total volume.

### 4C. Concept Cloud API (new endpoint on existing articles route)

```
GET /api/articles/concept-cloud
  ?domain=quantum|ai
  &hours=168

Response: {
  terms: [
    { text: "IonQ", weight: 45, type: "company" },
    { text: "error correction", weight: 38, type: "technology" },
    { text: "drug discovery", weight: 22, type: "use_case" },
    ...
  ]
}
```

Backend: Aggregate `companies_mentioned`, `technologies_mentioned`, and `use_case_domains` from articles within the time window. Parse comma-separated or JSON array fields, count frequencies, return top ~80 terms with weights.

---

## 5. New Frontend Types (api.ts additions)

```typescript
// Podcast quotes
interface PodcastQuote {
  quote_id: string
  podcast_name: string
  episode_title: string
  speaker_name: string
  speaker_role: string
  quote_text: string
  quote_type: string
  themes: string
  sentiment: string
  relevance_score: number
  published_at: string | null
  context_before?: string
  context_after?: string
}

// Trends
interface TrendDataPoint {
  date: string
  count: number
}

interface CategoryTrend {
  category: string
  data: TrendDataPoint[]
}

// Concept cloud
interface ConceptTerm {
  text: string
  weight: number
  type: 'company' | 'technology' | 'use_case' | 'topic'
}

// Insight Builder pinned item
interface PinnedItem {
  id: string
  content_type: 'article' | 'podcast_quote' | 'earnings_quote' | 'sec_nugget' | 'paper' | 'patent'
  title: string         // display title or quote snippet
  data: any             // original full object
  pinned_at: string     // ISO timestamp
  user_note?: string    // optional annotation
}
```

### New API Functions

```typescript
// In api object
getPodcastQuotes(params?: { domain?: Domain, quote_type?: string, speaker?: string, search?: string, limit?: number })
getArticleTrends(params?: { domain?: Domain, days?: number, top_n?: number })
getConceptCloud(params?: { domain?: Domain, hours?: number })
```

---

## 6. New Components

### `PodcastQuoteCard.tsx`
- Large italic quote text with left cyan border
- Speaker attribution: name + role (with company logo if available)
- Podcast name + episode title as subtitle
- Badge row: quote_type, sentiment, relevance score
- Theme tags (TagChip, cyan variant)
- Pin button

### `TrendChart.tsx`
- Multi-line sparkline chart (Recharts `LineChart` or `AreaChart`)
- Responsive, fits in analytics bar
- Color-coded by category
- Tooltip on hover showing date + count per category
- Legend with clickable category names (toggles line visibility)

### `ConceptCloud.tsx`
- Word cloud visualization
- Options: 
  - **react-wordcloud** (d3-cloud based) — most popular
  - **Custom SVG** — lighter weight, more control
- Words sized by weight, colored by type (company=teal, tech=blue, use_case=purple, topic=gray)
- Clickable — sets search filter
- Animates on domain/time change

### `InsightBuilder.tsx`
- Right panel component
- DnD reordering (react-beautiful-dnd or @dnd-kit/sortable)
- Compact pinned item cards
- Inline note editor (textarea)
- Export bar at bottom
- Empty state illustration

### `ContentTypeTabs.tsx`
- Horizontal tab bar: All | Articles | Voice Quotes | Research | Filings & IP
- Count badges on each tab
- Active tab styling consistent with existing LensChip pattern

### `UnifiedContentCard.tsx` (optional wrapper)
- Wrapper that renders the appropriate card component based on `content_type`
- Adds the pin button and source-type border color consistently
- Used in the "All" tab mixed feed

---

## 7. Data Flow — "All" Tab

The "All" tab needs to merge content from multiple APIs into a single chronological feed.

**Approach: Client-side merge with parallel queries**

```
1. Fire parallel queries:
   - api.getArticles({ domain, hours, limit: 50 })
   - api.getPodcastQuotes({ domain, limit: 30 })
   - api.getEarningsQuotes({ domain, limit: 30 })
   - api.getSecNuggets({ domain, limit: 20 })
   - api.getPapers({ days: hours/24, limit: 20 })

2. Normalize into unified items:
   { id, content_type, date, title, data }

3. Sort by date descending

4. Render with UnifiedContentCard
```

**Alternative: Server-side unified feed endpoint**
```
GET /api/explore/feed?domain=quantum&hours=168&limit=100
```
Returns pre-merged, pre-sorted items. More efficient but more complex backend work.

**Recommendation:** Start with client-side merge (faster to implement), move to server-side if performance becomes an issue.

---

## 8. Concept Cloud — Implementation Details

### Is a word/concept cloud worth it?

**Yes, with caveats:**
- Word clouds are visually engaging and give an instant "feel" for what's trending
- They work well as **interactive filters** — click a term to filter the feed
- They change meaningfully with domain toggle and time range (quantum shows different terms than AI)
- **Caveat:** Pure word clouds can feel dated. A "concept cloud" with grouped clusters or a bubble chart alternative could feel more modern.

### Options

1. **Classic Word Cloud** — react-wordcloud, random placement, sized by frequency
2. **Bubble Chart** — d3 force-directed circles, grouped by type, sized by frequency (more modern)
3. **Tag Wall** — Simple grid of TagChips, sized by weight classes (S/M/L/XL), fastest to implement

**Recommendation:** Start with **Tag Wall** (option 3) — simplest, fastest, native to existing design system. Upgrade to bubble chart later if desired.

### Tag Wall Implementation
```
┌─────────────────────────────────────────────┐
│  IonQ  Google  IBM  error correction        │
│  Microsoft  drug discovery  PQC  D-Wave     │
│  Rigetti  optimization  cybersecurity       │
│  trapped ions  neutral atoms  finance       │
│  NVIDIA  energy  superconducting            │
└─────────────────────────────────────────────┘
```
- Tags sized: XL (top 5), L (6-15), M (16-30), S (31-80)
- Color: company=teal, technology=blue, use_case=purple
- Clickable → populates search box

---

## 9. "Themes & Talking Points" Feature

### Goal
Make it easy for users to scan the Explore tab and quickly extract themes and talking points for meetings.

### Approach: AI-Generated Theme Summary

Add a collapsible "Key Themes" section at the top of the feed (below analytics bar, above content tabs):

```
┌─────────────────────────────────────────────────────────┐
│  📊 Key Themes This Week                    [Collapse ▲]│
│                                                         │
│  1. Error Correction Breakthroughs: IBM and Google both │
│     announced significant advances in quantum error     │
│     correction, with IBM's new code achieving...        │
│     → 8 articles, 3 earnings mentions                   │
│                                                         │
│  2. Post-Quantum Cryptography Urgency: NIST timeline    │
│     driving enterprise adoption pressure...             │
│     → 5 articles, 2 SEC nuggets                         │
│                                                         │
│  3. Drug Discovery Pipelines Maturing: Multiple pharma  │
│     companies reporting quantum advantage claims...     │
│     → 6 articles, 1 case study                          │
│                                                         │
│  [Use in briefing ↗]  [Copy as bullet points 📋]       │
└─────────────────────────────────────────────────────────┘
```

### Backend
- New endpoint: `GET /api/articles/themes?domain=quantum&hours=168`
- Implementation options:
  1. **LLM-generated**: Pass top ~30 article summaries to Claude → extract 3-5 key themes with supporting evidence counts. Cache for 1 hour.
  2. **Algorithmic**: Cluster articles by category + entity overlap → generate theme titles from category names + top entities. No LLM cost.
- **Recommendation:** Start with algorithmic (option 2 — free, fast, deterministic), add LLM refinement later.

### Response Shape
```json
{
  "themes": [
    {
      "title": "Error Correction Breakthroughs",
      "summary": "IBM and Google both announced significant advances...",
      "article_count": 8,
      "earnings_mentions": 3,
      "sec_mentions": 0,
      "top_companies": ["IBM", "Google", "Rigetti"],
      "categories": ["error_correction", "hardware_milestone"],
      "source_ids": ["article-id-1", "article-id-2", ...]
    }
  ],
  "talking_points": [
    "IBM achieved a 10x improvement in logical error rates",
    "Google's Willow chip demonstrated below-threshold error correction",
    "NIST PQC standards driving enterprise security reviews"
  ]
}
```

### "Use in briefing" action
- Pins the entire theme block into the Insight Builder
- User can edit/refine the talking points before export

---

## 10. Implementation Plan — Phased

### Phase 1: Foundation (Backend + Tab Consolidation) ✅
**Effort: ~1 session — COMPLETED Session 1 (March 4, 2026)**

1. ✅ Create `api/routes/podcasts.py` — podcast quotes endpoint
2. ✅ Create `GET /api/articles/trends` endpoint
3. ✅ Create `GET /api/articles/concept-cloud` endpoint  
4. ✅ Add `PodcastQuote` type + new API functions to `api.ts`
5. ✅ Remove Research, Filings, Patents from App.tsx nav
6. ✅ Keep old pages accessible via direct URL (don't delete yet)

**Files created/modified:**
- `api/routes/podcasts.py` — NEW: GET /api/podcasts with domain, quote_type, speaker, podcast, search filters
- `api/routes/articles.py` — added /trends and /concept-cloud endpoints
- `api/main.py` — registered podcasts router
- `frontend-react/src/api.ts` — added PodcastQuote, TrendDataPoint, CategoryTrend, ConceptTerm, PinnedItem types + getPodcastQuotes, getArticleTrends, getConceptCloud functions
- `frontend-react/src/App.tsx` — consolidated NAV_ITEMS to 4 tabs (Briefing, Explore, Case Studies, Markets)

### Phase 2: Explore Feed Redesign (Left Panel) ✅
**Effort: ~1 session — COMPLETED Session 2 (March 4, 2026)**

1. ✅ Build content type tabs (All | Articles | Voice Quotes | Research | Filings & IP)
2. ✅ Build `PodcastQuoteCard`, `EarningsQuoteCard`, `SecNuggetCard`, `PaperCard`, `PatentCard` components
3. ✅ Refactor `ExplorePage` — content type tabs, multi-source data fetching (parallel useQuery)
4. ✅ Implement "All" tab with client-side merge (FeedItem discriminated union, date-sorted)
5. ✅ Move Research content into "Research" tab
6. ✅ Move Filings + Patents into "Filings & IP" tab (with all/sec/patents sub-tab)
7. ✅ Wire up per-tab filters: lenses (articles), quote type (voice), sub-tab (filings); universal: domain, time, search
8. ✅ Add missing `Patent` type + `getRecentPatents` function to `api.ts`

**Files created:**
- `frontend-react/src/components/PodcastQuoteCard.tsx` — cyan border, Mic icon
- `frontend-react/src/components/EarningsQuoteCard.tsx` — purple border, Quote icon
- `frontend-react/src/components/SecNuggetCard.tsx` — orange border, ShieldAlert icon
- `frontend-react/src/components/PaperCard.tsx` — blue border, collapsible abstract
- `frontend-react/src/components/PatentCard.tsx` — gray border, FileBadge icon

**Files modified:**
- `frontend-react/src/api.ts` — added Patent interface (13 fields), getRecentPatents function
- `frontend-react/src/pages/ExplorePage.tsx` — full rewrite with tabs, parallel queries, unified feed

### Phase 3: Analytics Bar ✅
**Effort: ~1 session — COMPLETED Session 3 (March 4, 2026)**

1. ✅ Build `TrendChart` component (Recharts LineChart)
2. ✅ Build `ConceptCloud` component (Tag Wall v1)
3. ✅ Build category breakdown chart (horizontal bars, Recharts)
4. ✅ Create collapsible `AnalyticsBar` container (3-col grid, expand/collapse)
5. ✅ Wire to backend endpoints (trends, concept-cloud, categories) via useQuery in ExplorePage

**Files created:**
- `frontend-react/src/components/TrendChart.tsx` — Multi-line sparkline (Recharts LineChart), category color palette, date formatting
- `frontend-react/src/components/ConceptCloud.tsx` — Tag Wall with weight-based sizing (XL/L/M/S), color-coded by type (company/technology/use_case/topic), clickable → search
- `frontend-react/src/components/CategoryBreakdown.tsx` — Horizontal bar chart (Recharts BarChart), clickable → category filter
- `frontend-react/src/components/AnalyticsBar.tsx` — Collapsible container, 3-column grid (categories | trends | concepts), chevron toggle

**Files modified:**
- `frontend-react/src/pages/ExplorePage.tsx` — Added AnalyticsBar import, 3 new useQuery calls (trends, concepts, categories), category/concept click handlers, rendered between header and content tabs

### Phase 4: Insight Builder (Right Panel) ✅
**Effort: ~1 session — COMPLETED Session 4 (March 4, 2026)**

1. ✅ Build `InsightBuilder` component with empty state
2. ✅ Add pin buttons to all content cards
3. ✅ Implement pinned item state management (React context + localStorage)
4. ✅ DnD reordering (@dnd-kit)
5. ✅ Inline notes between items
6. ✅ Export: PDF (via print), Markdown (blob download)
7. ✅ "Send to Chat" integration (CustomEvent dispatch)

### Phase 5: Themes & Talking Points ✅
**Effort: ~0.5 session — COMPLETED Session 5 (March 5, 2026)**

1. ✅ Build `GET /api/articles/themes` endpoint (algorithmic v1)
2. ✅ Build `KeyThemes` collapsible component
3. ✅ "Copy as bullet points" clipboard action
4. ✅ "Use in briefing" → pins to Insight Builder (pin button on each theme card)
5. ✅ Add `Theme`, `ThemesResponse` types + `getThemes()` to `api.ts`

**Files created:**
- `frontend-react/src/components/KeyThemes.tsx` — Collapsible Key Themes section with theme cards, inline pin buttons, copy-talking-points action

**Files modified:**
- `api/routes/articles.py` — added `GET /articles/themes` algorithmic endpoint (cluster by category, top companies, talking points from key_takeaways)
- `frontend-react/src/api.ts` — added `Theme`, `ThemesResponse` types + `getThemes()` function
- `frontend-react/src/pages/ExplorePage.tsx` — added `themesQ` useQuery, rendered `<KeyThemes>` between AnalyticsBar and Content Type Tabs

### Phase 6: Polish & Responsive ✅
**Effort: ~0.5 session — COMPLETED Session 5 (March 5, 2026)**

1. ✅ Mobile responsive: InsightBuilder collapses to floating PIN button (FAB, bottom-right) that opens a slide-in drawer
2. ✅ Full-width mode toggle: desktop toggle button pops Insight Builder sidebar (hidden on mobile)
3. ✅ Loading skeletons: `ContentSkeletons` component replaces "Loading..." text with shimmer card placeholders
4. ✅ Analytics bar collapse/expand animation: smooth `max-h` + `opacity` CSS transition already in place
5. ✅ Removed old standalone page routes (Research /research, Filings /filings, Patents /patents) from App.tsx; content fully accessible via Explore tabs

**Files modified:**
- `frontend-react/src/pages/ExplorePage.tsx` — mobile drawer state, FAB, responsive aside (hidden lg), `ContentSkeletons` component, scrollable tab bar
- `frontend-react/src/App.tsx` — removed Research/Filings/Patents imports and routes; responsive nav (icon-only on xs, chat panel hidden on xs)
- `frontend-react/src/index.css` — added `animate-slide-in-right` keyframe, `skeleton` shimmer utility, `scrollbar-none` utility

---

## 11. Data Inventory (Current BigQuery State)

| Table | Count | Status |
|-------|-------|--------|
| articles | 811 | ✅ Active, 607 quantum + 204 AI |
| papers | 433 | ✅ Active |
| earnings_quotes | 1,900 | ✅ Active |
| sec_nuggets | 560 | ✅ Active |
| podcast_quotes | 376 | ✅ Fixed this session |
| podcast_transcripts | 1 | ✅ Fixed this session |
| case_studies | 5 | ✅ Fixed this session |
| stocks | 987 | ✅ Active |
| weekly_briefings | 4 | ✅ Active |
| patents | 0 | ⚠️ Pipeline exists but no data yet |
| funding_events | 0 | ⚠️ Pipeline exists but no data yet |

**Top article categories:** partnership_contract (62), hardware_milestone (59), algorithm_research (57), policy_regulation (53), use_case_cybersecurity (51)

**Top podcast quote types:** opinion (116), technical_insight (112), announcement (39), prediction (33)

**Top earnings quote types:** revenue_metric (384), strategy (368), competitive (291), technology_milestone (259)

---

## 12. Dependencies & Libraries

### New packages needed:
- `react-wordcloud` or `d3-cloud` — only if going beyond Tag Wall
- `@dnd-kit/core` + `@dnd-kit/sortable` — for Insight Builder drag-and-drop
- (Recharts already installed — used by RadarWidget)

### Existing libraries leveraged:
- `@tanstack/react-query` — data fetching + caching
- `recharts` — charts (trend lines, bar charts)
- `react-markdown` + `remark-gfm` — markdown rendering (export preview)
- `lucide-react` — icons

---

## 13. Open Questions

1. **Should the "All" feed be truly chronological or relevance-ranked?** Chronological is simpler but relevance-ranked surfaces better content. Could offer a toggle: "Latest" vs "Top".

2. **Insight Builder persistence** — localStorage only? Or save to backend (BigQuery table for user-created briefings)? localStorage is simpler for v1.

3. **Concept Cloud: Tag Wall vs Bubble Chart?** Tag Wall is faster to build and fits the existing design system. Bubble chart is more visually impressive but requires d3.

4. **Themes: Algorithmic vs LLM?** Algorithmic is free and fast but less nuanced. LLM costs ~$0.01-0.02 per generation but produces more natural language summaries. Could do algorithmic + LLM refinement on-demand ("Enhance with AI" button).

5. **Chat panel interaction** — When Explore becomes the main hub, should the chat panel have deeper integration? E.g., "Analyze this feed" button, or context-aware suggestions based on what the user is viewing.

6. **Mobile layout** — The split-screen is desktop-focused. On mobile, should the Insight Builder be a bottom sheet? A separate tab? A floating button that opens a drawer?

---

## 14. Success Metrics

After implementation, the Explore tab should enable a user to:
- [ ] See all content types in one place without switching tabs
- [ ] Quickly identify trending topics via analytics bar
- [ ] Filter to specific content types (articles, voice quotes, research, filings)
- [ ] Click concept cloud terms to drill into specific topics
- [ ] Pin interesting items to build a custom briefing
- [ ] Export that briefing as PDF or Markdown for a meeting
- [ ] Get pre-built talking points from the Key Themes section
- [ ] Do all of the above in under 5 minutes

---

*This spec should be implemented across 4-6 sessions following the phased plan in Section 10.*
