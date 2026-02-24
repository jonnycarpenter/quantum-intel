"""Test extraction with the fixed 180s timeout."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from storage.sqlite import SQLiteStorage
from processing.quote_extractor import QuoteExtractor
from config.settings import EarningsConfig
from models.earnings import EarningsTranscript

async def test():
    storage = SQLiteStorage(db_path="data/quantum_intel.db")
    config = EarningsConfig()
    extractor = QuoteExtractor(config)
    print(f"Model: {config.extraction_model}")
    print(f"Client timeout: {extractor.client.timeout}s")

    # Get shortest transcript for fastest test
    rows = storage._conn.execute(
        "SELECT transcript_id, ticker, company_name, year, quarter, transcript_text "
        "FROM earnings_transcripts ORDER BY char_count ASC LIMIT 1"
    ).fetchall()

    if not rows:
        print("No transcripts in DB!")
        return

    row = rows[0]
    transcript = EarningsTranscript(
        transcript_id=row[0], ticker=row[1], company_name=row[2],
        year=row[3], quarter=row[4], transcript_text=row[5],
    )
    print(f"Transcript: {transcript.unique_key} ({transcript.char_count:,} chars)")
    print(f"Calling LLM with 180s timeout...")

    result = await extractor.extract_quotes(transcript)
    print(f"\nQuotes extracted: {result.total_quotes}")

    if result.quotes:
        for i, q in enumerate(result.quotes[:5]):
            print(f"  [{q.speaker_name} ({q.speaker_role.value})] {q.quote_type.value}: {q.quote_text[:80]}...")

        # Save to DB
        saved = await storage.save_quotes(result.quotes)
        print(f"\nSaved {saved} quotes to DB")
    else:
        print("No quotes — extraction likely failed/errored")

    await storage.close()

asyncio.run(test())
