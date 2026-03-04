# Logo.dev Integration Guide

> **Purpose**: This document captures the complete Logo.dev inline company logo integration pattern used in the C1 Intelligence Hub. Follow this guide to replicate the feature in another project.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Logo.dev API Basics](#logodev-api-basics)
4. [Step 1: API Key Setup](#step-1-api-key-setup)
5. [Step 2: Backend Logo Service](#step-2-backend-logo-service)
6. [Step 3: Backend Proxy Endpoint](#step-3-backend-proxy-endpoint)
7. [Step 4: Company Name → Domain Mapping](#step-4-company-name--domain-mapping)
8. [Step 5: Enriching Data with Logo URLs](#step-5-enriching-data-with-logo-urls)
9. [Step 6: LLM Inline Logo Tags](#step-6-llm-inline-logo-tags)
10. [Step 7: Frontend CompanyLogo Component](#step-7-frontend-companylogo-component)
11. [Step 8: Frontend Text Parser for Inline Logos](#step-8-frontend-text-parser-for-inline-logos)
12. [Step 9: TypeScript Types](#step-9-typescript-types)
13. [Complete Data Flow](#complete-data-flow)
14. [Key Design Decisions](#key-design-decisions)
15. [Gotchas & Tips](#gotchas--tips)
16. [Quick Start Checklist](#quick-start-checklist)

---

## Overview

Logo.dev provides high-quality company logos by domain name. We use it to render inline company logos in LLM-generated text (briefings, research reports) and in structured UI cards (search results, company directories).

**The pattern has two modes**:

1. **Structured logos** — Backend enriches `companies_mentioned` arrays with domain + logo proxy URL. Frontend renders `<CompanyLogo>` components in cards/headers.
2. **Inline logos** — LLM wraps company names in `[[Company Name]]` double brackets. Frontend parses the text, extracts company names, looks them up in the enriched array, and renders inline logos next to the name.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ LLM Output                                                      │
│ "[[Boeing]] announced a $2.4B deal with [[Airbus]]..."          │
│ companies_mentioned: ["Boeing", "Airbus"]                        │
└────────────┬───────────────────────┬────────────────────────────┘
             │                       │
             ▼                       ▼
┌────────────────────┐   ┌───────────────────────────────────────┐
│ Text stored as-is  │   │ _enrich_with_logos(["Boeing","Airbus"])│
│ (with [[ ]] tags)  │   │                                       │
│                    │   │ company_name_to_domain("Boeing")       │
│                    │   │ → "boeing.com" (from KNOWN_DOMAINS)    │
│                    │   │                                       │
│                    │   │ logo_service.get_logo_url("boeing.com")│
│                    │   │ → "/api/pipeline/logo/boeing.com"      │
│                    │   │                                       │
│                    │   │ Result: {name, domain, logo_url}       │
└────────┬───────────┘   └───────────────┬───────────────────────┘
         │                               │
         ▼                               ▼
┌────────────────────────────────────────────────────────────────┐
│ Frontend: renderTextWithLogosAndCitations()                    │
│                                                                │
│ 1. Split text on regex: /(\[\[.*?\]\])/                        │
│ 2. Match [[Boeing]] → find in companiesWithLogos array         │
│ 3. Render: <bold>Boeing</bold> <CompanyLogo domain="boeing.com">│
└────────────────────────────────────────────┬───────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────┐
│ Browser: GET /api/pipeline/logo/boeing.com                     │
│          → Backend proxy → Logo.dev API                        │
│          → PNG bytes (cached 7 days)                           │
└────────────────────────────────────────────────────────────────┘
```

---

## Logo.dev API Basics

- **Endpoint**: `https://img.logo.dev/{domain}`
- **Auth**: Query parameter `token={YOUR_TOKEN}`
- **Params**: `size=128`, `format=png`
- **Full URL**: `https://img.logo.dev/boeing.com?token=YOUR_TOKEN&size=128&format=png`
- **Response**: PNG image bytes
- **Pricing**: See [logo.dev/pricing](https://logo.dev/pricing)
- **Sign up**: [logo.dev](https://logo.dev)

---

## Step 1: API Key Setup

### Get a Token
1. Sign up at [logo.dev](https://logo.dev)
2. Generate an API token from the dashboard

### Store in Environment

**Local development** (`.env` file):
```env
LOGO_DEV_TOKEN=pk_your_token_here
```

**GCP Secret Manager** (production):
```powershell
$key = "pk_your_token_here"
$key | gcloud secrets create LOGO_DEV_TOKEN --data-file=- --project=$PROJECT_ID
```

**Cloud Run deployment** (in `cloudbuild.yaml` `--set-secrets` line):
```yaml
LOGO_DEV_TOKEN=LOGO_DEV_TOKEN:latest
```

### Backend Settings (Pydantic)

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Logo.dev API (for company logos)
    logo_dev_token: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Step 2: Backend Logo Service

Create a service module that wraps the Logo.dev API. This keeps the token server-side and provides domain extraction utilities.

**File**: `app/services/logo_service.py`

```python
"""
Logo.dev Service for Company Logo Fetching

Provides:
- Logo proxy endpoint to keep API token server-side
- Company name to domain heuristics
- Domain extraction from URLs
"""

import re
import httpx
from typing import Optional
from urllib.parse import urlparse
from app.config.settings import settings

import logging
logger = logging.getLogger(__name__)


def extract_domain(url: str) -> str:
    """Extract clean domain from URL.
    
    Examples:
        "https://www.boeing.com/about" -> "boeing.com"
        "compositesone.com" -> "compositesone.com"
    """
    if not url:
        return ""
    try:
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.split(":")[0]  # Remove port
        return domain.lower().strip()
    except Exception:
        return ""


def company_name_to_domain(company_name: str) -> str:
    """Convert company name to likely domain.
    
    Uses a known-domains lookup first, then falls back to heuristic
    cleaning (strip suffixes like Inc/LLC/Corp, append .com).
    
    Examples:
        "Boeing" -> "boeing.com" (known)
        "General Electric" -> "ge.com" (known)
        "Acme Solutions Inc." -> "acmesolutions.com" (heuristic)
    """
    if not company_name:
        return ""
    
    # CUSTOMIZE THIS for your industry/domain
    KNOWN_DOMAINS = {
        "general electric": "ge.com",
        "ge": "ge.com",
        "3m": "3m.com",
        "3m company": "3m.com",
        "boeing": "boeing.com",
        "the boeing company": "boeing.com",
        "airbus": "airbus.com",
        "lockheed martin": "lockheedmartin.com",
        # Add your key companies here...
    }
    
    name_lower = company_name.lower().strip()
    if name_lower in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[name_lower]
    
    # Heuristic: Remove corporate suffixes → join → .com
    clean_name = name_lower
    suffixes = [
        r'\s*,?\s*inc\.?$', r'\s*,?\s*llc\.?$', r'\s*,?\s*ltd\.?$',
        r'\s*,?\s*corp\.?$', r'\s*,?\s*corporation$', r'\s*,?\s*company$',
        r'\s*,?\s*co\.?$', r'\s*,?\s*group$', r'\s*,?\s*holdings?$',
        r'\s*,?\s*international$', r'\s*,?\s*industries$',
    ]
    for suffix in suffixes:
        clean_name = re.sub(suffix, '', clean_name, flags=re.IGNORECASE)
    
    domain_base = re.sub(r'[^a-z0-9]', '', clean_name)
    return f"{domain_base}.com" if domain_base else ""


class LogoService:
    """Service for fetching company logos via Logo.dev."""
    
    def __init__(self):
        self.token = settings.logo_dev_token
        if not self.token:
            logger.warning("LOGO_DEV_TOKEN not configured")
        else:
            logger.info(f"Logo.dev service initialized")
    
    def get_logo_url(self, domain: str) -> Optional[str]:
        """Return the backend proxy path for a domain.
        
        This does NOT include the token — the proxy endpoint adds it.
        Frontend calls this relative URL to fetch the logo.
        """
        if not domain:
            return None
        domain = extract_domain(domain) if "/" in domain else domain.lower().strip()
        if not domain:
            return None
        return f"/api/pipeline/logo/{domain}"
    
    async def fetch_logo(self, domain: str) -> Optional[bytes]:
        """Fetch logo PNG bytes from Logo.dev API.
        
        Called by the proxy endpoint. Returns None if not found.
        """
        if not self.token or not domain:
            return None
        
        url = f"https://img.logo.dev/{domain}?token={self.token}&size=128&format=png"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.warning(f"Logo.dev returned {response.status_code} for {domain}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching logo for {domain}: {e}")
            return None


# Singleton
logo_service = LogoService()
```

**Key points**:
- `get_logo_url()` returns a **relative proxy path**, not the direct Logo.dev URL
- `fetch_logo()` is the only place the token appears — called by the proxy endpoint
- `company_name_to_domain()` has a hardcoded lookup for accuracy on known companies, plus a heuristic fallback
- `httpx` is used with a 10-second timeout

---

## Step 3: Backend Proxy Endpoint

Create a FastAPI route that proxies logo requests. This keeps the API token server-side and adds aggressive caching.

**File**: `app/api/routes/your_router.py`

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.services.logo_service import logo_service

router = APIRouter(prefix="/api/pipeline")

@router.get("/logo/{domain}")
async def get_company_logo(domain: str):
    """Proxy endpoint for fetching company logos from Logo.dev.
    
    Keeps the API token server-side and adds cache headers.
    Frontend calls: GET /api/pipeline/logo/boeing.com
    """
    try:
        logo_bytes = await logo_service.fetch_logo(domain)
        
        if logo_bytes:
            return Response(
                content=logo_bytes,
                media_type="image/png",
                headers={
                    # Cache for 7 days — logos rarely change
                    "Cache-Control": "public, max-age=604800, immutable",
                    "X-Logo-Domain": domain,
                }
            )
        else:
            raise HTTPException(status_code=404, detail=f"Logo not found for {domain}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logo: {str(e)}")
```

**Key points**:
- 7-day cache (`max-age=604800`) with `immutable` — browser won't re-request
- Returns 404 when Logo.dev doesn't have the logo — frontend shows a fallback
- Token is never exposed to the client

---

## Step 4: Company Name → Domain Mapping

The `company_name_to_domain()` function in the logo service handles this. The general approach:

1. **Known domains map**: Hardcode your most important companies. This is critical for companies where the domain doesn't match the name (e.g., "General Electric" → `ge.com`, "Spirit AeroSystems" → `spiritaero.com`, "Raytheon" → `rtx.com`).

2. **Heuristic fallback**: Strip corporate suffixes (Inc, LLC, Corp, etc.), remove non-alphanumeric characters, append `.com`. Works for ~80% of companies.

**Tip**: Build out KNOWN_DOMAINS as you go. When you notice a logo not rendering, check what domain is being generated and add a mapping.

---

## Step 5: Enriching Data with Logo URLs

When your backend produces data that includes company names (from LLM output, database queries, etc.), enrich them with logo info before sending to the frontend.

### Pydantic Model

```python
from pydantic import BaseModel
from typing import Optional

class CompanyWithLogo(BaseModel):
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
```

### Enrichment Function

```python
from app.services.logo_service import company_name_to_domain, logo_service

def enrich_with_logos(companies: list[str]) -> list[dict]:
    """Convert a list of company names into logo-enriched objects."""
    enriched = []
    for company in companies:
        domain = company_name_to_domain(company)
        logo_url = logo_service.get_logo_url(domain) if domain else None
        enriched.append({
            "name": company,
            "domain": domain,
            "logo_url": logo_url,
        })
    return enriched
```

### Usage in API Response

```python
# Example: LLM returns companies_mentioned: ["Boeing", "Airbus"]
companies = llm_output["companies_mentioned"]
companies_with_logos = enrich_with_logos(companies)

# Result:
# [
#   {"name": "Boeing", "domain": "boeing.com", "logo_url": "/api/pipeline/logo/boeing.com"},
#   {"name": "Airbus", "domain": "airbus.com", "logo_url": "/api/pipeline/logo/airbus.com"},
# ]
```

---

## Step 6: LLM Inline Logo Tags

To get inline logos in LLM-generated text, instruct the LLM to wrap company names in double brackets.

### Prompt Instructions

Add this to your LLM system prompt:

```
INLINE LOGOS:
- Wrap company names in double brackets: [[Company Name]]
- Use the EXACT company name as it appears in your companies_mentioned list
- Example: "[[Boeing]] announced a partnership with [[Airbus]] to develop..."
- Do NOT nest brackets or use logos for non-company entities
```

### LLM Output Example

```json
{
  "text": "[[Boeing]] announced a $2.4B partnership with [[Airbus]] to develop next-gen composite fuselages [1].",
  "companies_mentioned": ["Boeing", "Airbus"]
}
```

The text is stored as-is with the `[[...]]` tags. The frontend parser handles rendering.

### Optional: Entity Highlighting

You can extend this pattern for non-company entities:

```
ENTITY HIGHLIGHTING:
- Wrap important non-company entities in double curly braces: {{Entity Name}}
- Use for technologies, materials, products: "{{carbon fiber}} production..."
```

---

## Step 7: Frontend CompanyLogo Component

A reusable React component that renders a company logo with fallback.

**File**: `components/CompanyLogo.tsx`

```tsx
'use client'

import { useState } from 'react'
import { Building2 } from 'lucide-react'  // or any fallback icon

// Set this based on your environment
// Dev: "http://localhost:8000", Prod: "" (same origin)
const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface CompanyLogoProps {
  /** Company domain (e.g., "boeing.com") */
  domain?: string | null
  /** Logo proxy URL from API (e.g., "/api/pipeline/logo/boeing.com") */
  logoUrl?: string | null
  /** Size in pixels (default 40) */
  size?: number
  /** Additional CSS classes */
  className?: string
}

export default function CompanyLogo({ 
  domain, 
  logoUrl,
  size = 40, 
  className 
}: CompanyLogoProps) {
  const [imgError, setImgError] = useState(false)
  
  const getLogoUrl = (): string | null => {
    if (logoUrl) {
      if (logoUrl.startsWith('http')) return logoUrl
      if (logoUrl.startsWith('/')) return `${API_BASE}${logoUrl}`
    }
    if (domain) {
      const cleanDomain = domain
        .toLowerCase()
        .replace(/^https?:\/\//, '')
        .replace(/^www\./, '')
        .split('/')[0]
      return `${API_BASE}/api/pipeline/logo/${cleanDomain}`
    }
    return null
  }
  
  const finalLogoUrl = getLogoUrl()
  
  // Fallback: Building icon
  if (!finalLogoUrl || imgError) {
    return (
      <div 
        className={`bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg 
                     flex items-center justify-center shrink-0 ${className || ''}`}
        style={{ width: size, height: size }}
        title={domain || 'Company'}
      >
        <Building2 
          className="text-slate-400" 
          style={{ width: size * 0.5, height: size * 0.5 }}
        />
      </div>
    )
  }
  
  return (
    <img 
      src={finalLogoUrl}
      alt={domain || 'Company logo'}
      className={`rounded-lg object-contain bg-white border border-slate-200 
                   shrink-0 ${className || ''}`}
      style={{ width: size, height: size }}
      onError={() => setImgError(true)}
      loading="lazy"
    />
  )
}
```

**Key points**:
- Accepts either `domain` or `logoUrl` (the proxy path from the API)
- `onError` handler hides broken images and shows the fallback
- `loading="lazy"` for performance
- Clean domain stripping handles `www.` and protocol prefixes
- Fallback uses a `Building2` icon from lucide-react — swap for initials if preferred

### Alternative: Initials Fallback

For a text-based fallback (used in the weekly briefing inline logos):

```tsx
// Fallback: 2-letter initials
if (!logoUrl || imgError) {
  const initials = companyName
    .split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
    
  return (
    <div
      className="w-5 h-5 rounded bg-slate-200 flex items-center justify-center 
                 text-[8px] font-bold text-slate-500"
      title={companyName}
    >
      {initials}
    </div>
  )
}
```

---

## Step 8: Frontend Text Parser for Inline Logos

This is the core innovation — parsing `[[Company Name]]` tags from LLM text into rendered logos.

**File**: Include in the component that renders LLM-generated text.

```tsx
import { CompanyWithLogo } from '@/types/briefing'

/**
 * Parse text containing [[Company Name]] tags into React elements
 * with inline logos.
 * 
 * Also handles:
 * - [N] citation superscripts (clickable if source URL available)
 * - {{Entity}} bold entity highlights
 */
const renderTextWithLogos = (
  text: string,
  companiesWithLogos: CompanyWithLogo[],
) => {
  // Split on [[Company Name]] tags
  // Extend the regex if you also want citations [N] or entities {{Entity}}
  const parts = text.split(/(\[\[.*?\]\])/g)

  return parts.map((part, idx) => {
    // Handle company logos [[Company]]
    if (/^\[\[.*?\]\]$/.test(part)) {
      const companyName = part.replace(/[\[\]]/g, '')
      const company = companiesWithLogos.find(c => c.name === companyName)

      return (
        <span key={idx} className="inline-flex items-center gap-1.5 align-baseline">
          <span className="font-bold text-slate-900 mx-0.5">{companyName}</span>
          {company?.domain && (
            <span className="inline-block transform translate-y-0.5 shadow-sm rounded-sm">
              <CompanyLogo domain={company.domain} size={20} />
            </span>
          )}
        </span>
      )
    }

    // Plain text
    return <span key={idx}>{part}</span>
  })
}
```

### Extended Version with Citations and Entity Highlights

The C1 Hub uses a more complex regex to handle multiple tag types:

```tsx
const renderTextWithLogosAndCitations = (
  text: string,
  companiesWithLogos: CompanyWithLogo[],
  sourceArticles?: SourceArticle[]
) => {
  // Split on: [N] citations, [[Company]] logos, {{Entity}} highlights
  const parts = text.split(
    /(\[(?:Exa:)?\d+\]|\[\[.*?\]\]|\{\{.*?\}\}|\{[^{}]+\})/g
  )

  return parts.map((part, idx) => {
    // Citations [N] or [Exa:N]
    if (/^\[(?:Exa:)?\d+\]$/.test(part)) {
      const num = part.replace(/[\[\]Exa:]/g, '')
      return (
        <sup key={idx} className="text-emerald-600 font-semibold ml-0.5">
          {num}
        </sup>
      )
    }

    // Company logos [[Company]]
    if (/^\[\[.*?\]\]$/.test(part)) {
      const companyName = part.replace(/[\[\]]/g, '')
      const company = companiesWithLogos.find(c => c.name === companyName)
      return (
        <span key={idx} className="inline-flex items-center gap-1.5 align-baseline">
          <span className="font-bold text-slate-900 mx-0.5">{companyName}</span>
          {company?.domain && (
            <span className="inline-block transform translate-y-0.5">
              <CompanyLogo domain={company.domain} size={20} />
            </span>
          )}
        </span>
      )
    }

    // Entity highlights {{Entity}}
    if (/^\{\{.*?\}\}$/.test(part)) {
      const entity = part.replace(/[\{\}]/g, '')
      return (
        <span key={idx} className="font-bold text-slate-800 bg-slate-100/50 px-1 rounded">
          {entity}
        </span>
      )
    }

    return <span key={idx}>{part}</span>
  })
}
```

### Usage

```tsx
<p className="text-slate-700 leading-relaxed">
  {renderTextWithLogos(section.text, section.companies_with_logos)}
</p>
```

---

## Step 9: TypeScript Types

```typescript
// types/briefing.ts (or wherever your types live)

export interface CompanyWithLogo {
  name: string
  domain?: string
  logo_url?: string
}

// Example: used in a briefing section
export interface BriefingSection {
  title: string
  text: string  // Contains [[Company Name]] tags
  companies_with_logos: CompanyWithLogo[]
  source_articles?: SourceArticle[]
}

export interface SourceArticle {
  article_number: number
  title: string
  url: string
}
```

---

## Complete Data Flow

```
1. LLM generates text with [[Company Name]] tags
   + companies_mentioned: ["Boeing", "Airbus"]

2. Backend enriches companies:
   enrich_with_logos(["Boeing", "Airbus"])
   → [{name: "Boeing", domain: "boeing.com", logo_url: "/api/pipeline/logo/boeing.com"}, ...]

3. API sends to frontend:
   { text: "[[Boeing]] signed...", companies_with_logos: [...] }

4. Frontend parses text:
   text.split(/(\[\[.*?\]\])/g)
   → ["", "[[Boeing]]", " signed..."]

5. For each [[Company]] match:
   - Extract name → "Boeing"
   - Find in companies_with_logos → { domain: "boeing.com" }
   - Render: <bold>Boeing</bold> <CompanyLogo domain="boeing.com" size={20} />

6. CompanyLogo component:
   - Constructs URL: GET {API_BASE}/api/pipeline/logo/boeing.com
   - Renders <img> with onError fallback

7. Backend proxy:
   - Receives GET /api/pipeline/logo/boeing.com
   - Calls Logo.dev: https://img.logo.dev/boeing.com?token=XXX&size=128&format=png
   - Returns PNG with 7-day cache headers

8. Browser caches the image for 7 days (immutable)
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Backend proxy** instead of direct Logo.dev URLs | Keeps API token server-side; enables caching headers; single point to swap providers |
| **`[[Double brackets]]`** for company tags | Unambiguous, won't clash with Markdown `[links]` or citation `[1]` patterns |
| **Known domains map** over pure heuristic | Accuracy matters — "GE" → `ge.com` can't be derived algorithmically |
| **7-day immutable cache** | Logos change extremely rarely; reduces API calls dramatically |
| **Initials fallback** | Graceful degradation when Logo.dev doesn't have the company |
| **`onError` handler** on `<img>` | Handles 404s, network errors, Logo.dev outages cleanly |
| **Singleton service** | One instance, lazy init, avoids repeated initialization |

---

## Gotchas & Tips

1. **Name matching is exact**: `[[Boeing]]` must match `companies_with_logos.find(c => c.name === "Boeing")`. If the LLM writes `[[The Boeing Company]]` but the enriched array has `name: "Boeing"`, it won't match. Instruct the LLM to use exact names.

2. **The `logo_url` field is redundant**: In practice, the frontend constructs the URL from `domain` directly. The `logo_url` field exists for convenience but the frontend ignores it in the inline logo path.

3. **Logo.dev may not have every company**: Small/private companies often have no logo. Always implement a fallback (initials or icon).

4. **Domain cleaning matters**: Always strip `www.`, protocol, ports, and trailing paths before calling the API.

5. **Don't call Logo.dev directly from the browser**: The token would be exposed in network requests. Always proxy through your backend.

6. **`align-baseline` + `translate-y-0.5`**: The inline logo needs careful vertical alignment to look right next to text. These CSS utilities handle it.

7. **`httpx` over `requests`**: Use async HTTP client for the proxy endpoint since FastAPI is async. 10-second timeout prevents hanging.

8. **Build your KNOWN_DOMAINS map for your industry**: This is the highest-impact improvement. Add 20-30 key companies and your logo accuracy jumps dramatically.

---

## Quick Start Checklist

- [ ] Sign up at [logo.dev](https://logo.dev) and get API token
- [ ] Add `LOGO_DEV_TOKEN` to your `.env` / Secret Manager
- [ ] Add `logo_dev_token` to your Pydantic settings
- [ ] Create `logo_service.py` with `LogoService` class + `company_name_to_domain()`
- [ ] Populate `KNOWN_DOMAINS` with your industry's key companies
- [ ] Add proxy endpoint: `GET /api/pipeline/logo/{domain}`
- [ ] Create `CompanyLogo.tsx` frontend component with fallback
- [ ] Add `CompanyWithLogo` TypeScript interface
- [ ] Write `enrich_with_logos()` function for your API responses
- [ ] Add `[[Company Name]]` instructions to your LLM prompts
- [ ] Create `renderTextWithLogos()` parser in your text rendering component
- [ ] Test with a known company (e.g., `boeing.com`) end-to-end
- [ ] Install `httpx` (backend) and `lucide-react` (frontend, for fallback icon)
