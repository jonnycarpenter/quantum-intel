"""
Chat Page
=========

Interactive chat interface with the Intelligence Agent.
Domain-aware: uses quantum or AI prompts based on session state.
"""

import asyncio
import os
import streamlit as st


def _get_agent_components(domain: str = "quantum"):
    """Lazy-initialize agent components in session state.

    Re-initializes if domain has changed.
    """
    current_domain = st.session_state.get("agent_domain")
    if "agent_initialized" not in st.session_state or current_domain != domain:
        from utils.llm_client import ResilientAsyncClient
        from agents.router import RouterAgent
        from agents.intelligence import IntelligenceAgent

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None, None

        llm_client = ResilientAsyncClient(anthropic_api_key=api_key)
        st.session_state["router"] = RouterAgent(llm_client=llm_client, domain=domain)
        st.session_state["agent"] = IntelligenceAgent(llm_client=llm_client, domain=domain)
        st.session_state["agent_domain"] = domain
        st.session_state["agent_initialized"] = True

    return st.session_state.get("router"), st.session_state.get("agent")


def render_chat_page(domain: str = "quantum") -> None:
    """Render the chat page."""
    domain_label = "Quantum" if domain == "quantum" else "AI"
    st.header(f"{domain_label} Intelligence Chat")

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Clear chat button
    if st.button("Clear Chat", key="clear_chat"):
        st.session_state["messages"] = []
        st.rerun()

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set. Add it to your .env file.")
        return

    # Display chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"Sources ({len(msg['sources'])})"):
                    for src in msg["sources"]:
                        st.markdown(f"- [{src.get('title', 'Link')}]({src.get('url', '')})")
            if msg.get("route"):
                st.caption(f"Route: {msg['route']} | Tools: {msg.get('tool_calls', 0)}")

    # Chat input
    placeholder = (
        "Ask about quantum computing..."
        if domain == "quantum"
        else "Ask about AI news, models, deployments..."
    )
    if user_input := st.chat_input(placeholder):
        # Display user message
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get agent components (domain-aware)
        router, agent = _get_agent_components(domain)
        if router is None:
            st.error("Failed to initialize agents. Check ANTHROPIC_API_KEY.")
            return

        # Route and answer
        with st.chat_message("assistant"):
            with st.spinner("Routing query..."):
                route_result = asyncio.run(router.route(user_input))

            route_info = f"{route_result.route} (confidence: {route_result.confidence:.0%})"

            if route_result.route == "digest":
                from storage import get_storage
                storage = get_storage()
                digest = asyncio.run(storage.get_latest_digest())
                if digest:
                    answer = f"**Latest Digest** ({digest.created_at.strftime('%Y-%m-%d %H:%M')})\n\n{digest.executive_summary}"
                else:
                    answer = "No digest available. Run `python scripts/run_digest.py` first."
                sources = []
                tool_calls = 0

            elif route_result.route == "deep_research":
                answer = "Deep research is coming soon. Let me try a quick query instead."
                with st.spinner("Searching..."):
                    # Build conversation history for multi-turn
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["messages"][:-1]
                        if m["role"] in ("user", "assistant")
                    ][-10:]  # Keep last 10 turns

                    response = asyncio.run(agent.answer(
                        user_message=user_input,
                        conversation_history=history if history else None,
                        route_hint="quick_query",
                    ))
                answer = response.answer
                sources = response.sources
                tool_calls = response.tool_calls_made

            else:
                with st.spinner("Searching and analyzing..."):
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["messages"][:-1]
                        if m["role"] in ("user", "assistant")
                    ][-10:]

                    response = asyncio.run(agent.answer(
                        user_message=user_input,
                        conversation_history=history if history else None,
                        route_hint=route_result.route,
                    ))
                answer = response.answer
                sources = response.sources
                tool_calls = response.tool_calls_made

            st.markdown(answer)

            if sources:
                with st.expander(f"Sources ({len(sources)})"):
                    for src in sources:
                        st.markdown(f"- [{src.get('title', 'Link')}]({src.get('url', '')})")

            st.caption(f"Route: {route_info} | Tools: {tool_calls}")

        # Save assistant message
        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "sources": sources if "sources" in dir() else [],
            "route": route_info,
            "tool_calls": tool_calls if "tool_calls" in dir() else 0,
        })
