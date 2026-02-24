# KetZero Intel — React Frontend

React + TypeScript frontend for the Quantum Intelligence Hub.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + TypeScript |
| Build | Vite 7 |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite` plugin) |
| Routing | React Router v7 |
| Data Fetching | TanStack Query v5 (2-min stale time) |
| Icons | Lucide React |
| API | FastAPI (Python) — proxied via Vite in dev |

## Getting Started

### Prerequisites
- Node.js 18+
- FastAPI backend running on `localhost:8000`

### Development
```bash
# From project root — start FastAPI
uvicorn api.main:app --reload --port 8000

# From frontend-react/ — start Vite dev server
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies all `/api/*` requests to FastAPI.

### Production Build
```bash
npm run build
```
Output goes to `dist/`. FastAPI serves this automatically via `StaticFiles` mount in `api/main.py`.

## Architecture

### Layout
```
┌─────────────────────────────────────────────────────────┐
│ Header: Logo │ Domain Toggle (Quantum / AI) │ Settings  │
├─────────────────────────────────────────────────────────┤
│ Sub-nav Tabs: Briefing │ Explore │ Markets │ Research │ …│
├───────────────────────────────────────┬─────────────────┤
│                                       │                 │
│           Main Content Area           │   Chat Panel    │
│           (routed pages)              │   (380px, right)│
│                                       │                 │
├───────────────────────────────────────┴─────────────────┤
│ Status Bar: article count │ embeddings │ last updated   │
└─────────────────────────────────────────────────────────┘
```

- **Domain Toggle** — Global filter (Quantum / AI) passed to all pages
- **Chat Panel** — Collapsible right sidebar with context-aware AI assistant
- **Status Bar** — Live system stats polling `/api/stats` every 60s

### File Structure
```
src/
├── api.ts                  # Typed API client + all TypeScript interfaces
├── App.tsx                 # Shell layout (header, nav, routes, chat panel)
├── main.tsx                # Entry point (BrowserRouter + QueryClientProvider)
├── index.css               # Tailwind import + dark theme variables
├── components/
│   ├── ui.tsx              # Shared primitives (badges, cards, chips, helpers)
│   ├── ArticleCard.tsx     # Reusable article display card
│   ├── ChatPanel.tsx       # Right-side AI chat (placeholder — SSE TODO)
│   └── StatusBar.tsx       # Footer with live system stats
└── pages/
    ├── BriefingPage.tsx    # Weekly digest + 6 drill-down sections
    ├── ExplorePage.tsx     # Browse all content with lens presets + filters
    ├── MarketsPage.tsx     # Stock overview table → company deep-dive
    ├── ResearchPage.tsx    # ArXiv papers with type/readiness/keyword filters
    ├── FilingsPage.tsx     # SEC nuggets + Earnings quotes (tabbed)
    └── SettingsPage.tsx    # System health, API keys, storage info
```

## Pages

### Briefing (`/`)
Weekly "what you need to know" summary. Renders the AI-generated digest with stat cards and 6 expandable drill-down sections:
- **Top Stories** — Highest-priority articles
- **Deployments & ROI** — Real-world quantum deployments and commercial outcomes
- **Market Pulse** — Stock movers with earnings/SEC context
- **Executive Voices** — Notable quotes from earnings calls
- **Regulatory & Policy** — Standards, export controls, government programs
- **Papers & Research** — Key ArXiv papers by readiness level

### Explore (`/explore`)
Full content browser with lens presets (All, Deployments, Use Cases, Breakthroughs, Industry, Skepticism, Policy) and filters for category, priority, time range, and keyword search.

### Markets (`/markets`)
Stock overview table for 20 quantum tickers with price, change, volume. Click any company to drill into:
- Price history timeline
- Earnings call quotes
- SEC filing nuggets
- Related news articles

### Research (`/research`)
ArXiv paper browser with filters for paper type (theoretical, experimental, review, survey), quantum readiness level, time range, and keyword search. Collapsible abstracts and direct PDF links.

### Filings (`/filings`)
Two-tab view toggling between:
- **SEC Nuggets** — Extracted insights from 10-K/10-Q/8-K filings with risk level, disclosure status, and competitor mentions
- **Earnings Quotes** — Key quotes from earnings calls with speaker, confidence level, and sentiment

### Settings (`/settings`)
System dashboard showing article/embedding counts, API key status, storage backend info, and version.

## API Layer

FastAPI backend in `api/` wraps the existing Python `StorageBackend` with zero reimplementation.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/articles` | GET | Articles with category/priority/source/search filters |
| `/api/articles/{id}` | GET | Single article by ID |
| `/api/digest` | GET | Latest AI-generated digest |
| `/api/digest/briefing` | GET | Composite briefing (digest + stories + market + voices + regulatory + papers) |
| `/api/stocks` | GET | All tracked stocks with latest data |
| `/api/stocks/{ticker}` | GET | Deep-dive: history, articles, quotes, nuggets |
| `/api/papers` | GET | Papers with type/readiness/search filters |
| `/api/papers/{id}` | GET | Single paper by ID |
| `/api/earnings` | GET | Earnings quotes with ticker/type filters |
| `/api/sec` | GET | SEC nuggets with ticker/type/signal filters |
| `/api/stats` | GET | System health stats |

### API Files
```
api/
├── main.py             # FastAPI app, CORS, router mounts, static serving
├── dependencies.py     # Singleton StorageBackend via lru_cache
└── routes/
    ├── articles.py
    ├── digest.py
    ├── earnings.py
    ├── papers.py
    ├── sec.py
    ├── stats.py
    └── stocks.py
```

## Theming

Dark theme by default using CSS custom properties in `index.css`:

| Variable | Value | Usage |
|----------|-------|-------|
| `--color-bg-primary` | `#0f1117` | Main background |
| `--color-bg-secondary` | `#161b22` | Header, sidebar, cards |
| `--color-bg-tertiary` | `#1c2333` | Inputs, chips, hover states |
| `--color-accent-blue` | `#58a6ff` | Active nav, links |
| `--color-accent-cyan` | `#79c0ff` | Quantum branding |
| `--color-accent-purple` | `#bc8cff` | AI branding, earnings |
| `--color-accent-green` | `#3fb950` | Positive / bullish |
| `--color-accent-red` | `#f85149` | Critical / bearish |
| `--color-accent-orange` | `#d29922` | Warnings |
| `--color-accent-yellow` | `#e3b341` | Medium priority |

## TODO

- [ ] SSE streaming for chat panel → wire to intelligence agent
- [ ] Recharts/Plotly stock price charts on Markets deep-dive
- [ ] AI domain content pipeline (second ingestion source)
- [ ] GCP Cloud Run deployment (single container: FastAPI + React dist)
- [ ] Responsive / mobile layout tweaks
- [ ] Keyboard shortcuts (Cmd+K search, Esc close chat)
