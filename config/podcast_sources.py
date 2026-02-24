"""
Podcast Sources Configuration
==============================

Quantum computing and AI/ML podcasts for intelligence ingestion.
Quantum podcasts curated from QuEra's "Best Quantum Computing Podcasts" list;
AI podcasts curated from top-rated AI/ML shows for the AI Use Case Dashboard.

Each podcast has:
- RSS feed URL (for episode discovery + audio URLs)
- Metadata (host, description, cadence)
- discovery_method: "rss" (auto-discover via feed) or "manual" (provide audio URLs directly)

If an RSS feed is unavailable, episodes can be added manually via the
`manual_episodes` list — AssemblyAI will transcribe the audio regardless.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PodcastSourceConfig:
    """Configuration for a single podcast source."""
    podcast_id: str                    # Unique slug, e.g. "new-quantum-era"
    name: str                          # Display name
    hosts: List[str]                   # Host name(s)
    rss_url: Optional[str] = None      # RSS feed URL (None if not available)
    website_url: Optional[str] = None  # Show website
    apple_podcasts_id: Optional[str] = None
    spotify_url: Optional[str] = None
    description: str = ""
    cadence: str = "biweekly"          # weekly, biweekly, monthly, irregular
    discovery_method: str = "rss"      # "rss" or "manual"
    max_episodes: int = 20             # Max episodes to fetch per run
    enabled: bool = True               # Toggle individual podcasts on/off
    domain: str = "quantum"            # "quantum" or "ai" — selects extraction prompt


# =============================================================================
# QUANTUM COMPUTING PODCASTS
# =============================================================================

THE_NEW_QUANTUM_ERA = PodcastSourceConfig(
    podcast_id="new-quantum-era",
    name="The New Quantum Era",
    hosts=["Sebastian Hassinger"],
    rss_url="https://feeds.transistor.fm/the-new-quantum-era",
    website_url="https://podcast.newquantumera.com/",
    apple_podcasts_id="1637676725",
    spotify_url="https://open.spotify.com/show/2J0IwXAB4BQyWFUFtFi04k",
    description=(
        "Sebastian Hassinger interviews brilliant research scientists, software "
        "developers, engineers and others actively exploring the possibilities of "
        "our new quantum era. Covers quantum computing, networking and sensing."
    ),
    cadence="biweekly",
    max_episodes=20,
)

THE_SUPERPOSITION_GUY = PodcastSourceConfig(
    podcast_id="superposition-guy",
    name="The Superposition Guy's Podcast",
    hosts=["Yuval Boger"],
    rss_url="https://podcast.yboger.com/feed/",
    website_url="https://podcast.yboger.com/",
    apple_podcasts_id=None,
    spotify_url="https://open.spotify.com/show/superpositionguy",
    description=(
        "Yuval Boger interviews quantum computing executives, researchers, and "
        "practitioners. Covers business strategy, technology, and industry trends."
    ),
    cadence="weekly",
    max_episodes=20,
)

THE_QUANTUM_DIVIDE = PodcastSourceConfig(
    podcast_id="quantum-divide",
    name="The Quantum Divide",
    hosts=["Dan Holme", "Stephen DiAdamo"],
    rss_url="https://feeds.transistor.fm/the-quantum-divide",
    website_url="https://the-quantum-divide.transistor.fm/",
    apple_podcasts_id=None,
    spotify_url="https://open.spotify.com/show/4LbAg5XXdUbKVc4Yg7IVFy",
    description=(
        "Dan Holme and Stephen DiAdamo break down quantum computing news, "
        "research, and developments with a focus on quantum networking. "
        "Accessible and conversational format."
    ),
    cadence="biweekly",
    max_episodes=20,
)

IMPACT_QUANTUM = PodcastSourceConfig(
    podcast_id="impact-quantum",
    name="Impact Quantum",
    hosts=["Candace Gillhoolley", "Frank La Vigne"],
    rss_url="https://feeds.captivate.fm/impact-quantum/",
    website_url="https://impactquantum.com/",
    apple_podcasts_id="1527794236",
    spotify_url=None,
    description=(
        "Candace Gillhoolley and Frank La Vigne explore quantum computing "
        "for the quantum-curious. Features interviews with industry leaders, "
        "engineers, and educators shaping the quantum ecosystem."
    ),
    cadence="weekly",
    max_episodes=20,
)

QUANTUM_TECH_POD = PodcastSourceConfig(
    podcast_id="quantum-tech-pod",
    name="IQT The Quantum Dragon Podcast",
    hosts=["Christopher Bishop"],
    rss_url="https://www.insidequantumtechnology.com/feed/podcast/",
    website_url="https://www.insidequantumtechnology.com/news/podcast/",
    apple_podcasts_id="1577210670",
    spotify_url=None,
    description=(
        "Inside Quantum Technology's podcast (formerly Quantum Tech Pod) "
        "covering quantum computing industry news, business developments, "
        "and technology breakthroughs. 80+ episodes."
    ),
    cadence="weekly",
    max_episodes=20,
)

IEEE_QUANTUM_PODCAST = PodcastSourceConfig(
    podcast_id="ieee-quantum",
    name="IEEE Quantum Podcast",
    hosts=["IEEE"],
    rss_url="http://feeds.feedburner.com/ieeequantum",
    website_url="https://quantum.ieee.org/",
    apple_podcasts_id="1527803273",
    spotify_url="https://open.spotify.com/show/7BABUIRXiZS0rRJd4OVwaB",
    description=(
        "IEEE's podcast exploring quantum science and technology, featuring "
        "interviews with researchers and engineers working in the field. "
        "22 episodes covering quantum engineering, benchmarking, and standards."
    ),
    cadence="monthly",
    max_episodes=20,
)


# =============================================================================
# AI / ML PODCASTS
# =============================================================================

COGNITIVE_REVOLUTION = PodcastSourceConfig(
    podcast_id="cognitive-revolution",
    name="The Cognitive Revolution",
    hosts=["Nathan Labenz"],
    rss_url="https://feeds.megaphone.fm/RINTP3108857801",
    website_url="https://www.cognitiverevolution.ai/",
    description=(
        "Nathan Labenz explores the AI revolution with founders, researchers, "
        "and engineers building the future. Deep dives into LLMs, agents, safety."
    ),
    cadence="weekly",
    domain="ai",
)

LATENT_SPACE = PodcastSourceConfig(
    podcast_id="latent-space",
    name="Latent Space: The AI Engineer Podcast",
    hosts=["swyx", "Alessio Fanelli"],
    rss_url="https://rss.flightcast.com/vgnxzgiwwzwke85ym53fjnzu.xml",
    website_url="https://www.latent.space/",
    description=(
        "The podcast by and for AI Engineers. Technical deep dives into "
        "LLMs, infra, open source models, and the AI engineering stack."
    ),
    cadence="weekly",
    domain="ai",
)

PRACTICAL_AI = PodcastSourceConfig(
    podcast_id="practical-ai",
    name="Practical AI",
    hosts=["Daniel Whitenack", "Chris Benson"],
    rss_url="https://changelog.com/practicalai/feed",
    website_url="https://practicalai.fm/",
    description=(
        "Making AI practical, productive, and accessible. Covers real-world "
        "ML applications, tooling, and deployment patterns."
    ),
    cadence="weekly",
    domain="ai",
)

TWIML_AI = PodcastSourceConfig(
    podcast_id="twiml-ai",
    name="The TWIML AI Podcast",
    hosts=["Sam Charrington"],
    rss_url="https://feeds.megaphone.fm/MLN2155636147",
    website_url="https://twimlai.com/",
    description=(
        "Sam Charrington interviews ML/AI researchers and practitioners. "
        "One of the longest-running AI podcasts with 700+ episodes."
    ),
    cadence="weekly",
    domain="ai",
)

NO_PRIORS = PodcastSourceConfig(
    podcast_id="no-priors",
    name="No Priors",
    hosts=["Sarah Guo", "Elad Gil"],
    rss_url="https://feeds.megaphone.fm/nopriors",
    website_url="https://www.no-priors.com/",
    description=(
        "VCs Sarah Guo and Elad Gil interview leaders shaping AI — CEOs, "
        "researchers, and policymakers on what's next."
    ),
    cadence="weekly",
    domain="ai",
)

LAST_WEEK_IN_AI = PodcastSourceConfig(
    podcast_id="last-week-in-ai",
    name="Last Week in AI",
    hosts=["Andrey Kurenkov", "Jeremy Harris"],
    rss_url="https://rss.art19.com/last-week-in-ai",
    website_url="https://lastweekin.ai/",
    description=(
        "Weekly roundup of the most important AI news, research papers, "
        "and industry developments. Great for staying current."
    ),
    cadence="weekly",
    domain="ai",
)

HARD_FORK = PodcastSourceConfig(
    podcast_id="hard-fork",
    name="Hard Fork",
    hosts=["Kevin Roose", "Casey Newton"],
    rss_url="https://feeds.simplecast.com/l2i9YnTd",
    website_url="https://www.nytimes.com/column/hard-fork",
    description=(
        "NYT tech journalists Kevin Roose and Casey Newton cover AI, "
        "social media, and the tech industry. Wide audience reach."
    ),
    cadence="weekly",
    domain="ai",
)


# =============================================================================
# REGISTRY
# =============================================================================

ALL_PODCAST_SOURCES: List[PodcastSourceConfig] = [
    # Quantum computing
    THE_NEW_QUANTUM_ERA,
    THE_SUPERPOSITION_GUY,
    THE_QUANTUM_DIVIDE,
    IMPACT_QUANTUM,
    QUANTUM_TECH_POD,
    IEEE_QUANTUM_PODCAST,
    # AI / ML
    COGNITIVE_REVOLUTION,
    LATENT_SPACE,
    PRACTICAL_AI,
    TWIML_AI,
    NO_PRIORS,
    LAST_WEEK_IN_AI,
    HARD_FORK,
]

ENABLED_PODCAST_SOURCES: List[PodcastSourceConfig] = [
    p for p in ALL_PODCAST_SOURCES if p.enabled
]

# Quick lookup by podcast_id
PODCAST_SOURCE_MAP = {p.podcast_id: p for p in ALL_PODCAST_SOURCES}
