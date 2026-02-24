"""
AI Source Quality Boosts
========================

Source-based relevance score boosts for AI classification.
Higher-quality AI sources get a boost to their relevance score.

Matches pattern from processing/classifier.py SOURCE_BOOSTS.
"""

AI_SOURCE_BOOSTS = {
    # Tier 1: Dedicated AI news
    "the batch": 0.10,
    "deeplearning.ai": 0.10,
    "venturebeat": 0.05,
    "import ai": 0.10,
    # Tier 2: Vendor blogs
    "openai": 0.10,
    "anthropic": 0.10,
    "google ai": 0.10,
    "deepmind": 0.10,
    "meta ai": 0.05,
    "microsoft ai": 0.05,
    "hugging face": 0.05,
    "nvidia": 0.05,
    # Tier 3: Academic
    "mit news": 0.10,
    "stanford hai": 0.10,
    "berkeley ai": 0.05,
}
