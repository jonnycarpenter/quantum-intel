/**
 * CompanyLogo Component
 * =====================
 * Renders a company logo via the backend proxy endpoint.
 * Falls back to a 2-letter initials badge when the logo isn't available.
 *
 * Usage:
 *   <CompanyLogo domain="ionq.com" size={24} />
 *   <CompanyLogo companyName="IonQ" size={20} />
 */

import { useState } from 'react'
import { Building2 } from 'lucide-react'

interface CompanyLogoProps {
  /** Company domain (e.g., "ionq.com") */
  domain?: string | null
  /** Company name — used for initials fallback and alt text */
  companyName?: string
  /** Logo proxy URL from API (e.g., "/api/logo/ionq.com") */
  logoUrl?: string | null
  /** Size in pixels (default 20) */
  size?: number
  /** Additional CSS classes */
  className?: string
}

export default function CompanyLogo({
  domain,
  companyName,
  logoUrl,
  size = 20,
  className,
}: CompanyLogoProps) {
  const [imgError, setImgError] = useState(false)

  const getLogoUrl = (): string | null => {
    if (logoUrl) {
      if (logoUrl.startsWith('http')) return logoUrl
      if (logoUrl.startsWith('/')) return logoUrl
    }
    if (domain) {
      const cleanDomain = domain
        .toLowerCase()
        .replace(/^https?:\/\//, '')
        .replace(/^www\./, '')
        .split('/')[0]
      return `/api/logo/${cleanDomain}`
    }
    return null
  }

  const finalLogoUrl = getLogoUrl()

  // ----- Fallback: initials or icon -----
  if (!finalLogoUrl || imgError) {
    if (companyName) {
      const initials = companyName
        .split(/[\s\-]+/)
        .map((w) => w[0])
        .filter(Boolean)
        .slice(0, 2)
        .join('')
        .toUpperCase()

      return (
        <span
          className={`inline-flex items-center justify-center rounded bg-bg-tertiary
                      text-text-muted font-bold shrink-0 ${className ?? ''}`}
          style={{
            width: size,
            height: size,
            fontSize: size * 0.4,
            lineHeight: 1,
          }}
          title={companyName}
        >
          {initials}
        </span>
      )
    }

    return (
      <span
        className={`inline-flex items-center justify-center rounded bg-bg-tertiary shrink-0 ${className ?? ''}`}
        style={{ width: size, height: size }}
        title={domain ?? 'Company'}
      >
        <Building2
          className="text-text-muted"
          style={{ width: size * 0.55, height: size * 0.55 }}
        />
      </span>
    )
  }

  return (
    <img
      src={finalLogoUrl}
      alt={companyName ?? domain ?? 'Company logo'}
      className={`rounded object-contain bg-white border border-border shrink-0 ${className ?? ''}`}
      style={{ width: size, height: size }}
      onError={() => setImgError(true)}
      loading="lazy"
    />
  )
}
