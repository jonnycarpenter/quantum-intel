/**
 * Domain Toggle
 * =============
 * Reusable Quantum / AI pill toggle for page-level domain switching.
 */

import type { Domain } from '../api'

interface Props {
    domain: Domain
    onChange: (d: Domain) => void
}

export default function DomainToggle({ domain, onChange }: Props) {
    return (
        <div className="flex items-center bg-bg-tertiary rounded-lg p-0.5">
            <button
                onClick={() => onChange('quantum')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${domain === 'quantum'
                    ? 'bg-accent-cyan/20 text-accent-cyan'
                    : 'text-text-muted hover:text-text-secondary'
                    }`}
            >
                Quantum
            </button>
            <button
                onClick={() => onChange('ai')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${domain === 'ai'
                    ? 'bg-accent-purple/20 text-accent-purple'
                    : 'text-text-muted hover:text-text-secondary'
                    }`}
            >
                AI
            </button>
        </div>
    )
}
