import { ShieldAlert, Pin } from 'lucide-react'
import { Card } from './ui'
import CompanyLogo from './CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'
import type { SecNuggetDisplay } from '../api'

interface Props {
  nugget: SecNuggetDisplay
  onPin?: (nugget: SecNuggetDisplay) => void
  isPinned?: boolean
}

export default function SecNuggetCard({ nugget, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 border-l-2 border-l-accent-orange hover:border-border-light transition-colors">
      <div className="flex items-start gap-3">
        <ShieldAlert className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
          nugget.is_new_disclosure ? 'text-accent-red' : 'text-accent-orange'
        }`} />
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center gap-1 text-xs font-medium text-accent-blue">
              <CompanyLogo companyName={nugget.company_name} domain={companyNameToDomain(nugget.company_name || nugget.ticker)} size={16} />
              {nugget.ticker}
            </span>
            <span className="text-xs text-text-muted">
              {nugget.display_source ?? `${nugget.filing_type} FY${nugget.fiscal_year}`}
            </span>
            {nugget.is_new_disclosure && (
              <span className="text-xs px-2 py-0.5 rounded bg-accent-red/15 text-accent-red font-medium">
                NEW DISCLOSURE
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded ${
              nugget.risk_level === 'high'
                ? 'bg-accent-red/15 text-accent-red'
                : 'bg-bg-tertiary text-text-muted'
            }`}>
              {nugget.risk_level} risk
            </span>
          </div>

          {/* Nugget text */}
          <p className="text-sm text-text-primary leading-relaxed">
            "{nugget.nugget_text}"
          </p>

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className="text-xs px-2 py-0.5 rounded bg-accent-purple/15 text-accent-purple">
              {nugget.nugget_type.replace(/_/g, ' ')}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
              {nugget.section.replace(/_/g, ' ')}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-bg-tertiary text-text-muted">
              {nugget.signal_strength}
            </span>
            {nugget.competitors_named?.filter(Boolean).length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded bg-accent-cyan/15 text-accent-cyan">
                names: {nugget.competitors_named.filter(Boolean).join(', ')}
              </span>
            )}
          </div>
        </div>

        {/* Pin button */}
        {onPin && (
          <button
            onClick={() => onPin(nugget)}
            className={`flex-shrink-0 transition-colors ${isPinned ? 'text-accent-orange' : 'text-text-muted hover:text-accent-orange'}`}
            title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
          >
            <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </Card>
  )
}
