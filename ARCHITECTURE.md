# Architecture

MiniPay is a small payment-processing stack used for implementation and L2 support: a REST API, an operator UI served by the same process, PostgreSQL (SQLite for laptop tests), and a Python diagnostic CLI.

```text
Browser UI  ──►  MiniPay API :8080  ──►  PostgreSQL
                      ▲
                      └── L2 CLI (python/support_tool.py)
```

Kubernetes (corrected overlay):

```text
Namespace minipay
  StatefulSet minipay-db   PVC 5Gi    Service minipay-db (headless)
  Deployment  minipay-api  x2         Service minipay-api :80 → 8080
  ConfigMap   minipay-config
  Secret      minipay-secrets         (placeholders only)
```

## API
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/live` | no | Process liveness |
| GET | `/health` | no | Readiness: API + DB |
| POST | `/api/customers` | API key | 201 / 409 duplicate ref |
| GET | `/api/customers/{id}` | API key | |
| GET | `/api/customers/{id}/payments` | API key | |
| POST | `/api/payments` | API key | Idempotency-Key; 13.13 fails (test sentinel) |
| GET | `/api/payments/{id}` | API key | |
| GET | `/api/search?q=` | API key | Duplicate refs return 200 + warning |
| GET | `/api/ops/stuck` | API key | PROCESSING > 15 minutes |
| GET | `/api/ops/failed` | API key | |
| GET | `/api/ops/health` | API key | |

Auth: `X-API-Key` or `Authorization: Bearer`.

## Data
`customers`, `transactions`, `callbacks` — see `database/schema.sql`. Seed matches `database/generate_data.py` (50k txs, duplicate refs, ~6% SUCCESS without SUCCESS callback).

## Failure modes we operate on
- **INCIDENT-001:** non-unique `transaction_ref` + `.one()` → HTTP 500. Fixed in search; flag `BUGGY_SEARCH` reproduces it.
- **INCIDENT-002:** broken Service selector/ports/image in starter YAML.
- **INCIDENT-003:** unindexed `transaction_ref` sequential scan.

## Supportability
- JSON logs to stdout (container-friendly).
- Distinct live vs ready probes.
- Resource requests/limits.
- L2 CLI with timeouts, exit codes, `--json`, `--stuck`, `--health`.
- Secrets via env / Kubernetes Secret, not source.
