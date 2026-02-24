"""
RSS Feed Sources — AI Intelligence Hub
=======================================

RSS feeds for AI news ingestion. Organized by tier, matching the
quantum RSS feed structure. Curated for business-relevant AI intelligence.
"""

from typing import List, Dict, Any


AI_RSS_FEEDS: List[Dict[str, Any]] = [
    # =========================================================================
    # TIER 1: Dedicated AI News (Daily Pull)
    # =========================================================================
    # The Batch (deeplearning.ai) — removed, no native RSS feed (newsletter only)
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "tier": 1,
        "category": "ai_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "tier": 1,
        "category": "ai_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Import AI",
        "url": "https://importai.substack.com/feed",
        "tier": 1,
        "category": "ai_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    # The AI Beat — folded into VentureBeat AI category (already covered above)

    # =========================================================================
    # TIER 2: Vendor / Lab Blogs (2-3x Weekly)
    # =========================================================================
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    # Anthropic Blog — removed, no native RSS feed
    {
        "name": "Meta AI Research",
        "url": "https://research.facebook.com/feed/",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.05,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning", "LLM",
            "deep learning", "language model", "generative",
        ],
    },
    {
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },
    {
        "name": "NVIDIA AI Blog",
        "url": "https://blogs.nvidia.com/blog/tag/artificial-intelligence/feed/",
        "tier": 2,
        "category": "ai_vendor",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },

    # =========================================================================
    # TIER 3: Academic / Research (Weekly)
    # =========================================================================
    {
        "name": "MIT News - AI",
        "url": "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "tier": 3,
        "category": "ai_academic",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    # Stanford HAI — removed, no native RSS feed (migrated to Next.js, feed discontinued)
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "tier": 3,
        "category": "ai_academic",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Berkeley AI Research",
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "tier": 3,
        "category": "ai_academic",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },
    {
        "name": "Distill.pub",
        "url": "https://distill.pub/rss.xml",
        "tier": 3,
        "category": "ai_academic",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },

    # =========================================================================
    # TIER 4: General Tech (Keyword-Filtered)
    # =========================================================================
    {
        "name": "TechCrunch - AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning", "LLM",
            "GPT", "Claude", "Gemini", "deep learning", "neural network",
            "generative AI", "foundation model", "large language model",
        ],
    },
    {
        "name": "Ars Technica - AI",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning", "LLM",
            "GPT", "Claude", "Gemini", "deep learning", "neural network",
            "generative AI", "ChatGPT", "language model",
        ],
    },
    {
        "name": "The Verge - AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning", "LLM",
            "GPT", "Claude", "Gemini", "OpenAI", "Anthropic",
        ],
    },
    {
        "name": "Wired - AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning",
            "generative AI", "deep learning",
        ],
    },
    {
        "name": "Reuters Technology",
        "url": "https://news.google.com/rss/search?q=when:7d+allinurl:reuters.com+technology&ceid=US:en&hl=en-US&gl=US",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning",
            "OpenAI", "Anthropic", "Google AI", "Microsoft AI",
        ],
    },
    {
        "name": "Bloomberg Technology",
        "url": "https://feeds.bloomberg.com/technology/news.rss",
        "tier": 4,
        "category": "general_tech",
        "priority_boost": 0.0,
        "filter_keywords": [
            "AI", "artificial intelligence", "machine learning", "ChatGPT",
            "OpenAI", "Anthropic", "NVIDIA", "GPU",
        ],
    },
]


# Helper functions matching quantum RSS pattern
def get_ai_feeds_by_tier(tier: int) -> List[Dict[str, Any]]:
    """Get AI RSS feeds by tier number."""
    return [f for f in AI_RSS_FEEDS if f["tier"] == tier]


def get_ai_feeds_by_category(category: str) -> List[Dict[str, Any]]:
    """Get AI RSS feeds by category."""
    return [f for f in AI_RSS_FEEDS if f["category"] == category]
