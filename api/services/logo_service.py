"""
Logo.dev Service for Company Logo Fetching
==========================================

Provides:
- Logo proxy endpoint to keep API token server-side
- Company name → domain heuristics
- Domain extraction from URLs

The KNOWN_DOMAINS map covers quantum computing and AI ecosystem companies.
"""

import os
import re
import logging
from typing import Optional
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# ─── Token ────────────────────────────────────────────────

LOGO_DEV_TOKEN: str = os.getenv("LOGO_DEV_TOKEN", "")


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


# ─── Company → Domain Map ────────────────────────────────
# Covers quantum computing ecosystem + AI ecosystem companies.
# Organized by sector. Extend as needed.

KNOWN_DOMAINS: dict[str, str] = {
    # ── Quantum Pure-Play (Public) ──────────────────────
    "ionq": "ionq.com",
    "ionq inc.": "ionq.com",
    "ionq inc": "ionq.com",
    "d-wave": "dwavesys.com",
    "d-wave quantum": "dwavesys.com",
    "d-wave quantum inc.": "dwavesys.com",
    "d-wave systems": "dwavesys.com",
    "rigetti": "rigetti.com",
    "rigetti computing": "rigetti.com",
    "rigetti computing inc.": "rigetti.com",
    "quantum computing inc.": "quantumcomputinginc.com",
    "quantum computing inc": "quantumcomputinginc.com",
    "arqit": "arqit.uk",
    "arqit quantum": "arqit.uk",
    "arqit quantum inc.": "arqit.uk",
    "quantum corporation": "quantum.com",
    "quantum emotion": "quantumemotion.com",
    "quantum emotion corp.": "quantumemotion.com",
    "sealsq": "sealsq.com",
    "sealsq corp.": "sealsq.com",

    # ── Quantum Private ─────────────────────────────────
    "quantinuum": "quantinuum.com",
    "psiquantum": "psiquantum.com",
    "xanadu": "xanadu.ai",
    "atom computing": "atom-computing.com",
    "quera": "quera.com",
    "quera computing": "quera.com",
    "pasqal": "pasqal.com",
    "alice & bob": "alice-bob.com",
    "alice and bob": "alice-bob.com",
    "iqm": "meetiqm.com",
    "iqm quantum": "meetiqm.com",
    "quantum machines": "quantum-machines.co",
    "nord quantique": "nordquantique.ca",
    "zapata": "zapatacomputing.com",
    "zapata computing": "zapatacomputing.com",
    "strangeworks": "strangeworks.com",
    "classiq": "classiq.io",
    "q-ctrl": "q-ctrl.com",
    "qctrl": "q-ctrl.com",
    "oxford quantum circuits": "oqc.tech",
    "oqc": "oqc.tech",
    "infleqtion": "infleqtion.com",
    "coldquanta": "infleqtion.com",
    "multiverse computing": "multiversecomputing.com",
    "sandbox aq": "sandboxaq.com",
    "sandboxaq": "sandboxaq.com",

    # ── Major Tech (Quantum + AI) ───────────────────────
    "google": "google.com",
    "alphabet": "abc.xyz",
    "alphabet (google)": "google.com",
    "google quantum ai": "quantumai.google",
    "ibm": "ibm.com",
    "ibm quantum": "ibm.com",
    "microsoft": "microsoft.com",
    "azure quantum": "azure.microsoft.com",
    "amazon": "amazon.com",
    "aws": "aws.amazon.com",
    "amazon web services": "aws.amazon.com",
    "honeywell": "honeywell.com",
    "nvidia": "nvidia.com",
    "meta": "meta.com",
    "meta platforms": "meta.com",
    "facebook": "meta.com",
    "apple": "apple.com",
    "tesla": "tesla.com",
    "intel": "intel.com",
    "qualcomm": "qualcomm.com",
    "salesforce": "salesforce.com",
    "oracle": "oracle.com",
    "sap": "sap.com",
    "cisco": "cisco.com",

    # ── AI Pure-Play (Public) ───────────────────────────
    "palantir": "palantir.com",
    "palantir technologies": "palantir.com",
    "c3.ai": "c3.ai",
    "c3 ai": "c3.ai",
    "uipath": "uipath.com",
    "soundhound": "soundhound.com",
    "soundhound ai": "soundhound.com",
    "bigbear.ai": "bigbear.ai",
    "bigbear ai": "bigbear.ai",
    "applovin": "applovin.com",
    "coreweave": "coreweave.com",
    "arm": "arm.com",
    "arm holdings": "arm.com",
    "snowflake": "snowflake.com",
    "servicenow": "servicenow.com",
    "datadog": "datadoghq.com",
    "databricks": "databricks.com",
    "scale ai": "scale.com",
    "cohere": "cohere.com",

    # ── AI Infrastructure & Silicon ─────────────────────
    "amd": "amd.com",
    "advanced micro devices": "amd.com",
    "broadcom": "broadcom.com",
    "marvell": "marvell.com",
    "marvell technology": "marvell.com",
    "tsmc": "tsmc.com",
    "super micro computer": "supermicro.com",
    "supermicro": "supermicro.com",
    "cerebras": "cerebras.net",
    "cerebras systems": "cerebras.net",
    "groq": "groq.com",
    "graphcore": "graphcore.ai",
    "sambanova": "sambanova.ai",
    "sambanova systems": "sambanova.ai",
    "lambda": "lambdalabs.com",

    # ── AI Labs & Research ──────────────────────────────
    "openai": "openai.com",
    "anthropic": "anthropic.com",
    "deepmind": "deepmind.com",
    "google deepmind": "deepmind.com",
    "mistral": "mistral.ai",
    "mistral ai": "mistral.ai",
    "stability ai": "stability.ai",
    "hugging face": "huggingface.co",
    "huggingface": "huggingface.co",
    "midjourney": "midjourney.com",
    "runway": "runwayml.com",
    "runway ml": "runwayml.com",
    "inflection ai": "inflection.ai",
    "character.ai": "character.ai",
    "together ai": "together.ai",
    "perplexity": "perplexity.ai",
    "perplexity ai": "perplexity.ai",
    "xai": "x.ai",
    "replicate": "replicate.com",
    "anyscale": "anyscale.com",
    "adept ai": "adept.ai",
    "aleph alpha": "aleph-alpha.com",

    # ── Cloud & Enterprise ──────────────────────────────
    "google cloud": "cloud.google.com",
    "azure": "azure.microsoft.com",
    "cloudflare": "cloudflare.com",
    "dell": "dell.com",
    "dell technologies": "dell.com",
    "hpe": "hpe.com",
    "hewlett packard enterprise": "hpe.com",
    "accenture": "accenture.com",
    "deloitte": "deloitte.com",
    "mckinsey": "mckinsey.com",
    "boston consulting group": "bcg.com",
    "bcg": "bcg.com",

    # ── Defense & Government ────────────────────────────
    "lockheed martin": "lockheedmartin.com",
    "boeing": "boeing.com",
    "raytheon": "rtx.com",
    "rtx": "rtx.com",
    "northrop grumman": "northropgrumman.com",
    "bae systems": "baesystems.com",
    "booz allen hamilton": "boozallen.com",
    "booz allen": "boozallen.com",
    "darpa": "darpa.mil",
    "leidos": "leidos.com",

    # ── Financial ───────────────────────────────────────
    "jpmorgan": "jpmorgan.com",
    "jp morgan": "jpmorgan.com",
    "jpmorgan chase": "jpmorgan.com",
    "goldman sachs": "goldmansachs.com",
    "morgan stanley": "morganstanley.com",
    "hsbc": "hsbc.com",
    "barclays": "barclays.com",
    "wells fargo": "wellsfargo.com",
    "citigroup": "citigroup.com",
    "citi": "citigroup.com",

    # ── Pharma & Biotech (Quantum Use Cases) ────────────
    "roche": "roche.com",
    "merck": "merck.com",
    "pfizer": "pfizer.com",
    "biogen": "biogen.com",
    "moderna": "modernatx.com",
    "johnson & johnson": "jnj.com",
    "j&j": "jnj.com",

    # ── Automotive (AI/Quantum) ─────────────────────────
    "volkswagen": "volkswagen.com",
    "vw": "volkswagen.com",
    "bmw": "bmw.com",
    "mercedes": "mercedes-benz.com",
    "mercedes-benz": "mercedes-benz.com",
    "toyota": "toyota.com",
    "hyundai": "hyundai.com",

    # ── Academic / Research Orgs ────────────────────────
    "mit": "mit.edu",
    "harvard": "harvard.edu",
    "stanford": "stanford.edu",
    "caltech": "caltech.edu",
    "berkeley": "berkeley.edu",
    "uc berkeley": "berkeley.edu",
    "yale": "yale.edu",
    "oxford": "ox.ac.uk",
    "university of oxford": "ox.ac.uk",
    "cambridge": "cam.ac.uk",
    "university of cambridge": "cam.ac.uk",
    "eth zurich": "ethz.ch",
    "delft": "tudelft.nl",
    "tu delft": "tudelft.nl",
    "nist": "nist.gov",
}


def company_name_to_domain(company_name: str) -> str:
    """Convert company name to likely domain.

    Uses a known-domains lookup first, then falls back to heuristic
    cleaning (strip suffixes like Inc/LLC/Corp, append .com).

    Examples:
        "IonQ" -> "ionq.com" (known)
        "NVIDIA" -> "nvidia.com" (known)
        "Acme Solutions Inc." -> "acmesolutions.com" (heuristic)
    """
    if not company_name:
        return ""

    name_lower = company_name.lower().strip()
    if name_lower in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[name_lower]

    # Heuristic: Remove corporate suffixes → join → .com
    clean_name = name_lower
    suffixes = [
        r"\s*,?\s*inc\.?$", r"\s*,?\s*llc\.?$", r"\s*,?\s*ltd\.?$",
        r"\s*,?\s*corp\.?$", r"\s*,?\s*corporation$", r"\s*,?\s*company$",
        r"\s*,?\s*co\.?$", r"\s*,?\s*group$", r"\s*,?\s*holdings?$",
        r"\s*,?\s*international$", r"\s*,?\s*industries$",
        r"\s*,?\s*technologies$", r"\s*,?\s*technology$",
        r"\s*,?\s*systems$",
    ]
    for suffix in suffixes:
        clean_name = re.sub(suffix, "", clean_name, flags=re.IGNORECASE)

    domain_base = re.sub(r"[^a-z0-9]", "", clean_name)
    return f"{domain_base}.com" if domain_base else ""


class LogoService:
    """Service for fetching company logos via Logo.dev."""

    def __init__(self) -> None:
        self.token = LOGO_DEV_TOKEN
        if not self.token:
            logger.warning("[LOGO] LOGO_DEV_TOKEN not configured — logos will be unavailable")
        else:
            logger.info("[LOGO] Logo.dev service initialized")

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
        return f"/api/logo/{domain}"

    async def fetch_logo(self, domain: str) -> Optional[bytes]:
        """Fetch logo PNG bytes from Logo.dev API.

        Called by the proxy endpoint. Returns None if not found.
        Uses aiohttp (already a project dependency) instead of httpx.
        """
        if not self.token or not domain:
            return None

        url = f"https://img.logo.dev/{domain}?token={self.token}&size=128&format=png"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        logger.warning(f"[LOGO] Logo.dev returned {resp.status} for {domain}")
                        return None
        except Exception as e:
            logger.error(f"[LOGO] Error fetching logo for {domain}: {e}")
            return None


# Singleton
logo_service = LogoService()


def enrich_companies_with_logos(companies: list[str]) -> list[dict]:
    """Convert a list of company names into logo-enriched objects.

    Returns list of {name, domain, logo_url} dicts.
    Used by API endpoints to enrich response data.
    """
    enriched = []
    seen = set()
    for company in companies:
        if not company or company in seen:
            continue
        seen.add(company)
        domain = company_name_to_domain(company)
        logo_url = logo_service.get_logo_url(domain) if domain else None
        enriched.append({
            "name": company,
            "domain": domain,
            "logo_url": logo_url,
        })
    return enriched
