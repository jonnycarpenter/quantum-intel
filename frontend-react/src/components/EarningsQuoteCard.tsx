import { Quote, Pin } from 'lucide-react'
import { Card } from './ui'
import CompanyLogo from './CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'
import type { EarningsQuote } from '../api'

interface Props {
  quote: EarningsQuote
  onPin?: (quote: EarningsQuote) => void
  isPinned?: boolean
}

export default function EarningsQuoteCard({ quote, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 border-l-2 border-l-accent-purple hover:border-border-light transition-colors">
      <div className="flex items-start gap-3">
        <Quote className="w-5 h-5 text-accent-purple flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1 text-xs font-medium text-accent-blue">
              <CompanyLogo companyName={quote.company_name} domain={companyNameToDomain(quote.company_name)} size={16} />
              {quote.ticker}
            </span>
            <span className="text-xs text-text-muted">
              {quote.company_name} • Q{quote.quarter} {quote.year}
            </span>
          </div>

          {/* Quote text */}
          <p className="text-sm text-text-primary leading-relaxed italic">
            "{quote.quote_text}"
          </p>

          {/* Speaker */}
          <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
            <span className="font-medium text-text-secondary">{quote.speaker_name}</span>
            <span>•</span>
            <span className="uppercase">{quote.speaker_role}</span>
            <span>•</span>
            <span>{quote.section.replace(/_/g, ' ')}</span>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            <span className="text-xs px-2 py-0.5 rounded bg-accent-purple/15 text-accent-purple">
              {quote.quote_type.replace(/_/g, ' ')}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              quote.confidence_level === 'definitive'
                ? 'bg-accent-green/15 text-accent-green'
                : quote.confidence_level === 'hedged'
                  ? 'bg-accent-red/15 text-accent-red'
                  : 'bg-accent-yellow/15 text-accent-yellow'
            }`}>
              {quote.confidence_level}
            </span>
            {quote.sentiment && quote.sentiment !== 'neutral' && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                quote.sentiment === 'bullish'
                  ? 'bg-accent-green/15 text-accent-green'
                  : 'bg-accent-red/15 text-accent-red'
              }`}>
                {quote.sentiment}
              </span>
            )}
            <span className="text-xs text-text-muted">●{quote.relevance_score.toFixed(2)}</span>
          </div>
        </div>

        {/* Pin button */}
        {onPin && (
          <button
            onClick={() => onPin(quote)}
            className={`flex-shrink-0 transition-colors ${isPinned ? 'text-accent-purple' : 'text-text-muted hover:text-accent-purple'}`}
            title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
          >
            <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </Card>
  )
}
