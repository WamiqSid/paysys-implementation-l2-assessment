# INCIDENT-002 – Application Unavailable After Deployment

**Priority:** P1  
**Service:** MiniPay on Kubernetes  
**Status:** Closed – starter manifest defects identified and replaced with corrected resources

## Symptom
A new release was applied. Pods could appear, but users could not reach MiniPay. This matches `starter/kubernetes/broken-api.yaml`.

## Reproduction

```bash
kubectl create namespace minipay --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f starter/kubernetes/broken-api.yaml
kubectl -n minipay get pods,svc,endpoints,events
```

Expected (and observed against this manifest):

1. Image `YOUR_IMAGE_HERE` cannot be pulled (`ErrImagePull` / `ImagePullBackOff`).
2. Even with a real image, readiness probes hit **port 8081** while the process listens on **8080**, so pods never become Ready.
3. Service selector `app: minipay-backend` matches **no pods** (they are `app: minipay-api`), so `Endpoints` stay empty.
4. Service `targetPort: 8081` would still miss the container port after the selector was fixed.

## Evidence (commands to capture)

```bash
kubectl -n minipay describe deploy minipay-api
kubectl -n minipay describe svc minipay-api
kubectl -n minipay get endpoints minipay-api -o yaml
kubectl -n minipay logs deploy/minipay-api --tail=100
```

`investigation/kubernetes-findings.md` lists each defect. `kubernetes/broken-api.annotated.yaml` is the starter file with inline comments. Corrected resources are `kubernetes/*.yaml`.

## Root causes (all present in the starter file)

| Defect | Effect |
|---|---|
| Placeholder image | Pod never starts |
| Readiness port 8081 vs container 8080 | Pod not Ready; Service has no backends |
| Service selector `minipay-backend` | No Endpoints |
| Service targetPort 8081 | Traffic would miss the process |
| Namespace referenced, not created | Apply fails unless `minipay` already exists |
| No requests/limits, ConfigMap, Secret, PVC | Incomplete, unsafe production shape |

The incident text (“pods appear to start, users cannot access”) is specifically the probe + selector mismatch: kubelet may start the container while the Service still has zero ready endpoints.

## Correction
Apply the working set (real image, probes on named port `http`/8080, selector `app: minipay-api`, `targetPort: http`, namespace, ConfigMap, Secret placeholders, Postgres StatefulSet + PVC, resource requests/limits, distinct `/live` vs `/health`):

```bash
docker build -t minipay-api:1.0.0 ./minipay
kind load docker-image minipay-api:1.0.0 --name minipay
kubectl apply -k kubernetes/
kubectl -n minipay rollout status deploy/minipay-api
kubectl -n minipay port-forward svc/minipay-api 8080:80
curl -fsS http://127.0.0.1:8080/health
```

## Validation
- Manifest review: each starter defect maps to a field in `investigation/kubernetes-findings.md` and a correction in `kubernetes/`.
- Expected live checks (when the cluster engine is healthy):
  - `kubectl -n minipay get endpoints minipay-api` shows pod IPs on port 8080.
  - Readiness `/health`; liveness `/live`.
  - Two API replicas behind the Service.
- Live apply on the Windows assessment PC (2026-09-17): kustomize applied; pods did **not** become Ready because Rancher Desktop/Docker died (image never built, node not usable). That outage is documented in `evidence/environment-blockers.md` and is **not** a remaining starter-YAML defect.

## Preventive controls
1. **kubeconform / kube-linter** on manifests in CI (selector/port sanity).
2. **Smoke test after rollout:** `curl /health` via port-forward or ingress in the pipeline; fail the job if Endpoints are empty.
3. **Named ports** (`http`) so probe, containerPort, and Service targetPort cannot drift independently.
4. Staging apply of the *same* kustomize overlay used in production.
5. Rancher workload view: Ready 0/N is a stop-ship signal (see `evidence/rancher.md`).
