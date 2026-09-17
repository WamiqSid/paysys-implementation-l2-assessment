-- 5. Daily success rate as a percentage.
SELECT
    created_at::date AS tx_day,
    COUNT(*) AS total_tx,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') AS success_tx,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status = 'SUCCESS') / NULLIF(COUNT(*), 0),
        2
    ) AS success_rate_pct
FROM transactions
GROUP BY created_at::date
ORDER BY tx_day;
