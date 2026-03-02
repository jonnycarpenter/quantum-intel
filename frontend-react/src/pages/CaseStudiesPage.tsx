/**
 * Case Studies Page
 * =================
 * Browse extracted case studies — real-world deployments, outcomes, and
 * implementation narratives grounded in source material.
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Quote } from 'lucide-react'
import { api } from '../api'
import type { Domain, CaseStudy } from '../api'
import { Card, SectionHeader, StatCard, EmptyState, TagChip } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import CompanyLogo from '../components/CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'

// ─── Readiness Level Styles ─────────────────────────────

const READINESS_STYLES: Record<string, string> = {
  production: 'bg-accent-green/15 text-accent-green',
  pilot: 'bg-accent-blue/15 text-accent-blue',
  announced: 'bg-accent-purple/15 text-accent-purple',
  research: 'bg-accent-yellow/15 text-accent-yellow',
  theoretical: 'bg-bg-tertiary text-text-muted',
}

const SOURCE_LABELS: Record<string, string> = {
  article: 'Article',
  podcast: 'Podcast',
  earnings: 'Earnings Call',
  sec_filing: 'SEC Filing',
  arxiv: 'ArXiv Paper',
}

const selectClass =
  'bg-bg-tertiary text-text-secondary text-sm rounded-lg px-3 py-1.5 border border-border outline-none focus:border-accent-blue'

// ─── CaseStudyCard ──────────────────────────────────────

function CaseStudyCard({ cs }: { cs: CaseStudy }) {
  const readinessStyle = READINESS_STYLES[cs.readiness_level] ?? READINESS_STYLES.theoretical

  return (
    <Card className="p-4">
      {/* Outcome metric highlight */}
      {cs.outcome_metric && (
        <div
          className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium mb-3 ${
            cs.outcome_quantified
              ? 'bg-accent-teal/15 text-accent-teal'
              : 'bg-bg-tertiary text-text-secondary'
          }`}
        >
          {cs.outcome_metric}
        </div>
      )}

      {/* Badge row */}
      <div className="flex flex-wrap items-center gap-2 mb-1.5">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-accent-blue">
          <CompanyLogo companyName={cs.company} domain={companyNameToDomain(cs.company)} size={16} />
          {cs.company}
        </span>
        {cs.industry && <span className="text-xs text-text-muted">{cs.industry}</span>}
        <span className={`text-xs px-2 py-0.5 rounded ${readinessStyle}`}>
          {cs.readiness_level}
        </span>
        {cs.outcome_type && (
          <span className="text-xs px-2 py-0.5 rounded bg-accent-purple/15 text-accent-purple">
            {cs.outcome_type.replace(/_/g, ' ')}
          </span>
        )}
        <span className="text-xs px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
          {SOURCE_LABELS[cs.source_type] ?? cs.source_type}
        </span>
        <span className="text-xs text-text-muted">
          {cs.relevance_score.toFixed(2)}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-medium text-text-primary leading-snug">
        {cs.use_case_title}
      </h3>

      {/* Summary */}
      {cs.use_case_summary && (
        <p className="text-sm text-text-secondary leading-relaxed mt-1.5">
          {cs.use_case_summary}
        </p>
      )}

      {/* Tech stack */}
      {cs.technology_stack?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {cs.technology_stack.map((t) => (
            <TagChip key={t} label={t} variant="purple" />
          ))}
        </div>
      )}

      {/* Expandable details */}
      <details className="mt-3">
        <summary className="text-xs text-accent-blue cursor-pointer hover:underline">
          Show details
        </summary>
        <div className="mt-2 space-y-3">
          {/* Grounding quote */}
          <div className="border-l-2 border-accent-teal pl-4 py-1">
            <Quote className="w-4 h-4 text-text-muted mb-1" />
            <p className="text-sm text-text-primary leading-relaxed italic">
              &ldquo;{cs.grounding_quote}&rdquo;
            </p>
            {cs.speaker && (
              <div className="text-xs text-text-muted mt-1">
                <span className="font-medium text-text-secondary">{cs.speaker}</span>
                {cs.speaker_role && <span> — {cs.speaker_role}</span>}
                {cs.speaker_company && <span>, {cs.speaker_company}</span>}
              </div>
            )}
          </div>

          {/* Implementation details */}
          {(cs.implementation_detail || cs.scale || cs.timeline || cs.department) && (
            <div className="text-sm text-text-secondary space-y-1">
              {cs.implementation_detail && <p>{cs.implementation_detail}</p>}
              <div className="flex flex-wrap gap-3 text-xs text-text-muted">
                {cs.department && <span>Dept: {cs.department}</span>}
                {cs.scale && <span>Scale: {cs.scale}</span>}
                {cs.timeline && <span>Timeline: {cs.timeline}</span>}
              </div>
            </div>
          )}

          {/* Quantum-specific */}
          {cs.domain === 'quantum' &&
            (cs.qubit_type || cs.gate_fidelity || cs.commercial_viability || cs.scientific_significance) && (
              <div className="flex flex-wrap gap-1.5">
                {cs.qubit_type && <TagChip label={`Qubit: ${cs.qubit_type}`} variant="cyan" />}
                {cs.gate_fidelity && <TagChip label={cs.gate_fidelity} variant="cyan" />}
                {cs.commercial_viability && <TagChip label={cs.commercial_viability} variant="green" />}
                {cs.scientific_significance && (
                  <p className="text-xs text-text-muted w-full mt-1">{cs.scientific_significance}</p>
                )}
              </div>
            )}

          {/* AI-specific */}
          {cs.domain === 'ai' &&
            (cs.ai_model_used || cs.roi_metric || cs.deployment_type) && (
              <div className="flex flex-wrap gap-1.5">
                {cs.ai_model_used && <TagChip label={`Model: ${cs.ai_model_used}`} variant="purple" />}
                {cs.deployment_type && <TagChip label={cs.deployment_type} />}
                {cs.roi_metric && (
                  <span className="text-xs px-2 py-0.5 rounded bg-accent-green/15 text-accent-green">
                    ROI: {cs.roi_metric}
                  </span>
                )}
              </div>
            )}
        </div>
      </details>
    </Card>
  )
}

// ─── Page Component ─────────────────────────────────────

export default function CaseStudiesPage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const [sourceType, setSourceType] = useState('')
  const [readinessLevel, setReadinessLevel] = useState('')
  const [outcomeType, setOutcomeType] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  // Reset filters on domain change
  useEffect(() => {
    setSourceType('')
    setReadinessLevel('')
    setOutcomeType('')
    setSearch('')
    setSearchInput('')
  }, [domain])

  // Stats for dashboard
  const { data: statsData } = useQuery({
    queryKey: ['case-study-stats', domain],
    queryFn: () => api.getCaseStudyStats(domain),
  })

  // Case study list
  const { data, isLoading } = useQuery({
    queryKey: ['case-studies', domain, sourceType, readinessLevel, outcomeType, search],
    queryFn: () =>
      api.getCaseStudies({
        domain,
        source_type: sourceType || undefined,
        readiness_level: readinessLevel || undefined,
        outcome_type: outcomeType || undefined,
        search: search || undefined,
        limit: 100,
      }),
  })

  const caseStudies = data?.case_studies ?? []
  const stats = statsData

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-text-primary">Case Studies</h1>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Stats Dashboard */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Total Case Studies" value={stats.total} />
          <StatCard
            label="Quantified Outcomes"
            value={stats.quantified_outcomes}
            color="text-accent-teal"
          />
          <StatCard
            label="Production Ready"
            value={stats.by_readiness?.production ?? 0}
            color="text-accent-green"
          />
          <StatCard
            label="Companies"
            value={stats.unique_companies}
            color="text-accent-blue"
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          className={selectClass}
        >
          <option value="">All Sources</option>
          {['article', 'podcast', 'earnings', 'sec_filing', 'arxiv'].map((s) => (
            <option key={s} value={s}>
              {SOURCE_LABELS[s] ?? s}
            </option>
          ))}
        </select>

        <select
          value={readinessLevel}
          onChange={(e) => setReadinessLevel(e.target.value)}
          className={selectClass}
        >
          <option value="">All Readiness</option>
          {['production', 'pilot', 'announced', 'research', 'theoretical'].map((r) => (
            <option key={r} value={r}>
              {r.charAt(0).toUpperCase() + r.slice(1)}
            </option>
          ))}
        </select>

        <select
          value={outcomeType}
          onChange={(e) => setOutcomeType(e.target.value)}
          className={selectClass}
        >
          <option value="">All Outcomes</option>
          {[
            'efficiency',
            'revenue',
            'accuracy',
            'scale',
            'cost_reduction',
            'speed',
            'risk_reduction',
            'scientific',
            'competitive',
            'partnership',
            'regulatory',
            'other',
          ].map((o) => (
            <option key={o} value={o}>
              {o.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>

        <div className="flex items-center bg-bg-tertiary rounded-lg border border-border px-3 py-1.5 gap-2">
          <Search className="w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') setSearch(searchInput)
            }}
            placeholder="Search case studies..."
            className="bg-transparent text-sm text-text-primary placeholder-text-muted outline-none w-48"
          />
        </div>
      </div>

      {/* Results */}
      <SectionHeader title="Case Studies" count={caseStudies.length} />

      {isLoading ? (
        <div className="text-text-muted text-sm animate-pulse">Loading case studies...</div>
      ) : caseStudies.length ? (
        <div className="space-y-3">
          {caseStudies.map((cs) => (
            <CaseStudyCard key={cs.case_study_id} cs={cs} />
          ))}
        </div>
      ) : (
        <EmptyState message="No case studies found. Run: python scripts/run_case_studies.py --domain quantum" />
      )}
    </div>
  )
}
