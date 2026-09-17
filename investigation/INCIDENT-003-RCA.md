# INCIDENT-003 – Transaction Search Performance

**Priority:** P2  
**Service:** MiniPay database / search API  
**Status:** Closed – sequential scan on `transaction_ref` replaced with btree index

## Symptom
Operator searches slow down as volume grows. At 50k transactions they are already noticeable; they will worsen linearly.

## Reproduction
1. Load the generator volume (`python minipay/seed.py` → 1,000 customers / 50,000 transactions).
2. Explain the search used by the UI and L2 tool:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE transaction_ref = 'TXN00004999';
```

3. Local SQLite equivalent (this workstation fallback):

```bash
python sql/benchmark_search.py
```

## Evidence
The schema comment is explicit: *“Intentionally minimal indexing.”* There is no index on `transaction_ref`, `status`, or `customer_id`.

PostgreSQL therefore chooses a **Seq Scan**, filtering ~50k rows per search. SQLite shows `SCAN transactions` until `idx_transactions_ref` exists, then `SEARCH … USING INDEX`.

Measured on the seeded 50k-row SQLite database (`python sql/benchmark_search.py`):

```text
plan_before=SCAN transactions          avg_ms_before=10.922
plan_after=SEARCH USING INDEX idx_transactions_ref   avg_ms_after=0.011
speedup_x=965.8
```

Full write-up: `sql/PERFORMANCE.md`. Indexes: `sql/indexes.sql`.

## Hypotheses considered

| Hypothesis | Result |
|---|---|
| API JSON serialisation | Unlikely: slowness reported as data volume grows |
| N+1 callback queries | Possible secondary issue; `selectinload` used in the API. Not the SQL ticket. |
| Missing index on `transaction_ref` | **Confirmed** |
| Locking / vacuum | Not required to explain a sequential search |

## Root cause
Search-by-reference is the primary L2 access path and was unindexed. Cost is O(n) in table size.

## Improvement
```sql
CREATE INDEX idx_transactions_ref ON transactions (transaction_ref);
```

Also added supporting indexes for stuck-payment (`status, created_at`), customer history (`customer_id`), and callback joins. Duplicate refs remain, so the index is **non-unique** until INCIDENT-001 cleanup.

## Validation
Re-run `sql/explain_search.sql` after `sql/indexes.sql`. Plan must be an index scan/search. `python sql/benchmark_search.py` prints before/after milliseconds and a speedup ratio on SQLite.

## Preventive action
- Treat “how will L2 look this up?” as part of schema review.
- `EXPLAIN ANALYZE` on the top operator queries in staging with production-like volume before go-live.
- Do not add a unique constraint until duplicates are gone.
