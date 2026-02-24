"""Detailed DB report for Phase 4B verification."""
import sqlite3, sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/quantum_intel.db"
conn = sqlite3.connect(db_path)

print("=" * 60)
print("PHASE 4B SMOKE TEST - DB REPORT")
print("=" * 60)

# Transcripts
rows = conn.execute(
    "SELECT ticker, year, quarter, char_count FROM earnings_transcripts ORDER BY ticker, year, quarter"
).fetchall()
print(f"\nEARNINGS TRANSCRIPTS: {len(rows)}")
for r in rows:
    print(f"  {r[0]} Q{r[2]} {r[1]}: {r[3]:,} chars")

# Quotes
count = conn.execute("SELECT COUNT(*) FROM earnings_quotes").fetchone()[0]
print(f"\nEARNINGS QUOTES: {count}")
quotes = conn.execute(
    "SELECT ticker, speaker_name, speaker_role, quote_type, relevance_score, quote_text "
    "FROM earnings_quotes ORDER BY ticker, relevance_score DESC"
).fetchall()
for q in quotes:
    print(f"  [{q[0]}] {q[1]} ({q[2]}) | {q[3]} | rel={q[4]}")
    print(f"    \"{q[5][:120]}...\"")

# Tickers with no transcripts
print(f"\nTICKERS WITHOUT TRANSCRIPTS:")
all_tickers = ['IONQ', 'QBTS', 'RGTI', 'QUBT', 'ARQQ', 'QMCO', 'QTUM', 'GOOG', 'GOOGL', 'IBM', 'MSFT', 'AMZN', 'HON', 'NVDA']
found = set(r[0] for r in rows)
missing = [t for t in all_tickers if t not in found]
print(f"  {missing if missing else '(none)'}")

# Articles
art_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
print(f"\nARTICLES: {art_count}")

conn.close()
