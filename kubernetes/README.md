# Kubernetes operations

Primary path: Kind (or Minikube/K3s). Rancher can sit in front of the same cluster.

## Build and load the API image

```bash
docker build -t minipay-api:1.0.0 ./minipay
kind create cluster --name minipay
kind load docker-image minipay-api:1.0.0 --name minipay
kubectl apply -k kubernetes/
kubectl -n minipay rollout status deploy/minipay-api
kubectl -n minipay get pods,svc,endpoints
kubectl -n minipay logs deploy/minipay-api --tail=100
kubectl -n minipay port-forward svc/minipay-api 8080:80
```

Seed after Postgres is Ready:

```bash
kubectl -n minipay wait --for=condition=ready pod -l app=minipay-db --timeout=180s
# Copy seed job or run:
kubectl -n minipay exec deploy/minipay-api -- python seed.py --reset
```

If `seed.py` is not in the runtime image working tree beyond `/app/seed.py`, it is.

## Rollout / restart

```bash
kubectl -n minipay rollout restart deploy/minipay-api
kubectl -n minipay rollout status deploy/minipay-api
kubectl -n minipay rollout undo deploy/minipay-api   # rollback
kubectl -n minipay scale deploy/minipay-api --replicas=3
```

## Live apply on the assessment workstation (2026-09-17)

`kubectl apply -k kubernetes/` created the Deployment and StatefulSet. Pods stayed `ContainerCreating` / `Pending` because Rancher Desktop’s VM was dying and `docker build` never produced `minipay-api:1.0.0`. See `evidence/environment-blockers.md`. Re-run the build/load steps above only after `docker version` shows a Server and `kubectl get nodes` is Ready.

## What was wrong with the starter manifest

See `investigation/kubernetes-findings.md` and `broken-api.annotated.yaml`.
Do not apply `starter/kubernetes/broken-api.yaml`.
