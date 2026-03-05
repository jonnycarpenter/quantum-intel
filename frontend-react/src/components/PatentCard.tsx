import { FileBadge, ExternalLink, Users, Pin } from 'lucide-react'
import { Card } from './ui'
import CompanyLogo from './CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'
import type { Patent } from '../api'

interface Props {
  patent: Patent
  onPin?: (patent: Patent) => void
  isPinned?: boolean
}

export default function PatentCard({ patent, onPin, isPinned }: Props) {
  return (
    <Card className="p-4 border-l-2 border-l-text-muted hover:border-accent-blue/50 transition-colors group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <FileBadge className="w-5 h-5 flex-shrink-0 text-accent-blue mt-0.5" />
          <div className="flex-1 space-y-2">
            {/* Header: assignee + patent ID + dates */}
            <div className="flex items-center flex-wrap gap-2 text-xs">
              <span className="inline-flex items-center gap-1 font-medium text-text-primary">
                <CompanyLogo companyName={patent.assignee} domain={companyNameToDomain(patent.assignee)} size={16} />
                {patent.assignee}
              </span>
              <span className="text-text-muted">•</span>
              <span className="text-text-secondary font-mono bg-bg-tertiary px-1.5 py-0.5 rounded">{patent.id}</span>
              <span className="text-text-muted">•</span>
              <span className="text-text-muted">Filed: {patent.filing_date || 'Unknown'}</span>
              {patent.publication_date && (
                <>
                  <span className="text-text-muted">•</span>
                  <span className="text-text-muted">Published: {patent.publication_date}</span>
                </>
              )}
            </div>

            {/* Title */}
            <h3 className="text-base font-medium text-text-primary leading-tight group-hover:text-accent-blue transition-colors">
              <a href={patent.patent_url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1.5 w-fit">
                {patent.title}
                <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
              </a>
            </h3>

            {/* Abstract */}
            <p className="text-sm text-text-secondary leading-relaxed line-clamp-3">
              {patent.abstract}
            </p>

            {/* Inventors */}
            {patent.inventors?.length > 0 && (
              <div className="flex items-center gap-1.5 mt-2 text-xs text-text-muted bg-bg-tertiary w-fit px-2 py-1 rounded">
                <Users size={12} />
                <span className="truncate max-w-[500px]">
                  {patent.inventors.join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Pin button */}
        {onPin && (
          <button
            onClick={() => onPin(patent)}
            className={`flex-shrink-0 transition-colors ${isPinned ? 'text-accent-blue' : 'text-text-muted hover:text-accent-blue'}`}
            title={isPinned ? 'Pinned to Insight Builder' : 'Pin to Insight Builder'}
          >
            <Pin className={`w-4 h-4 ${isPinned ? 'fill-current' : ''}`} />
          </button>
        )}
      </div>
    </Card>
  )
}
