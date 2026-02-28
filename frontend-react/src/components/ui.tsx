/**
 * Shared UI Components
 * ====================
 * Reusable badges, cards, and layout primitives.
 */

import type { ReactNode } from 'react'

// ─── Priority Badge ────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  critical: 'bg-priority-critical/15 text-priority-critical border-priority-critical/25',
  high: 'bg-priority-high/15 text-priority-high border-priority-high/25',
  medium: 'bg-priority-medium/15 text-priority-medium border-priority-medium/25',
  low: 'bg-priority-low/15 text-priority-low border-priority-low/25',
}

export function PriorityBadge({ priority }: { priority: string }) {
  const style = PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.low
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {priority.toUpperCase()}
    </span>
  )
}

// ─── Category Badge ────────────────────────────────────

export function CategoryBadge({ category }: { category: string }) {
  const label = category.replace(/_/g, ' ').replace(/\buse case\b/i, '').trim()
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-blue/15 text-accent-blue border border-accent-blue/25">
      {label}
    </span>
  )
}

// ─── Tag Chip ──────────────────────────────────────────

export function TagChip({ label, variant = 'default' }: { label: string; variant?: 'default' | 'green' | 'purple' | 'cyan' }) {
  const colors = {
    default: 'bg-bg-tertiary text-text-secondary',
    green: 'bg-accent-green/15 text-accent-green',
    purple: 'bg-accent-purple/15 text-accent-purple',
    cyan: 'bg-accent-cyan/15 text-accent-cyan',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${colors[variant]}`}>
      {label}
    </span>
  )
}

// ─── Card ──────────────────────────────────────────────

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-bg-secondary border border-border rounded-lg ${className}`}>
      {children}
    </div>
  )
}

// ─── Section Header ────────────────────────────────────

export function SectionHeader({ title, count, action, icon }: { title: string; count?: number; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">{title}</h2>
        {count !== undefined && (
          <span className="text-xs text-text-muted bg-bg-tertiary px-2 py-0.5 rounded-full">{count}</span>
        )}
      </div>
      {action}
    </div>
  )
}

// ─── Stat Card ─────────────────────────────────────────

export function StatCard({ label, value, subtext, color = 'text-text-primary' }: {
  label: string
  value: string | number
  subtext?: string
  color?: string
}) {
  return (
    <Card className="px-4 py-3">
      <div className="text-xs text-text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {subtext && <div className="text-xs text-text-muted mt-1">{subtext}</div>}
    </Card>
  )
}

// ─── Empty State ───────────────────────────────────────

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-text-muted text-sm">
      {message}
    </div>
  )
}

// ─── Lens Chip (for Explore page preset filters) ───────

export function LensChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-accent-blue/15 text-accent-blue border border-accent-blue/25'
          : 'bg-bg-tertiary text-text-muted hover:text-text-secondary hover:bg-bg-hover border border-transparent'
      }`}
    >
      {label}
    </button>
  )
}

// ─── Time Ago Helper ───────────────────────────────────

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}
