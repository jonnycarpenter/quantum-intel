"""
Settings Page
=============

Displays system configuration, storage stats, and API status.
"""

import asyncio
import os
import streamlit as st


def render_settings_page() -> None:
    """Render the settings page."""
    st.header("System Settings")

    # API Key Status
    st.subheader("API Keys")
    col1, col2 = st.columns(2)
    with col1:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        status = "Configured" if anthropic_key else "Not Set"
        color = "green" if anthropic_key else "red"
        st.markdown(f"Anthropic API: :{color}[**{status}**]")

    with col2:
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        status = "Configured" if tavily_key else "Not Set"
        color = "green" if tavily_key else "red"
        st.markdown(f"Tavily API: :{color}[**{status}**]")

    st.divider()

    # Storage Stats
    st.subheader("Storage")

    from storage import get_storage
    storage = get_storage()

    try:
        stats = asyncio.run(storage.get_stats(hours=24 * 30))  # Last 30 days
        col1, col2, col3 = st.columns(3)
        col1.metric("Articles (30d)", stats.get("article_count", 0))
        col2.metric("Categories", stats.get("category_count", 0))
        col3.metric("Sources", stats.get("source_count", 0))
    except Exception as e:
        st.warning(f"Could not fetch storage stats: {e}")

    # Embeddings Stats
    st.subheader("Embeddings")
    try:
        from storage import get_embeddings_store
        embeddings = get_embeddings_store()
        st.metric("Indexed Documents", embeddings.count())
    except Exception as e:
        st.warning(f"ChromaDB not available: {e}")

    st.divider()

    # Model Configuration
    st.subheader("Model Configuration")

    from config.settings import AgentConfig
    config = AgentConfig()

    st.markdown(f"""
    | Setting | Value |
    |---------|-------|
    | Router Model | `{config.router_model}` |
    | Intelligence Model | `{config.intelligence_model}` |
    | Temperature | `{config.intelligence_temperature}` |
    | Max Tool Calls | `{config.max_tool_calls}` |
    | Max Tokens | `{config.intelligence_max_tokens}` |
    """)

    st.divider()

    # Storage Path Info
    st.subheader("Paths")
    db_path = os.getenv("SQLITE_DB_PATH", "data/quantum_intel.db")
    embed_path = os.getenv("EMBEDDINGS_PATH", "data/embeddings")
    st.code(f"SQLite DB: {db_path}\nEmbeddings: {embed_path}")
