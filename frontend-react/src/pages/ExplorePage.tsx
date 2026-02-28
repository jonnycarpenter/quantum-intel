/**
 * Explore Page
 * ============
 * Browse all content with lens presets and filters.
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { Domain } from '../api'
import ArticleCard from '../components/ArticleCard'
import DomainToggle from '../components/DomainToggle'
import { SectionHeader, EmptyState, LensChip } from '../components/ui'
import { Search } from 'lucide-react'

// Lens presets: domain-aware
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

export default function ExplorePage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [activeLens, setActiveLens] = useState(0)
  const [category, setCategory] = useState<string>('')
  const [priority, setPriority] = useState<string>('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [hours, setHours] = useState(168)

  // Reset filters when domain changes
  useEffect(() => {
    setActiveLens(0)
    setCategory('')
  }, [domain])

  // Domain-aware lenses and categories
  const lenses = domain === 'ai' ? AI_LENSES : QUANTUM_LENSES
  const categories = domain === 'ai' ? AI_CATEGORIES : QUANTUM_CATEGORIES

  // Build query params
  const queryCategory = activeLens > 0 ? undefined : (category || undefined)
  const queryPriority = priority || undefined

  const { data, isLoading } = useQuery({
    queryKey: ['articles', domain, hours, queryCategory, queryPriority, search],
    queryFn: () => api.getArticles({
      hours,
      limit: 200,
      category: queryCategory,
      priority: queryPriority,
      search: search || undefined,
      domain,
    }),
  })

  // Apply lens-based filtering on the client side
  let articles = data?.articles ?? []
  if (activeLens > 0 && lenses[activeLens].categories) {
    const cats = new Set(lenses[activeLens].categories)
    articles = articles.filter(a => cats.has(a.category))
  }

  const handleSearch = () => {
    setSearch(searchInput)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Explore</h1>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Lens Chips */}
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

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Category dropdown (only when "All" lens) */}
        {activeLens === 0 && (
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

        {/* Priority */}
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

        {/* Time range */}
        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border">
          {TIME_RANGES.map(tr => (
            <button
              key={tr.hours}
              onClick={() => setHours(tr.hours)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${hours === tr.hours
                  ? 'text-accent-blue bg-accent-blue/15'
                  : 'text-text-muted hover:text-text-secondary'
                }`}
            >
              {tr.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border px-3 py-1.5 gap-2">
          <Search className="w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search articles..."
            className="bg-transparent text-sm text-text-primary placeholder-text-muted outline-none w-48"
          />
        </div>
      </div>

      {/* Results */}
      <SectionHeader title="Articles" count={articles.length} />

      {isLoading ? (
        <div className="text-text-muted text-sm animate-pulse">Loading articles...</div>
      ) : articles.length ? (
        <div className="space-y-3">
          {articles.map(article => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      ) : (
        <EmptyState message="No articles match your filters" />
      )}
    </div>
  )
}
