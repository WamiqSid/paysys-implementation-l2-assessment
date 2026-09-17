# API integration notes

Command for the full API suite:

```bash
python -m pytest tests/api -q
```

Against a running server the same cases can be replayed with any HTTP client; the pytest module is the source of truth.

## Timeouts
Callers should set an explicit connect/read timeout (MiniPay CLI defaults to 8s). `/live` is process liveness only; `/health` includes a database ping and is the readiness signal. If `/health` times out, fail the instance out of the load balancer rather than retrying forever.

## Retries
Retry **only** on transport failures, HTTP 408, 425, 429, and 5xx, with exponential backoff and jitter. Never retry 400/401/403/404/409/422 — those are client or state errors. Payment creation must send an `Idempotency-Key` (or a stable `transaction_ref`) so a retried POST cannot double-charge.

## Idempotency
`POST /api/payments` treats `Idempotency-Key` or `transaction_ref` as a replay token. The same payload returns the original payment (`200`). A different payload with the same key returns `409`.

## HTTP 4xx versus 5xx
- **4xx**: the request is wrong or not allowed (validation, auth, missing customer, conflict). The client must change the request.
- **5xx**: MiniPay failed (example: INCIDENT-001 used `.one()` on a non-unique `transaction_ref` and raised `MultipleResultsFound`). Operators fix the service; clients may retry with backoff and idempotency.

## Error bodies
Errors return JSON `{"detail": "..."}` and, for the documented search defect, `{"code": "DUPLICATE_REF_LOOKUP"}`. Tests assert status, body shape, and a 500 ms budget for `/health`.
