/**
 * Research Page
 * =============
 * ArXiv papers with filters for type, readiness, and keyword search.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, SectionHeader, EmptyState } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import { ExternalLink, FileText, Search } from 'lucide-react'
import type { Domain } from '../api'

const PAPER_TYPES = ['breakthrough', 'incremental', 'review', 'theoretical']
const READINESS_LEVELS = ['near_term', 'mid_term', 'long_term', 'theoretical']

export default function ResearchPage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [days, setDays] = useState(30)
  const [paperType, setPaperType] = useState<string>('')
  const [readiness, setReadiness] = useState<string>('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['papers', domain, days, paperType, readiness, search],
    queryFn: () => api.getPapers({
      days,
      limit: 100,
      paper_type: paperType || undefined,
      readiness: readiness || undefined,
      search: search || undefined,
    }),
  })

  const papers = data?.papers ?? []

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Research</h1>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Paper Type */}
        <select
          value={paperType}
          onChange={e => setPaperType(e.target.value)}
          className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
        >
          <option value="">All Types</option>
          {PAPER_TYPES.map(t => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>

        {/* Readiness */}
        <select
          value={readiness}
          onChange={e => setReadiness(e.target.value)}
          className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
        >
          <option value="">All Readiness</option>
          {READINESS_LEVELS.map(r => (
            <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
          ))}
        </select>

        {/* Days */}
        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border">
          {[7, 30, 60, 90].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${days === d
                ? 'text-accent-blue bg-accent-blue/15'
                : 'text-text-muted hover:text-text-secondary'
                }`}
            >
              {d}d
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
            onKeyDown={e => { if (e.key === 'Enter') setSearch(searchInput) }}
            placeholder="Search papers..."
            className="bg-transparent text-sm text-text-primary placeholder-text-muted outline-none w-48"
          />
        </div>
      </div>

      {/* Results */}
      <SectionHeader title="Papers" count={papers.length} />

      {isLoading ? (
        <div className="text-text-muted text-sm animate-pulse">Loading papers...</div>
      ) : papers.length ? (
        <div className="space-y-3">
          {papers.map(p => (
            <Card key={p.arxiv_id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <a
                    href={p.abs_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-text-primary hover:text-accent-blue transition-colors leading-snug"
                  >
                    {p.title}
                    <ExternalLink className="inline w-3 h-3 ml-1 opacity-50" />
                  </a>

                  <div className="text-xs text-text-muted mt-1">
                    {p.authors?.slice(0, 5).join(', ')}
                    {(p.authors?.length ?? 0) > 5 && ` et al.`}
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {p.relevance_score && (
                      <span className="text-xs px-2 py-0.5 rounded bg-accent-cyan/15 text-accent-cyan">
                        {p.relevance_score}/10
                      </span>
                    )}
                    {p.paper_type && (
                      <span className={`text-xs px-2 py-0.5 rounded ${p.paper_type === 'breakthrough'
                        ? 'bg-accent-red/15 text-accent-red font-medium'
                        : 'bg-accent-blue/15 text-accent-blue'
                        }`}>
                        {p.paper_type}
                      </span>
                    )}
                    {p.commercial_readiness && (
                      <span className={`text-xs px-2 py-0.5 rounded ${p.commercial_readiness === 'near_term'
                        ? 'bg-accent-green/15 text-accent-green'
                        : 'bg-bg-tertiary text-text-muted'
                        }`}>
                        {p.commercial_readiness.replace(/_/g, ' ')}
                      </span>
                    )}
                    {p.categories?.slice(0, 3).map(c => (
                      <span key={c} className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
                        {c}
                      </span>
                    ))}
                  </div>

                  {/* Significance */}
                  {p.significance_summary && (
                    <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                      {p.significance_summary}
                    </p>
                  )}

                  {/* Abstract (collapsible) */}
                  {p.abstract && (
                    <details className="mt-2">
                      <summary className="text-xs text-accent-blue cursor-pointer hover:underline">
                        Show abstract
                      </summary>
                      <p className="text-sm text-text-muted mt-1 leading-relaxed">
                        {p.abstract}
                      </p>
                    </details>
                  )}
                </div>

                {/* PDF link */}
                {p.pdf_url && (
                  <a
                    href={p.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-text-muted hover:text-accent-blue transition-colors flex-shrink-0"
                    title="Download PDF"
                  >
                    <FileText className="w-5 h-5" />
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState message="No papers match your filters" />
      )}
    </div>
  )
}
