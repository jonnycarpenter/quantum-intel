"""
Quantum Intelligence Hub — Streamlit Frontend
==============================================

Multi-page Streamlit app for browsing intelligence, chatting with
the agent, viewing stock data, and exploring ArXiv papers.

Run:
    streamlit run frontend/app.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st


def main():
    st.set_page_config(
        page_title="Quantum Intelligence Hub",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar navigation
    st.sidebar.title("Quantum Intel Hub")
    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigate",
        ["Digest", "Chat", "Stocks", "Papers", "Settings"],
        index=0,
    )

    st.sidebar.divider()
    st.sidebar.caption("Quantum Intelligence Hub v0.3")
    st.sidebar.caption("Phase 3: Intelligence Layer")

    # Route to page
    if page == "Digest":
        from frontend.pages.digest import render_digest_page
        render_digest_page()

    elif page == "Chat":
        from frontend.pages.chat import render_chat_page
        render_chat_page()

    elif page == "Stocks":
        from frontend.pages.stocks import render_stocks_page
        render_stocks_page()

    elif page == "Papers":
        from frontend.pages.papers import render_papers_page
        render_papers_page()

    elif page == "Settings":
        from frontend.pages.settings import render_settings_page
        render_settings_page()


if __name__ == "__main__":
    main()
