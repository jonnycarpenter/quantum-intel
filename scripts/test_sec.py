"""Test nugget extraction on saved filing."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import sqlite3
from datetime import datetime, timezone
from models.sec_filing import SecFiling
from processing.nugget_extractor import NuggetExtractor
from config.settings import SecConfig

async def main():
    config = SecConfig()
    extractor = NuggetExtractor(config)
    print(f"Model: {extractor.model}")
    
    # Get filing from DB
    c = sqlite3.connect("data/quantum_intel.db")
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM sec_filings WHERE fiscal_year=2025 LIMIT 1").fetchone()
    c.close()
    
    d = dict(row)
    print(f"Filing: {d['ticker']} {d['filing_type']} FY{d['fiscal_year']}")
    print(f"raw_content: {len(d.get('raw_content',''))} chars")
    
    filing = SecFiling(
        ticker=d["ticker"],
        company_name=d.get("company_name", "IonQ Inc."),
        cik=d.get("cik", "1824920"),
        accession_number=d.get("accession_number", ""),
        filing_type=d["filing_type"],
        filing_date=datetime.fromisoformat(d["filing_date"]) if d.get("filing_date") else None,
        fiscal_year=d["fiscal_year"],
        fiscal_quarter=d.get("fiscal_quarter"),
        raw_content=d.get("raw_content", ""),
    )
    
    result = await extractor.extract_nuggets(filing)
    print(f"\nExtracted: {result.total_nuggets} nuggets")
    for n in result.nuggets[:3]:
        print(f"  [{n.nugget_type.value}] {n.nugget_text[:100]}...")

asyncio.run(main())
