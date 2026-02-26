/**
 * Markets Page
 * ============
 * Stock overview table + single-company deep-dive.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, SectionHeader, EmptyState } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import { TrendingUp, TrendingDown, Quote, ShieldAlert, ExternalLink } from 'lucide-react'
import type { Domain } from '../api'

export default function MarketsPage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const { data: overview, isLoading } = useQuery({
    queryKey: ['stocks-overview'],
    queryFn: api.getStockOverview,
  })

  const { data: detail } = useQuery({
    queryKey: ['stock-detail', selectedTicker, days],
    queryFn: () => api.getTickerDetail(selectedTicker!, days),
    enabled: !!selectedTicker,
  })

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Markets</h1>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Overview Table */}
      <div>
        <SectionHeader title="Market Overview" count={overview?.stocks?.length} />
        {isLoading ? (
          <div className="text-text-muted text-sm animate-pulse">Loading market data...</div>
        ) : overview?.stocks?.length ? (
          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-bg-tertiary text-text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-4 py-2">Ticker</th>
                  <th className="text-left px-4 py-2">Company</th>
                  <th className="text-right px-4 py-2">Close</th>
                  <th className="text-right px-4 py-2">Change %</th>
                  <th className="text-right px-4 py-2 hidden md:table-cell">Volume</th>
                  <th className="text-right px-4 py-2 hidden lg:table-cell">SMA-20</th>
                  <th className="text-right px-4 py-2 hidden lg:table-cell">SMA-50</th>
                </tr>
              </thead>
              <tbody>
                {overview.stocks.map(s => (
                  <tr
                    key={s.ticker}
                    onClick={() => setSelectedTicker(s.ticker)}
                    className={`border-t border-border cursor-pointer transition-colors ${selectedTicker === s.ticker
                        ? 'bg-accent-blue/5 border-l-2 border-l-accent-blue'
                        : 'hover:bg-bg-hover'
                      }`}
                  >
                    <td className="px-4 py-2.5 font-medium text-accent-blue">{s.ticker}</td>
                    <td className="px-4 py-2.5 text-text-secondary">{s.company}</td>
                    <td className="px-4 py-2.5 text-right">${s.close?.toFixed(2) ?? '–'}</td>
                    <td className={`px-4 py-2.5 text-right font-medium ${(s.change_percent ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
                      }`}>
                      <span className="inline-flex items-center gap-1">
                        {(s.change_percent ?? 0) >= 0
                          ? <TrendingUp className="w-3 h-3" />
                          : <TrendingDown className="w-3 h-3" />
                        }
                        {(s.change_percent ?? 0) >= 0 ? '+' : ''}{(s.change_percent ?? 0).toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-text-muted hidden md:table-cell">
                      {s.volume ? (s.volume / 1e6).toFixed(1) + 'M' : '–'}
                    </td>
                    <td className="px-4 py-2.5 text-right text-text-muted hidden lg:table-cell">
                      {s.sma_20?.toFixed(2) ?? '–'}
                    </td>
                    <td className="px-4 py-2.5 text-right text-text-muted hidden lg:table-cell">
                      {s.sma_50?.toFixed(2) ?? '–'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        ) : (
          <EmptyState message="No stock data available. Run the ingestion pipeline first." />
        )}
      </div>

      {/* Company Deep Dive */}
      {selectedTicker && detail && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-text-primary">{detail.ticker}</h2>
              <p className="text-sm text-text-muted">{detail.company} — {detail.focus}</p>
            </div>
            <div className="flex items-center bg-bg-tertiary rounded-lg border border-border">
              {[7, 30, 90].map(d => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${days === d
                      ? 'text-accent-blue bg-accent-blue/10'
                      : 'text-text-muted hover:text-text-secondary'
                    }`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>

          {/* Price History (simple table for now — Plotly chart in next phase) */}
          {detail.history?.length > 0 && (
            <Card className="p-4">
              <SectionHeader title="Price History" count={detail.history.length} />
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-text-muted">Latest Close</div>
                  <div className="text-lg font-bold">
                    ${detail.history[detail.history.length - 1]?.close?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-text-muted">Period High</div>
                  <div className="text-lg font-bold text-accent-green">
                    ${Math.max(...detail.history.map(h => h.high ?? 0)).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-text-muted">Period Low</div>
                  <div className="text-lg font-bold text-accent-red">
                    ${Math.min(...detail.history.filter(h => h.low).map(h => h.low!)).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-text-muted">SMA-20</div>
                  <div className="text-lg font-bold text-accent-orange">
                    ${detail.history[detail.history.length - 1]?.sma_20?.toFixed(2) ?? '–'}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Earnings Quotes */}
          {detail.quotes?.length > 0 && (
            <div>
              <SectionHeader title="Earnings Quotes" count={detail.quotes.length} />
              <div className="space-y-2">
                {detail.quotes.slice(0, 5).map(q => (
                  <Card key={q.quote_id} className="p-3">
                    <div className="flex items-start gap-2">
                      <Quote className="w-4 h-4 text-accent-purple flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm text-text-primary italic">"{q.quote_text}"</p>
                        <div className="text-xs text-text-muted mt-1">
                          {q.speaker_name} • {q.speaker_role.toUpperCase()} • Q{q.quarter} {q.year}
                          <span className={`ml-2 px-1.5 py-0.5 rounded ${q.confidence_level === 'definitive'
                              ? 'bg-accent-green/10 text-accent-green'
                              : 'bg-accent-yellow/10 text-accent-yellow'
                            }`}>
                            {q.confidence_level}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* SEC Nuggets */}
          {detail.nuggets?.length > 0 && (
            <div>
              <SectionHeader title="SEC Filings" count={detail.nuggets.length} />
              <div className="space-y-2">
                {detail.nuggets.slice(0, 5).map(n => (
                  <Card key={n.nugget_id} className="p-3">
                    <div className="flex items-start gap-2">
                      <ShieldAlert className={`w-4 h-4 flex-shrink-0 mt-0.5 ${n.is_new_disclosure ? 'text-accent-red' : 'text-accent-orange'
                        }`} />
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs text-text-muted">
                            {n.display_source ?? `${n.filing_type} FY${n.fiscal_year}`}
                          </span>
                          {n.is_new_disclosure && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-accent-red/10 text-accent-red">
                              NEW
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-text-primary">"{n.nugget_text}"</p>
                        <div className="flex gap-1 mt-1">
                          <span className="text-xs px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
                            {n.nugget_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
                            {n.section.replace(/_/g, ' ')}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Related Articles */}
          {detail.articles?.length > 0 && (
            <div>
              <SectionHeader title="Related News" count={detail.articles.length} />
              <div className="space-y-2">
                {detail.articles.map(a => (
                  <Card key={a.id} className="p-3">
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-text-primary hover:text-accent-blue transition-colors"
                    >
                      {a.title}
                      <ExternalLink className="inline w-3 h-3 ml-1 opacity-50" />
                    </a>
                    <div className="text-xs text-text-muted mt-1">
                      {a.source_name} • {a.category.replace(/_/g, ' ')}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
