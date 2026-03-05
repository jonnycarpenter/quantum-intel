import { useState } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Pin, X, GripVertical, FileText, Download, MessageSquare, Trash2, StickyNote } from 'lucide-react'
import { usePinnedItems } from '../context/PinnedItemsContext'
import type { PinnedItem } from '../api'

// ─── Content Type Colors ──────────────────────────────

const TYPE_COLORS: Record<string, { border: string; bg: string; text: string; label: string }> = {
  article: { border: 'border-l-accent-teal', bg: 'bg-accent-teal/10', text: 'text-accent-teal', label: 'Article' },
  podcast_quote: { border: 'border-l-accent-cyan', bg: 'bg-accent-cyan/10', text: 'text-accent-cyan', label: 'Podcast' },
  earnings_quote: { border: 'border-l-accent-purple', bg: 'bg-accent-purple/10', text: 'text-accent-purple', label: 'Earnings' },
  sec_nugget: { border: 'border-l-accent-orange', bg: 'bg-accent-orange/10', text: 'text-accent-orange', label: 'SEC Filing' },
  paper: { border: 'border-l-accent-blue', bg: 'bg-accent-blue/10', text: 'text-accent-blue', label: 'Paper' },
  patent: { border: 'border-l-accent-blue', bg: 'bg-accent-blue/10', text: 'text-accent-blue', label: 'Patent' },
}

// ─── Sortable Pinned Item ─────────────────────────────

function SortablePinnedCard({ item }: { item: PinnedItem }) {
  const { unpinItem, updateNote } = usePinnedItems()
  const [showNote, setShowNote] = useState(!!item.user_note)
  const colors = TYPE_COLORS[item.content_type] ?? TYPE_COLORS.article

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`bg-bg-secondary border border-border rounded-lg border-l-3 ${colors.border} ${isDragging ? 'shadow-lg' : ''}`}
    >
      <div className="flex items-start gap-2 p-3">
        {/* Drag Handle */}
        <button
          {...attributes}
          {...listeners}
          className="mt-0.5 text-text-muted hover:text-text-secondary cursor-grab active:cursor-grabbing flex-shrink-0"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
              {colors.label}
            </span>
          </div>
          <p className="text-sm text-text-primary line-clamp-2 leading-snug">
            {item.title}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => setShowNote(!showNote)}
            className={`p-1 rounded transition-colors ${showNote ? 'text-accent-teal' : 'text-text-muted hover:text-text-secondary'}`}
            title="Add note"
          >
            <StickyNote className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => unpinItem(item.id)}
            className="p-1 text-text-muted hover:text-red-400 rounded transition-colors"
            title="Remove"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Inline Note */}
      {showNote && (
        <div className="px-3 pb-3 pt-0">
          <textarea
            value={item.user_note ?? ''}
            onChange={e => updateNote(item.id, e.target.value)}
            placeholder="Add a note..."
            rows={2}
            className="w-full text-xs bg-bg-tertiary border border-border rounded-md px-2 py-1.5 text-text-secondary placeholder-text-muted outline-none focus:border-accent-teal resize-none"
          />
        </div>
      )}
    </div>
  )
}

// ─── Export Helpers ────────────────────────────────────

function generateMarkdown(items: PinnedItem[]): string {
  const lines: string[] = ['# Custom Briefing', '', `*Generated ${new Date().toLocaleDateString()}*`, '']

  for (const item of items) {
    const colors = TYPE_COLORS[item.content_type]
    lines.push(`## ${colors?.label ?? item.content_type}: ${item.title}`)
    lines.push('')

    if (item.user_note) {
      lines.push(`> **Note:** ${item.user_note}`)
      lines.push('')
    }

    // Add content based on type
    const d = item.data as Record<string, unknown>
    if (item.content_type === 'article') {
      if (d.summary) lines.push(String(d.summary))
      if (d.key_takeaway) lines.push('', `**Key Takeaway:** ${d.key_takeaway}`)
      if (d.url) lines.push('', `[Source](${d.url})`)
    } else if (item.content_type === 'podcast_quote' || item.content_type === 'earnings_quote') {
      if (d.quote_text) lines.push(`> "${d.quote_text}"`)
      const speaker = [d.speaker_name, d.speaker_role].filter(Boolean).join(', ')
      if (speaker) lines.push(`> — ${speaker}`)
    } else if (item.content_type === 'sec_nugget') {
      if (d.nugget_text) lines.push(`> ${d.nugget_text}`)
      if (d.company_name) lines.push('', `*${d.company_name} — ${d.filing_type}*`)
    } else if (item.content_type === 'paper') {
      if (d.significance_summary) lines.push(String(d.significance_summary))
      else if (d.abstract) lines.push(String(d.abstract).slice(0, 300) + '...')
      if (d.abs_url) lines.push('', `[ArXiv](${d.abs_url})`)
    } else if (item.content_type === 'patent') {
      if (d.abstract) lines.push(String(d.abstract).slice(0, 300) + '...')
      if (d.assignee) lines.push('', `*Assignee: ${d.assignee}*`)
    }

    lines.push('', '---', '')
  }

  return lines.join('\n')
}

function downloadMarkdown(items: PinnedItem[]) {
  const md = generateMarkdown(items)
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `briefing_${new Date().toISOString().slice(0, 10)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function sendToChat(items: PinnedItem[]) {
  const summaries = items.map((item, i) => {
    const colors = TYPE_COLORS[item.content_type]
    return `${i + 1}. [${colors?.label}] ${item.title}`
  }).join('\n')

  const message = `Analyze these ${items.length} items I've collected:\n\n${summaries}\n\nProvide a synthesis of the key themes, connections between items, and strategic implications.`

  // Dispatch custom event for ChatPanel to pick up
  window.dispatchEvent(new CustomEvent('ketzero-send-to-chat', { detail: { message } }))
}

// ─── Main Component ───────────────────────────────────

export default function InsightBuilder() {
  const { pinnedItems, reorderItems, clearAll } = usePinnedItems()

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = pinnedItems.findIndex(p => p.id === active.id)
    const newIndex = pinnedItems.findIndex(p => p.id === over.id)
    if (oldIndex !== -1 && newIndex !== -1) {
      reorderItems(oldIndex, newIndex)
    }
  }

  // ─── Empty State ────────────────────────────────────

  if (pinnedItems.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Pin className="w-4 h-4 text-accent-teal" />
            <h2 className="text-sm font-semibold text-text-primary">Insight Builder</h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <div className="w-12 h-12 rounded-full bg-bg-tertiary flex items-center justify-center mb-4">
            <Pin className="w-6 h-6 text-text-muted" />
          </div>
          <p className="text-sm font-medium text-text-secondary mb-2">
            Build your briefing
          </p>
          <p className="text-xs text-text-muted leading-relaxed">
            Pin items from the feed to collect and organize intelligence.
            Export as a PDF or send to the AI assistant for deeper analysis.
          </p>
        </div>
      </div>
    )
  }

  // ─── Has Items ──────────────────────────────────────

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Pin className="w-4 h-4 text-accent-teal" />
            <h2 className="text-sm font-semibold text-text-primary">Insight Builder</h2>
            <span className="text-xs text-text-muted bg-bg-tertiary px-1.5 py-0.5 rounded-full">
              {pinnedItems.length}
            </span>
          </div>
        </div>
      </div>

      {/* Pinned Items List */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={pinnedItems.map(p => p.id)}
            strategy={verticalListSortingStrategy}
          >
            {pinnedItems.map(item => (
              <SortablePinnedCard key={item.id} item={item} />
            ))}
          </SortableContext>
        </DndContext>
      </div>

      {/* Export Bar */}
      <div className="px-3 py-3 border-t border-border space-y-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-bg-tertiary hover:bg-bg-hover text-text-secondary rounded-lg transition-colors"
            title="Export as PDF"
          >
            <FileText className="w-3.5 h-3.5" />
            PDF
          </button>
          <button
            onClick={() => downloadMarkdown(pinnedItems)}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-bg-tertiary hover:bg-bg-hover text-text-secondary rounded-lg transition-colors"
            title="Download Markdown"
          >
            <Download className="w-3.5 h-3.5" />
            Markdown
          </button>
          <button
            onClick={() => sendToChat(pinnedItems)}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-accent-teal/15 hover:bg-accent-teal/25 text-accent-teal rounded-lg transition-colors"
            title="Send to AI Assistant"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Chat
          </button>
        </div>
        <button
          onClick={clearAll}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs text-text-muted hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3 h-3" />
          Clear all
        </button>
      </div>
    </div>
  )
}
