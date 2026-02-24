# Quantum Computing Intelligence Hub — Build Specification

**Version:** 1.0
**Last Updated:** February 20, 2026
**Author:** Jonny (Ket Zero Intelligence)
**Target Audience:** Internal development reference + Claude Code build spec

---

## 1. PROJECT OVERVIEW

### 1.1 Product Name
**Quantum Intelligence Hub**

### 1.2 One-Line Description
A multi-agent AI system that monitors the quantum computing ecosystem — tracking companies, research breakthroughs, real-world use cases, market signals, and investment activity — delivering proactive intelligence digests and on-demand deep research.

### 1.3 Business Goal
Provide a continuously updated intelligence platform for the quantum computing industry that surfaces what matters: which companies are making real progress, where commercial use cases are emerging, what the research pipeline looks like, and how the investment landscape is shifting. Oriented toward **real-world use cases and commercial viability**, not hype.

### 1.4 Intelligence Philosophy
This hub takes a **"No Hot Takes Allowed"** approach:
- Focus on verifiable progress over press release hype
- Distinguish between lab results and commercial readiness
- Track real deployments and customer wins, not just funding rounds
- Surface contrarian signals (e.g., timeline skepticism, technical barriers)

### 1.5 Success Criteria (POC)
- [ ] Daily automated data ingestion from all configured sources
- [ ] Classified news digest with priority triage (High / Medium / Low)
- [ ] Deep research workflow for on-demand queries
- [ ] Stock tracking for public quantum companies
- [ ] ArXiv paper monitoring with relevance scoring
- [ ] Podcast transcript ingestion (2 shows)
- [ ] Deployed on GCP (Cloud Run + BigQuery + GCS)

---

## 2. DATA SOURCES

### 2.1 Stock Tickers — Quantum Computing Companies

#### Pure-Play Quantum Companies (Primary Watch)

| Ticker | Company | Focus Area |
|--------|---------|------------|
| IONQ | IonQ Inc. | Trapped-ion quantum computing, QCaaS |
| QBTS | D-Wave Quantum Inc. | Quantum annealing, hybrid quantum-classical |
| RGTI | Rigetti Computing Inc. | Superconducting quantum processors, cloud |
| QUBT | Quantum Computing Inc. | Photonic quantum, integrated photonics |
| ARQQ | Arqit Quantum Inc. | Quantum encryption / cybersecurity |
| QMCO | Quantum Corporation | Quantum storage/data management (adjacent) |
| QNCCF | Quantum eMotion Corp. | Quantum-safe cybersecurity (OTC) |
| LAES | SealSQ Corp. | Post-quantum semiconductors / security |

#### Major Tech Companies with Quantum Divisions (Secondary Watch)

| Ticker | Company | Quantum Initiative |
|--------|---------|-------------------|
| GOOGL | Alphabet (Google) | Google Quantum AI, Willow processor |
| IBM | IBM | IBM Quantum, Qiskit, Nighthawk processor |
| MSFT | Microsoft | Azure Quantum, topological qubits |
| AMZN | Amazon | AWS Braket, quantum computing service |
| HON | Honeywell | Quantinuum (subsidiary), trapped-ion |
| NVDA | Nvidia | Hybrid quantum-classical GPU integration |

#### Quantum ETF

| Ticker | Name | Description |
|--------|------|-------------|
| QTUM | Defiance Quantum ETF | Broad quantum computing + ML exposure |

#### Notable Private Companies (Track for IPO / Funding News)

| Company | Focus Area | Status |
|---------|------------|--------|
| Quantinuum | Full-stack quantum (Honeywell spin-off) | Private, potential IPO |
| PsiQuantum | Photonic quantum computing | Private, $665M+ raised |
| Xanadu | Photonic quantum, PennyLane software | Private |
| Atom Computing | Neutral atom quantum computing | Private |
| QuEra Computing | Neutral atom, Harvard/MIT spinout | Private |
| Pasqal | Neutral atom quantum, EU-based | Private, raising €200M+ |
| Alice & Bob | Cat qubits, error correction | Private, EU-based |
| IQM Quantum | Superconducting, EU-based | Private |
| Quantum Machines | Quantum control hardware/software | Private, Israel-based |
| Nord Quantique | Bosonic quantum computing | Private, Canada |

---

### 2.2 Tavily Search Queries (~50 Use-Case Oriented)

These queries are grouped by strategic theme and designed to surface **real-world applications and commercial progress**, not theoretical research. Run daily.

#### Theme 1: Drug Discovery & Healthcare (8 queries)
```
1.  "quantum computing drug discovery clinical trial"
2.  "quantum simulation protein folding pharmaceutical"
3.  "quantum computing genomics precision medicine"
4.  "quantum machine learning medical imaging diagnostics"
5.  "quantum computing vaccine development molecular simulation"
6.  "quantum chemistry drug interaction modeling"
7.  "quantum computing healthcare deployment production"
8.  "quantum biology enzyme catalysis simulation"
```

#### Theme 2: Financial Services & Optimization (7 queries)
```
9.  "quantum computing portfolio optimization hedge fund"
10. "quantum Monte Carlo risk analysis financial services"
11. "quantum computing fraud detection banking"
12. "quantum advantage derivatives pricing options"
13. "quantum computing credit risk modeling"
14. "quantum algorithms trading strategy Wall Street"
15. "quantum optimization insurance actuarial"
```

#### Theme 3: Cybersecurity & Post-Quantum Cryptography (7 queries)
```
16. "post-quantum cryptography migration enterprise"
17. "quantum key distribution commercial deployment"
18. "NIST post-quantum standards implementation timeline"
19. "quantum threat harvest now decrypt later"
20. "quantum-safe encryption adoption government"
21. "quantum random number generator commercial"
22. "quantum computing cybersecurity readiness assessment"
```

#### Theme 4: Supply Chain, Logistics & Optimization (5 queries)
```
23. "quantum computing supply chain optimization deployment"
24. "quantum annealing logistics routing scheduling"
25. "quantum optimization manufacturing production planning"
26. "quantum computing warehouse operations fleet management"
27. "D-Wave quantum supply chain customer case study"
```

#### Theme 5: Energy, Climate & Materials Science (6 queries)
```
28. "quantum computing battery materials discovery"
29. "quantum simulation catalyst design clean energy"
30. "quantum computing carbon capture climate modeling"
31. "quantum chemistry solar cell material optimization"
32. "quantum computing power grid optimization energy"
33. "quantum simulation superconductor discovery room temperature"
```

#### Theme 6: AI & Machine Learning Intersection (5 queries)
```
34. "quantum machine learning advantage classical comparison"
35. "quantum neural network training speedup"
36. "quantum computing AI inference acceleration"
37. "hybrid quantum classical machine learning production"
38. "quantum reservoir computing time series"
```

#### Theme 7: Hardware & Error Correction Milestones (6 queries)
```
39. "quantum error correction logical qubit milestone"
40. "quantum processor qubit count fidelity improvement"
41. "quantum computing fault tolerant timeline roadmap"
42. "quantum supremacy advantage benchmark real problem"
43. "quantum interconnect networking multi-processor"
44. "quantum computing room temperature photonic breakthrough"
```

#### Theme 8: Government, Defense & Geopolitics (4 queries)
```
45. "quantum computing government contract defense department"
46. "China quantum computing progress satellite"
47. "quantum technology export controls national security"
48. "quantum computing workforce talent shortage training"
```

#### Theme 9: Industry Adoption & Commercial Readiness (4 queries)
```
49. "quantum computing enterprise pilot customer deployment"
50. "quantum computing revenue commercial product launch"
51. "quantum as a service cloud platform customer growth"
52. "quantum computing skepticism timeline reality check"
```

---

### 2.3 RSS Feeds — Quantum News Sources

#### Tier 1: Dedicated Quantum News (Daily Pull)

| Source | RSS Feed URL | Focus |
|--------|-------------|-------|
| The Quantum Insider | `https://thequantuminsider.com/feed/` | Breaking news, industry analysis, editorial |
| Quantum Computing Report | `https://quantumcomputingreport.com/feed/` | Comprehensive weekly updates, authoritative |
| Quantum Untangled (Substack) | `https://quantumuntangled.substack.com/feed` | Interviews, in-depth industry analysis |
| ScienceDaily - Quantum | `https://www.sciencedaily.com/rss/computers_math/quantum_computers.xml` | Research papers, aggregated studies |
| Inside Quantum Technology | `https://insidequantumtechnology.com/feed/` | Industry news, market analysis |
| Quantum Zeitgeist | `https://quantumzeitgeist.com/feed` | News, insights, quantum market coverage |

#### Tier 2: Industry & Vendor Blogs (Daily Pull)

| Source | RSS Feed URL | Focus |
|--------|-------------|-------|
| IBM Quantum / Qiskit Blog | `https://www.ibm.com/quantum/blog/rss` | Hardware updates, community, Qiskit |
| Google Quantum AI Blog | `https://blog.google/technology/research/rss/` (filter: quantum) | Willow, research breakthroughs |
| AWS Quantum Technologies | `https://aws.amazon.com/blogs/quantum-computing/feed/` | Braket, cloud quantum services |
| IonQ Blog | `https://ionq.com/blog/rss.xml` | Trapped-ion, commercial updates |
| Microsoft Azure Quantum | `https://devblogs.microsoft.com/qsharp/feed/` | Topological qubits, Azure Quantum |
| D-Wave Blog | `https://www.dwavesys.com/blog/feed/` | Quantum annealing, customer stories |

**Note:** Some vendor blogs may not have direct RSS. Fallback strategy: use Tavily Extract on blog index pages weekly, or monitor via Google Alerts → RSS bridge.

#### Tier 3: Academic & Research News (Daily Pull)

| Source | RSS Feed URL | Focus |
|--------|-------------|-------|
| Nature - Quantum Information | `https://www.nature.com/subjects/quantum-information.rss` | Peer-reviewed breakthroughs |
| MIT News - Quantum Computing | `https://news.mit.edu/topic/quantum-computing/feed` | University research, academic dev |
| Quanta Magazine - Quantum | `https://quantamagazine.org/tag/quantum-computing/feed` | Accessible science journalism |
| Quantum Frontiers (Caltech) | `https://quantumfrontiers.com/feed` | IQI @ Caltech research blog |

#### Tier 4: Broader Tech Coverage (Daily Pull, Filtered)

| Source | RSS Feed URL | Filter Keywords |
|--------|-------------|----------------|
| Ars Technica - Science | `https://feeds.arstechnica.com/arstechnica/science` | "quantum" |
| IEEE Spectrum | `https://spectrum.ieee.org/feeds/topic/computing.rss` | "quantum" |
| Wired - Science | `https://www.wired.com/feed/tag/science/latest/rss` | "quantum" |
| TechCrunch | `https://techcrunch.com/feed/` | "quantum" |

---

### 2.4 ArXiv.org API — Quantum Papers

#### API Details
- **Base URL:** `http://export.arxiv.org/api/query`
- **Method:** HTTP GET with URL parameters
- **Rate Limit:** 1 request per 3 seconds (be respectful)
- **Response Format:** Atom XML

#### Primary Categories to Monitor

| Category | arxiv ID | Description |
|----------|----------|-------------|
| Quantum Physics | `quant-ph` | Core quantum computing papers |
| Quantum Gases | `cond-mat.quant-gas` | Quantum materials, BEC |
| Emerging Technologies | `cs.ET` | Quantum computing (CS perspective) |
| Cryptography | `cs.CR` | Post-quantum crypto, QKD |

#### Example API Queries

```python
# Recent quantum computing papers (last 7 days)
import urllib.parse

base_url = "http://export.arxiv.org/api/query?"

# Search for quantum computing papers
params = {
    "search_query": "cat:quant-ph AND (ti:quantum+computing OR ti:quantum+error+correction OR ti:quantum+algorithm OR ti:quantum+advantage)",
    "start": 0,
    "max_results": 50,
    "sortBy": "submittedDate",
    "sortOrder": "descending"
}

url = base_url + urllib.parse.urlencode(params)

# Use-case focused queries
USE_CASE_QUERIES = [
    # Drug discovery / chemistry
    'cat:quant-ph AND (abs:"drug discovery" OR abs:"molecular simulation" OR abs:"quantum chemistry")',
    
    # Optimization
    'cat:quant-ph AND (abs:"combinatorial optimization" OR abs:"quantum annealing" OR abs:"QAOA")',
    
    # Machine learning
    'cat:quant-ph AND (abs:"quantum machine learning" OR abs:"variational quantum" OR abs:"quantum neural")',
    
    # Error correction (milestone tracking)
    'cat:quant-ph AND (abs:"quantum error correction" OR abs:"logical qubit" OR abs:"fault tolerant")',
    
    # Cryptography
    '(cat:quant-ph OR cat:cs.CR) AND (abs:"post-quantum" OR abs:"quantum key distribution" OR abs:"lattice-based")',
    
    # Hardware
    'cat:quant-ph AND (abs:"superconducting qubit" OR abs:"trapped ion" OR abs:"photonic quantum" OR abs:"neutral atom")',
]
```

#### Paper Processing Pipeline
```
ArXiv API Query (daily, 6 category queries)
    ↓
Parse Atom XML → Extract: title, authors, abstract, categories, date, arxiv_id
    ↓
Relevance Scoring (LLM-based)
    - Score 1-10: How relevant to commercial quantum computing?
    - Tag: use_case_category (drug_discovery, optimization, crypto, etc.)
    - Tag: paper_type (breakthrough, incremental, review, theoretical)
    ↓
Store in BigQuery: quantum_papers table
    ↓
Surface in digest: papers scored 7+ or tagged "breakthrough"
```

---

### 2.5 Podcasts — Quantum Computing

#### Primary Podcasts (Weekly Transcript Ingestion)

| Podcast | Host(s) | Platform | Frequency | Focus |
|---------|---------|----------|-----------|-------|
| **The Superposition Guy** | Yuval Boger (QuEra CCO) | Spotify, Apple, Web | ~Weekly | Industry interviews, quantum leaders, broad coverage |
| **The Post-Quantum World** | Protiviti (Konstantinos Karagiannis) | Spotify, Apple, Web | Bi-weekly | PQC, quantum security, enterprise readiness |

**Backup/Supplementary Options:**
- **Quantum Computing Now** — Ethan Hansen / Shwetha Jayaraj (community-driven, accessible)
- **The Coherence Times** — IBM Quantum (Ryan Mandelbaum) — launched Nov 2025, bi-weekly
- **Quantum Computing Report Podcasts** — Doug Finke — interviews with industry leaders

#### Podcast Processing Pipeline
```
RSS Feed / Spotify API → New episode detection
    ↓
Download audio file (or fetch transcript if available)
    ↓
Speech-to-text (Whisper API or Google Cloud Speech-to-Text)
    ↓
LLM Summarization:
    - Key takeaways (3-5 bullets)
    - Guest name + affiliation
    - Companies/technologies mentioned
    - Notable claims or predictions
    - Sentiment: bullish/bearish/neutral on quantum timeline
    ↓
Store in BigQuery: podcast_episodes table
    ↓
Surface in weekly digest
```

---

## 3. ARCHITECTURE OVERVIEW

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUANTUM INTELLIGENCE HUB                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   DATA INGESTION LAYER                       │   │
│  │                                                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │   │
│  │  │ RSS/News │  │ Tavily   │  │ ArXiv    │  │ Podcast   │   │   │
│  │  │ Feeds    │  │ Search   │  │ API      │  │ Ingestion │   │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘   │   │
│  │       │              │             │              │          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │   │
│  │  │ Stock    │  │ SEC/     │  │ Press    │  │ NewsData  │   │   │
│  │  │ Data     │  │ Earnings │  │ Releases │  │ .io       │   │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘   │   │
│  │       └──────────────┴─────────────┴──────────────┘          │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                PROCESSING & STORAGE LAYER                    │   │
│  │                                                              │   │
│  │  BigQuery Tables:                                            │   │
│  │  • quantum_articles    (RSS + news articles)                 │   │
│  │  • quantum_papers      (ArXiv papers, scored)                │   │
│  │  • quantum_stocks      (daily price + signals)               │   │
│  │  • quantum_podcasts    (episode transcripts + summaries)     │   │
│  │  • quantum_press       (press releases, Tavily extract)      │   │
│  │  • quantum_digests     (pre-computed daily/weekly digests)   │   │
│  │                                                              │   │
│  │  GCS Buckets:                                                │   │
│  │  • Raw audio files (podcasts)                                │   │
│  │  • PDF downloads (whitepapers, reports)                      │   │
│  │  • Backfill snapshots                                        │   │
│  │                                                              │   │
│  │  Vertex AI Vector Search:                                    │   │
│  │  • Embedded articles for semantic search                     │   │
│  │  • Embedded paper abstracts                                  │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                   AGENT LAYER (LangGraph)                    │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │   │
│  │  │  Router     │  │ Intelligence│  │ Deep Research        │ │   │
│  │  │  Agent      │  │ Agent       │  │ Workflow             │ │   │
│  │  │ (classify   │  │ (fast query │  │ (multi-agent:        │ │   │
│  │  │  intent)    │  │  + digest)  │  │  query groom →       │ │   │
│  │  └─────────────┘  └─────────────┘  │  industry + finance  │ │   │
│  │                                    │  → synthesis)         │ │   │
│  │                                    └─────────────────────┘ │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                    PRESENTATION LAYER                        │   │
│  │                                                              │   │
│  │  • Streamlit / FastAPI frontend                              │   │
│  │  • Daily Intelligence Digest (auto-generated)                │   │
│  │  • Chat interface for on-demand queries                      │   │
│  │  • Stock dashboard with quantum sector performance           │   │
│  │  • ArXiv paper feed with relevance scores                    │   │
│  │  • Weekly briefing export (PPTX / PDF)                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Proposed Directory Structure

```
quantum-intelligence-hub/
│
├── README.md
├── requirements.txt
├── Dockerfile
├── .env.example
├── .env
│
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Environment config, API keys
│   ├── prompts.py                  # All LLM system prompts
│   ├── tickers.py                  # Stock ticker lists + metadata
│   ├── rss_sources.py              # RSS feed URLs + categories
│   ├── tavily_queries.py           # All 52 Tavily query strings
│   └── arxiv_queries.py            # ArXiv search query configs
│
├── data_ingestion/
│   ├── __init__.py
│   ├── scheduler.py                # Cloud Scheduler orchestration
│   ├── rss_collector.py            # RSS feed ingestion
│   ├── tavily_collector.py         # Tavily search execution
│   ├── arxiv_collector.py          # ArXiv API client
│   ├── stock_collector.py          # Stock price data collection
│   ├── podcast_collector.py        # Podcast episode detection + transcription
│   ├── press_release_collector.py  # Press release monitoring
│   └── newsdata_collector.py       # NewsData.io integration
│
├── processing/
│   ├── __init__.py
│   ├── classifier.py               # LLM-based article classification
│   ├── entity_extractor.py         # Company/tech entity extraction
│   ├── relevance_scorer.py         # Content relevance scoring (1-10)
│   ├── deduplicator.py             # Cross-source deduplication
│   ├── digest_generator.py         # Daily/weekly digest compilation
│   └── embeddings.py               # Text embedding for vector search
│
├── agents/
│   ├── __init__.py
│   ├── router.py                   # Intent classification agent
│   ├── intelligence_agent.py       # Fast queries, corpus search, digest
│   └── research_agent.py           # Deep research multi-agent workflow
│
├── tools/
│   ├── __init__.py
│   ├── web_search.py               # Tavily search + extract wrapper
│   ├── corpus_search.py            # BigQuery / vector search over stored data
│   ├── stock_data.py               # Stock price + financial data tool
│   ├── arxiv_search.py             # ArXiv paper search tool
│   ├── podcast_search.py           # Search podcast transcripts
│   └── trend_analysis.py           # Time-series trend detection
│
├── storage/
│   ├── __init__.py
│   ├── bigquery_client.py          # BigQuery read/write operations
│   ├── gcs_client.py               # GCS file operations
│   ├── schemas.py                  # BigQuery table schemas
│   └── vector_store.py             # Vertex AI Vector Search client
│
├── api/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   ├── routes/
│   │   ├── chat.py                 # Chat endpoint (streaming)
│   │   ├── digest.py               # Digest retrieval endpoint
│   │   ├── stocks.py               # Stock data endpoint
│   │   └── papers.py               # ArXiv papers endpoint
│   └── models/
│       ├── requests.py             # API request schemas
│       └── responses.py            # API response schemas
│
├── frontend/                       # Streamlit or React
│   ├── app.py                      # Main Streamlit app
│   ├── pages/
│   │   ├── digest.py               # Intelligence digest view
│   │   ├── chat.py                 # Chat interface
│   │   ├── stocks.py               # Quantum stock dashboard
│   │   ├── papers.py               # ArXiv paper feed
│   │   └── settings.py             # User preferences
│   └── components/
│       ├── article_card.py
│       ├── stock_chart.py
│       └── paper_summary.py
│
├── templates/
│   └── weekly_briefing_template.pptx
│
└── tests/
    ├── test_rss_collector.py
    ├── test_tavily_collector.py
    ├── test_arxiv_collector.py
    └── test_classifier.py
```

---

## 4. TECH STACK

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Orchestration** | LangGraph | Multi-agent workflow management |
| **LLM** | Claude (Anthropic API) | claude-sonnet-4-20250514 for agents, haiku for classification |
| **Web Search** | Tavily API | Search + Extract endpoints |
| **News API** | NewsData.io | Supplementary news coverage |
| **Compute** | Google Cloud Run | Containerized API + frontend |
| **Database** | BigQuery | Structured data storage, analytics |
| **Object Storage** | Google Cloud Storage | Raw files, audio, PDFs |
| **Vector Search** | Vertex AI Vector Search | Semantic search over corpus |
| **Scheduling** | Google Cloud Scheduler | Trigger daily/hourly ingestion |
| **Task Queue** | Cloud Tasks or Pub/Sub | Async processing pipeline |
| **Transcription** | Whisper API or GCP Speech-to-Text | Podcast audio → text |
| **Embeddings** | text-embedding-004 (Google) or Voyage AI | Document embeddings |
| **Frontend** | Streamlit or React + FastAPI | User interface |

---

## 5. PIPELINE SCHEDULES

| Pipeline | Frequency | Estimated Volume | Cost Driver |
|----------|-----------|-----------------|-------------|
| RSS Feed Ingestion | Every 4 hours | ~100-200 articles/day | Minimal (free RSS) |
| Tavily Search Queries | Daily (morning) | 52 queries/day | ~$30-60/mo Tavily |
| ArXiv Paper Monitoring | Daily | ~20-50 papers/day | Free API |
| Stock Data Collection | Daily (market close) | 20 tickers | Depends on data source |
| Podcast Episode Check | Daily | ~2-4 episodes/week | Whisper API cost |
| Press Release Monitoring | Daily | ~5-15/day | Tavily Extract cost |
| NewsData.io Pull | Every 6 hours | ~50-100 articles/day | $0-75/mo depending on tier |
| Digest Generation | Daily (6 AM) | 1 digest/day | LLM inference cost |
| Weekly Briefing | Sunday evening | 1 briefing/week | LLM inference cost |

---

## 6. CLASSIFICATION TAXONOMY

Every piece of content ingested should be classified with:

### 6.1 Content Categories
```python
CONTENT_CATEGORIES = [
    "hardware_milestone",           # Qubit count, fidelity, new processor
    "error_correction",             # QEC breakthroughs, logical qubits
    "algorithm_research",           # New quantum algorithms, improvements
    "use_case_drug_discovery",      # Pharma/biotech applications
    "use_case_finance",             # Financial services applications
    "use_case_optimization",        # Supply chain, logistics, scheduling
    "use_case_cybersecurity",       # PQC, QKD, quantum-safe
    "use_case_energy_materials",    # Battery, catalyst, materials discovery
    "use_case_ai_ml",              # Quantum ML, hybrid quantum-AI
    "use_case_other",              # Other commercial applications
    "company_earnings",            # Earnings reports, financial results
    "funding_ipo",                 # Funding rounds, IPO news, SPAC
    "partnership_contract",        # Commercial partnerships, gov contracts
    "personnel_leadership",        # Executive moves, key hires
    "policy_regulation",           # Government policy, export controls
    "geopolitics",                 # US-China quantum race, national programs
    "market_analysis",             # Industry forecasts, market sizing
    "skepticism_critique",         # Timeline pushback, technical barriers
    "education_workforce",         # Quantum education, talent pipeline
]
```

### 6.2 Priority Levels
```python
PRIORITY_LEVELS = {
    "critical": "Major breakthrough, significant market event, or security-relevant",
    "high": "Notable company news, new deployment, meaningful milestone",
    "medium": "Industry trend, research paper of interest, partnership",
    "low": "General coverage, educational content, opinion piece",
}
```

### 6.3 Entity Types
```python
ENTITY_TYPES = [
    "company",          # IonQ, D-Wave, Google Quantum AI, etc.
    "technology",       # Trapped-ion, superconducting, photonic, neutral atom
    "product",          # Willow, Nighthawk, Aria, Ankaa, Advantage2
    "person",           # Key researchers, CEOs, policy makers
    "institution",      # Universities, national labs, government agencies
    "standard",         # NIST PQC standards, CRYSTALS-Kyber, etc.
    "use_case_domain",  # Pharma, finance, logistics, defense, etc.
]
```

---

## 7. DIGEST FORMAT

### 7.1 Daily Intelligence Digest

```
┌─────────────────────────────────────────────────────────────────┐
│  QUANTUM INTELLIGENCE DIGEST: February 20, 2026                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔴 CRITICAL (0-2 items)                                       │
│  • [If any: major breakthroughs, security events, market moves]│
│                                                                 │
│  📈 MARKET SNAPSHOT                                            │
│  • IONQ: $XX.XX (▲/▼ X.X%)  |  QBTS: $XX.XX (▲/▼ X.X%)     │
│  • RGTI: $XX.XX (▲/▼ X.X%)  |  QTUM ETF: $XX.XX (▲/▼ X.X%) │
│                                                                 │
│  🏢 COMPANY NEWS (3-5 items)                                   │
│  • [Company] [headline summary] [source]                       │
│                                                                 │
│  🔬 RESEARCH & MILESTONES (2-4 items)                          │
│  • [Paper/announcement] [significance] [source]                │
│                                                                 │
│  💼 USE CASES & DEPLOYMENTS (2-3 items)                        │
│  • [Company] deployed [technology] for [use case] [source]     │
│                                                                 │
│  🔒 CYBERSECURITY & PQC (1-2 items)                           │
│  • [PQC migration news, QKD deployments, standards updates]    │
│                                                                 │
│  📄 NOTABLE PAPERS (top 3 by relevance score)                  │
│  • [Title] — [Authors] — Score: X/10 — [1-line significance]  │
│                                                                 │
│  🎙️ PODCAST HIGHLIGHTS (if new episode this week)              │
│  • [Show]: [Guest] discussed [key takeaway]                    │
│                                                                 │
│  📊 WEEKLY TRENDS (Sundays only)                               │
│  • Sector sentiment: [bullish/bearish/neutral]                 │
│  • Most discussed companies this week                          │
│  • Emerging themes                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. BigQuery TABLE SCHEMAS

### 8.1 quantum_articles
```sql
CREATE TABLE quantum_hub.quantum_articles (
    article_id STRING NOT NULL,           -- UUID
    source_name STRING,                    -- "The Quantum Insider", "Nature", etc.
    source_type STRING,                    -- "rss", "tavily", "newsdata", "press_release"
    url STRING,
    title STRING,
    content_text STRING,                   -- Full text or summary
    published_at TIMESTAMP,
    ingested_at TIMESTAMP,
    
    -- Classification (LLM-generated)
    category STRING,                       -- From CONTENT_CATEGORIES
    priority STRING,                       -- critical/high/medium/low
    relevance_score FLOAT64,              -- 1-10
    sentiment STRING,                      -- bullish/bearish/neutral
    
    -- Entities (JSON arrays)
    companies_mentioned ARRAY<STRING>,
    technologies_mentioned ARRAY<STRING>,
    people_mentioned ARRAY<STRING>,
    use_case_domains ARRAY<STRING>,
    
    -- Metadata
    is_duplicate BOOL DEFAULT FALSE,
    duplicate_of STRING,                   -- article_id of original
    summary STRING,                        -- LLM-generated 2-3 sentence summary
    key_takeaway STRING,                   -- Single sentence takeaway
);
```

### 8.2 quantum_papers
```sql
CREATE TABLE quantum_hub.quantum_papers (
    arxiv_id STRING NOT NULL,
    title STRING,
    authors ARRAY<STRING>,
    abstract STRING,
    categories ARRAY<STRING>,
    published_at TIMESTAMP,
    updated_at TIMESTAMP,
    ingested_at TIMESTAMP,
    pdf_url STRING,
    
    -- LLM-generated fields
    relevance_score FLOAT64,              -- 1-10 commercial relevance
    paper_type STRING,                     -- breakthrough/incremental/review/theoretical
    use_case_category STRING,              -- drug_discovery, optimization, etc.
    significance_summary STRING,           -- 1-2 sentence plain-English significance
    commercial_readiness STRING,           -- near_term / mid_term / long_term / theoretical
);
```

### 8.3 quantum_stocks
```sql
CREATE TABLE quantum_hub.quantum_stocks (
    ticker STRING NOT NULL,
    date DATE NOT NULL,
    open FLOAT64,
    high FLOAT64,
    low FLOAT64,
    close FLOAT64,
    volume INT64,
    change_percent FLOAT64,
    market_cap FLOAT64,
    
    -- Derived
    sma_20 FLOAT64,
    sma_50 FLOAT64,
    relative_strength FLOAT64,
);
```

### 8.4 quantum_podcasts
```sql
CREATE TABLE quantum_hub.quantum_podcasts (
    episode_id STRING NOT NULL,
    podcast_name STRING,
    episode_title STRING,
    published_at TIMESTAMP,
    audio_url STRING,
    transcript_gcs_path STRING,
    duration_seconds INT64,
    
    -- LLM-generated
    guest_name STRING,
    guest_affiliation STRING,
    key_takeaways ARRAY<STRING>,
    companies_mentioned ARRAY<STRING>,
    technologies_discussed ARRAY<STRING>,
    timeline_sentiment STRING,             -- bullish/bearish/neutral on quantum timeline
    summary STRING,
);
```

---

## 9. AGENT SPECIFICATIONS

### 9.1 Router Agent
- **Purpose:** Classify user intent and route to appropriate agent
- **Model:** claude-haiku (fast, cheap)
- **Routes:**
  - `digest` → Intelligence Agent (show latest digest)
  - `quick_query` → Intelligence Agent (search corpus + Tavily)
  - `deep_research` → Research Agent (multi-agent workflow)
  - `stock_query` → Intelligence Agent (stock data tool)
  - `paper_search` → Intelligence Agent (ArXiv corpus search)

### 9.2 Intelligence Agent
- **Purpose:** Fast answers from stored corpus + real-time search
- **Model:** claude-sonnet-4-20250514
- **Tools Available:**
  - `corpus_search` — Search BigQuery articles/papers by keyword + vector similarity
  - `web_search` — Tavily search for real-time queries
  - `stock_data` — Current stock prices + historical data
  - `arxiv_search` — Search stored ArXiv papers
  - `podcast_search` — Search podcast transcripts

### 9.3 Deep Research Workflow (Multi-Agent)
- **Purpose:** Comprehensive research on complex questions
- **Architecture:** Query Groom → [Industry Agent || Financial Agent] → Synthesis Agent
- **Model:** claude-sonnet-4-20250514 for all agents
- **Parallel execution** of industry and financial research
- **Synthesis agent** merges findings, resolves conflicts, produces structured output

---

## 10. ENVIRONMENT VARIABLES

```bash
# ===========================================
# API Keys
# ===========================================
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
NEWSDATA_API_KEY=pub_...

# ===========================================
# Google Cloud Platform
# ===========================================
GCP_PROJECT_ID=quantum-intelligence-hub
GCP_REGION=us-central1
BIGQUERY_DATASET=quantum_hub
GCS_BUCKET=quantum-hub-data

# ===========================================
# Stock Data
# ===========================================
# Options: FMP, Alpha Vantage, or Yahoo Finance (yfinance - free)
STOCK_DATA_PROVIDER=yfinance

# ===========================================
# Agent Configuration
# ===========================================
DEFAULT_MODEL=claude-sonnet-4-20250514
CLASSIFICATION_MODEL=claude-haiku-4-5-20251001
ROUTER_MODEL=claude-haiku-4-5-20251001

INTELLIGENCE_AGENT_TEMP=0.3
RESEARCH_AGENT_TEMP=0.4
CLASSIFICATION_TEMP=0.1

# ===========================================
# Feature Flags
# ===========================================
ENABLE_PODCAST_INGESTION=true
ENABLE_ARXIV_MONITORING=true
ENABLE_STOCK_TRACKING=true
ENABLE_DEEP_RESEARCH=true

# ===========================================
# Server
# ===========================================
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 11. IMPLEMENTATION PRIORITY (BUILD ORDER)

### Phase 1: Foundation (Week 1)
1. Project scaffolding + directory structure
2. BigQuery table creation + schemas
3. RSS feed ingestion pipeline (Tier 1 sources)
4. Basic article classification (LLM-based)
5. Simple daily digest generation

### Phase 2: Enrichment (Week 2)
6. Tavily search query execution (52 queries)
7. ArXiv paper monitoring + relevance scoring
8. Stock data collection (yfinance for POC)
9. Entity extraction pipeline
10. Deduplication logic

### Phase 3: Intelligence (Week 3)
11. Intelligence Agent (fast query + corpus search)
12. Router Agent
13. Vector embeddings + semantic search
14. Streamlit frontend (digest view + chat)

### Phase 4: Advanced (Week 4)
15. Deep Research multi-agent workflow
16. Podcast ingestion + transcription
17. Press release monitoring (Tavily Extract)
18. Weekly briefing auto-generation
19. GCP deployment (Cloud Run + Cloud Scheduler)

### Phase 5: Polish (Ongoing)
20. Stock dashboard with sector performance charts
21. ArXiv paper feed with filtering
22. Alert/notification system
23. Export capabilities (PPTX briefings)
24. Monitoring dashboard (GCP Cloud Monitoring)

---

## 12. KEY DIFFERENTIATORS FROM OTHER HUBS

| Feature | Quantum Hub Specific |
|---------|---------------------|
| **ArXiv integration** | New for this hub — academic papers are critical signal in quantum |
| **Hardware milestone tracking** | Qubit counts, fidelity improvements, error correction progress |
| **Timeline reality scoring** | Classify claims as near-term / mid-term / long-term / theoretical |
| **Use-case orientation** | Every piece of content tagged by commercial application area |
| **Skepticism signal** | Actively surface contrarian takes and technical barrier analysis |
| **Private company tracking** | Many key players are pre-IPO — track funding, partnerships, talent moves |
| **Geopolitics layer** | US-China quantum race is a significant factor |

---

## 13. NOTES FOR CLAUDE CODE

- This project follows the same architectural patterns as the C1 Intelligence Hub and Sprite Intelligence Hub
- Use LangGraph for agent orchestration — same StateGraph pattern
- BigQuery is the primary data store — no SQLite or ChromaDB
- All LLM calls should use the Anthropic Python SDK
- RSS parsing: use `feedparser` library
- ArXiv parsing: use `feedparser` (Atom format) or `requests` + `xml.etree`
- Stock data: start with `yfinance` (free), upgrade to FMP if needed
- Tavily: use both `search` and `extract` endpoints
- Classification should use Haiku for cost efficiency (high volume)
- Research agents should use Sonnet for quality
- All timestamps should be UTC
- Deduplication: use URL as primary key, with fuzzy title matching as secondary
- Follow existing patterns from `/data_ingestion/` directory of other hubs
