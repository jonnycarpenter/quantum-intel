"""
Article Card Component
======================

Reusable Streamlit component for displaying classified articles.
"""

import streamlit as st
from typing import Optional, List


# Priority → color mapping
PRIORITY_COLORS = {
    "critical": "#FF4444",
    "high": "#FF8C00",
    "medium": "#4A90D9",
    "low": "#888888",
}

PRIORITY_EMOJI = {
    "critical": "!!!",
    "high": "!!",
    "medium": "!",
    "low": "",
}


def render_article_card(
    title: str,
    source: str,
    url: str,
    summary: str,
    category: str,
    priority: str,
    relevance_score: float,
    published_at: Optional[str] = None,
    companies: Optional[List[str]] = None,
    technologies: Optional[List[str]] = None,
) -> None:
    """
    Render a styled article card.

    Args:
        title: Article title
        source: Source name
        url: Article URL
        summary: AI-generated summary
        category: Content category
        priority: Priority level
        relevance_score: 0.0-1.0
        published_at: Optional date string
        companies: Optional company names
        technologies: Optional technology names
    """
    color = PRIORITY_COLORS.get(priority, "#888888")
    priority_label = priority.upper()

    with st.container():
        # Header row: priority badge + title
        cols = st.columns([1, 8])
        with cols[0]:
            st.markdown(
                f'<span style="background-color:{color}; color:white; '
                f'padding:2px 8px; border-radius:4px; font-size:0.75em; '
                f'font-weight:bold;">{priority_label}</span>',
                unsafe_allow_html=True,
            )
        with cols[1]:
            st.markdown(f"**[{title}]({url})**")

        # Metadata row
        meta_parts = [f"Source: {source}"]
        if published_at:
            meta_parts.append(f"Date: {published_at}")
        meta_parts.append(f"Category: {category.replace('_', ' ').title()}")
        meta_parts.append(f"Relevance: {relevance_score:.0%}")
        st.caption(" | ".join(meta_parts))

        # Summary
        if summary:
            st.markdown(summary[:300])

        # Entity tags
        tags = []
        if companies:
            tags.extend([f"`{c}`" for c in companies[:5]])
        if technologies:
            tags.extend([f"`{t}`" for t in technologies[:5]])
        if tags:
            st.markdown(" ".join(tags))

        st.divider()
