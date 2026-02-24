"""
Strategic Priorities
====================

Defines the strategic priority sections for each domain (quantum / AI).
Used by the Research Agent to map observations and by the Briefing Agent
to structure sections. Also used by the frontend for section rendering.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class StrategicPriority:
    """A single strategic priority definition."""
    tag: str               # "P1", "P2", etc.
    label: str             # Human-readable label (used as section header)
    description: str       # 1-2 sentence description for LLM context
    categories: List[str]  # ContentCategory values that map to this priority
    keywords: List[str]    # Keywords for voice enrichment search


# =============================================================================
# QUANTUM PRIORITIES
# =============================================================================

QUANTUM_PRIORITIES: List[StrategicPriority] = [
    StrategicPriority(
        tag="P1",
        label="Quantum Advantage",
        description="Real quantum computing solving real problems. Demonstrations of quantum utility or advantage with evidence, production use cases, verified speedups over classical.",
        categories=[
            "use_case_drug_discovery", "use_case_finance", "use_case_optimization",
            "use_case_energy_materials", "use_case_ai_ml", "use_case_other",
        ],
        keywords=[
            "quantum advantage", "quantum utility", "real-world", "production",
            "deployment", "speedup", "outperform classical", "practical application",
        ],
    ),
    StrategicPriority(
        tag="P2",
        label="Error Correction & Logical Qubits",
        description="Quantum error correction progress. Logical qubits, fault tolerance thresholds, QEC code breakthroughs, below-threshold error rates.",
        categories=["error_correction", "algorithm_research"],
        keywords=[
            "error correction", "logical qubit", "fault tolerant", "QEC",
            "surface code", "threshold", "error rate", "fault tolerance",
        ],
    ),
    StrategicPriority(
        tag="P3",
        label="Hardware Race",
        description="Quantum hardware competition. Processor milestones, qubit counts, gate fidelity records, new architectures, quantum volume, platform comparisons.",
        categories=["hardware_milestone"],
        keywords=[
            "processor", "qubit", "hardware", "superconducting", "trapped ion",
            "photonic", "neutral atom", "topological", "fidelity", "quantum volume",
        ],
    ),
    StrategicPriority(
        tag="P4",
        label="Commercial & Contracts",
        description="Business deals, funding, partnerships, revenue milestones, QCaaS contracts, IPOs, acquisitions in the quantum space.",
        categories=[
            "company_earnings", "funding_ipo", "partnership_contract",
            "personnel_leadership", "market_analysis",
        ],
        keywords=[
            "contract", "deal", "partnership", "revenue", "funding", "IPO",
            "acquisition", "QCaaS", "booking", "customer", "commercial",
        ],
    ),
    StrategicPriority(
        tag="P5",
        label="Government & Defense",
        description="Government quantum programs, defense contracts, export controls, national strategies, NIST standards, post-quantum cryptography mandates.",
        categories=["policy_regulation", "geopolitics", "use_case_cybersecurity"],
        keywords=[
            "government", "defense", "DARPA", "DOE", "DOD", "export control",
            "NIST", "PQC", "post-quantum", "national strategy", "NATO",
        ],
    ),
]


# =============================================================================
# AI PRIORITIES
# =============================================================================

AI_PRIORITIES: List[StrategicPriority] = [
    StrategicPriority(
        tag="P1",
        label="Enterprise AI & ROI",
        description="Enterprise AI deployments with measurable ROI. Real business outcomes, production systems, customer wins, cost savings, revenue impact.",
        categories=[
            "ai_use_case_enterprise", "ai_use_case_healthcare",
            "ai_use_case_finance", "ai_use_case_other",
        ],
        keywords=[
            "enterprise", "ROI", "deployment", "production", "customer",
            "revenue", "cost savings", "use case", "implementation",
        ],
    ),
    StrategicPriority(
        tag="P2",
        label="Frontier Models & Capabilities",
        description="Frontier model releases, benchmark results, reasoning capabilities, multimodal advances, scaling laws, agentic capabilities.",
        categories=["ai_model_release", "ai_product_launch", "ai_research_breakthrough"],
        keywords=[
            "model release", "GPT", "Claude", "Gemini", "Llama", "benchmark",
            "frontier", "reasoning", "multimodal", "agent", "capabilities",
        ],
    ),
    StrategicPriority(
        tag="P3",
        label="Safety & Regulation",
        description="AI safety research, alignment progress, governance frameworks, EU AI Act, executive orders, responsible AI practices.",
        categories=["ai_safety_alignment", "policy_regulation"],
        keywords=[
            "safety", "alignment", "regulation", "AI Act", "governance",
            "responsible AI", "red teaming", "evaluation", "policy",
        ],
    ),
    StrategicPriority(
        tag="P4",
        label="Infrastructure & Compute",
        description="GPU supply, custom AI chips, training clusters, inference optimization, cloud AI platforms, data center buildout.",
        categories=["ai_infrastructure"],
        keywords=[
            "GPU", "compute", "infrastructure", "data center", "NVIDIA", "TPU",
            "training", "inference", "chip", "AMD", "custom silicon",
        ],
    ),
    StrategicPriority(
        tag="P5",
        label="Open Source Dynamics",
        description="Open source model releases, framework developments, community contributions, licensing debates, open weights momentum.",
        categories=["ai_open_source"],
        keywords=[
            "open source", "open weights", "Llama", "Mistral", "community",
            "license", "Apache", "framework", "Hugging Face",
        ],
    ),
]


# =============================================================================
# DOMAIN MAPS
# =============================================================================

DOMAIN_PRIORITIES: Dict[str, List[StrategicPriority]] = {
    "quantum": QUANTUM_PRIORITIES,
    "ai": AI_PRIORITIES,
}


def get_priority_for_category(category: str, domain: str) -> str:
    """
    Map a content category to a priority tag.
    Returns the tag (e.g. "P1") or "unmatched" if no priority claims the category.
    """
    priorities = DOMAIN_PRIORITIES.get(domain, QUANTUM_PRIORITIES)
    for p in priorities:
        if category in p.categories:
            return p.tag
    return "unmatched"


def format_priorities_block(domain: str) -> str:
    """
    Format priorities as a readable text block for LLM prompt injection.
    """
    priorities = DOMAIN_PRIORITIES.get(domain, QUANTUM_PRIORITIES)
    lines = []
    for p in priorities:
        lines.append(f"- {p.tag}: {p.label} — {p.description}")
    return "\n".join(lines)
