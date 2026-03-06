/**
 * TrendChart — Multi-line sparkline showing category trends over time.
 * Uses Recharts LineChart. Responds to domain toggle and time range.
 */

import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { CategoryTrend } from '../api'

// Category color palette — consistent, distinguishable colors
const CATEGORY_COLORS = [
  '#2BB0A6', // teal
  '#60a5fa', // blue
  '#a78bfa', // purple
  '#fb923c', // orange
  '#34d399', // green
  '#f87171', // red
  '#fbbf24', // yellow
  '#ec4899', // pink
]

function formatCategoryLabel(cat: string): string {
  return cat
    .replace(/^(ai_|use_case_)/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatDateTick(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

interface TrendChartProps {
  trends: CategoryTrend[]
  isLoading?: boolean
}

export default function TrendChart({ trends, isLoading }: TrendChartProps) {
  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center text-text-muted text-xs animate-pulse">
        Loading trends...
      </div>
    )
  }

  if (!trends.length) {
    return (
      <div className="h-48 flex items-center justify-center text-text-muted text-xs">
        No trend data available
      </div>
    )
  }

  // Merge all category data into a single dataset keyed by date
  const dateMap = new Map<string, Record<string, number>>()
  for (const trend of trends) {
    for (const pt of trend.data) {
      if (!dateMap.has(pt.date)) dateMap.set(pt.date, {})
      dateMap.get(pt.date)![trend.category] = pt.count
    }
  }

  const chartData = Array.from(dateMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, counts]) => ({ date, ...counts }))

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <XAxis
            dataKey="date"
            tickFormatter={formatDateTick}
            tick={{ fontSize: 10, fill: '#718096' }}
            axisLine={{ stroke: '#E2E8F0' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#718096' }}
            axisLine={false}
            tickLine={false}
            width={28}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
            }}
            labelFormatter={(val) => {
              const d = new Date(String(val))
              return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            }}
            formatter={(value: number | undefined, name: string | undefined) => [value ?? 0, formatCategoryLabel(name ?? '')] as [number, string]}
          />
          <Legend
            formatter={formatCategoryLabel}
            wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }}
          />
          {trends.map((t, i) => (
            <Line
              key={t.category}
              type="monotone"
              dataKey={t.category}
              stroke={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
