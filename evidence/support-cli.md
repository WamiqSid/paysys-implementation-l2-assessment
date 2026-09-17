# L2 support CLI run

Against the local API (50k-row SQLite seed) on 2026-09-14:

```bash
python python/support_tool.py --health
python python/support_tool.py --transaction TXN00004999
python python/support_tool.py --stuck
```

`--health` returned API up / database up.

`--transaction TXN00004999` (planted duplicate) exited 2 and reported:

- `DUPLICATE_TRANSACTION_REF` (2 rows)
- `PAYMENT_FAILED` (`UPSTREAM_ERROR`, 2 callback attempts)

`--stuck` listed 50 PROCESSING payments older than 15 minutes (endpoint cap). Exit code 2 is intentional when anomalies exist (0 = clean, 1 = not found, 3 = dependency failure, 4 = usage).
