"""
Papers Page
===========

ArXiv paper feed with filtering and search.
"""

import asyncio
import streamlit as st


def render_papers_page() -> None:
    """Render the papers feed page."""
    st.header("ArXiv Papers")

    from storage import get_storage
    storage = get_storage()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.slider("Days back", 7, 90, 30)
    with col2:
        paper_type_filter = st.multiselect(
            "Paper Type",
            ["breakthrough", "incremental", "review", "theoretical"],
            default=[],
        )
    with col3:
        readiness_filter = st.multiselect(
            "Commercial Readiness",
            ["near_term", "mid_term", "long_term", "theoretical"],
            default=[],
        )

    # Search
    search_query = st.text_input("Search papers", placeholder="e.g., error correction, surface codes...")

    # Fetch papers
    papers = asyncio.run(storage.get_recent_papers(days=days, limit=100))

    if not papers:
        st.info(
            "No papers in the corpus. Run ingestion with ArXiv:\n\n"
            "```\npython scripts/run_ingestion.py --sources arxiv\n```"
        )
        return

    # Apply filters
    filtered = papers

    if paper_type_filter:
        filtered = [p for p in filtered if p.paper_type in paper_type_filter]

    if readiness_filter:
        filtered = [p for p in filtered if p.commercial_readiness in readiness_filter]

    if search_query:
        query_terms = search_query.lower().split()
        filtered = [
            p for p in filtered
            if any(
                term in f"{p.title} {p.abstract}".lower()
                for term in query_terms
            )
        ]

    # Display count
    st.caption(f"Showing {len(filtered)} of {len(papers)} papers")

    if not filtered:
        st.info("No papers match the current filters.")
        return

    # Sort by relevance score (highest first)
    filtered.sort(
        key=lambda p: (p.relevance_score or 0),
        reverse=True,
    )

    # Render paper cards
    from frontend.components.paper_summary import render_paper_summary
    for paper in filtered:
        render_paper_summary(paper)
