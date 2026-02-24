"""Check SEC pipeline results in the database."""
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/quantum_intel.db"
conn = sqlite3.connect(db_path)

print("=" * 60)
print("SEC PIPELINE - DB REPORT")
print("=" * 60)

# Filings
rows = conn.execute(
    "SELECT ticker, filing_type, filing_date, char_count "
    "FROM sec_filings ORDER BY ticker, filing_date"
).fetchall()
print(f"\nSEC FILINGS: {len(rows)}")
for r in rows:
    print(f"  {r[0]} {r[1]} {r[2]} | {r[3]:,} chars")

# Nuggets
nug_count = conn.execute("SELECT COUNT(*) FROM sec_nuggets").fetchone()[0]
print(f"\nSEC NUGGETS: {nug_count}")

# Sample nuggets
nuggets = conn.execute(
    "SELECT ticker, nugget_type, signal_strength, relevance_score, "
    "substr(nugget_text, 1, 150) "
    "FROM sec_nuggets ORDER BY relevance_score DESC LIMIT 10"
).fetchall()
print(f"\nTOP 10 NUGGETS (by relevance):")
for n in nuggets:
    print(f"  [{n[0]}] {n[1]} | strength={n[2]} | rel={n[3]}")
    print(f'    "{n[4]}..."')

# Per-ticker nugget counts
ticker_counts = conn.execute(
    "SELECT ticker, COUNT(*) as cnt FROM sec_nuggets GROUP BY ticker ORDER BY cnt DESC"
).fetchall()
print(f"\nNUGGETS PER TICKER:")
for tc in ticker_counts:
    print(f"  {tc[0]}: {tc[1]} nuggets")

# Filing content quality check
sample = conn.execute(
    "SELECT ticker, filing_type, substr(raw_content, 1, 200) "
    "FROM sec_filings LIMIT 1"
).fetchone()
if sample:
    print(f"\nSAMPLE CONTENT ({sample[0]} {sample[1]}):")
    print(f'  "{sample[2]}..."')

conn.close()
