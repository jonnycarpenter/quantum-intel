"""
Exa Search Queries — Quantum Computing Intelligence Hub
========================================================

52 use-case oriented queries grouped by strategic theme.
From spec §2.2. Run biweekly.
"""

from typing import List, Dict, Any


EXA_QUERIES: List[Dict[str, Any]] = [
    # =========================================================================
    # Theme 1: Drug Discovery & Healthcare (8 queries)
    # =========================================================================
    {"query": "quantum computing drug discovery clinical trial", "theme": "drug_discovery_healthcare", "id": 1},
    {"query": "quantum simulation protein folding pharmaceutical", "theme": "drug_discovery_healthcare", "id": 2},
    {"query": "quantum computing genomics precision medicine", "theme": "drug_discovery_healthcare", "id": 3},
    {"query": "quantum machine learning medical imaging diagnostics", "theme": "drug_discovery_healthcare", "id": 4},
    {"query": "quantum computing vaccine development molecular simulation", "theme": "drug_discovery_healthcare", "id": 5},
    {"query": "quantum chemistry drug interaction modeling", "theme": "drug_discovery_healthcare", "id": 6},
    {"query": "quantum computing healthcare deployment production", "theme": "drug_discovery_healthcare", "id": 7},
    {"query": "quantum biology enzyme catalysis simulation", "theme": "drug_discovery_healthcare", "id": 8},

    # =========================================================================
    # Theme 2: Financial Services & Optimization (7 queries)
    # =========================================================================
    {"query": "quantum computing portfolio optimization hedge fund", "theme": "financial_services", "id": 9},
    {"query": "quantum Monte Carlo risk analysis financial services", "theme": "financial_services", "id": 10},
    {"query": "quantum computing fraud detection banking", "theme": "financial_services", "id": 11},
    {"query": "quantum advantage derivatives pricing options", "theme": "financial_services", "id": 12},
    {"query": "quantum computing credit risk modeling", "theme": "financial_services", "id": 13},
    {"query": "quantum algorithms trading strategy Wall Street", "theme": "financial_services", "id": 14},
    {"query": "quantum optimization insurance actuarial", "theme": "financial_services", "id": 15},

    # =========================================================================
    # Theme 3: Cybersecurity & Post-Quantum Cryptography (7 queries)
    # =========================================================================
    {"query": "post-quantum cryptography migration enterprise", "theme": "cybersecurity_pqc", "id": 16},
    {"query": "quantum key distribution commercial deployment", "theme": "cybersecurity_pqc", "id": 17},
    {"query": "NIST post-quantum standards implementation timeline", "theme": "cybersecurity_pqc", "id": 18},
    {"query": "quantum threat harvest now decrypt later", "theme": "cybersecurity_pqc", "id": 19},
    {"query": "quantum-safe encryption adoption government", "theme": "cybersecurity_pqc", "id": 20},
    {"query": "quantum random number generator commercial", "theme": "cybersecurity_pqc", "id": 21},
    {"query": "quantum computing cybersecurity readiness assessment", "theme": "cybersecurity_pqc", "id": 22},

    # =========================================================================
    # Theme 4: Supply Chain, Logistics & Optimization (5 queries)
    # =========================================================================
    {"query": "quantum computing supply chain optimization deployment", "theme": "supply_chain_optimization", "id": 23},
    {"query": "quantum annealing logistics routing scheduling", "theme": "supply_chain_optimization", "id": 24},
    {"query": "quantum optimization manufacturing production planning", "theme": "supply_chain_optimization", "id": 25},
    {"query": "quantum computing warehouse operations fleet management", "theme": "supply_chain_optimization", "id": 26},
    {"query": "D-Wave quantum supply chain customer case study", "theme": "supply_chain_optimization", "id": 27},

    # =========================================================================
    # Theme 5: Energy, Climate & Materials Science (6 queries)
    # =========================================================================
    {"query": "quantum computing battery materials discovery", "theme": "energy_climate_materials", "id": 28},
    {"query": "quantum simulation catalyst design clean energy", "theme": "energy_climate_materials", "id": 29},
    {"query": "quantum computing carbon capture climate modeling", "theme": "energy_climate_materials", "id": 30},
    {"query": "quantum chemistry solar cell material optimization", "theme": "energy_climate_materials", "id": 31},
    {"query": "quantum computing power grid optimization energy", "theme": "energy_climate_materials", "id": 32},
    {"query": "quantum simulation superconductor discovery room temperature", "theme": "energy_climate_materials", "id": 33},

    # =========================================================================
    # Theme 6: AI & Machine Learning Intersection (5 queries)
    # =========================================================================
    {"query": "quantum machine learning advantage classical comparison", "theme": "ai_ml_intersection", "id": 34},
    {"query": "quantum neural network training speedup", "theme": "ai_ml_intersection", "id": 35},
    {"query": "quantum computing AI inference acceleration", "theme": "ai_ml_intersection", "id": 36},
    {"query": "hybrid quantum classical machine learning production", "theme": "ai_ml_intersection", "id": 37},
    {"query": "quantum reservoir computing time series", "theme": "ai_ml_intersection", "id": 38},

    # =========================================================================
    # Theme 7: Hardware & Error Correction Milestones (6 queries)
    # =========================================================================
    {"query": "quantum error correction logical qubit milestone", "theme": "hardware_error_correction", "id": 39},
    {"query": "quantum processor qubit count fidelity improvement", "theme": "hardware_error_correction", "id": 40},
    {"query": "quantum computing fault tolerant timeline roadmap", "theme": "hardware_error_correction", "id": 41},
    {"query": "quantum supremacy advantage benchmark real problem", "theme": "hardware_error_correction", "id": 42},
    {"query": "quantum interconnect networking multi-processor", "theme": "hardware_error_correction", "id": 43},
    {"query": "quantum computing room temperature photonic breakthrough", "theme": "hardware_error_correction", "id": 44},

    # =========================================================================
    # Theme 8: Government, Defense & Geopolitics (4 queries)
    # =========================================================================
    {"query": "quantum computing government contract defense department", "theme": "government_defense", "id": 45},
    {"query": "China quantum computing progress satellite", "theme": "government_defense", "id": 46},
    {"query": "quantum technology export controls national security", "theme": "government_defense", "id": 47},
    {"query": "quantum computing workforce talent shortage training", "theme": "government_defense", "id": 48},

    # =========================================================================
    # Theme 9: Industry Adoption & Commercial Readiness (4 queries)
    # =========================================================================
    {"query": "quantum computing enterprise pilot customer deployment", "theme": "industry_adoption", "id": 49},
    {"query": "quantum computing revenue commercial product launch", "theme": "industry_adoption", "id": 50},
    {"query": "quantum as a service cloud platform customer growth", "theme": "industry_adoption", "id": 51},
    {"query": "quantum computing skepticism timeline reality check", "theme": "industry_adoption", "id": 52},

    # =========================================================================
    # Theme 10: Venture Capital & Startup Funding (5 queries)
    # =========================================================================
    {"query": "quantum computing startup seed funding series A venture capital", "theme": "venture_capital_funding", "id": 53},
    {"query": "quantum hardware software startup investment round raised", "theme": "venture_capital_funding", "id": 54},
    {"query": "quantum computing new company launch stealth mode funding", "theme": "venture_capital_funding", "id": 55},
    {"query": "quantum technology IPO SPAC public market valuation", "theme": "venture_capital_funding", "id": 56},
    {"query": "quantum computing incubator accelerator startup ecosystem", "theme": "venture_capital_funding", "id": 57},
]


def get_queries_by_theme(theme: str) -> List[Dict[str, Any]]:
    """Get all queries for a specific theme."""
    return [q for q in EXA_QUERIES if q["theme"] == theme]


def get_all_query_strings() -> List[str]:
    """Get just the query strings for execution."""
    return [q["query"] for q in EXA_QUERIES]


THEMES = [
    "drug_discovery_healthcare",
    "financial_services",
    "cybersecurity_pqc",
    "supply_chain_optimization",
    "energy_climate_materials",
    "ai_ml_intersection",
    "hardware_error_correction",
    "government_defense",
    "industry_adoption",
    "venture_capital_funding",
]
