import { ExternalLink, Pin } from 'lucide-react'
import { PriorityBadge, CategoryBadge, TagChip, Card, timeAgo } from './ui'
import CompanyLogo from './CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'
import type { Article } from '../api'

interface Props {
  article: Article
  compact?: boolean
  onPin?: (article: Article) => void
  isPinned?: boolean
}

export default function ArticleCard({ article, compact = false, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 hover:border-border-light transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Header: priority + category */}
          <div className="flex items-center gap-2 mb-1.5">
            <PriorityBadge priority={article.priority} />
            <CategoryBadge category={article.category} />
            <span className="text-xs text-text-muted">●{article.relevance_score.toFixed(2)}</span>
          </div>

          {/* Title */}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-text-primary hover:text-accent-blue transition-colors leading-snug line-clamp-2"
          >
            {article.title}
            <ExternalLink className="inline w-3 h-3 ml-1 opacity-50" />
          </a>

          {/* Meta line */}
          <div className="flex items-center gap-2 mt-1.5 text-xs text-text-muted">
            <span>{article.source_name}</span>
            <span>•</span>
            <span>{timeAgo(article.published_at)}</span>
            {article.sentiment && article.sentiment !== 'neutral' && (
              <>
                <span>•</span>
                <span className={article.sentiment === 'bullish' ? 'text-accent-green' : 'text-accent-red'}>
                  {article.sentiment}
                </span>
              </>
            )}
          </div>

          {/* Summary */}
          {!compact && article.summary && (
            <p className="mt-2 text-sm text-text-secondary leading-relaxed line-clamp-3">
              {article.summary}
            </p>
          )}

          {/* Tags */}
          {!compact && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {article.companies_mentioned?.slice(0, 4).map(c => (
                <span key={c} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-accent-cyan/15 text-accent-cyan">
                  <CompanyLogo companyName={c} domain={companyNameToDomain(c)} size={14} />
                  {c}
                </span>
              ))}
              {article.technologies_mentioned?.slice(0, 3).map(t => (
                <TagChip key={t} label={t} variant="purple" />
              ))}
            </div>
          )}
        </div>

        {/* Pin button */}
        {onPin && (
          <button
            onClick={() => onPin(article)}
            className={`flex-shrink-0 transition-colors ${isPinned ? 'text-accent-teal' : 'text-text-muted hover:text-accent-teal'}`}
            title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
          >
            <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </Card>
  )
}
