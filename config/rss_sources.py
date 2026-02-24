"""
RSS Feed Sources — Quantum Computing Intelligence Hub
=====================================================

RSS feeds organized by tier. From spec §2.3.
Verified as of February 2026.
"""

from typing import List, Dict, Any


RSS_FEEDS: List[Dict[str, Any]] = [
    # =========================================================================
    # TIER 1: Dedicated Quantum News (Daily Pull)
    # =========================================================================
    {
        "name": "The Quantum Insider",
        "url": "https://thequantuminsider.com/feed/",
        "tier": 1,
        "category": "quantum_dedicated",
        "priority_boost": 0.15,
        "filter_keywords": [],
    },
    {
        "name": "Quantum Computing Report",
        "url": "https://quantumcomputingreport.com/feed/",
        "tier": 1,
        "category": "quantum_dedicated",
        "priority_boost": 0.15,
        "filter_keywords": [],
    },
    # Quantum Untangled — removed, newsletter dormant since 2023 (moved to techmonitor.substack.com)
    {
        "name": "ScienceDaily - Quantum",
        "url": "https://www.sciencedaily.com/rss/computers_math/quantum_computers.xml",
        "tier": 1,
        "category": "quantum_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Inside Quantum Technology",
        "url": "https://insidequantumtechnology.com/feed/",
        "tier": 1,
        "category": "quantum_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Quantum Zeitgeist",
        "url": "https://quantumzeitgeist.com/feed",
        "tier": 1,
        "category": "quantum_dedicated",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },

    # =========================================================================
    # TIER 2: Industry & Vendor Blogs (Daily Pull)
    # =========================================================================
    # IBM Quantum Blog — removed, no native RSS feed (site migrated, no feed endpoint)
    {
        "name": "Google Research Blog",
        "url": "https://blog.google/technology/research/rss/",
        "tier": 2,
        "category": "vendor_blog",
        "priority_boost": 0.10,
        "filter_keywords": ["quantum"],
    },
    {
        "name": "AWS Quantum Computing",
        "url": "https://aws.amazon.com/blogs/quantum-computing/feed/",
        "tier": 2,
        "category": "vendor_blog",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "IonQ Blog",
        "url": "https://ionq.com/blog/rss.xml",
        "tier": 2,
        "category": "vendor_blog",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Microsoft Q# Blog",
        "url": "https://devblogs.microsoft.com/qsharp/feed/",
        "tier": 2,
        "category": "vendor_blog",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "D-Wave Blog",
        "url": "https://dwave.medium.com/feed",
        "tier": 2,
        "category": "vendor_blog",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },

    # =========================================================================
    # TIER 3: Academic & Research News (Daily Pull)
    # =========================================================================
    {
        "name": "Nature - Quantum Information",
        "url": "https://www.nature.com/subjects/quantum-information.rss",
        "tier": 3,
        "category": "academic",
        "priority_boost": 0.15,
        "filter_keywords": [],
    },
    {
        "name": "MIT News - Quantum Computing",
        "url": "https://news.mit.edu/rss/topic/quantum-computing",
        "tier": 3,
        "category": "academic",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Quanta Magazine - Quantum",
        "url": "https://quantamagazine.org/tag/quantum-computing/feed",
        "tier": 3,
        "category": "academic",
        "priority_boost": 0.10,
        "filter_keywords": [],
    },
    {
        "name": "Quantum Frontiers (Caltech)",
        "url": "https://quantumfrontiers.com/feed",
        "tier": 3,
        "category": "academic",
        "priority_boost": 0.05,
        "filter_keywords": [],
    },

    # =========================================================================
    # TIER 4: Broader Tech Coverage (Daily Pull, Keyword Filtered)
    # =========================================================================
    {
        "name": "Ars Technica - Science",
        "url": "https://feeds.arstechnica.com/arstechnica/science",
        "tier": 4,
        "category": "tech_general",
        "priority_boost": 0.0,
        "filter_keywords": ["quantum"],
    },
    {
        "name": "IEEE Spectrum - Computing",
        "url": "https://spectrum.ieee.org/feeds/topic/computing.rss",
        "tier": 4,
        "category": "tech_general",
        "priority_boost": 0.0,
        "filter_keywords": ["quantum"],
    },
    {
        "name": "Wired - Science",
        "url": "https://www.wired.com/feed/category/science/latest/rss",
        "tier": 4,
        "category": "tech_general",
        "priority_boost": 0.0,
        "filter_keywords": ["quantum"],
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "tier": 4,
        "category": "tech_general",
        "priority_boost": 0.0,
        "filter_keywords": ["quantum"],
    },
]
