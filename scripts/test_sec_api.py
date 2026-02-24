"""Smoke test for sec-api.io integration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fetchers.sec import SecFetcher
from config.settings import SecConfig

config = SecConfig()
print(f"API key: {config.sec_api_key[:10]}...")
print(f"Query URL: {config.sec_api_query_url}")
print(f"Extractor URL: {config.sec_api_extractor_url}")
print()

fetcher = SecFetcher(config)

# Step 1: Search for IONQ 10-K filings
print("=== STEP 1: Filing Search ===")
filings = fetcher.get_company_filings("IONQ", ["10-K"], max_filings=2)
print(f"Found {len(filings)} filings")
for f in filings:
    print(f"  {f.unique_key} | date={f.filing_date} | url={f.filing_url[:80]}")
print()

if not filings:
    print("FAILED: No filings found")
    sys.exit(1)

# Step 2: Extract sections for the most recent filing
print("=== STEP 2: Section Extraction ===")
filing = filings[0]
result = fetcher.fetch_filing_content(filing)

if not result:
    print("FAILED: Section extraction returned None")
    sys.exit(1)

print(f"Content length: {result.char_count:,} chars")
print(f"Sections: {list(result.sections.keys())}")
for name, content in result.sections.items():
    print(f"  {name}: {len(content):,} chars")
    # Show first 200 chars of each section
    preview = content[:200].replace("\n", " ")
    print(f"    Preview: {preview}...")
print()

# Verify quality
if result.char_count < 1000:
    print("FAILED: Content too short")
    sys.exit(1)

if not result.sections.get("risk_factors"):
    print("WARNING: No risk_factors section extracted")

print("=== SMOKE TEST PASSED ===")
