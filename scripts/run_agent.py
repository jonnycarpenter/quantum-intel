"""
Run Agent (CLI Chat)
====================

Interactive terminal interface for the Intelligence Agent.
Routes queries through RouterAgent → IntelligenceAgent.

Usage:
    python scripts/run_agent.py
    python scripts/run_agent.py --domain ai
    python scripts/run_agent.py --model claude-sonnet-4-5-20250929
"""

import argparse
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents.router import RouterAgent
from agents.intelligence import IntelligenceAgent
from storage import get_storage
from utils.llm_client import ResilientAsyncClient
from utils.logger import configure_root_logger


async def run_chat(args: argparse.Namespace) -> None:
    """Main chat loop."""
    configure_root_logger()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in environment.")
        return

    domain = args.domain

    # Initialize components
    llm_client = ResilientAsyncClient(anthropic_api_key=api_key)
    router = RouterAgent(llm_client=llm_client, domain=domain)
    agent = IntelligenceAgent(
        llm_client=llm_client,
        model=args.model,
        max_tool_calls=args.max_tool_calls,
        domain=domain,
    )
    storage = get_storage()

    domain_label = "Quantum" if domain == "quantum" else "AI"
    print("=" * 60)
    print(f"  {domain_label} Intelligence Hub — Agent Chat")
    print("=" * 60)
    if domain == "quantum":
        print("Ask questions about quantum computing news, stocks, papers.")
    else:
        print("Ask questions about AI news, models, deployments, research.")
    print("Type 'quit' or 'exit' to leave.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if user_input.lower() == "clear":
            conversation_history.clear()
            print("Chat history cleared.")
            continue

        # Route the query
        route_result = await router.route(user_input)
        print(f"\n[Route: {route_result.route} | confidence: {route_result.confidence:.2f}]")

        # Handle special routes
        if route_result.route == "digest":
            digest = await storage.get_latest_digest()
            if digest:
                print(f"\n--- Digest ({digest.created_at.strftime('%Y-%m-%d %H:%M')}) ---")
                print(f"\n{digest.executive_summary}")
                print(f"\nItems: {digest.total_items} | "
                      f"Critical: {digest.critical_count} | "
                      f"High: {digest.high_count} | "
                      f"Medium: {digest.medium_count}")
            else:
                print("\nNo digest available. Run: python scripts/run_digest.py")
            continue

        if route_result.route == "deep_research":
            print("\nDeep research is coming soon. "
                  "Routing to quick query instead...")
            route_result.route = "quick_query"

        # Run the Intelligence Agent
        response = await agent.answer(
            user_message=user_input,
            conversation_history=conversation_history if conversation_history else None,
            route_hint=route_result.route,
        )

        # Display the answer
        print(f"\n{response.answer}")

        # Show sources
        if response.sources:
            print(f"\n--- Sources ({len(response.sources)}) ---")
            for src in response.sources[:5]:
                print(f"  - {src.get('title', 'Untitled')}: {src.get('url', '')}")

        print(f"\n[{response.tool_calls_made} tool calls | model: {response.model}]")

        # Update conversation history for multi-turn
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response.answer})

        # Keep history manageable
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-10:]


def main():
    parser = argparse.ArgumentParser(description="Intelligence Hub — Agent Chat")
    parser.add_argument(
        "--domain",
        choices=["quantum", "ai"],
        default="quantum",
        help="Intelligence domain (default: quantum)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model for the Intelligence Agent (default: claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=5,
        help="Maximum tool calls per query (default: 5)",
    )
    args = parser.parse_args()

    asyncio.run(run_chat(args))


if __name__ == "__main__":
    main()
