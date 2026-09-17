-- Apply after capturing the baseline plan in PERFORMANCE.md.
-- These indexes match the L2 investigation and UI/API search workload.

CREATE INDEX IF NOT EXISTS idx_transactions_ref
    ON transactions (transaction_ref);

CREATE INDEX IF NOT EXISTS idx_transactions_status_created
    ON transactions (status, created_at);

CREATE INDEX IF NOT EXISTS idx_transactions_customer_id
    ON transactions (customer_id);

CREATE INDEX IF NOT EXISTS idx_transactions_created_at
    ON transactions (created_at);

CREATE INDEX IF NOT EXISTS idx_callbacks_transaction_id
    ON callbacks (transaction_id);

CREATE INDEX IF NOT EXISTS idx_callbacks_status
    ON callbacks (callback_status);

ANALYZE customers;
ANALYZE transactions;
ANALYZE callbacks;
