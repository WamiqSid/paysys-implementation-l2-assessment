# Paysys Labs – MiniPay implementation & L2 assessment

Public submission for the Implementation & L2 Support Engineer exercise. MiniPay is a small payment stack: operator UI, REST API, PostgreSQL (SQLite locally), Kubernetes manifests, SQL investigations, a Python L2 CLI, API/UI automation, and three incident RCAs.

**Default login (local demo):** API key `minipay-dev-key`  
**App:** http://127.0.0.1:8080 after setup

## Quick start
See [SETUP.md](SETUP.md). Shortest path:

```bash
pip install -r minipay/requirements.txt pytest httpx
pip install -r python/requirements.txt
cd minipay && python seed.py --reset && python -m uvicorn app.main:app --port 8080
```

## Repository map

| Path | What it is |
|---|---|
| `minipay/` | FastAPI app + operator UI + Dockerfile + seeder |
| `database/` | Canonical schema and 50k-row generator |
| `sql/` | Seven investigation queries, indexes, performance write-up |
| `kubernetes/` | Corrected manifests (do not apply the starter YAML) |
| `python/` | L2 support CLI + unit tests |
| `tests/api/` | pytest API suite (`python -m pytest tests/api -q`) |
| `tests/ui/` | Playwright journeys (`npx playwright test`) |
| `investigation/` | INCIDENT-001/002/003 RCAs + Kubernetes findings |
| `evidence/` | Linux capture, Rancher attempt, Docker/K8s blockers |
| `ARCHITECTURE.md` | Runtime design |
| `AI_USAGE.md` | How AI was used and where it was overruled |

## Scoring coverage

| Area | Where to look |
|---|---|
| L2 incidents (20) | `investigation/INCIDENT-00*.md` |
| Kubernetes (15) | `kubernetes/`, `investigation/kubernetes-findings.md` (live pods blocked: `evidence/environment-blockers.md`) |
| SQL (15) | `sql/*.sql`, `sql/PERFORMANCE.md` |
| Python CLI (15) | `python/support_tool.py` |
| API tests (10) | `tests/api/` |
| UI tests (10) | `tests/ui/` |
| Linux (5) | `evidence/linux.md`, `evidence/healthcheck.sh` |
| Git (5) | history + tag `submission-v1.0` |
| Rancher (5) | `evidence/rancher.md` (Desktop installed; cluster VM did not stay up) |

## What is still environment-blocked
Application code, SQL, CLI, API/UI tests, and corrected Kubernetes YAML are in the repo. A **live** Ready cluster and Rancher screenshots were not finished on this Windows PC: Docker/Rancher Desktop crashed (Hyper-V socket, missing docker pipe, `6443` refused, WSL `rancher-desktop` Stopped). Causes and commands: `evidence/environment-blockers.md`. Evaluator can replay K8s on any machine with a working Docker/Kind/K3s using `SETUP.md` and `kubernetes/README.md`.

## Git
Work is on `main`. Tag the final pushed snapshot `submission-v1.0`.
