import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, SectionHeader, EmptyState } from '../components/ui'
import DomainToggle from '../components/DomainToggle'
import CompanyLogo from '../components/CompanyLogo'
import { companyNameToDomain } from '../utils/logoUtils'
import { FileBadge, ExternalLink, Users } from 'lucide-react'
import type { Domain } from '../api'

export default function PatentsPage() {
    const [domain, setDomain] = useState<Domain>('quantum')

    const { data, isLoading, error } = useQuery({
        queryKey: ['recent-patents', domain],
        queryFn: () => api.getRecentPatents(domain, 50),
    })

    // The API returns { status, domain, data: Patent[] }
    const patents = data?.data || []

    return (
        <div className="max-w-5xl mx-auto space-y-4">
            <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold text-text-primary">Patent IP Tracking</h1>
                <DomainToggle domain={domain} onChange={setDomain} />
            </div>

            <SectionHeader title="Recent Patent Filings" count={patents.length} />

            {isLoading ? (
                <div className="text-text-muted text-sm animate-pulse">Scanning IP databases...</div>
            ) : error ? (
                <EmptyState message="Failed to load patent data. Please try again later." />
            ) : patents.length > 0 ? (
                <div className="space-y-4">
                    {patents.map(p => (
                        <Card key={p.id} className="p-4 hover:border-accent-blue/50 transition-colors group">
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex items-start gap-3 flex-1">
                                    <FileBadge className="w-5 h-5 flex-shrink-0 text-accent-blue mt-0.5" />
                                    <div className="flex-1 space-y-2">
                                        <div className="flex items-center flex-wrap gap-2 text-xs">
                                            <span className="inline-flex items-center gap-1 font-medium text-text-primary">
                                                <CompanyLogo companyName={p.assignee} domain={companyNameToDomain(p.assignee)} size={16} />
                                                {p.assignee}
                                            </span>
                                            <span className="text-text-muted">•</span>
                                            <span className="text-text-secondary font-mono bg-bg-tertiary px-1.5 py-0.5 rounded">{p.id}</span>
                                            <span className="text-text-muted">•</span>
                                            <span className="text-text-muted">Filed: {p.filing_date || 'Unknown'}</span>
                                            {p.publication_date && (
                                                <>
                                                    <span className="text-text-muted">•</span>
                                                    <span className="text-text-muted">Published: {p.publication_date}</span>
                                                </>
                                            )}
                                        </div>

                                        <h3 className="text-base font-medium text-text-primary leading-tight group-hover:text-accent-blue transition-colors">
                                            <a href={p.patent_url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1.5 w-fit">
                                                {p.title}
                                                <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </a>
                                        </h3>

                                        <p className="text-sm text-text-secondary leading-relaxed line-clamp-3">
                                            {p.abstract}
                                        </p>

                                        {p.inventors?.length > 0 && (
                                            <div className="flex items-center gap-1.5 mt-2 text-xs text-text-muted bg-bg-tertiary w-fit px-2 py-1 rounded">
                                                <Users size={12} />
                                                <span className="truncate max-w-[500px]">
                                                    {p.inventors.join(', ')}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <EmptyState message={`No recent patents found for tracked ${domain} companies.`} />
            )}
        </div>
    )
}
