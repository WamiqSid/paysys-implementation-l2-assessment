# API test run

Command:

```bash
python -m pytest tests/api python/tests -q
```

Result (this submission):

```text
19 passed, 28 warnings in 1.36s
```

Covers success paths, validation 422, unknown 404, missing/invalid API key 401, idempotent replay 200, idempotency conflict 409, failed sentinel amount, duplicate-ref 200, buggy-search 500, stuck-ops, and `/health` under 500 ms.
