/**
 * ConceptCloud — Tag Wall visualization of trending concepts.
 * Tags sized by weight, colored by type (company/technology/use_case/topic).
 * Clickable — populates search filter.
 */

import type { ConceptTerm } from '../api'

// Color mapping by concept type
const TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  company:    { bg: 'bg-accent-teal/12', text: 'text-accent-teal', border: 'border-accent-teal/20' },
  technology: { bg: 'bg-accent-blue/12', text: 'text-accent-blue', border: 'border-accent-blue/20' },
  use_case:   { bg: 'bg-accent-purple/12', text: 'text-accent-purple', border: 'border-accent-purple/20' },
  topic:      { bg: 'bg-bg-tertiary', text: 'text-text-secondary', border: 'border-border' },
}

// Size classes based on weight rank
function getSizeClass(rank: number): string {
  if (rank < 5) return 'text-base font-semibold px-3 py-1.5'       // XL — top 5
  if (rank < 15) return 'text-sm font-medium px-2.5 py-1'          // L — 6-15
  if (rank < 30) return 'text-xs font-medium px-2 py-0.5'          // M — 16-30
  return 'text-[11px] px-1.5 py-0.5'                                // S — 31+
}

interface ConceptCloudProps {
  terms: ConceptTerm[]
  onTermClick?: (term: string) => void
  isLoading?: boolean
}

export default function ConceptCloud({ terms, onTermClick, isLoading }: ConceptCloudProps) {
  if (isLoading) {
    return (
      <div className="h-32 flex items-center justify-center text-text-muted text-xs animate-pulse">
        Loading concepts...
      </div>
    )
  }

  if (!terms.length) {
    return (
      <div className="h-32 flex items-center justify-center text-text-muted text-xs">
        No concept data available
      </div>
    )
  }

  // Sort by weight descending for ranking
  const sorted = [...terms].sort((a, b) => b.weight - a.weight)

  return (
    <div className="flex flex-wrap gap-1.5 py-1">
      {sorted.map((term, i) => {
        const colors = TYPE_COLORS[term.type] || TYPE_COLORS.topic
        const sizeClass = getSizeClass(i)
        return (
          <button
            key={term.text}
            onClick={() => onTermClick?.(term.text)}
            className={`inline-flex items-center rounded-md border transition-all hover:scale-105 hover:shadow-sm cursor-pointer ${colors.bg} ${colors.text} ${colors.border} ${sizeClass}`}
            title={`${term.text} (${term.type}, weight: ${term.weight})`}
          >
            {term.text}
          </button>
        )
      })}
    </div>
  )
}
