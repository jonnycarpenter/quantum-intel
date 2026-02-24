"""
Paper Summary Component
=======================

Renders ArXiv paper cards with metadata badges.
"""

import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.paper import Paper

# Commercial readiness color coding
READINESS_COLORS = {
    "near_term": "#4CAF50",
    "mid_term": "#FF9800",
    "long_term": "#FF5722",
    "theoretical": "#9E9E9E",
}


def render_paper_summary(paper: "Paper") -> None:
    """
    Render a paper summary card.

    Args:
        paper: Paper dataclass instance
    """
    with st.container():
        # Title with ArXiv link
        st.markdown(f"**[{paper.title}]({paper.abs_url})**")

        # Authors
        if paper.authors:
            authors_str = ", ".join(paper.authors[:5])
            if len(paper.authors) > 5:
                authors_str += f" et al. ({len(paper.authors)} authors)"
            st.caption(authors_str)

        # Metadata row
        meta_cols = st.columns(4)

        with meta_cols[0]:
            if paper.categories:
                st.markdown(f"Categories: {', '.join(paper.categories[:3])}")

        with meta_cols[1]:
            if paper.relevance_score is not None:
                st.markdown(f"Relevance: **{paper.relevance_score}/10**")

        with meta_cols[2]:
            if paper.paper_type:
                st.markdown(f"Type: {paper.paper_type.title()}")

        with meta_cols[3]:
            if paper.commercial_readiness:
                color = READINESS_COLORS.get(paper.commercial_readiness, "#9E9E9E")
                label = paper.commercial_readiness.replace("_", " ").title()
                st.markdown(
                    f'<span style="background-color:{color}; color:white; '
                    f'padding:2px 8px; border-radius:4px; font-size:0.75em;">'
                    f'{label}</span>',
                    unsafe_allow_html=True,
                )

        # Abstract excerpt
        if paper.abstract:
            with st.expander("Abstract", expanded=False):
                st.write(paper.abstract[:600])

        # Significance summary
        if paper.significance_summary:
            st.info(paper.significance_summary)

        # Published date
        if paper.published_at:
            st.caption(f"Published: {paper.published_at.strftime('%Y-%m-%d')}")

        # PDF link
        if paper.pdf_url:
            st.markdown(f"[PDF]({paper.pdf_url})")

        st.divider()
