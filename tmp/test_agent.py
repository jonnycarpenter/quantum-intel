import asyncio
import os
import sys

# Ensure we can import from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import ResilientAsyncClient
from agents.intelligence import IntelligenceAgent
from utils.env_loader import ensure_env

async def main():
    ensure_env()
    
    # Force sqlite for fast local testing
    os.environ["STORAGE_MODE"] = "sqlite"
    
    llm = ResilientAsyncClient(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022"  # standard fallback
    )
    
    agent = IntelligenceAgent(
        llm_client=llm,
        domain="ai"
    )
    
    query = "What are executives saying about GPU CapEx during recent earnings calls?"
    print(f"Query: {query}\n")
    
    response = await agent.answer(query, route_hint="quick_query")
    
    print("\n--- FINAL ANSWER ---")
    print(response.answer)
    print("\n--- SOURCES ---")
    for s in response.sources:
        print(s)

if __name__ == "__main__":
    asyncio.run(main())
