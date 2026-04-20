"""Quick utility to peek at what's in the dedup DB."""
import sqlite3
import sys

source_filter = sys.argv[1] if len(sys.argv) > 1 else ""

conn = sqlite3.connect("data/seen.db")
if source_filter:
    q = "SELECT source, title FROM seen WHERE source LIKE ? LIMIT 10"
    rows = conn.execute(q, (f"{source_filter}%",)).fetchall()
else:
    rows = conn.execute("SELECT source, title FROM seen LIMIT 10").fetchall()

for src, title in rows:
    print(f"[{src}] {title}")

print(f"\nTotal rows: {conn.execute('SELECT COUNT(*) FROM seen').fetchone()[0]}")