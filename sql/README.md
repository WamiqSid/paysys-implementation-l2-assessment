# SQL investigation

PostgreSQL scripts for MiniPay. Apply `database/schema.sql`, load data (`python minipay/seed.py` or `database/generate_data.py`), then:

```bash
psql "$DATABASE_URL" -f sql/01_tx_count_value_by_status_day.sql
psql "$DATABASE_URL" -f sql/02_top10_customers_success.sql
psql "$DATABASE_URL" -f sql/03_stuck_processing.sql
psql "$DATABASE_URL" -f sql/04_duplicate_refs.sql
psql "$DATABASE_URL" -f sql/05_daily_success_rate.sql
psql "$DATABASE_URL" -f sql/06_reconciliation.sql
psql "$DATABASE_URL" -f sql/07_processing_time_avg_p95.sql
```

Capture the slow-search plan **before** indexing:

```bash
psql "$DATABASE_URL" -f sql/explain_search.sql
psql "$DATABASE_URL" -f sql/indexes.sql
psql "$DATABASE_URL" -f sql/explain_search.sql
```

Details of the index change are in `PERFORMANCE.md`.
