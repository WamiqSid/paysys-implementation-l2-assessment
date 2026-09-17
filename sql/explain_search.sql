-- Baseline vs indexed lookup used for INCIDENT-003 / PERFORMANCE.md.
-- Run before sql/indexes.sql, then again after.

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT *
FROM transactions
WHERE transaction_ref = 'TXN00004999';
