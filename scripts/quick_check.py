import sqlite3
c = sqlite3.connect('data/quantum_intel.db')
print('=== SEC Pipeline Results ===')
print(f'Filings: {c.execute("SELECT COUNT(*) FROM sec_filings").fetchone()[0]}')
print(f'Nuggets: {c.execute("SELECT COUNT(*) FROM sec_nuggets").fetchone()[0]}')
print()
print('Per-ticker breakdown:')
rows = c.execute('SELECT ticker, COUNT(*) as cnt FROM sec_nuggets GROUP BY ticker ORDER BY cnt DESC').fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]} nuggets')
print()
print('By nugget type:')
rows = c.execute('SELECT nugget_type, COUNT(*) as cnt FROM sec_nuggets GROUP BY nugget_type ORDER BY cnt DESC').fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]}')
print()
print('Sample high-relevance nuggets:')
rows = c.execute('SELECT ticker, nugget_type, nugget_text FROM sec_nuggets WHERE relevance_score >= 0.9 LIMIT 5').fetchall()
for r in rows:
    print(f'  [{r[0]}] [{r[1]}] {r[2][:150]}')
c.close()
