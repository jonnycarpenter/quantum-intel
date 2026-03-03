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

// ─── Inline Logo Detection ──────────────────────────────
// Build a regex that matches known company names in narrative text.
// Used by BriefingPage to inject tiny logos inline next to company mentions.

// Canonical display names → domain (only names likely to appear in prose)
const INLINE_LOGO_NAMES: Record<string, string> = {
  // Quantum Pure-Play
  'IonQ': 'ionq.com',
  'D-Wave': 'dwavesys.com',
  'Rigetti': 'rigetti.com',
  'Arqit': 'arqit.uk',
  'SEALSQ': 'sealsq.com',
  'Quantinuum': 'quantinuum.com',
  'PsiQuantum': 'psiquantum.com',
  'Xanadu': 'xanadu.ai',
  'Atom Computing': 'atom-computing.com',
  'QuEra': 'quera.com',
  'Pasqal': 'pasqal.com',
  'Alice & Bob': 'alice-bob.com',
  'IQM': 'meetiqm.com',
  'Quantum Machines': 'quantum-machines.co',
  'Nord Quantique': 'nordquantique.ca',
  'Strangeworks': 'strangeworks.com',
  'Classiq': 'classiq.io',
  'Q-CTRL': 'q-ctrl.com',
  'OQC': 'oqc.tech',
  'Infleqtion': 'infleqtion.com',
  'SandboxAQ': 'sandboxaq.com',
  // Major Tech
  'Google': 'google.com',
  'IBM': 'ibm.com',
  'Microsoft': 'microsoft.com',
  'Amazon': 'amazon.com',
  'AWS': 'aws.amazon.com',
  'Honeywell': 'honeywell.com',
  'NVIDIA': 'nvidia.com',
  'Meta': 'meta.com',
  'Apple': 'apple.com',
  'Tesla': 'tesla.com',
  'Intel': 'intel.com',
  'Qualcomm': 'qualcomm.com',
  'Salesforce': 'salesforce.com',
  'Oracle': 'oracle.com',
  'SAP': 'sap.com',
  'Cisco': 'cisco.com',
  // AI Pure-Play
  'Palantir': 'palantir.com',
  'C3.ai': 'c3.ai',
  'UiPath': 'uipath.com',
  'SoundHound': 'soundhound.com',
  'AppLovin': 'applovin.com',
  'CoreWeave': 'coreweave.com',
  'Arm': 'arm.com',
  'Snowflake': 'snowflake.com',
  'ServiceNow': 'servicenow.com',
  'Datadog': 'datadoghq.com',
  'Databricks': 'databricks.com',
  'Scale AI': 'scale.com',
  'Cohere': 'cohere.com',
  // AI Silicon
  'AMD': 'amd.com',
  'Broadcom': 'broadcom.com',
  'Marvell': 'marvell.com',
  'TSMC': 'tsmc.com',
  'Supermicro': 'supermicro.com',
  'Cerebras': 'cerebras.net',
  'Groq': 'groq.com',
  'SambaNova': 'sambanova.ai',
  // AI Labs
  'OpenAI': 'openai.com',
  'Anthropic': 'anthropic.com',
  'DeepMind': 'deepmind.com',
  'Google DeepMind': 'deepmind.com',
  'Mistral': 'mistral.ai',
  'Stability AI': 'stability.ai',
  'Hugging Face': 'huggingface.co',
  'Midjourney': 'midjourney.com',
  'Perplexity': 'perplexity.ai',
  'xAI': 'x.ai',
  'Together AI': 'together.ai',
  'Replicate': 'replicate.com',
  // Defense
  'Lockheed Martin': 'lockheedmartin.com',
  'Boeing': 'boeing.com',
  'Raytheon': 'rtx.com',
  'Northrop Grumman': 'northropgrumman.com',
  'Booz Allen': 'boozallen.com',
  // Financial
  'JPMorgan': 'jpmorgan.com',
  'Goldman Sachs': 'goldmansachs.com',
  'Morgan Stanley': 'morganstanley.com',
  'HSBC': 'hsbc.com',
  'Barclays': 'barclays.com',
  // Pharma
  'Roche': 'roche.com',
  'Merck': 'merck.com',
  'Pfizer': 'pfizer.com',
  'Moderna': 'modernatx.com',
  // Auto
  'Volkswagen': 'volkswagen.com',
  'BMW': 'bmw.com',
  'Mercedes-Benz': 'mercedes-benz.com',
  'Toyota': 'toyota.com',
  'Hyundai': 'hyundai.com',
}

// Sort names longest-first so "Google DeepMind" matches before "Google"
const INLINE_NAMES_SORTED = Object.keys(INLINE_LOGO_NAMES).sort((a, b) => b.length - a.length)

// Build one regex that matches any known company name at a word boundary
const INLINE_REGEX = new RegExp(
  '(' + INLINE_NAMES_SORTED.map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')(?=[\\s,;:.!?\'\"\\)\\]—–-]|$)',
  'g'
)

export interface InlineLogoMatch {
  /** Offset in the original string where this match starts */
  index: number
  /** The matched company name */
  name: string
  /** Domain for logo proxy */
  domain: string
}

/**
 * Find all known company names in a text string.
 * Returns matches in order of appearance.
 * Only matches the first occurrence of each company per call (to avoid repeating logos).
 */
export function findInlineLogos(text: string): InlineLogoMatch[] {
  const seen = new Set<string>()
  const matches: InlineLogoMatch[] = []

  INLINE_REGEX.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = INLINE_REGEX.exec(text)) !== null) {
    const name = m[1]
    const domain = INLINE_LOGO_NAMES[name]
    // Skip if we already matched this name (only logo the first mention)
    if (seen.has(domain)) continue
    seen.add(domain)
    matches.push({ index: m.index, name, domain })
  }
  return matches
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
