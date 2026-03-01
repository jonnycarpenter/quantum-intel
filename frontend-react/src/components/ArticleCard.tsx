import { ExternalLink } from 'lucide-react'
import { PriorityBadge, CategoryBadge, TagChip, Card, timeAgo } from './ui'
import type { Article } from '../api'

interface Props {
  article: Article
  compact?: boolean
}

export default function ArticleCard({ article, compact = false }: Props) {
  return (
    <Card className="p-4 hover:border-border-light transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Header: priority + category */}
          <div className="flex items-center gap-2 mb-1.5">
            <PriorityBadge priority={article.priority} />
            <CategoryBadge category={article.category} />
            <span className="text-xs text-text-muted">●{article.relevance_score.toFixed(2)}</span>
            {article.metadata?.reality_check_score && (
              <span
                className="ml-auto text-[10px] sm:text-xs px-2 py-0.5 rounded bg-accent-purple/10 text-accent-purple cursor-help border border-accent-purple/20 transition-all hover:bg-accent-purple/20"
                title={article.metadata.reality_check_reasoning || "Reality Check Score"}
              >
                Signal: {article.metadata.reality_check_score}/100
              </span>
            )}
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
                <TagChip key={c} label={c} variant="cyan" />
              ))}
              {article.technologies_mentioned?.slice(0, 3).map(t => (
                <TagChip key={t} label={t} variant="purple" />
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
