"""
ArXiv API Configuration — Quantum Computing Intelligence Hub
=============================================================

ArXiv categories and use-case focused queries. From spec §2.4.
"""

from typing import List, Dict, Any


# ============================================================================
# Primary Categories to Monitor
# ============================================================================

ARXIV_CATEGORIES: List[Dict[str, str]] = [
    {"category": "quant-ph", "description": "Core quantum computing papers"},
    {"category": "cond-mat.quant-gas", "description": "Quantum materials, BEC"},
    {"category": "cs.ET", "description": "Quantum computing (CS perspective)"},
    {"category": "cs.CR", "description": "Post-quantum crypto, QKD"},
]

# ============================================================================
# Use-Case Focused Queries
# ============================================================================

ARXIV_QUERIES: List[Dict[str, Any]] = [
    {
        "name": "drug_discovery_chemistry",
        "query": 'cat:quant-ph AND (abs:"drug discovery" OR abs:"molecular simulation" OR abs:"quantum chemistry")',
        "use_case": "use_case_drug_discovery",
    },
    {
        "name": "optimization",
        "query": 'cat:quant-ph AND (abs:"combinatorial optimization" OR abs:"quantum annealing" OR abs:"QAOA")',
        "use_case": "use_case_optimization",
    },
    {
        "name": "machine_learning",
        "query": 'cat:quant-ph AND (abs:"quantum machine learning" OR abs:"variational quantum" OR abs:"quantum neural")',
        "use_case": "use_case_ai_ml",
    },
    {
        "name": "error_correction",
        "query": 'cat:quant-ph AND (abs:"quantum error correction" OR abs:"logical qubit" OR abs:"fault tolerant")',
        "use_case": "error_correction",
    },
    {
        "name": "cryptography",
        "query": '(cat:quant-ph OR cat:cs.CR) AND (abs:"post-quantum" OR abs:"quantum key distribution" OR abs:"lattice-based")',
        "use_case": "use_case_cybersecurity",
    },
    {
        "name": "hardware",
        "query": 'cat:quant-ph AND (abs:"superconducting qubit" OR abs:"trapped ion" OR abs:"photonic quantum" OR abs:"neutral atom")',
        "use_case": "hardware_milestone",
    },
]

# ============================================================================
# General quantum computing search (catch-all)
# ============================================================================

ARXIV_GENERAL_QUERY = (
    "cat:quant-ph AND ("
    "ti:quantum+computing OR "
    "ti:quantum+error+correction OR "
    "ti:quantum+algorithm OR "
    "ti:quantum+advantage"
    ")"
)

# ArXiv API config
ARXIV_API_BASE_URL = "http://export.arxiv.org/api/query"
ARXIV_RATE_LIMIT_SECONDS = 3.0
ARXIV_MAX_RESULTS = 50
