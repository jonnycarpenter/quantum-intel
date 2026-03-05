/**
 * Explore Page
 * ============
 * Unified feed with content type tabs: All | Articles | Voice Quotes | Research | Filings & IP
 * Multi-source data fetching with client-side merge for the "All" tab.
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { Domain, Article, PodcastQuote, EarningsQuote, SecNuggetDisplay, Paper, Patent, PinnedItem } from '../api'
import ArticleCard from '../components/ArticleCard'
import PodcastQuoteCard from '../components/PodcastQuoteCard'
import EarningsQuoteCard from '../components/EarningsQuoteCard'
import SecNuggetCard from '../components/SecNuggetCard'
import PaperCard from '../components/PaperCard'
import PatentCard from '../components/PatentCard'
import DomainToggle from '../components/DomainToggle'
import AnalyticsBar from '../components/AnalyticsBar'
import KeyThemes from '../components/KeyThemes'
import InsightBuilder from '../components/InsightBuilder'
import { usePinnedItems } from '../context/PinnedItemsContext'
import { SectionHeader, EmptyState, LensChip } from '../components/ui'
import { Search, Newspaper, Mic, FlaskConical, Shield, PanelRightClose, PanelRightOpen, Pin, X } from 'lucide-react'

// ─── Content Type Tabs ────────────────────────────────

type ContentTab = 'all' | 'articles' | 'voice' | 'research' | 'filings'

const CONTENT_TABS: { key: ContentTab; label: string; icon: React.ReactNode }[] = [
  { key: 'all', label: 'All', icon: null },
  { key: 'articles', label: 'Articles', icon: <Newspaper className="w-3.5 h-3.5" /> },
  { key: 'voice', label: 'Voice Quotes', icon: <Mic className="w-3.5 h-3.5" /> },
  { key: 'research', label: 'Research', icon: <FlaskConical className="w-3.5 h-3.5" /> },
  { key: 'filings', label: 'Filings & IP', icon: <Shield className="w-3.5 h-3.5" /> },
]

// ─── Article Lens Presets (Articles tab only) ─────────

type Lens = { label: string; categories?: string[] }

const QUANTUM_LENSES: Lens[] = [
  { label: 'All' },
  { label: 'Deployments', categories: ['use_case_drug_discovery', 'use_case_finance', 'use_case_optimization', 'use_case_cybersecurity', 'use_case_energy_materials', 'use_case_ai_ml', 'use_case_other', 'partnership_contract'] },
  { label: 'Breakthroughs', categories: ['hardware_milestone', 'error_correction', 'algorithm_research'] },
  { label: 'Industry', categories: ['company_earnings', 'funding_ipo', 'partnership_contract', 'market_analysis'] },
  { label: 'Skepticism', categories: ['skepticism_critique'] },
  { label: 'Policy', categories: ['policy_regulation', 'geopolitics'] },
]

const AI_LENSES: Lens[] = [
  { label: 'All' },
  { label: 'Models & Products', categories: ['ai_model_release', 'ai_product_launch'] },
  { label: 'Use Cases', categories: ['ai_use_case_enterprise', 'ai_use_case_healthcare', 'ai_use_case_finance', 'ai_use_case_other'] },
  { label: 'Infrastructure', categories: ['ai_infrastructure'] },
  { label: 'Safety & Policy', categories: ['ai_safety_alignment', 'policy_regulation', 'geopolitics'] },
  { label: 'Research', categories: ['ai_research_breakthrough', 'ai_open_source'] },
  { label: 'Industry', categories: ['company_earnings', 'funding_ipo', 'partnership_contract', 'market_analysis'] },
]

const QUANTUM_CATEGORIES = [
  'hardware_milestone', 'error_correction', 'algorithm_research',
  'use_case_drug_discovery', 'use_case_finance', 'use_case_optimization',
  'use_case_cybersecurity', 'use_case_energy_materials', 'use_case_ai_ml', 'use_case_other',
  'company_earnings', 'funding_ipo', 'partnership_contract', 'personnel_leadership',
  'policy_regulation', 'geopolitics', 'market_analysis', 'skepticism_critique', 'education_workforce',
]

const AI_CATEGORIES = [
  'ai_model_release', 'ai_product_launch', 'ai_infrastructure',
  'ai_safety_alignment', 'ai_open_source',
  'ai_use_case_enterprise', 'ai_use_case_healthcare', 'ai_use_case_finance', 'ai_use_case_other',
  'ai_research_breakthrough',
  'company_earnings', 'funding_ipo', 'partnership_contract', 'personnel_leadership',
  'policy_regulation', 'geopolitics', 'market_analysis', 'skepticism_critique',
]

const PRIORITIES = ['critical', 'high', 'medium', 'low']
const TIME_RANGES = [
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 },
  { label: '30d', hours: 720 },
  { label: '90d', hours: 2160 },
]

// ─── Unified Feed Item ────────────────────────────────

type FeedItem =
  | { type: 'article'; date: string; data: Article }
  | { type: 'podcast_quote'; date: string; data: PodcastQuote }
  | { type: 'earnings_quote'; date: string; data: EarningsQuote }
  | { type: 'sec_nugget'; date: string; data: SecNuggetDisplay }
  | { type: 'paper'; date: string; data: Paper }
  | { type: 'patent'; date: string; data: Patent }

function extractDate(item: FeedItem): number {
  return new Date(item.date).getTime() || 0
}

// ─── Component ────────────────────────────────────────

export default function ExplorePage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [activeTab, setActiveTab] = useState<ContentTab>('all')
  const [activeLens, setActiveLens] = useState(0)
  const [category, setCategory] = useState<string>('')
  const [priority, setPriority] = useState<string>('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [hours, setHours] = useState(168)
  const [builderOpen, setBuilderOpen] = useState(true)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)

  // Voice Quotes sub-filter
  const [voiceQuoteType, setVoiceQuoteType] = useState<string>('')

  // Filings sub-filter
  const [filingsSubTab, setFilingsSubTab] = useState<'all' | 'sec' | 'patents'>('all')

  // ─── Pin helpers ──────────────────────────────────────

  const { pinItem, unpinItem, isItemPinned } = usePinnedItems()

  const handlePin = useCallback((contentType: PinnedItem['content_type'], id: string, title: string, data: PinnedItem['data']) => {
    if (isItemPinned(id)) {
      unpinItem(id)
    } else {
      pinItem({ id, content_type: contentType, title, data })
    }
  }, [pinItem, unpinItem, isItemPinned])

  // Reset filters when domain changes
  useEffect(() => {
    setActiveLens(0)
    setCategory('')
  }, [domain])

  const lenses = domain === 'ai' ? AI_LENSES : QUANTUM_LENSES
  const categories = domain === 'ai' ? AI_CATEGORIES : QUANTUM_CATEGORIES
  const days = Math.ceil(hours / 24)

  // ─── Data Queries (parallel) ──────────────────────────

  const needsArticles = activeTab === 'all' || activeTab === 'articles'
  const needsPodcasts = activeTab === 'all' || activeTab === 'voice'
  const needsEarnings = activeTab === 'all' || activeTab === 'voice'
  const needsPapers = activeTab === 'all' || activeTab === 'research'
  const needsSec = activeTab === 'all' || activeTab === 'filings'
  const needsPatents = activeTab === 'all' || activeTab === 'filings'

  const queryCategory = activeLens > 0 ? undefined : (category || undefined)
  const queryPriority = priority || undefined

  const articlesQ = useQuery({
    queryKey: ['explore-articles', domain, hours, queryCategory, queryPriority, search],
    queryFn: () => api.getArticles({
      hours,
      limit: 100,
      category: queryCategory,
      priority: queryPriority,
      search: search || undefined,
      domain,
    }),
    enabled: needsArticles,
  })

  const podcastsQ = useQuery({
    queryKey: ['explore-podcasts', domain, search],
    queryFn: () => api.getPodcastQuotes({
      domain,
      search: search || undefined,
      limit: 50,
    }),
    enabled: needsPodcasts,
  })

  const earningsQ = useQuery({
    queryKey: ['explore-earnings', search],
    queryFn: () => api.getEarningsQuotes({
      quote_type: voiceQuoteType || undefined,
    }),
    enabled: needsEarnings,
  })

  const papersQ = useQuery({
    queryKey: ['explore-papers', days, search],
    queryFn: () => api.getPapers({
      days,
      limit: 50,
      search: search || undefined,
    }),
    enabled: needsPapers,
  })

  const secQ = useQuery({
    queryKey: ['explore-sec', search],
    queryFn: () => api.getSecNuggets(),
    enabled: needsSec,
  })

  const patentsQ = useQuery({
    queryKey: ['explore-patents', domain],
    queryFn: () => api.getRecentPatents(domain, 50),
    enabled: needsPatents,
  })

  // ─── Analytics Queries ────────────────────────────────

  const trendsQ = useQuery({
    queryKey: ['explore-trends', domain, days],
    queryFn: () => api.getArticleTrends({ domain, days, top_n: 5 }),
  })

  const conceptsQ = useQuery({
    queryKey: ['explore-concepts', domain, hours],
    queryFn: () => api.getConceptCloud({ domain, hours }),
  })

  const categoriesQ = useQuery({
    queryKey: ['explore-categories', domain, hours],
    queryFn: () => api.getCategoryCounts(hours, domain),
  })

  const themesQ = useQuery({
    queryKey: ['explore-themes', domain, hours],
    queryFn: () => api.getThemes({ domain, hours }),
  })

  // ─── Analytics Data ───────────────────────────────────

  const trends = trendsQ.data?.trends ?? []
  const concepts = conceptsQ.data?.terms ?? []
  const categoryCountsRaw = categoriesQ.data?.categories ?? {}
  const categoryCounts = Object.entries(categoryCountsRaw)
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count)

  // ─── Data Extraction ──────────────────────────────────

  const articles = articlesQ.data?.articles ?? []
  const podcastQuotes = podcastsQ.data?.quotes ?? []
  const earningsQuotes = earningsQ.data?.quotes ?? []
  const papers = papersQ.data?.papers ?? []
  const secNuggets = secQ.data?.nuggets ?? []
  const patents = patentsQ.data?.data ?? []

  // Apply lens filtering for articles
  let filteredArticles = articles
  if (activeLens > 0 && lenses[activeLens].categories) {
    const cats = new Set(lenses[activeLens].categories)
    filteredArticles = articles.filter(a => cats.has(a.category))
  }

  // ─── Unified "All" Feed ───────────────────────────────

  const unifiedFeed = useMemo<FeedItem[]>(() => {
    if (activeTab !== 'all') return []

    const items: FeedItem[] = []

    for (const a of filteredArticles) {
      items.push({ type: 'article', date: a.published_at || '', data: a })
    }
    for (const q of podcastQuotes) {
      items.push({ type: 'podcast_quote', date: q.published_at || q.extracted_at || '', data: q })
    }
    for (const q of earningsQuotes) {
      // Approximate date from year + quarter
      const month = ((q.quarter - 1) * 3) + 2 // Q1→Feb, Q2→May, Q3→Aug, Q4→Nov
      items.push({ type: 'earnings_quote', date: `${q.year}-${String(month).padStart(2, '0')}-15`, data: q })
    }
    for (const n of secNuggets) {
      items.push({ type: 'sec_nugget', date: n.filing_date || '', data: n })
    }
    for (const p of papers) {
      items.push({ type: 'paper', date: p.published_at || '', data: p })
    }
    for (const p of patents) {
      items.push({ type: 'patent', date: p.publication_date || p.filing_date || '', data: p })
    }

    items.sort((a, b) => extractDate(b) - extractDate(a))
    return items
  }, [activeTab, filteredArticles, podcastQuotes, earningsQuotes, secNuggets, papers, patents])

  // ─── Tab counts ───────────────────────────────────────

  const tabCounts: Record<ContentTab, number> = {
    all: filteredArticles.length + podcastQuotes.length + earningsQuotes.length + papers.length + secNuggets.length + patents.length,
    articles: filteredArticles.length,
    voice: podcastQuotes.length + earningsQuotes.length,
    research: papers.length,
    filings: secNuggets.length + patents.length,
  }

  // ─── Loading state ────────────────────────────────────

  const isLoading =
    (needsArticles && articlesQ.isLoading) ||
    (needsPodcasts && podcastsQ.isLoading) ||
    (needsEarnings && earningsQ.isLoading) ||
    (needsPapers && papersQ.isLoading) ||
    (needsSec && secQ.isLoading) ||
    (needsPatents && patentsQ.isLoading)

  const handleSearch = () => setSearch(searchInput)

  // ─── Render ───────────────────────────────────────────

  const { pinnedItems: pinnedList } = usePinnedItems()

  return (
    <div className="flex gap-4 h-full -m-6">
      {/* ─── Feed Panel (left) ─── */}
      <div className={`flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 space-y-4 ${builderOpen ? '' : 'max-w-5xl mx-auto'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Explore</h1>
        <div className="flex items-center gap-3">
          <DomainToggle domain={domain} onChange={setDomain} />
          {/* Desktop toggle */}
          <button
            onClick={() => setBuilderOpen(!builderOpen)}
            className="hidden lg:block p-1.5 text-text-muted hover:text-accent-teal transition-colors rounded-md hover:bg-bg-tertiary"
            title={builderOpen ? 'Hide Insight Builder' : 'Show Insight Builder'}
          >
            {builderOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Analytics Bar */}
      <AnalyticsBar
        trends={trends}
        trendsLoading={trendsQ.isLoading}
        concepts={concepts}
        conceptsLoading={conceptsQ.isLoading}
        categories={categoryCounts}
        categoriesLoading={categoriesQ.isLoading}
        onCategoryClick={(cat) => {
          setActiveTab('articles')
          setActiveLens(0)
          setCategory(cat)
        }}
        onConceptClick={(term) => {
          setSearchInput(term)
          setSearch(term)
        }}
      />

      {/* Key Themes */}
      <KeyThemes data={themesQ.data} isLoading={themesQ.isLoading} />

      {/* Content Type Tabs */}
      <div className="flex items-center gap-1 border-b border-border pb-0 overflow-x-auto scrollbar-none">
        {CONTENT_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-accent-blue text-accent-blue'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            {tab.icon}
            {tab.label}
            <span className={`text-xs ml-1 px-1.5 py-0.5 rounded-full ${
              activeTab === tab.key
                ? 'bg-accent-blue/15 text-accent-blue'
                : 'bg-bg-tertiary text-text-muted'
            }`}>
              {tabCounts[tab.key]}
            </span>
          </button>
        ))}
      </div>

      {/* Article Lens Chips — only on Articles tab */}
      {activeTab === 'articles' && (
        <div className="flex flex-wrap gap-2">
          {lenses.map((lens, i) => (
            <LensChip
              key={lens.label}
              label={lens.label}
              active={activeLens === i}
              onClick={() => { setActiveLens(i); setCategory('') }}
            />
          ))}
        </div>
      )}

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Category — articles tab only, when "All" lens */}
        {activeTab === 'articles' && activeLens === 0 && (
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
          >
            <option value="">All Categories</option>
            {categories.map(c => (
              <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
            ))}
          </select>
        )}

        {/* Priority — articles tab only */}
        {(activeTab === 'articles' || activeTab === 'all') && (
          <select
            value={priority}
            onChange={e => setPriority(e.target.value)}
            className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
          >
            <option value="">All Priorities</option>
            {PRIORITIES.map(p => (
              <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
            ))}
          </select>
        )}

        {/* Voice quote type — voice tab only */}
        {activeTab === 'voice' && (
          <select
            value={voiceQuoteType}
            onChange={e => setVoiceQuoteType(e.target.value)}
            className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
          >
            <option value="">All Quote Types</option>
            <option value="strategic_direction">Strategic Direction</option>
            <option value="financial_metric">Financial Metric</option>
            <option value="product_roadmap">Product Roadmap</option>
            <option value="competitive_positioning">Competitive Positioning</option>
            <option value="market_insight">Market Insight</option>
            <option value="technical_detail">Technical Detail</option>
          </select>
        )}

        {/* Filings sub-tab — filings tab only */}
        {activeTab === 'filings' && (
          <div className="flex items-center bg-bg-tertiary rounded-lg border border-border">
            {(['all', 'sec', 'patents'] as const).map(st => (
              <button
                key={st}
                onClick={() => setFilingsSubTab(st)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  filingsSubTab === st
                    ? 'text-accent-blue bg-accent-blue/15'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {st === 'all' ? 'All' : st === 'sec' ? 'SEC Filings' : 'Patents'}
              </button>
            ))}
          </div>
        )}

        {/* Time range — universal */}
        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border">
          {TIME_RANGES.map(tr => (
            <button
              key={tr.hours}
              onClick={() => setHours(tr.hours)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                hours === tr.hours
                  ? 'text-accent-blue bg-accent-blue/15'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {tr.label}
            </button>
          ))}
        </div>

        {/* Search — universal */}
        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border px-3 py-1.5 gap-2">
          <Search className="w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search..."
            className="bg-transparent text-sm text-text-primary placeholder-text-muted outline-none w-48"
          />
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <ContentSkeletons />
      ) : (
        <>
          {/* ── All Tab ── */}
          {activeTab === 'all' && (
            <>
              <SectionHeader title="All Content" count={unifiedFeed.length} />
              {unifiedFeed.length > 0 ? (
                <div className="space-y-3">
                  {unifiedFeed.map((item, i) => (
                    <FeedCard key={`${item.type}-${i}`} item={item} onPin={handlePin} isItemPinned={isItemPinned} />
                  ))}
                </div>
              ) : (
                <EmptyState message="No content matches your filters" />
              )}
            </>
          )}

          {/* ── Articles Tab ── */}
          {activeTab === 'articles' && (
            <>
              <SectionHeader title="Articles" count={filteredArticles.length} />
              {filteredArticles.length > 0 ? (
                <div className="space-y-3">
                  {filteredArticles.map(a => (
                    <ArticleCard key={a.id} article={a} onPin={(a) => handlePin('article', a.id, a.title, a)} isPinned={isItemPinned(a.id)} />
                  ))}
                </div>
              ) : (
                <EmptyState message="No articles match your filters" />
              )}
            </>
          )}

          {/* ── Voice Quotes Tab ── */}
          {activeTab === 'voice' && (
            <>
              <SectionHeader title="Voice Quotes" count={podcastQuotes.length + earningsQuotes.length} />
              {(podcastQuotes.length + earningsQuotes.length) > 0 ? (
                <div className="space-y-3">
                  {podcastQuotes.map(q => (
                    <PodcastQuoteCard key={q.quote_id} quote={q} onPin={(q) => handlePin('podcast_quote', q.quote_id, q.quote_text.slice(0, 80), q)} isPinned={isItemPinned(q.quote_id)} />
                  ))}
                  {earningsQuotes.map(q => (
                    <EarningsQuoteCard key={q.quote_id} quote={q} onPin={(q) => handlePin('earnings_quote', q.quote_id, q.quote_text.slice(0, 80), q)} isPinned={isItemPinned(q.quote_id)} />
                  ))}
                </div>
              ) : (
                <EmptyState message="No voice quotes available" />
              )}
            </>
          )}

          {/* ── Research Tab ── */}
          {activeTab === 'research' && (
            <>
              <SectionHeader title="Research Papers" count={papers.length} />
              {papers.length > 0 ? (
                <div className="space-y-3">
                  {papers.map(p => (
                    <PaperCard key={p.arxiv_id} paper={p} onPin={(p) => handlePin('paper', p.arxiv_id, p.title, p)} isPinned={isItemPinned(p.arxiv_id)} />
                  ))}
                </div>
              ) : (
                <EmptyState message="No research papers found" />
              )}
            </>
          )}

          {/* ── Filings & IP Tab ── */}
          {activeTab === 'filings' && (
            <>
              <SectionHeader
                title="Filings & IP"
                count={
                  filingsSubTab === 'sec' ? secNuggets.length
                    : filingsSubTab === 'patents' ? patents.length
                    : secNuggets.length + patents.length
                }
              />
              {(filingsSubTab === 'all' || filingsSubTab === 'sec') && secNuggets.length > 0 && (
                <div className="space-y-3">
                  {secNuggets.map(n => (
                    <SecNuggetCard key={n.nugget_id} nugget={n} onPin={(n) => handlePin('sec_nugget', n.nugget_id, n.nugget_text.slice(0, 80), n)} isPinned={isItemPinned(n.nugget_id)} />
                  ))}
                </div>
              )}
              {(filingsSubTab === 'all' || filingsSubTab === 'patents') && patents.length > 0 && (
                <div className="space-y-3 mt-3">
                  {patents.map(p => (
                    <PatentCard key={p.id} patent={p} onPin={(p) => handlePin('patent', p.id, p.title, p)} isPinned={isItemPinned(p.id)} />
                  ))}
                </div>
              )}
              {((filingsSubTab === 'all' && secNuggets.length === 0 && patents.length === 0) ||
                (filingsSubTab === 'sec' && secNuggets.length === 0) ||
                (filingsSubTab === 'patents' && patents.length === 0)) && (
                <EmptyState message="No filings or patents found" />
              )}
            </>
          )}
        </>
      )}
      </div>{/* end feed panel */}

      {/* ─── Insight Builder Panel — Desktop (right sidebar) ─── */}
      {builderOpen && (
        <aside className="hidden lg:block w-[340px] min-w-[340px] border-l border-border bg-bg-secondary flex-shrink-0">
          <InsightBuilder />
        </aside>
      )}

      {/* ─── Insight Builder — Mobile Floating Button ─── */}
      <button
        onClick={() => setMobileDrawerOpen(true)}
        className="lg:hidden fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-accent-teal text-white shadow-lg hover:bg-accent-teal/90 transition-colors flex items-center justify-center"
        title="Open Insight Builder"
      >
        <Pin className="w-5 h-5" />
        {pinnedList.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-accent-red text-white text-[10px] font-bold flex items-center justify-center">
            {pinnedList.length}
          </span>
        )}
      </button>

      {/* ─── Insight Builder — Mobile Drawer ─── */}
      {mobileDrawerOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileDrawerOpen(false)}
          />
          {/* Drawer */}
          <div className="relative w-[340px] max-w-[85vw] bg-bg-secondary shadow-2xl animate-slide-in-right">
            <button
              onClick={() => setMobileDrawerOpen(false)}
              className="absolute top-3 right-3 z-10 p-1.5 text-text-muted hover:text-text-primary rounded-md hover:bg-bg-tertiary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            <InsightBuilder />
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Unified Feed Card Renderer ─────────────────────────

function FeedCard({ item, onPin, isItemPinned }: {
  item: FeedItem
  onPin: (contentType: PinnedItem['content_type'], id: string, title: string, data: PinnedItem['data']) => void
  isItemPinned: (id: string) => boolean
}) {
  switch (item.type) {
    case 'article':
      return <ArticleCard article={item.data} onPin={(a) => onPin('article', a.id, a.title, a)} isPinned={isItemPinned(item.data.id)} />
    case 'podcast_quote':
      return <PodcastQuoteCard quote={item.data} onPin={(q) => onPin('podcast_quote', q.quote_id, q.quote_text.slice(0, 80), q)} isPinned={isItemPinned(item.data.quote_id)} />
    case 'earnings_quote':
      return <EarningsQuoteCard quote={item.data} onPin={(q) => onPin('earnings_quote', q.quote_id, q.quote_text.slice(0, 80), q)} isPinned={isItemPinned(item.data.quote_id)} />
    case 'sec_nugget':
      return <SecNuggetCard nugget={item.data} onPin={(n) => onPin('sec_nugget', n.nugget_id, n.nugget_text.slice(0, 80), n)} isPinned={isItemPinned(item.data.nugget_id)} />
    case 'paper':
      return <PaperCard paper={item.data} onPin={(p) => onPin('paper', p.arxiv_id, p.title, p)} isPinned={isItemPinned(item.data.arxiv_id)} />
    case 'patent':
      return <PatentCard patent={item.data} onPin={(p) => onPin('patent', p.id, p.title, p)} isPinned={isItemPinned(item.data.id)} />
  }
}

// ─── Content Loading Skeletons ──────────────────────────

function ContentSkeletons() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="bg-bg-secondary border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="skeleton h-5 w-16" />
            <div className="skeleton h-5 w-12" />
          </div>
          <div className="skeleton h-5 w-3/4" />
          <div className="space-y-1.5">
            <div className="skeleton h-3.5 w-full" />
            <div className="skeleton h-3.5 w-5/6" />
          </div>
          <div className="flex items-center gap-2">
            <div className="skeleton h-4 w-20" />
            <div className="skeleton h-4 w-24" />
            <div className="skeleton h-4 w-16" />
          </div>
        </div>
      ))}
    </div>
  )
}
