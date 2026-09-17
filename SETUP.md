# Setup

## Prerequisites
- Python 3.12+
- Node.js 20+ (UI tests only)
- Docker + Docker Compose (recommended PostgreSQL path)
- Optional: Kind or K3s, kubectl, Rancher Desktop

If Docker or `kubectl` fail on Windows (Hyper-V socket timeout, missing `docker_engine` pipe, or `127.0.0.1:6443` refused), use **section 1** and read `evidence/environment-blockers.md`. Those errors are the workstation runtime, not MiniPay.

## 1. Local (SQLite, no Docker)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r minipay/requirements.txt -r python/requirements.txt pytest httpx
copy .env.example .env   # Windows
# cp .env.example .env  # Linux/macOS

cd minipay
python seed.py --reset --transactions 50000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open http://127.0.0.1:8080 and sign in with `minipay-dev-key`.

## 2. Docker Compose (PostgreSQL)

```bash
docker compose up --build -d
docker compose --profile seed run --rm seed
curl -fsS http://127.0.0.1:8080/health
```

## 3. Kubernetes

See `kubernetes/README.md`. Summary:

```bash
docker build -t minipay-api:1.0.0 ./minipay
kind create cluster --name minipay
kind load docker-image minipay-api:1.0.0 --name minipay
kubectl apply -k kubernetes/
kubectl -n minipay rollout status deploy/minipay-api
kubectl -n minipay port-forward svc/minipay-api 8080:80
```

Do **not** apply `starter/kubernetes/broken-api.yaml` except to reproduce INCIDENT-002.

## Tests

```bash
python -m pytest tests/api python/tests -q

cd tests/ui
npm install
npx playwright install chromium
npx playwright test
```

L2 tool:

```bash
python python/support_tool.py --health
python python/support_tool.py --transaction TXN00000001
```

SQL (Postgres URL):

```bash
psql "$DATABASE_URL" -f sql/01_tx_count_value_by_status_day.sql
# ... 02–07, then explain_search.sql, indexes.sql
```

## Default credentials (local demo only)
- API key: `minipay-dev-key`
- Compose DB: `minipay` / `minipay` / database `minipay`

Never commit real secrets. Kubernetes `secret.yaml` contains placeholders labelled `change-me`.
