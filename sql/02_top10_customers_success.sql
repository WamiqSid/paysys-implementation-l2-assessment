-- 2. Top 10 customers by successful transaction value.
SELECT
    c.id,
    c.customer_ref,
    c.name,
    COUNT(*) AS success_count,
    SUM(t.amount) AS success_value
FROM transactions t
JOIN customers c ON c.id = t.customer_id
WHERE t.status = 'SUCCESS'
GROUP BY c.id, c.customer_ref, c.name
ORDER BY success_value DESC, c.id
LIMIT 10;
