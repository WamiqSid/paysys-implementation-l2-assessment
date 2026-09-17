-- 6. Reconciliation: successful transactions vs successful callbacks.
-- A SUCCESS row with no SUCCESS callback is a downstream notification gap.
WITH tx AS (
    SELECT
        COUNT(*) AS success_count,
        COALESCE(SUM(amount), 0) AS success_value
    FROM transactions
    WHERE status = 'SUCCESS'
),
cb AS (
    SELECT
        COUNT(*) AS callback_success_count,
        COALESCE(SUM(t.amount), 0) AS callback_success_value
    FROM callbacks c
    JOIN transactions t ON t.id = c.transaction_id
    WHERE c.callback_status = 'SUCCESS'
),
gaps AS (
    SELECT
        COUNT(*) AS success_without_callback_count,
        COALESCE(SUM(t.amount), 0) AS success_without_callback_value
    FROM transactions t
    WHERE t.status = 'SUCCESS'
      AND NOT EXISTS (
          SELECT 1
          FROM callbacks c
          WHERE c.transaction_id = t.id
            AND c.callback_status = 'SUCCESS'
      )
)
SELECT
    tx.success_count,
    tx.success_value,
    cb.callback_success_count,
    cb.callback_success_value,
    tx.success_count - cb.callback_success_count AS count_gap,
    tx.success_value - cb.callback_success_value AS value_gap,
    gaps.success_without_callback_count,
    gaps.success_without_callback_value
FROM tx, cb, gaps;
