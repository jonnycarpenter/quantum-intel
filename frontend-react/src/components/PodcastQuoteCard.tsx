import { Mic, Pin } from 'lucide-react'
import { TagChip, Card, timeAgo } from './ui'
import type { PodcastQuote } from '../api'

interface Props {
  quote: PodcastQuote
  onPin?: (quote: PodcastQuote) => void
  isPinned?: boolean
}

export default function PodcastQuoteCard({ quote, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 border-l-2 border-l-accent-cyan hover:border-border-light transition-colors">
      <div className="flex items-start gap-3">
        <Mic className="w-5 h-5 text-accent-cyan flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          {/* Header: podcast + episode */}
          <div className="flex items-center gap-2 mb-1.5 text-xs text-text-muted">
            <span className="font-medium text-accent-cyan">{quote.podcast_name}</span>
            <span>•</span>
            <span className="truncate">{quote.episode_title}</span>
            {quote.published_at && (
              <>
                <span>•</span>
                <span>{timeAgo(quote.published_at)}</span>
              </>
            )}
          </div>

          {/* Quote text */}
          <p className="text-sm text-text-primary leading-relaxed italic">
            "{quote.quote_text}"
          </p>

          {/* Speaker attribution */}
          <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
            <span className="font-medium text-text-secondary">{quote.speaker_name}</span>
            {quote.speaker_role && (
              <>
                <span>•</span>
                <span className="uppercase">{quote.speaker_role}</span>
              </>
            )}
            {quote.speaker_company && (
              <>
                <span>•</span>
                <span>{quote.speaker_company}</span>
              </>
            )}
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className="text-xs px-2 py-0.5 rounded bg-accent-cyan/15 text-accent-cyan">
              {quote.quote_type.replace(/_/g, ' ')}
            </span>
            {quote.sentiment && quote.sentiment !== 'neutral' && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                quote.sentiment === 'bullish' || quote.sentiment === 'excited'
                  ? 'bg-accent-green/15 text-accent-green'
                  : quote.sentiment === 'bearish'
                    ? 'bg-accent-red/15 text-accent-red'
                    : 'bg-accent-yellow/15 text-accent-yellow'
              }`}>
                {quote.sentiment}
              </span>
            )}
            <span className="text-xs text-text-muted">●{quote.relevance_score.toFixed(2)}</span>
            {quote.themes && quote.themes.split(',').filter(Boolean).slice(0, 3).map(t => (
              <TagChip key={t.trim()} label={t.trim().replace(/_/g, ' ')} variant="cyan" />
            ))}
          </div>
        </div>

        {/* Pin button */}
        {onPin && (
          <button
            onClick={() => onPin(quote)}
            className={`flex-shrink-0 transition-colors ${isPinned ? 'text-accent-cyan' : 'text-text-muted hover:text-accent-cyan'}`}
            title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
          >
            <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </Card>
  )
}
