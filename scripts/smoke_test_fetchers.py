"""Quick smoke test for SEC and Earnings fetchers."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fetchers.sec import SecFetcher
from fetchers.earnings import EarningsFetcher
from config.settings import SecConfig, EarningsConfig


def test_sec():
    print("=" * 60)
    print("SEC EDGAR Smoke Test")
    print("=" * 60)
    config = SecConfig()
    fetcher = SecFetcher(config)
    print(f"User-Agent: {config.edgar_user_agent}")

    try:
        filings = fetcher.get_company_filings(
            "IONQ", filing_types=["10-K"], max_filings=1
        )
        if filings:
            f = filings[0]
            print(f"SUCCESS: {f.ticker} {f.filing_type} FY{f.fiscal_year}")
            print(f"  accession: {f.accession_number}")
            print(f"  chars: {f.char_count}")
            sections = list(f.sections.keys()) if f.sections else []
            print(f"  sections: {sections}")
        else:
            print("WARNING: No filings returned (may be rate limited)")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


def test_earnings():
    print()
    print("=" * 60)
    print("Earnings (API Ninjas) Smoke Test")
    print("=" * 60)
    config = EarningsConfig()

    if not config.api_ninja_api_key:
        print("SKIP: No API_NINJA_API_KEY set")
        return

    fetcher = EarningsFetcher(config)
    print(f"API key present: ****{config.api_ninja_api_key[-4:]}")

    try:
        transcript = fetcher.fetch_transcript("IONQ", year=2024, quarter=3)
        if transcript:
            print(f"SUCCESS: {transcript.ticker} Q{transcript.quarter} {transcript.year}")
            print(f"  chars: {transcript.char_count}")
            print(f"  transcript_id: {transcript.transcript_id}")
        else:
            print("INFO: No transcript available for IONQ Q3 2024 (may not exist)")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_sec()
    test_earnings()
    print()
    print("Smoke tests complete.")
