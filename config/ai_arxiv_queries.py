"""
ArXiv API Configuration — AI Intelligence Hub
===============================================

ArXiv categories and research-focused queries for AI/ML papers.
Covers cs.AI, cs.CL, cs.LG, cs.CV, and related categories.
"""

from typing import List, Dict, Any


# ============================================================================
# Primary Categories to Monitor
# ============================================================================

AI_ARXIV_CATEGORIES: List[Dict[str, str]] = [
    {"category": "cs.AI", "description": "Core artificial intelligence"},
    {"category": "cs.CL", "description": "Computation and language (NLP)"},
    {"category": "cs.LG", "description": "Machine learning"},
    {"category": "cs.CV", "description": "Computer vision and pattern recognition"},
    {"category": "cs.MA", "description": "Multi-agent systems"},
    {"category": "stat.ML", "description": "Machine learning (statistics)"},
]

# ============================================================================
# Research-Focused Queries
# ============================================================================

AI_ARXIV_QUERIES: List[Dict[str, Any]] = [
    {
        "name": "large_language_models",
        "query": (
            '(cat:cs.CL OR cat:cs.AI) AND '
            '(abs:"large language model" OR abs:"LLM" OR abs:"foundation model" '
            'OR abs:"instruction tuning" OR abs:"in-context learning")'
        ),
        "use_case": "ai_model_release",
    },
    {
        "name": "ai_agents",
        "query": (
            '(cat:cs.AI OR cat:cs.MA OR cat:cs.CL) AND '
            '(abs:"AI agent" OR abs:"autonomous agent" OR abs:"tool use" '
            'OR abs:"multi-agent" OR abs:"agentic")'
        ),
        "use_case": "ai_research_breakthrough",
    },
    {
        "name": "safety_alignment",
        "query": (
            '(cat:cs.AI OR cat:cs.CL OR cat:cs.LG) AND '
            '(abs:"alignment" OR abs:"RLHF" OR abs:"constitutional AI" '
            'OR abs:"red teaming" OR abs:"safety" OR abs:"jailbreak")'
        ),
        "use_case": "ai_safety_alignment",
    },
    {
        "name": "computer_vision",
        "query": (
            'cat:cs.CV AND '
            '(abs:"vision transformer" OR abs:"diffusion model" OR abs:"image generation" '
            'OR abs:"object detection" OR abs:"multimodal")'
        ),
        "use_case": "ai_research_breakthrough",
    },
    {
        "name": "efficient_inference",
        "query": (
            '(cat:cs.LG OR cat:cs.AI) AND '
            '(abs:"quantization" OR abs:"distillation" OR abs:"pruning" '
            'OR abs:"efficient inference" OR abs:"mixture of experts" OR abs:"MoE")'
        ),
        "use_case": "ai_infrastructure",
    },
    {
        "name": "reinforcement_learning",
        "query": (
            '(cat:cs.LG OR cat:cs.AI) AND '
            '(abs:"reinforcement learning" OR abs:"reward model" '
            'OR abs:"policy optimization" OR abs:"RLHF")'
        ),
        "use_case": "ai_research_breakthrough",
    },
    {
        "name": "open_source_models",
        "query": (
            '(cat:cs.CL OR cat:cs.LG) AND '
            '(abs:"open source" OR abs:"open weight" OR abs:"Llama" '
            'OR abs:"Mistral" OR abs:"Qwen" OR abs:"Gemma")'
        ),
        "use_case": "ai_open_source",
    },
    {
        "name": "retrieval_augmented",
        "query": (
            '(cat:cs.CL OR cat:cs.IR) AND '
            '(abs:"retrieval augmented" OR abs:"RAG" OR abs:"knowledge grounding" '
            'OR abs:"vector database" OR abs:"embedding")'
        ),
        "use_case": "ai_use_case_enterprise",
    },
]

# ============================================================================
# General AI/ML search (catch-all)
# ============================================================================

AI_ARXIV_GENERAL_QUERY = (
    "(cat:cs.AI OR cat:cs.CL OR cat:cs.LG) AND ("
    "ti:artificial+intelligence OR "
    "ti:large+language+model OR "
    "ti:deep+learning OR "
    "ti:transformer OR "
    "ti:neural+network"
    ")"
)
