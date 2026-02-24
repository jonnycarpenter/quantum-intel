"""
Stock Tickers — Quantum Computing Companies
=============================================

From spec §2.1.
"""

from typing import List, Dict, Any


# ============================================================================
# Pure-Play Quantum Companies (Primary Watch)
# ============================================================================

PURE_PLAY_TICKERS: List[Dict[str, Any]] = [
    {"ticker": "IONQ", "company": "IonQ Inc.", "focus": "Trapped-ion quantum computing, QCaaS"},
    {"ticker": "QBTS", "company": "D-Wave Quantum Inc.", "focus": "Quantum annealing, hybrid quantum-classical"},
    {"ticker": "RGTI", "company": "Rigetti Computing Inc.", "focus": "Superconducting quantum processors, cloud"},
    {"ticker": "QUBT", "company": "Quantum Computing Inc.", "focus": "Photonic quantum, integrated photonics"},
    {"ticker": "ARQQ", "company": "Arqit Quantum Inc.", "focus": "Quantum encryption / cybersecurity"},
    {"ticker": "QMCO", "company": "Quantum Corporation", "focus": "Quantum storage/data management (adjacent)"},
    {"ticker": "QNCCF", "company": "Quantum eMotion Corp.", "focus": "Quantum-safe cybersecurity (OTC)"},
    {"ticker": "LAES", "company": "SealSQ Corp.", "focus": "Post-quantum semiconductors / security"},
]

# ============================================================================
# Major Tech Companies with Quantum Divisions (Secondary Watch)
# ============================================================================

MAJOR_TECH_TICKERS: List[Dict[str, Any]] = [
    {"ticker": "GOOGL", "company": "Alphabet (Google)", "focus": "Google Quantum AI, Willow processor"},
    {"ticker": "IBM", "company": "IBM", "focus": "IBM Quantum, Qiskit, Nighthawk processor"},
    {"ticker": "MSFT", "company": "Microsoft", "focus": "Azure Quantum, topological qubits"},
    {"ticker": "AMZN", "company": "Amazon", "focus": "AWS Braket, quantum computing service"},
    {"ticker": "HON", "company": "Honeywell", "focus": "Quantinuum (subsidiary), trapped-ion"},
    {"ticker": "NVDA", "company": "Nvidia", "focus": "Hybrid quantum-classical GPU integration"},
]

# ============================================================================
# Quantum ETF
# ============================================================================

ETF_TICKERS: List[Dict[str, Any]] = [
    {"ticker": "QTUM", "company": "Defiance Quantum ETF", "focus": "Broad quantum computing + ML exposure"},
]

# ============================================================================
# All tracked tickers (convenience list)
# ============================================================================

ALL_TICKERS: List[str] = (
    [t["ticker"] for t in PURE_PLAY_TICKERS]
    + [t["ticker"] for t in MAJOR_TECH_TICKERS]
    + [t["ticker"] for t in ETF_TICKERS]
)

# ============================================================================
# Notable Private Companies (Track for IPO / Funding News)
# ============================================================================

PRIVATE_COMPANIES: List[Dict[str, Any]] = [
    {"company": "Quantinuum", "focus": "Full-stack quantum (Honeywell spin-off)", "status": "Private, potential IPO"},
    {"company": "PsiQuantum", "focus": "Photonic quantum computing", "status": "Private, $665M+ raised"},
    {"company": "Xanadu", "focus": "Photonic quantum, PennyLane software", "status": "Private"},
    {"company": "Atom Computing", "focus": "Neutral atom quantum computing", "status": "Private"},
    {"company": "QuEra Computing", "focus": "Neutral atom, Harvard/MIT spinout", "status": "Private"},
    {"company": "Pasqal", "focus": "Neutral atom quantum, EU-based", "status": "Private"},
    {"company": "Alice & Bob", "focus": "Cat qubits, error correction", "status": "Private, EU-based"},
    {"company": "IQM Quantum", "focus": "Superconducting, EU-based", "status": "Private"},
    {"company": "Quantum Machines", "focus": "Quantum control hardware/software", "status": "Private, Israel-based"},
    {"company": "Nord Quantique", "focus": "Bosonic quantum computing", "status": "Private, Canada"},
]

# All known company names (for entity extraction)
ALL_COMPANY_NAMES: List[str] = (
    [t["company"] for t in PURE_PLAY_TICKERS]
    + [t["company"] for t in MAJOR_TECH_TICKERS]
    + [p["company"] for p in PRIVATE_COMPANIES]
)
