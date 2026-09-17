-- 7. Average and p95 processing time (created_at → completed_at).
SELECT
    COUNT(*) AS completed_tx,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)))::numeric, 3) AS avg_seconds,
    ROUND(
        (percentile_cont(0.95) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at))
        ))::numeric,
        3
    ) AS p95_seconds
FROM transactions
WHERE completed_at IS NOT NULL;
