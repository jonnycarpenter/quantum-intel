/**
 * Settings Page
 * =============
 * System status, API key status, storage info, about.
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, SectionHeader } from '../components/ui'
import { Server, Key, Database, Info, CheckCircle, XCircle, RefreshCw } from 'lucide-react'

interface Props {
  domain: string
}

function StatusDot({ ok }: { ok: boolean }) {
  return ok
    ? <CheckCircle className="w-4 h-4 text-accent-green" />
    : <XCircle className="w-4 h-4 text-accent-red" />
}

export default function SettingsPage({ domain }: Props) {
  const { data: stats, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
  })

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Settings & Status</h1>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 text-sm text-accent-blue hover:text-accent-cyan transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="text-text-muted text-sm animate-pulse">Loading system status...</div>
      )}

      {stats && (
        <>
          {/* ─── System Health ─── */}
          <section>
            <SectionHeader title="System Health" icon={<Server className="w-4 h-4" />} />
            <Card className="p-4 mt-2">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-text-muted mb-1">Articles</div>
                  <div className="text-lg font-semibold text-text-primary">{stats.stats.total_articles.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-xs text-text-muted mb-1">By Priority</div>
                  <div className="text-lg font-semibold text-text-primary">{Object.values(stats.stats.by_priority).reduce((a, b) => a + b, 0).toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-xs text-text-muted mb-1">Embeddings</div>
                  <div className="text-lg font-semibold text-text-primary">{stats.embeddings_count.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-xs text-text-muted mb-1">Avg Relevance</div>
                  <div className="text-lg font-semibold text-text-primary">{stats.stats.avg_relevance.toFixed(2)}</div>
                </div>
              </div>
            </Card>
          </section>

          {/* ─── API Keys ─── */}
          <section>
            <SectionHeader title="API Keys" icon={<Key className="w-4 h-4" />} />
            <Card className="p-4 mt-2">
              <div className="space-y-3">
                {Object.entries(stats.api_keys).map(([key, active]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm text-text-secondary font-mono">{key}</span>
                    <StatusDot ok={active as boolean} />
                  </div>
                ))}
              </div>
            </Card>
          </section>

          {/* ─── Storage ─── */}
          <section>
            <SectionHeader title="Storage" icon={<Database className="w-4 h-4" />} />
            <Card className="p-4 mt-2">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Backend</span>
                  <span className="text-sm text-text-primary font-medium">
                    {stats.storage_backend ?? 'SQLite'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Database Path</span>
                  <span className="text-sm text-text-secondary font-mono truncate max-w-[60%]">
                    {stats.db_path ?? 'data/quantum_intel.db'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">Embeddings Path</span>
                  <span className="text-sm text-text-secondary font-mono truncate max-w-[60%]">
                    data/embeddings
                  </span>
                </div>
              </div>
            </Card>
          </section>

          {/* ─── About ─── */}
          <section>
            <SectionHeader title="About" icon={<Info className="w-4 h-4" />} />
            <Card className="p-4 mt-2">
              <div className="space-y-2 text-sm text-text-secondary">
                <p>
                  <span className="text-text-muted">Version:</span>{' '}
                  <span className="text-text-primary font-medium">0.5.0</span>
                </p>
                <p>
                  <span className="text-text-muted">Stack:</span>{' '}
                  FastAPI + React + SQLite + ChromaDB
                </p>
                <p>
                  <span className="text-text-muted">Domain:</span>{' '}
                  <span className="capitalize text-text-primary">{domain}</span> Intelligence
                </p>
                <p className="text-text-muted text-xs mt-3">
                  Quantum Intelligence Hub — Multi-agent AI system monitoring the quantum computing ecosystem.
                </p>
              </div>
            </Card>
          </section>
        </>
      )}
    </div>
  )
}
