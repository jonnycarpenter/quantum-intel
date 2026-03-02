/**
 * Logo Utilities
 * ==============
 * Client-side company name → domain resolution + helpers for inline logo rendering.
 * Mirrors the backend KNOWN_DOMAINS map from api/services/logo_service.py.
 */

// ─── Known Company → Domain Map ─────────────────────────
// Covers quantum computing + AI ecosystem. Must stay in sync with backend.

const KNOWN_DOMAINS: Record<string, string> = {
  // Quantum Pure-Play (Public)
  'ionq': 'ionq.com',
  'ionq inc.': 'ionq.com',
  'ionq inc': 'ionq.com',
  'd-wave': 'dwavesys.com',
  'd-wave quantum': 'dwavesys.com',
  'd-wave quantum inc.': 'dwavesys.com',
  'rigetti': 'rigetti.com',
  'rigetti computing': 'rigetti.com',
  'rigetti computing inc.': 'rigetti.com',
  'arqit': 'arqit.uk',
  'arqit quantum': 'arqit.uk',
  'quantum corporation': 'quantum.com',
  'sealsq': 'sealsq.com',

  // Quantum Private
  'quantinuum': 'quantinuum.com',
  'psiquantum': 'psiquantum.com',
  'xanadu': 'xanadu.ai',
  'atom computing': 'atom-computing.com',
  'quera': 'quera.com',
  'quera computing': 'quera.com',
  'pasqal': 'pasqal.com',
  'alice & bob': 'alice-bob.com',
  'iqm': 'meetiqm.com',
  'iqm quantum': 'meetiqm.com',
  'quantum machines': 'quantum-machines.co',
  'nord quantique': 'nordquantique.ca',
  'strangeworks': 'strangeworks.com',
  'classiq': 'classiq.io',
  'q-ctrl': 'q-ctrl.com',
  'oqc': 'oqc.tech',
  'infleqtion': 'infleqtion.com',
  'sandboxaq': 'sandboxaq.com',
  'sandbox aq': 'sandboxaq.com',

  // Major Tech
  'google': 'google.com',
  'alphabet': 'abc.xyz',
  'alphabet (google)': 'google.com',
  'ibm': 'ibm.com',
  'microsoft': 'microsoft.com',
  'amazon': 'amazon.com',
  'aws': 'aws.amazon.com',
  'honeywell': 'honeywell.com',
  'nvidia': 'nvidia.com',
  'meta': 'meta.com',
  'meta platforms': 'meta.com',
  'apple': 'apple.com',
  'tesla': 'tesla.com',
  'intel': 'intel.com',
  'qualcomm': 'qualcomm.com',
  'salesforce': 'salesforce.com',
  'oracle': 'oracle.com',
  'sap': 'sap.com',
  'cisco': 'cisco.com',

  // AI Pure-Play
  'palantir': 'palantir.com',
  'palantir technologies': 'palantir.com',
  'c3.ai': 'c3.ai',
  'c3 ai': 'c3.ai',
  'uipath': 'uipath.com',
  'soundhound': 'soundhound.com',
  'soundhound ai': 'soundhound.com',
  'bigbear.ai': 'bigbear.ai',
  'applovin': 'applovin.com',
  'coreweave': 'coreweave.com',
  'arm': 'arm.com',
  'arm holdings': 'arm.com',
  'snowflake': 'snowflake.com',
  'servicenow': 'servicenow.com',
  'datadog': 'datadoghq.com',
  'databricks': 'databricks.com',
  'scale ai': 'scale.com',
  'cohere': 'cohere.com',

  // AI Infrastructure & Silicon
  'amd': 'amd.com',
  'advanced micro devices': 'amd.com',
  'broadcom': 'broadcom.com',
  'marvell': 'marvell.com',
  'marvell technology': 'marvell.com',
  'tsmc': 'tsmc.com',
  'super micro computer': 'supermicro.com',
  'supermicro': 'supermicro.com',
  'cerebras': 'cerebras.net',
  'groq': 'groq.com',
  'sambanova': 'sambanova.ai',

  // AI Labs & Research
  'openai': 'openai.com',
  'anthropic': 'anthropic.com',
  'deepmind': 'deepmind.com',
  'google deepmind': 'deepmind.com',
  'mistral': 'mistral.ai',
  'mistral ai': 'mistral.ai',
  'stability ai': 'stability.ai',
  'hugging face': 'huggingface.co',
  'huggingface': 'huggingface.co',
  'midjourney': 'midjourney.com',
  'perplexity': 'perplexity.ai',
  'perplexity ai': 'perplexity.ai',
  'xai': 'x.ai',
  'together ai': 'together.ai',
  'replicate': 'replicate.com',

  // Defense
  'lockheed martin': 'lockheedmartin.com',
  'boeing': 'boeing.com',
  'raytheon': 'rtx.com',
  'northrop grumman': 'northropgrumman.com',
  'booz allen': 'boozallen.com',

  // Financial
  'jpmorgan': 'jpmorgan.com',
  'jp morgan': 'jpmorgan.com',
  'goldman sachs': 'goldmansachs.com',
  'morgan stanley': 'morganstanley.com',
  'hsbc': 'hsbc.com',
  'barclays': 'barclays.com',

  // Pharma
  'roche': 'roche.com',
  'merck': 'merck.com',
  'pfizer': 'pfizer.com',
  'moderna': 'modernatx.com',

  // Automotive
  'volkswagen': 'volkswagen.com',
  'bmw': 'bmw.com',
  'mercedes-benz': 'mercedes-benz.com',
  'toyota': 'toyota.com',
  'hyundai': 'hyundai.com',
}

/**
 * Resolve a company name to a domain.
 * Known map first, then heuristic fallback.
 */
export function companyNameToDomain(name: string): string {
  if (!name) return ''

  const lower = name.toLowerCase().trim()
  if (KNOWN_DOMAINS[lower]) return KNOWN_DOMAINS[lower]

  // Heuristic: strip suffixes, join, .com
  let clean = lower
    .replace(/[,.]?\s*(inc|llc|ltd|corp|corporation|company|co|group|holdings?|international|industries|technologies|technology|systems)\.?$/i, '')
    .trim()
  const base = clean.replace(/[^a-z0-9]/g, '')
  return base ? `${base}.com` : ''
}

/**
 * Get the proxy logo URL for a company name.
 */
export function getLogoUrlForCompany(name: string): string | null {
  const domain = companyNameToDomain(name)
  return domain ? `/api/logo/${domain}` : null
}

export interface CompanyWithLogo {
  name: string
  domain: string
  logo_url: string | null
}

/**
 * Enrich a list of company names with domain + logo_url.
 * Pure client-side — no API call needed.
 */
export function enrichCompaniesWithLogos(companies: string[]): CompanyWithLogo[] {
  const seen = new Set<string>()
  return companies
    .filter((c) => {
      if (!c || seen.has(c)) return false
      seen.add(c)
      return true
    })
    .map((name) => {
      const domain = companyNameToDomain(name)
      return {
        name,
        domain,
        logo_url: domain ? `/api/logo/${domain}` : null,
      }
    })
}
