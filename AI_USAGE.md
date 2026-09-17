# AI usage

AI tools were used as an accelerator, not as the owner of the design. All behaviour below was reviewed, run (or traced), and in several places changed.

## Tools
- Cursor agent (Grok) for scaffolding, tests, and first-pass documentation
- Manual review of the starter Kubernetes file, schema, and data generator **before** any generated code

## Tasks where AI was used
- FastAPI/SQLAlchemy layout and pytest fixtures
- Playwright selectors and config
- First drafts of RCA documents and SETUP/ARCHITECTURE
- Kubernetes YAML boilerplate (probes, StatefulSet, kustomize)

## Representative prompts / interaction summaries
1. “Analyse this repo first” — used to map scoring, required folders, and planted defects before writing code.
2. “Finish this assessment 100%” — implement MiniPay, SQL, K8s, CLI, tests, and incidents as a coherent submission.
3. “Identify defects in `broken-api.yaml` rather than replacing it silently” — findings file + annotated copy.
4. “Support CLI should diagnose stuck, recon gaps, and duplicate refs with exit codes.”
5. “INCIDENT-001 must introduce a realistic defect, reproduce it, then fix it.”
6. Terminal paste of `docker build` / `kubectl apply` failures (Hyper-V socket, `docker_engine` pipe, `6443` refused) — diagnose as **Rancher Desktop VM down**, not MiniPay YAML; record in `evidence/environment-blockers.md`.

## How output was validated
- Read `starter/kubernetes/broken-api.yaml` line by line; every defect in `investigation/kubernetes-findings.md` maps to a concrete field (selector, ports, image).
- Traced `database/generate_data.py` to confirm duplicate refs (`i % 5000`) and callback gaps (`random() < 0.94`).
- API tests cover auth, 422, 404, idempotency, duplicate search, the 500 reproduction flag, and `/health` latency.
- Analyzer unit tests cover stuck, recon gap, and duplicate findings without needing a live cluster.
- Idempotency lookup was corrected after the first generated version only searched `Idempotency-Key` and would have missed `transaction_ref` replays.

## Example of rejected / materially improved AI output
**Rejected:** apply a unique constraint on `transaction_ref` immediately as the INCIDENT-001 fix.

**Why:** the generator *intentionally* inserts duplicates. A unique constraint would make `seed.py` fail and hide the incident instead of documenting it.

**What shipped instead:** search returns all rows with `duplicate_ref: true`; a non-unique btree fixes INCIDENT-003; unique constraint is listed as a *follow-up after cleanup*.

**Also rejected:** silently replacing `starter/kubernetes/broken-api.yaml`. The starter file is unchanged; the diagnosis lives in `investigation/kubernetes-findings.md` and `kubernetes/broken-api.annotated.yaml`.

**Also rejected (2026-09-17):** treating `ContainerCreating` / `Pending` after `kubectl apply -k` as INCIDENT-002 still being unfixed. The overlay had already corrected selectors/ports; the engine had no image and the WSL VM was crash-looping. Documented as environment evidence instead of changing working YAML.
