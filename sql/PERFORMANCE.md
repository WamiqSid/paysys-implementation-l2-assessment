# Query performance

## Workload
MiniPay L2 search and the operator UI look up payments by `transaction_ref`. The supplied schema has **no index** on that column. After seeding 50,000 transactions this is a sequential scan on every search, matching INCIDENT-003.

The generator also plants duplicate refs (`i % 5000 == 0`), so a unique constraint cannot be added until those rows are cleaned up. A **non-unique btree** is the safe first fix.

## Query (before and after)

```sql
SELECT *
FROM transactions
WHERE transaction_ref = 'TXN00004999';
```

## Change
`sql/indexes.sql` adds:

```sql
CREATE INDEX idx_transactions_ref ON transactions (transaction_ref);
```

Related indexes for stuck-payment and customer history queries:

- `(status, created_at)` for PROCESSING older than 15 minutes
- `(customer_id)` for `/api/customers/{id}/payments`
- `(created_at)` for daily aggregations
- `callbacks(transaction_id)` for reconciliation joins

## Expected PostgreSQL 16 plans

**Before** (`EXPLAIN (ANALYZE, BUFFERS)` on ~50k rows, cold cache typical):

```text
Seq Scan on transactions
  Filter: (transaction_ref = 'TXN00004999')
  Rows Removed by Filter: ~49998
  Planning Time: <1 ms
  Execution Time: 8–25 ms (grows linearly with table size)
```

**After:**

```text
Index Scan using idx_transactions_ref on transactions
  Index Cond: (transaction_ref = 'TXN00004999')
  Planning Time: <1 ms
  Execution Time: <1 ms
```

Reproduce:

```bash
psql "$DATABASE_URL" -f sql/explain_search.sql   # before
psql "$DATABASE_URL" -f sql/indexes.sql
psql "$DATABASE_URL" -f sql/explain_search.sql   # after
```

On SQLite (local fallback) the same shape appears as `SCAN transactions` versus `SEARCH transactions USING INDEX idx_transactions_ref`. Capture it with:

```bash
python sql/benchmark_search.py
```

Captured on this submission’s 50,000-row SQLite database (`python minipay/seed.py --reset`):

```text
rows=50000
plan_before=[(2, 0, 216, 'SCAN transactions')]
avg_ms_before=10.922
plan_after=[(3, 0, 62, 'SEARCH transactions USING INDEX idx_transactions_ref (transaction_ref=?)')]
avg_ms_after=0.011
speedup_x=965.8
```

Lookups by `transaction_ref` dropped from **10.9 ms to 0.011 ms** (~966×).

## Why this and not a unique constraint first
A unique index would reject the planted duplicates and break seed reload. Non-unique btree fixes the read path immediately. After L2 cleans duplicates (see INCIDENT-001), a unique constraint is the permanent control.

## Trade-off
Each insert maintains the extra indexes. For this volume that cost is negligible compared with a full table scan on every operator search.
