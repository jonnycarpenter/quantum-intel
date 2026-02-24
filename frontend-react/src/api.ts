/**
 * API Client
 * ==========
 * Typed fetch wrappers for all backend endpoints.
 */

const BASE = '/api'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

// ─── Types ─────────────────────────────────────────────

export interface Article {
  id: string
  url: string
  title: string
  source_name: string
  source_type: string
  published_at: string | null
  summary: string
  key_takeaway: string
  category: string
  priority: string
  relevance_score: number
  sentiment: string
  companies_mentioned: string[]
  technologies_mentioned: string[]
  people_mentioned: string[]
  use_case_domains: string[]
  confidence: number
  domain?: string
}

export interface DigestData {
  id: string
  created_at: string
  period_hours: number
  executive_summary: string
  items: DigestItem[]
  total_items: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
}

export interface DigestItem {
  id: string
  title: string
  source_name: string
  url: string
  summary: string
  category: string
  priority: string
  relevance_score: number
  published_at: string | null
  companies_mentioned: string[]
  technologies_mentioned: string[]
}

export interface BriefingData {
  digest: { executive_summary: string | null; created_at: string | null }
  priority_counts: Record<string, number>
  top_stories: Article[]
  market_pulse: StockOverview[]
  exec_voices: ExecQuote[]
  regulatory: RegulatoryNugget[]
  papers: PaperBrief[]
}

export interface StockOverview {
  ticker: string
  company?: string
  focus?: string
  close: number | null
  change_percent: number | null
  volume: number | null
  sma_20?: number | null
  sma_50?: number | null
  market_cap?: number | null
  date: string
}

export interface StockDetail {
  ticker: string
  company: string
  focus: string
  history: StockDataPoint[]
  articles: Article[]
  quotes: EarningsQuote[]
  nuggets: SecNuggetDisplay[]
}

export interface StockDataPoint {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
  change_percent: number | null
  sma_20: number | null
  sma_50: number | null
}

export interface Paper {
  arxiv_id: string
  title: string
  authors: string[]
  abstract: string
  categories: string[]
  published_at: string | null
  pdf_url: string | null
  abs_url: string
  relevance_score: number | null
  paper_type: string | null
  commercial_readiness: string | null
  significance_summary: string | null
}

export interface PaperBrief {
  arxiv_id: string
  title: string
  authors: string[]
  relevance_score: number | null
  paper_type: string | null
  commercial_readiness: string | null
  significance_summary: string | null
  abs_url: string
}

export interface EarningsQuote {
  quote_id: string
  quote_text: string
  speaker_name: string
  speaker_role: string
  speaker_title?: string
  ticker: string
  company_name: string
  year: number
  quarter: number
  quote_type: string
  confidence_level: string
  sentiment: string
  section: string
  themes: string[]
  relevance_score: number
  is_quotable?: boolean
  companies_mentioned: string[]
  technologies_mentioned: string[]
  competitors_mentioned: string[]
}

export interface ExecQuote {
  quote_text: string
  speaker_name: string
  speaker_role: string
  ticker: string
  company_name: string
  year: number
  quarter: number
  quote_type: string
  confidence_level: string
  relevance_score: number
}

export interface SecNuggetDisplay {
  nugget_id: string
  nugget_text: string
  filing_type: string
  section: string
  nugget_type: string
  themes: string[]
  signal_strength: string
  ticker: string
  company_name: string
  fiscal_year: number
  fiscal_quarter: number | null
  filing_date: string | null
  competitors_named: string[]
  risk_level: string
  is_new_disclosure: boolean
  relevance_score: number
  is_actionable: boolean
  display_source?: string
}

export interface RegulatoryNugget {
  nugget_text: string
  ticker: string
  company_name: string
  filing_type: string
  section: string
  nugget_type: string
  signal_strength: string
  is_new_disclosure: boolean
  relevance_score: number
  fiscal_year: number
}

// ─── Weekly Briefing Types ────────────────────────────

export interface WeeklyBriefingVoiceQuote {
  text: string
  speaker: string
  role: string
  company: string
  source_type: string  // "earnings" | "sec" | "podcast"
  source_context: string
  relevance_score: number
}

export interface WeeklyBriefingCitation {
  number: number
  article_id: string
  title: string
  url: string
  source_name: string
  published_at: string | null
}

export interface WeeklyBriefingSection {
  section_id: string
  header: string
  priority_tag: string   // "P1"..."P5"
  priority_label: string // e.g. "Quantum Advantage"
  narrative: string      // Markdown with inline [1], [2] citations
  voice_quotes: WeeklyBriefingVoiceQuote[]
  citations: WeeklyBriefingCitation[]
  has_content: boolean
}

export interface WeeklyBriefingMarketMover {
  ticker: string
  company_name: string
  close: number | null
  change_pct: number
  context_text: string
  linked_article_ids: string[]
}

export interface WeeklyBriefingPaper {
  arxiv_id: string
  title: string
  authors: string[]
  why_it_matters: string
  commercial_readiness: string | null
  relevance_score: number | null
  abs_url: string
}

export interface WeeklyBriefingData {
  id: string
  domain: string
  week_of: string
  created_at: string
  sections: WeeklyBriefingSection[]
  market_movers: WeeklyBriefingMarketMover[]
  research_papers: WeeklyBriefingPaper[]
  articles_analyzed: number
  sections_active: number
  sections_total: number
  generation_cost_usd: number
  pre_brief_id: string | null
}

export interface SystemStats {
  stats: {
    total_articles: number
    by_category: Record<string, number>
    by_priority: Record<string, number>
    by_source: Record<string, number>
    avg_relevance: number
    hours: number
  }
  embeddings_count: number
  api_keys: Record<string, boolean>
  storage_backend: string
  db_path: string
}

// ─── API Functions ─────────────────────────────────────

export type Domain = 'quantum' | 'ai'

export const api = {
  // Briefing
  getBriefing: (domain?: Domain) =>
    fetchJson<BriefingData>(`/digest/briefing${domain ? '?domain=' + domain : ''}`),
  getDigest: () => fetchJson<{ digest: DigestData | null }>('/digest'),

  // Weekly Briefing
  getWeeklyBriefing: (domain?: Domain, week?: string) => {
    const sp = new URLSearchParams()
    if (domain) sp.set('domain', domain)
    if (week) sp.set('week', week)
    const qs = sp.toString()
    return fetchJson<{ briefing: WeeklyBriefingData | null }>(
      `/digest/weekly-briefing${qs ? '?' + qs : ''}`
    )
  },

  // Articles
  getArticles: (params?: {
    hours?: number
    limit?: number
    category?: string
    priority?: string
    search?: string
    source_type?: string
    domain?: Domain
  }) => {
    const sp = new URLSearchParams()
    if (params?.hours) sp.set('hours', String(params.hours))
    if (params?.limit) sp.set('limit', String(params.limit))
    if (params?.category) sp.set('category', params.category)
    if (params?.priority) sp.set('priority', params.priority)
    if (params?.search) sp.set('search', params.search)
    if (params?.source_type) sp.set('source_type', params.source_type)
    if (params?.domain) sp.set('domain', params.domain)
    const qs = sp.toString()
    return fetchJson<{ articles: Article[]; count: number }>(`/articles${qs ? '?' + qs : ''}`)
  },

  getCategoryCounts: (hours?: number, domain?: Domain) => {
    const sp = new URLSearchParams()
    if (hours) sp.set('hours', String(hours))
    if (domain) sp.set('domain', domain)
    const qs = sp.toString()
    return fetchJson<{ categories: Record<string, number>; total: number }>(
      `/articles/categories${qs ? '?' + qs : ''}`
    )
  },

  getPriorityCounts: (hours?: number, domain?: Domain) => {
    const sp = new URLSearchParams()
    if (hours) sp.set('hours', String(hours))
    if (domain) sp.set('domain', domain)
    const qs = sp.toString()
    return fetchJson<{ priorities: Record<string, number>; total: number }>(
      `/articles/priorities${qs ? '?' + qs : ''}`
    )
  },

  // Stocks
  getStockOverview: () =>
    fetchJson<{ stocks: StockOverview[]; groups: Record<string, string[]> }>('/stocks'),

  getTickerDetail: (ticker: string, days?: number) =>
    fetchJson<StockDetail>(`/stocks/${ticker}${days ? '?days=' + days : ''}`),

  // Papers
  getPapers: (params?: {
    days?: number
    limit?: number
    paper_type?: string
    readiness?: string
    search?: string
  }) => {
    const sp = new URLSearchParams()
    if (params?.days) sp.set('days', String(params.days))
    if (params?.limit) sp.set('limit', String(params.limit))
    if (params?.paper_type) sp.set('paper_type', params.paper_type)
    if (params?.readiness) sp.set('readiness', params.readiness)
    if (params?.search) sp.set('search', params.search)
    const qs = sp.toString()
    return fetchJson<{ papers: Paper[]; count: number }>(`/papers${qs ? '?' + qs : ''}`)
  },

  // Earnings
  getEarningsQuotes: (params?: { ticker?: string; quote_type?: string; confidence?: string }) => {
    const sp = new URLSearchParams()
    if (params?.ticker) sp.set('ticker', params.ticker)
    if (params?.quote_type) sp.set('quote_type', params.quote_type)
    if (params?.confidence) sp.set('confidence', params.confidence)
    const qs = sp.toString()
    return fetchJson<{ quotes: EarningsQuote[]; count: number }>(`/earnings${qs ? '?' + qs : ''}`)
  },

  // SEC
  getSecNuggets: (params?: {
    ticker?: string
    nugget_type?: string
    signal_strength?: string
    new_only?: boolean
  }) => {
    const sp = new URLSearchParams()
    if (params?.ticker) sp.set('ticker', params.ticker)
    if (params?.nugget_type) sp.set('nugget_type', params.nugget_type)
    if (params?.signal_strength) sp.set('signal_strength', params.signal_strength)
    if (params?.new_only) sp.set('new_only', 'true')
    const qs = sp.toString()
    return fetchJson<{ nuggets: SecNuggetDisplay[]; count: number }>(`/sec${qs ? '?' + qs : ''}`)
  },

  // Stats
  getStats: () => fetchJson<SystemStats>('/stats'),
}
