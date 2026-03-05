/**
 * AnalyticsBar — Collapsible container holding three analytics widgets:
 * 1. Category Breakdown (horizontal bar chart)
 * 2. Trend Over Time (multi-line sparkline)
 * 3. Concept Cloud (tag wall)
 *
 * Expanded by default on desktop, collapsed on mobile.
 */

import { useState } from 'react'
import { ChevronDown, ChevronUp, BarChart3, TrendingUp, Cloud } from 'lucide-react'
import TrendChart from './TrendChart'
import ConceptCloud from './ConceptCloud'
import CategoryBreakdown from './CategoryBreakdown'
import type { CategoryTrend, ConceptTerm } from '../api'

interface CategoryCount {
  category: string
  count: number
}

interface AnalyticsBarProps {
  trends: CategoryTrend[]
  trendsLoading: boolean
  concepts: ConceptTerm[]
  conceptsLoading: boolean
  categories: CategoryCount[]
  categoriesLoading: boolean
  onCategoryClick?: (category: string) => void
  onConceptClick?: (term: string) => void
}

export default function AnalyticsBar({
  trends,
  trendsLoading,
  concepts,
  conceptsLoading,
  categories,
  categoriesLoading,
  onCategoryClick,
  onConceptClick,
}: AnalyticsBarProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-bg-hover transition-colors"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Analytics
        </span>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-muted" />
        )}
      </button>

      {/* Collapsible content */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          expanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 pb-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Widget 1: Category Breakdown */}
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart3 className="w-3.5 h-3.5 text-text-muted" />
              <span className="text-xs font-medium text-text-secondary">Categories</span>
            </div>
            <CategoryBreakdown
              categories={categories}
              onCategoryClick={onCategoryClick}
              isLoading={categoriesLoading}
            />
          </div>

          {/* Widget 2: Trend Over Time */}
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp className="w-3.5 h-3.5 text-text-muted" />
              <span className="text-xs font-medium text-text-secondary">Trends</span>
            </div>
            <TrendChart trends={trends} isLoading={trendsLoading} />
          </div>

          {/* Widget 3: Concept Cloud */}
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 mb-2">
              <Cloud className="w-3.5 h-3.5 text-text-muted" />
              <span className="text-xs font-medium text-text-secondary">Concepts</span>
            </div>
            <ConceptCloud
              terms={concepts}
              onTermClick={onConceptClick}
              isLoading={conceptsLoading}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
