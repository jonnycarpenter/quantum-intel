"""Verify model aliases work on the Anthropic API."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from utils.llm_client import ResilientAsyncClient

async def test():
    client = ResilientAsyncClient(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=1,
    )
    models = ["claude-sonnet-4-6", "claude-haiku-4-5"]
    for model in models:
        try:
            r = await client.messages_create(
                model=model, max_tokens=20,
                messages=[{"role": "user", "content": "Say hi"}],
            )
            print(f"  {model}: OK - {client.extract_text(r)[:30]}")
        except Exception as e:
            print(f"  {model}: FAILED - {type(e).__name__}: {e}")

asyncio.run(test())
