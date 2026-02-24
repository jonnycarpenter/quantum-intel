"""
Digest Page
===========

Displays the latest intelligence digest with priority-grouped articles.
"""

import asyncio
import streamlit as st


def render_digest_page() -> None:
    """Render the digest page."""
    st.header("Intelligence Digest")

    from storage import get_storage
    storage = get_storage()

    # Fetch latest digest
    if st.button("Refresh Digest"):
        st.session_state.pop("cached_digest", None)

    if "cached_digest" not in st.session_state:
        digest = asyncio.run(storage.get_latest_digest())
        st.session_state["cached_digest"] = digest
    else:
        digest = st.session_state["cached_digest"]

    if digest is None:
        st.info(
            "No digest available yet. Run the digest generator:\n\n"
            "```\npython scripts/run_digest.py\n```"
        )
        return

    # Digest header
    st.caption(f"Generated: {digest.created_at.strftime('%Y-%m-%d %H:%M UTC')}")

    # Stats bar
    cols = st.columns(5)
    cols[0].metric("Total Items", digest.total_items)
    cols[1].metric("Critical", digest.critical_count)
    cols[2].metric("High", digest.high_count)
    cols[3].metric("Medium", digest.medium_count)
    cols[4].metric("Low", digest.low_count)

    st.divider()

    # Executive Summary
    if digest.executive_summary:
        st.subheader("Executive Summary")
        st.markdown(digest.executive_summary)
        st.divider()

    # Items grouped by priority
    if digest.items:
        from frontend.components.article_card import render_article_card

        priority_groups = {"critical": [], "high": [], "medium": [], "low": []}
        for item in digest.items:
            priority_val = (
                item.priority.value
                if hasattr(item.priority, "value")
                else str(item.priority)
            )
            priority_groups.get(priority_val, priority_groups["medium"]).append(item)

        for priority_name in ["critical", "high", "medium", "low"]:
            items = priority_groups[priority_name]
            if items:
                st.subheader(f"{priority_name.upper()} ({len(items)})")
                for item in items:
                    render_article_card(
                        title=item.title,
                        source=item.source_name,
                        url=item.url,
                        summary=item.summary,
                        category=item.category,
                        priority=priority_name,
                        relevance_score=item.relevance_score,
                        published_at=(
                            item.published_at.strftime("%Y-%m-%d")
                            if item.published_at else None
                        ),
                        companies=item.companies_mentioned,
                        technologies=item.technologies_mentioned,
                    )
    else:
        st.info("Digest has no items.")
