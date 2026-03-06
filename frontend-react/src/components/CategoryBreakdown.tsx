/**
 * CategoryBreakdown — Horizontal bar chart showing article count by category.
 * Clickable — clicking a category filters the feed.
 * Uses Recharts BarChart.
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

interface CategoryCount {
  category: string
  count: number
}

// Alternate between two accent colors for visual distinction
const BAR_COLORS = ['#2BB0A6', '#60a5fa']

function formatCategoryLabel(cat: string): string {
  return cat
    .replace(/^(ai_|use_case_)/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

// Truncate long labels for the Y axis
function truncateLabel(label: string, maxLen = 18): string {
  const formatted = formatCategoryLabel(label)
  return formatted.length > maxLen ? formatted.slice(0, maxLen - 1) + '…' : formatted
}

interface CategoryBreakdownProps {
  categories: CategoryCount[]
  onCategoryClick?: (category: string) => void
  isLoading?: boolean
  maxCategories?: number
}

export default function CategoryBreakdown({
  categories,
  onCategoryClick,
  isLoading,
  maxCategories = 8,
}: CategoryBreakdownProps) {
  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center text-text-muted text-xs animate-pulse">
        Loading categories...
      </div>
    )
  }

  if (!categories.length) {
    return (
      <div className="h-48 flex items-center justify-center text-text-muted text-xs">
        No category data available
      </div>
    )
  }

  // Take top N and format
  const data = categories
    .slice(0, maxCategories)
    .map(c => ({
      category: c.category,
      label: truncateLabel(c.category),
      count: c.count,
    }))

  const chartHeight = Math.max(data.length * 28 + 20, 120)

  return (
    <div style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
        >
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: '#718096' }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 11, fill: '#4A5568' }}
            axisLine={false}
            tickLine={false}
            width={130}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number | undefined) => [value ?? 0, 'Articles'] as [number, string]}
            labelFormatter={(label) => formatCategoryLabel(String(label))}
          />
          <Bar
            dataKey="count"
            radius={[0, 4, 4, 0]}
            cursor="pointer"
            onClick={(entry: {category?: string}) => {
              if (onCategoryClick && entry?.category) {
                onCategoryClick(entry.category)
              }
            }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
