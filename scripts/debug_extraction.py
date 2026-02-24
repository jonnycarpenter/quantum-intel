"""Direct test of nugget extraction with verbose error capture."""
import asyncio
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from fetchers.sec import SecFetcher
from processing.nugget_extractor import NuggetExtractor
from config.settings import SecConfig

async def test():
    config = SecConfig()
    fetcher = SecFetcher(config)
    extractor = NuggetExtractor(config)

    # Fetch one filing
    print("=== Fetching IONQ 10-K ===")
    filings = fetcher.get_company_filings("IONQ", ["10-K"], max_filings=1)
    if not filings:
        print("FAIL: No filings found")
        return

    filing = filings[0]
    filing = fetcher.fetch_filing_content(filing)
    if not filing:
        print("FAIL: No content fetched")
        return

    print(f"Filing: {filing.unique_key}")
    print(f"Content: {filing.char_count:,} chars")
    print(f"Sections: {list(filing.sections.keys()) if filing.sections else 'None'}")
    print()

    # Test extraction with explicit error handling
    print("=== Running Extraction ===")
    print(f"Model: {extractor.model}")
    print(f"Max tokens: {extractor.max_tokens}")

    try:
        # Manually replicate extract_nuggets to see the error
        from config.earnings_tickers import CORE_TICKERS

        is_core = filing.ticker in CORE_TICKERS
        tier = "core" if is_core else "secondary"
        tier_guidance = (
            "extract ALL relevant nuggets — this is a pure-play quantum company"
            if is_core
            else "only extract nuggets specifically mentioning quantum computing"
        )

        content = ""
        if filing.sections:
            for sn, st in filing.sections.items():
                content += f"\n\n--- {sn.upper()} ---\n\n{st}"
        else:
            content = filing.raw_content or ""

        max_chars = config.max_filing_chars
        if len(content) > max_chars:
            print(f"Truncating from {len(content):,} to {max_chars:,}")
            content = content[:max_chars]

        print(f"Content to send: {len(content):,} chars")

        from processing.nugget_extractor import NUGGET_EXTRACTION_PROMPT

        fiscal_period = f"FY{filing.fiscal_year}"
        prompt = NUGGET_EXTRACTION_PROMPT.format(
            ticker=filing.ticker,
            company_name=filing.company_name,
            filing_type=filing.filing_type,
            fiscal_period=fiscal_period,
            filing_date=filing.filing_date.strftime("%Y-%m-%d") if filing.filing_date else "N/A",
            tier=tier,
            tier_guidance=tier_guidance,
        )

        print(f"Prompt length: {len(prompt):,} chars")
        print(f"Total tokens estimate: ~{(len(prompt) + len(content)) // 4:,}")
        print()

        print("Calling LLM...")
        response = await extractor.client.messages_create(
            model=extractor.model,
            max_tokens=extractor.max_tokens,
            system=prompt,
            messages=[{"role": "user", "content": f"FILING CONTENT:\n\n{content}"}],
            temperature=extractor.temperature,
        )

        response_text = extractor.client.extract_text(response)
        print(f"\nLLM Response length: {len(response_text):,} chars")
        print(f"Response preview (first 500):\n{response_text[:500]}")
        print(f"\nResponse tail (last 200):\n{response_text[-200:]}")

        # Try parsing
        nuggets = extractor._parse_nuggets(response_text, filing)
        print(f"\nParsed nuggets: {len(nuggets)}")
        if nuggets:
            for i, n in enumerate(nuggets[:3]):
                print(f"\n  Nugget #{i+1}: [{n.nugget_type.value}]")
                print(f"    {n.nugget_text[:150]}...")
        else:
            print("  NO NUGGETS PARSED")
            # Try to understand why
            import json, re
            try:
                data = json.loads(response_text)
                print(f"  Direct JSON parse: type={type(data)}, len={len(data) if isinstance(data, list) else 'N/A'}")
            except json.JSONDecodeError as e:
                print(f"  Direct JSON parse failed: {e}")

            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
            if json_match:
                print(f"  Found code fence, content length: {len(json_match.group(1))}")
                try:
                    data = json.loads(json_match.group(1))
                    print(f"  Code fence parse: type={type(data)}, len={len(data) if isinstance(data, list) else 'N/A'}")
                except json.JSONDecodeError as e:
                    print(f"  Code fence parse failed: {e}")
            else:
                print("  No code fence found")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

asyncio.run(test())
