-- 3. Transactions that have remained in PROCESSING for more than 15 minutes.
SELECT
    id,
    transaction_ref,
    customer_id,
    amount,
    status,
    created_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - created_at)) / 60.0, 2) AS minutes_open
FROM transactions
WHERE status = 'PROCESSING'
  AND created_at < NOW() - INTERVAL '15 minutes'
ORDER BY created_at;
