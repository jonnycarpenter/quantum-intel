import { ExternalLink, FileText, Pin } from 'lucide-react'
import { Card } from './ui'
import type { Paper } from '../api'

interface Props {
  paper: Paper
  onPin?: (paper: Paper) => void
  isPinned?: boolean
}

export default function PaperCard({ paper, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 border-l-2 border-l-accent-blue hover:border-border-light transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Title */}
          <a
            href={paper.abs_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-text-primary hover:text-accent-blue transition-colors leading-snug"
          >
            {paper.title}
            <ExternalLink className="inline w-3 h-3 ml-1 opacity-50" />
          </a>

          {/* Authors */}
          <div className="text-xs text-text-muted mt-1">
            {paper.authors?.slice(0, 5).join(', ')}
            {(paper.authors?.length ?? 0) > 5 && ' et al.'}
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            {paper.relevance_score != null && (
              <span className="text-xs px-2 py-0.5 rounded bg-accent-cyan/15 text-accent-cyan">
                {paper.relevance_score}/10
              </span>
            )}
            {paper.paper_type && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                paper.paper_type === 'breakthrough'
                  ? 'bg-accent-red/15 text-accent-red font-medium'
                  : 'bg-accent-blue/15 text-accent-blue'
              }`}>
                {paper.paper_type}
              </span>
            )}
            {paper.commercial_readiness && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                paper.commercial_readiness === 'near_term'
                  ? 'bg-accent-green/15 text-accent-green'
                  : 'bg-bg-tertiary text-text-muted'
              }`}>
                {paper.commercial_readiness.replace(/_/g, ' ')}
              </span>
            )}
            {paper.categories?.slice(0, 3).map(c => (
              <span key={c} className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
                {c}
              </span>
            ))}
          </div>

          {/* Significance */}
          {paper.significance_summary && (
            <p className="text-sm text-text-secondary mt-2 leading-relaxed">
              {paper.significance_summary}
            </p>
          )}

          {/* Abstract (collapsible) */}
          {paper.abstract && (
            <details className="mt-2">
              <summary className="text-xs text-accent-blue cursor-pointer hover:underline">
                Show abstract
              </summary>
              <p className="text-sm text-text-muted mt-1 leading-relaxed">
                {paper.abstract}
              </p>
            </details>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Pin button */}
          {onPin && (
            <button
              onClick={() => onPin(paper)}
              className={`transition-colors ${isPinned ? 'text-accent-blue' : 'text-text-muted hover:text-accent-blue'}`}
              title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
            >
              <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
            </button>
          )}
          {/* PDF link */}
          {paper.pdf_url && (
            <a
              href={paper.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-muted hover:text-accent-blue transition-colors"
              title="Download PDF"
            >
              <FileText className="w-5 h-5" />
            </a>
          )}
        </div>
      </div>
    </Card>
  )
}
