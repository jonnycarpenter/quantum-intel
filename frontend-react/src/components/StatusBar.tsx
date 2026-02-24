import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Database, FileText, FlaskConical, Clock } from 'lucide-react'

export default function StatusBar() {
  const { data } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60_000,
  })

  const stats = data?.stats

  return (
    <footer className="flex items-center gap-6 px-6 py-1.5 bg-bg-secondary border-t border-border text-xs text-text-muted">
      <div className="flex items-center gap-1.5">
        <Clock className="w-3 h-3" />
        <span>Last sync: just now</span>
      </div>
      <div className="flex items-center gap-1.5">
        <Database className="w-3 h-3" />
        <span>{stats?.total_articles ?? '–'} articles</span>
      </div>
      <div className="flex items-center gap-1.5">
        <FlaskConical className="w-3 h-3" />
        <span>{data?.embeddings_count ?? '–'} embeddings</span>
      </div>
      <div className="flex items-center gap-1.5">
        <FileText className="w-3 h-3" />
        <span>{data?.storage_backend ?? 'sqlite'}</span>
      </div>
    </footer>
  )
}
