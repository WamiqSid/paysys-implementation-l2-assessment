-- 1. Transaction count and total value by status and day.
SELECT
    created_at::date AS tx_day,
    status,
    COUNT(*) AS tx_count,
    SUM(amount) AS total_value
FROM transactions
GROUP BY created_at::date, status
ORDER BY tx_day, status;
