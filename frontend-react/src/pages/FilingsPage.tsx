/**
 * Filings Page
 * ============
 * SEC filings + Earnings calls in one tab with toggle.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, SectionHeader, EmptyState, LensChip } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import { Quote, ShieldAlert } from 'lucide-react'
import type { Domain } from '../api'

type Tab = 'sec' | 'earnings'

const NUGGET_TYPES = [
  'competitive_disclosure', 'risk_admission', 'technology_investment',
  'forward_guidance', 'quantum_readiness', 'material_change',
]

const QUOTE_TYPES = [
  'strategy', 'guidance', 'competitive', 'technology_milestone',
  'timeline_outlook', 'risk_factor', 'analyst_pressure', 'revenue_metric',
]

export default function FilingsPage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [tab, setTab] = useState<Tab>('sec')
  const [secTicker, setSecTicker] = useState('')
  const [secType, setSecType] = useState('')
  const [newOnly, setNewOnly] = useState(false)
  const [earningsTicker, setEarningsTicker] = useState('')
  const [quoteType, setQuoteType] = useState('')

  // SEC data
  const { data: secData, isLoading: secLoading } = useQuery({
    queryKey: ['sec-nuggets', secTicker, secType, newOnly],
    queryFn: () => api.getSecNuggets({
      ticker: secTicker || undefined,
      nugget_type: secType || undefined,
      new_only: newOnly || undefined,
    }),
    enabled: tab === 'sec',
  })

  // Earnings data
  const { data: earningsData, isLoading: earningsLoading } = useQuery({
    queryKey: ['earnings-quotes', earningsTicker, quoteType],
    queryFn: () => api.getEarningsQuotes({
      ticker: earningsTicker || undefined,
      quote_type: quoteType || undefined,
    }),
    enabled: tab === 'earnings',
  })

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Filings</h1>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Tab Toggle */}
      <div className="flex gap-2">
        <LensChip label="SEC Filings" active={tab === 'sec'} onClick={() => setTab('sec')} />
        <LensChip label="Earnings Calls" active={tab === 'earnings'} onClick={() => setTab('earnings')} />
      </div>

      {/* ─── SEC Tab ─── */}
      {tab === 'sec' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              value={secTicker}
              onChange={e => setSecTicker(e.target.value.toUpperCase())}
              placeholder="Ticker (e.g. IONQ)"
              className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue w-32"
            />
            <select
              value={secType}
              onChange={e => setSecType(e.target.value)}
              className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
            >
              <option value="">All Types</option>
              {NUGGET_TYPES.map(t => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={newOnly}
                onChange={e => setNewOnly(e.target.checked)}
                className="rounded border-border bg-bg-tertiary"
              />
              New disclosures only
            </label>
          </div>

          <SectionHeader title="SEC Nuggets" count={secData?.count} />

          {secLoading ? (
            <div className="text-text-muted text-sm animate-pulse">Loading SEC data...</div>
          ) : (secData?.nuggets?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              {secData!.nuggets.map(n => (
                <Card key={n.nugget_id} className="p-4">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className={`w-5 h-5 flex-shrink-0 mt-0.5 ${n.is_new_disclosure ? 'text-accent-red' : 'text-accent-orange'
                      }`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-medium text-accent-blue">{n.ticker}</span>
                        <span className="text-xs text-text-muted">
                          {n.display_source ?? `${n.filing_type} FY${n.fiscal_year}`}
                        </span>
                        {n.is_new_disclosure && (
                          <span className="text-xs px-2 py-0.5 rounded bg-accent-red/15 text-accent-red font-medium">
                            NEW DISCLOSURE
                          </span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded ${n.risk_level === 'high'
                          ? 'bg-accent-red/15 text-accent-red'
                          : 'bg-bg-tertiary text-text-muted'
                          }`}>
                          {n.risk_level} risk
                        </span>
                      </div>
                      <p className="text-sm text-text-primary leading-relaxed">
                        "{n.nugget_text}"
                      </p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-accent-purple/15 text-accent-purple">
                          {n.nugget_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
                          {n.section.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
                          {n.signal_strength}
                        </span>
                        {n.competitors_named?.filter(Boolean).length > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded bg-accent-cyan/15 text-accent-cyan">
                            names: {n.competitors_named.filter(Boolean).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState message="No SEC nuggets match your filters" />
          )}
        </div>
      )}

      {/* ─── Earnings Tab ─── */}
      {tab === 'earnings' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              value={earningsTicker}
              onChange={e => setEarningsTicker(e.target.value.toUpperCase())}
              placeholder="Ticker (e.g. IBM)"
              className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue w-32"
            />
            <select
              value={quoteType}
              onChange={e => setQuoteType(e.target.value)}
              className="bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue"
            >
              <option value="">All Quote Types</option>
              {QUOTE_TYPES.map(t => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <SectionHeader title="Earnings Quotes" count={earningsData?.count} />

          {earningsLoading ? (
            <div className="text-text-muted text-sm animate-pulse">Loading earnings data...</div>
          ) : (earningsData?.quotes?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              {earningsData!.quotes.map(q => (
                <Card key={q.quote_id} className="p-4">
                  <div className="flex items-start gap-3">
                    <Quote className="w-5 h-5 text-accent-purple flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-medium text-accent-blue">{q.ticker}</span>
                        <span className="text-xs text-text-muted">
                          {q.company_name} • Q{q.quarter} {q.year}
                        </span>
                      </div>
                      <p className="text-sm text-text-primary leading-relaxed italic">
                        "{q.quote_text}"
                      </p>
                      <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
                        <span className="font-medium text-text-secondary">{q.speaker_name}</span>
                        <span>•</span>
                        <span className="uppercase">{q.speaker_role}</span>
                        <span>•</span>
                        <span>{q.section.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        <span className="text-xs px-2 py-0.5 rounded bg-accent-purple/15 text-accent-purple">
                          {q.quote_type.replace(/_/g, ' ')}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${q.confidence_level === 'definitive'
                          ? 'bg-accent-green/15 text-accent-green'
                          : q.confidence_level === 'hedged'
                            ? 'bg-accent-red/15 text-accent-red'
                            : 'bg-accent-yellow/15 text-accent-yellow'
                          }`}>
                          {q.confidence_level}
                        </span>
                        {q.sentiment && q.sentiment !== 'neutral' && (
                          <span className={`text-xs px-2 py-0.5 rounded ${q.sentiment === 'bullish'
                            ? 'bg-accent-green/15 text-accent-green'
                            : 'bg-accent-red/15 text-accent-red'
                            }`}>
                            {q.sentiment}
                          </span>
                        )}
                        <span className="text-xs text-text-muted">●{q.relevance_score.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState message="No earnings quotes match your filters" />
          )}
        </div>
      )}
    </div>
  )
}
