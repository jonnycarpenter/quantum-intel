/**
 * KeyThemes Component
 * ===================
 * Collapsible section showing algorithmically-extracted themes
 * and talking points from recent articles.
 * Supports copy-to-clipboard and pin-to-Insight-Builder.
 */

import { useState } from 'react'
import { ChevronDown, ChevronUp, BarChart3, Copy, Check, Pin, Building2, Newspaper } from 'lucide-react'
import type { Theme, ThemesResponse } from '../api'
import { usePinnedItems } from '../context/PinnedItemsContext'

interface KeyThemesProps {
  data: ThemesResponse | undefined
  isLoading: boolean
}

export default function KeyThemes({ data, isLoading }: KeyThemesProps) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)
  const { pinItem } = usePinnedItems()

  if (isLoading) {
    return (
      <div className="bg-bg-secondary border border-border rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 bg-bg-tertiary rounded animate-pulse" />
          <div className="h-4 w-40 bg-bg-tertiary rounded animate-pulse" />
        </div>
        <div className="mt-3 space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-bg-tertiary rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!data || data.themes.length === 0) return null

  const handleCopyTalkingPoints = async () => {
    const text = data.talking_points.map((tp, i) => `${i + 1}. ${tp}`).join('\n')
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePinTheme = (theme: Theme) => {
    pinItem({
      id: `theme-${theme.category}`,
      content_type: 'article',
      title: `🎯 ${theme.title} (${theme.article_count} articles)`,
      data: {
        id: `theme-${theme.category}`,
        url: '',
        title: theme.title,
        source_name: 'Key Themes',
        source_type: 'theme',
        published_at: new Date().toISOString(),
        summary: theme.summary,
        key_takeaway: `Theme: ${theme.title} — ${theme.article_count} articles. Top companies: ${theme.top_companies.join(', ')}`,
        category: theme.category,
        priority: 'high',
        relevance_score: 1,
        sentiment: 'neutral',
        companies_mentioned: theme.top_companies,
        technologies_mentioned: [],
        people_mentioned: [],
        use_case_domains: [],
        confidence: 1,
      },
      pinned_at: new Date().toISOString(),
    })
  }

  return (
    <div className="bg-bg-secondary border border-border rounded-lg mb-4 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent-blue" />
          <span className="text-sm font-semibold text-text-primary">Key Themes This Week</span>
          <span className="text-xs text-text-muted bg-bg-tertiary px-2 py-0.5 rounded-full">
            {data.themes.length}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-muted" />
        )}
      </button>

      {/* Content */}
      <div
        className="transition-all duration-300 ease-in-out"
        style={{
          maxHeight: expanded ? '800px' : '0',
          opacity: expanded ? 1 : 0,
          overflow: 'hidden',
        }}
      >
        <div className="px-4 pb-4">
          {/* Themes */}
          <div className="space-y-3 mb-4">
            {data.themes.map((theme, idx) => (
              <ThemeCard
                key={theme.category}
                theme={theme}
                index={idx + 1}
                onPin={() => handlePinTheme(theme)}
              />
            ))}
          </div>

          {/* Talking Points */}
          {data.talking_points.length > 0 && (
            <div className="border-t border-border pt-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Talking Points
                </span>
                <button
                  onClick={handleCopyTalkingPoints}
                  className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-blue transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      Copy as bullet points
                    </>
                  )}
                </button>
              </div>
              <ul className="space-y-1.5">
                {data.talking_points.slice(0, 6).map((point, i) => (
                  <li key={i} className="text-xs text-text-secondary flex gap-2">
                    <span className="text-text-muted shrink-0">•</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Theme Card ────────────────────────────────────────

function ThemeCard({
  theme,
  index,
  onPin,
}: {
  theme: Theme
  index: number
  onPin: () => void
}) {
  return (
    <div className="flex gap-3 group">
      {/* Index */}
      <div className="shrink-0 w-6 h-6 rounded-full bg-accent-blue/15 text-accent-blue flex items-center justify-center text-xs font-bold mt-0.5">
        {index}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-medium text-text-primary">{theme.title}</h4>
          <button
            onClick={onPin}
            className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-bg-tertiary"
            title="Pin to Insight Builder"
          >
            <Pin className="w-3.5 h-3.5 text-text-muted" />
          </button>
        </div>
        <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{theme.summary}</p>
        <div className="flex items-center gap-3 mt-1.5">
          <span className="flex items-center gap-1 text-xs text-text-muted">
            <Newspaper className="w-3 h-3" />
            {theme.article_count} articles
          </span>
          {theme.top_companies.length > 0 && (
            <span className="flex items-center gap-1 text-xs text-text-muted">
              <Building2 className="w-3 h-3" />
              {theme.top_companies.slice(0, 3).join(', ')}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
