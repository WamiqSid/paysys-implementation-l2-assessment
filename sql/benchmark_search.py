"""Time transaction_ref lookups before and after a btree index.

Works with the local SQLite database (DATABASE_URL) so the INCIDENT-003
evidence can be produced without PostgreSQL. For Postgres plans see PERFORMANCE.md.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "minipay.db"


def db_path() -> Path:
    url = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB.as_posix()}")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    raise SystemExit("benchmark_search.py is the SQLite helper; use sql/explain_search.sql on PostgreSQL")


def timed_lookup(con: sqlite3.Connection, ref: str, n: int = 200) -> float:
    cur = con.cursor()
    start = time.perf_counter()
    for _ in range(n):
        cur.execute("SELECT id, status, amount FROM transactions WHERE transaction_ref = ?", (ref,))
        cur.fetchall()
    return (time.perf_counter() - start) / n * 1000


def main() -> None:
    path = db_path()
    if not path.exists():
        print(f"database not found at {path}; run: python minipay/seed.py", file=sys.stderr)
        raise SystemExit(1)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    plan_before = con.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM transactions WHERE transaction_ref = 'TXN00004999'"
    ).fetchall()
    ms_before = timed_lookup(con, "TXN00004999")
    con.execute("CREATE INDEX IF NOT EXISTS idx_transactions_ref ON transactions (transaction_ref)")
    plan_after = con.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM transactions WHERE transaction_ref = 'TXN00004999'"
    ).fetchall()
    ms_after = timed_lookup(con, "TXN00004999")
    count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"rows={count}")
    print(f"plan_before={plan_before}")
    print(f"avg_ms_before={ms_before:.3f}")
    print(f"plan_after={plan_after}")
    print(f"avg_ms_after={ms_after:.3f}")
    if ms_after > 0:
        print(f"speedup_x={ms_before / ms_after:.1f}")


if __name__ == "__main__":
    main()
