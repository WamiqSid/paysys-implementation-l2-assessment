-- 4. Duplicate transaction references (data-quality issue planted by the generator).
SELECT
    transaction_ref,
    COUNT(*) AS occurrences,
    ARRAY_AGG(id ORDER BY id) AS transaction_ids,
    SUM(amount) AS combined_value
FROM transactions
GROUP BY transaction_ref
HAVING COUNT(*) > 1
ORDER BY occurrences DESC, transaction_ref;
