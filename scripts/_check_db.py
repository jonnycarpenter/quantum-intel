"""Quick DB check — tables and row counts."""
import sqlite3, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db = "data/quantum_intel.db"
print(f"DB exists: {os.path.exists(db)}")
conn = sqlite3.connect(db)
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print(f"\n{'Table':<30} {'Rows':>8}")
print("-" * 40)
for t in tables:
    count = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"{t:<30} {count:>8}")

# Check article domains
print("\n--- Articles by domain ---")
try:
    for row in c.execute("SELECT domain, COUNT(*) FROM articles GROUP BY domain").fetchall():
        print(f"  {row[0] or 'NULL'}: {row[1]}")
except Exception as e:
    print(f"  Error: {e}")

# Check briefings
print("\n--- Weekly briefings ---")
try:
    for row in c.execute("SELECT domain, week_of FROM weekly_briefings ORDER BY week_of DESC LIMIT 5").fetchall():
        print(f"  {row[0]}: {row[1]}")
except Exception as e:
    print(f"  No briefings table or error: {e}")

conn.close()
