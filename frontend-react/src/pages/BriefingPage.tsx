/**
 * Briefing Page
 * =============
 * Synthesized weekly intelligence briefing — narrative sections mapped to
 * strategic priorities, with voice enrichment, citations, market movers,
 * and research frontier. Powered by the 2-agent pipeline.
 */

import { useState, useMemo, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api'
import type {
  Domain,
  WeeklyBriefingData,
  WeeklyBriefingSection,
  WeeklyBriefingVoiceQuote,
  WeeklyBriefingCitation,
} from '../api'
import { Card, EmptyState } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import { RadarWidget } from '../components/RadarWidget'
import CompanyLogo from '../components/CompanyLogo'
import { companyNameToDomain, findInlineLogos } from '../utils/logoUtils'
import { Quote, ExternalLink, TrendingUp, TrendingDown, BookOpen } from 'lucide-react'

// ─── Priority Tag Styles ──────────────────────────────

const PRIORITY_TAG_COLORS: Record<string, string> = {
  P1: 'bg-accent-cyan/20 text-accent-cyan border-accent-cyan/35',
  P2: 'bg-accent-blue/20 text-accent-blue border-accent-blue/35',
  P3: 'bg-accent-purple/20 text-accent-purple border-accent-purple/35',
  P4: 'bg-accent-green/20 text-accent-green border-accent-green/35',
  P5: 'bg-accent-orange/20 text-accent-orange border-accent-orange/35',
}

const VOICE_BORDER_COLORS: Record<string, string> = {
  earnings: 'border-l-accent-purple',
  sec: 'border-l-accent-orange',
  podcast: 'border-l-accent-cyan',
}

const VOICE_LABELS: Record<string, string> = {
  earnings: 'Earnings Call',
  sec: 'SEC Filing',
  podcast: 'Podcast',
}

// ─── Helpers ──────────────────────────────────────────

/**
 * Inject styled citation badges into plain text.
 * Replaces [1], [2] etc. with styled clickable spans.
 */
function injectCitations(text: string, sectionId: string): ReactNode[] {
  const parts = text.split(/(\[\d+\])/)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) {
      return (
        <a
          key={i}
          href={`#sources-${sectionId}`}
          className="inline-flex items-center justify-center w-5 h-5 mx-0.5 rounded text-[10px] font-bold
                     bg-accent-blue/20 text-accent-blue hover:bg-accent-blue/30 transition-colors
                     align-super leading-none no-underline"
        >
          {match[1]}
        </a>
      )
    }
    return part ? <span key={i}>{part}</span> : null
  })
}

/**
 * Render narrative markdown with:
 * - ### sub-headlines styled as story dividers
 * - **bold** for lead sentences
 * - [N] citation badges as interactive links
 * - Proper paragraph spacing for scannability
 */
function NarrativeRenderer({ text, sectionId }: { text: string; sectionId: string }) {
  // Memoize the custom components to avoid re-creating on every render
  const components = useMemo(() => ({
    // Sub-headlines within a section — render as styled story dividers
    h3: ({ children }: { children?: ReactNode }) => (
      <h4 className="text-sm font-semibold text-text-primary mt-5 mb-2 pt-3 border-t border-border/40 first:mt-0 first:pt-0 first:border-t-0">
        {children}
      </h4>
    ),
    // Paragraphs — inject citation badges into text content
    p: ({ children }: { children?: ReactNode }) => {
      const processed = processChildren(children, sectionId)
      return <p className="mb-3 last:mb-0">{processed}</p>
    },
    // Bold — used for lead sentences
    strong: ({ children }: { children?: ReactNode }) => (
      <strong className="font-semibold text-text-primary">{children}</strong>
    ),
    // Prevent any h1/h2 from disrupting the layout (shouldn't appear, but safety)
    h1: ({ children }: { children?: ReactNode }) => (
      <h4 className="text-sm font-semibold text-text-primary mt-4 mb-2">{children}</h4>
    ),
    h2: ({ children }: { children?: ReactNode }) => (
      <h4 className="text-sm font-semibold text-text-primary mt-4 mb-2">{children}</h4>
    ),
  }), [sectionId])

  return (
    <div className="text-sm text-text-secondary leading-relaxed briefing-narrative">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  )
}

/**
 * Split a text string at known company names and inject inline logo chips.
 * Returns an array of ReactNode (strings + logo elements).
 */
function injectInlineLogos(text: string): ReactNode[] {
  const matches = findInlineLogos(text)
  if (matches.length === 0) return [text]

  const parts: ReactNode[] = []
  let cursor = 0
  matches.forEach((m, i) => {
    // Text before this match
    if (m.index > cursor) {
      parts.push(text.slice(cursor, m.index))
    }
    // The company name with inline logo
    parts.push(
      <span key={`logo-${i}`} className="inline-flex items-center gap-0.5">
        <CompanyLogo domain={m.domain} companyName={m.name} size={14} className="inline-block -mt-px" />
        {m.name}
      </span>
    )
    cursor = m.index + m.name.length
  })
  // Remaining text
  if (cursor < text.length) {
    parts.push(text.slice(cursor))
  }
  return parts
}

/**
 * Recursively process React children to inject citation badges and inline logos into text nodes.
 */
function processChildren(children: ReactNode, sectionId: string): ReactNode {
  if (typeof children === 'string') {
    // First inject inline logos, then inject citations into the resulting text segments
    const logoParts = injectInlineLogos(children)
    // Now process each part for citations
    return (
      <>
        {logoParts.map((part, i) => {
          if (typeof part === 'string' && /\[\d+\]/.test(part)) {
            return <span key={`c-${i}`}>{injectCitations(part, sectionId)}</span>
          }
          return typeof part === 'string' ? <span key={`t-${i}`}>{part}</span> : part
        })}
      </>
    )
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => (
      <span key={i}>{processChildren(child, sectionId)}</span>
    ))
  }
  return children
}

// ─── Sub-Components ───────────────────────────────────

function VoiceQuoteCard({ quote }: { quote: WeeklyBriefingVoiceQuote }) {
  const borderColor = VOICE_BORDER_COLORS[quote.source_type] ?? 'border-l-text-muted'
  const label = VOICE_LABELS[quote.source_type] ?? quote.source_type

  return (
    <div className={`border-l-2 ${borderColor} pl-4 py-2`}>
      <div className="flex items-start gap-2">
        <Quote className="w-4 h-4 text-text-muted flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm text-text-primary leading-relaxed italic">
            "{quote.text}"
          </p>
          <div className="flex flex-wrap items-center gap-1.5 mt-2 text-xs text-text-muted">
            <span className="font-medium text-text-secondary">{quote.speaker}</span>
            {quote.role && <><span>-</span><span>{quote.role}</span></>}
            {quote.company && (
              <>
                <span>-</span>
                <span className="inline-flex items-center gap-1">
                  <CompanyLogo companyName={quote.company} domain={companyNameToDomain(quote.company)} size={14} />
                  {quote.company}
                </span>
              </>
            )}
            <span className="px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
              {label}
            </span>
            {quote.source_context && (
              <span className="text-text-muted">{quote.source_context}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function CitationsList({ citations, sectionId }: { citations: WeeklyBriefingCitation[]; sectionId: string }) {
  if (!citations.length) return null
  return (
    <div id={`sources-${sectionId}`} className="mt-4 pt-3 border-t border-border/50">
      <div className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">Sources</div>
      <div className="space-y-1">
        {citations.map(c => (
          <div key={c.number} className="flex items-start gap-2 text-xs">
            <span className="text-accent-blue font-bold min-w-[1.2rem]">[{c.number}]</span>
            <div className="flex-1">
              {c.url ? (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-secondary hover:text-accent-blue transition-colors"
                >
                  {c.title || 'Source'}
                  <ExternalLink className="inline w-3 h-3 ml-1 -mt-0.5" />
                </a>
              ) : (
                <span className="text-text-secondary">{c.title || 'Source'}</span>
              )}
              {c.source_name && (
                <span className="text-text-muted ml-1">- {c.source_name}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function BriefingSectionCard({ section }: { section: WeeklyBriefingSection }) {
  const tagStyle = PRIORITY_TAG_COLORS[section.priority_tag] ?? 'bg-bg-tertiary text-text-muted border-border'

  return (
    <Card className="p-5">
      {/* Section header */}
      <div className="flex items-center gap-3 mb-4">
        <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-bold border ${tagStyle}`}>
          {section.priority_tag}
        </span>
        <div>
          <h3 className="text-base font-semibold text-text-primary">{section.header}</h3>
          <span className="text-xs text-text-muted">{section.priority_label}</span>
        </div>
      </div>

      {/* Narrative */}
      <div className="mb-4">
        <NarrativeRenderer text={section.narrative} sectionId={section.section_id} />
      </div>

      {/* Voice quotes */}
      {section.voice_quotes.length > 0 && (
        <div className="space-y-3 mb-4">
          {section.voice_quotes.map((vq, i) => (
            <VoiceQuoteCard key={i} quote={vq} />
          ))}
        </div>
      )}

      {/* Citations */}
      <CitationsList citations={section.citations} sectionId={section.section_id} />
    </Card>
  )
}

// ─── Main Page ────────────────────────────────────────

export default function BriefingPage() {
  const [domain, setDomain] = useState<Domain>('quantum')
  const { data, isLoading, error } = useQuery({
    queryKey: ['weekly-briefing', domain],
    queryFn: () => api.getWeeklyBriefing(domain),
  })

  if (isLoading) {
    return <div className="text-text-muted text-sm animate-pulse p-8">Loading weekly briefing...</div>
  }

  if (error) {
    return (
      <div className="text-accent-red text-sm p-8">
        Failed to load briefing: {(error as Error).message}
      </div>
    )
  }

  const briefing = data?.briefing as WeeklyBriefingData | null

  if (!briefing) {
    return (
      <div className="max-w-5xl mx-auto py-12">
        <EmptyState message={`No weekly briefing generated yet for ${domain === 'ai' ? 'AI' : 'Quantum'}. Run: python scripts/run_weekly_briefing.py --domain ${domain} --save`} />
      </div>
    )
  }

  const activeSections = briefing.sections.filter(s => s.has_content)
  const inactiveSections = briefing.sections.filter(s => !s.has_content)

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">
            {domain === 'ai' ? 'AI' : 'Quantum'} Weekly Briefing
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-1 text-sm text-text-muted">
            <span>Week of {briefing.week_of}</span>
            <span>-</span>
            <span>{briefing.articles_analyzed} articles analyzed</span>
            <span>-</span>
            <span>{briefing.sections_active} of {briefing.sections_total} sections active</span>
            {briefing.generation_cost_usd > 0 && (
              <>
                <span>-</span>
                <span>${briefing.generation_cost_usd.toFixed(4)}</span>
              </>
            )}
          </div>
        </div>
        <DomainToggle domain={domain} onChange={setDomain} />
      </div>

      {/* Maturity Radar */}
      <div className="mb-6">
        <RadarWidget domain={domain} />
      </div>

      {/* Priority Sections */}
      {activeSections.length > 0 ? (
        <div className="space-y-4">
          {activeSections.map(section => (
            <BriefingSectionCard key={section.section_id} section={section} />
          ))}
        </div>
      ) : (
        <EmptyState message="No priority sections had updates this week" />
      )}

      {/* Market Movers */}
      {briefing.market_movers.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-accent-green" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
              Market Movers
            </h2>
            <span className="text-xs text-text-muted">(&gt;5% weekly change)</span>
          </div>
          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-bg-tertiary text-text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-4 py-2">Ticker</th>
                  <th className="text-right px-4 py-2">Close</th>
                  <th className="text-right px-4 py-2">Weekly Change</th>
                  <th className="text-left px-4 py-2">Context</th>
                </tr>
              </thead>
              <tbody>
                {briefing.market_movers.map(mm => (
                  <tr key={mm.ticker} className="border-t border-border hover:bg-bg-hover transition-colors">
                    <td className="px-4 py-2 font-medium">
                      <span className="inline-flex items-center gap-2">
                        <CompanyLogo companyName={mm.company_name} domain={companyNameToDomain(mm.company_name)} size={20} />
                        {mm.ticker}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {mm.close != null ? `$${mm.close.toFixed(2)}` : '-'}
                    </td>
                    <td className={`px-4 py-2 text-right font-medium flex items-center justify-end gap-1 ${mm.change_pct >= 0 ? 'text-accent-green' : 'text-accent-red'
                      }`}>
                      {mm.change_pct >= 0 ? (
                        <TrendingUp className="w-3.5 h-3.5" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5" />
                      )}
                      {mm.change_pct >= 0 ? '+' : ''}{mm.change_pct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-text-muted text-xs max-w-xs truncate">
                      {mm.context_text}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* Research Frontier */}
      {briefing.research_papers.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-4 h-4 text-accent-blue" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
              Research Frontier
            </h2>
          </div>
          <div className="space-y-3">
            {briefing.research_papers.map(rp => (
              <Card key={rp.arxiv_id} className="p-4">
                <a
                  href={rp.abs_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-text-primary hover:text-accent-blue transition-colors"
                >
                  {rp.title}
                  <ExternalLink className="inline w-3 h-3 ml-1 -mt-0.5" />
                </a>
                <div className="text-xs text-text-muted mt-1">
                  {rp.authors.slice(0, 3).join(', ')}
                  {rp.authors.length > 3 && ' et al.'}
                </div>
                {rp.why_it_matters && (
                  <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                    {rp.why_it_matters}
                  </p>
                )}
                <div className="flex gap-1.5 mt-2">
                  {rp.commercial_readiness && (
                    <span className="text-xs px-2 py-0.5 rounded bg-accent-green/15 text-accent-green">
                      {rp.commercial_readiness.replace(/_/g, ' ')}
                    </span>
                  )}
                  {rp.relevance_score != null && (
                    <span className="text-xs text-text-muted">{rp.relevance_score}/10</span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Footer — inactive sections */}
      {inactiveSections.length > 0 && (
        <div className="text-xs text-text-muted pt-4 border-t border-border/50">
          Sections with no updates this week:{' '}
          {inactiveSections.map(s => `${s.priority_tag}: ${s.priority_label}`).join(', ')}
        </div>
      )}
    </div>
  )
}
