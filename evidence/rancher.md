# Rancher evidence

## What this workstation actually had

[Rancher Desktop](https://rancherdesktop.io/) **was installed and used** (not only a Helm theory). kubectl context: `rancher-desktop`. Kubernetes toggle: enabled. Container engine: moby. Settings snapshot via `rdctl list-settings`: Kubernetes 1.36.4 on port 6443, VM **2 GB / 2 CPUs**.

A full Rancher **Manager** Helm chart (`cattle-system`) was **not** installed. Rancher Desktop is the local k3s + UI path allowed by the instructions.

## Attempt (commands run)

```powershell
docker build -t minipay-api:1.0.0 ./minipay
# failed: timed out dialing Hyper-V socket

kubectl apply -k kubernetes/
# succeeded while API was briefly up: minipay-api Deployment, minipay-db StatefulSet created

kubectl -n minipay get pods
# API: ContainerCreating; DB: Pending

rdctl api /v1/backend_state
# {"vmState":"ERROR","locked":false}  then later STARTING with rancher-desktop WSL Stopped
```

Full error text, log excerpts, and causes: **`evidence/environment-blockers.md`**.

## Blockers (short)

1. Docker engine socket / named pipe down → image never built.
2. `rancher-desktop` WSL distro crash-loop (`/sbin/init` exit 1).
3. VM sized at 2 GB; Windows disk ~93% full.
4. Second Rancher Desktop instance started (backend race).
5. After the VM died: `kubectl` → `127.0.0.1:6443` connection refused.

## Procedure once the cluster is Running

Use Cluster Explorer (Rancher Desktop / Rancher Manager) **or** the kubectl equivalents. Same tasks either way.

| Required evidence | Rancher UI | kubectl |
|---|---|---|
| Cluster / workload visibility | Cluster → Workloads, namespace `minipay` | `kubectl get deploy,sts,po -n minipay` |
| Pod status | Pods Ready 1/1 | `kubectl -n minipay get pods -o wide` |
| Logs | Pod → View Logs | `kubectl -n minipay logs deploy/minipay-api --tail=200` |
| Config / env | Deployment → Environment (redact secrets) | `kubectl -n minipay describe deploy minipay-api` |
| Scale / restart | Scale / Redeploy | `kubectl -n minipay scale deploy/minipay-api --replicas=3` then `rollout restart` |
| Resource / health | Metrics | `kubectl top pod -n minipay` |

Optional Helm Rancher Manager (when Docker works):

```bash
helm repo add rancher-latest https://releases.rancher.com/server-charts/latest
kubectl create namespace cattle-system
helm install rancher rancher-latest/rancher \
  --namespace cattle-system \
  --set hostname=rancher.localhost \
  --set replicas=1 \
  --set bootstrapPassword=CHANGE_ME
```

Do not commit the bootstrap password.

## Screenshots

Not captured: the UI never stayed in a healthy Kubernetes Running state long enough for a meaningful workload screenshot. When captured, store under `evidence/screenshots/` with secrets redacted.

## After INCIDENT-002 (manifests, independent of this outage)

Starter YAML → Ready 0/N and empty Endpoints (`investigation/kubernetes-findings.md`). Corrected overlay: `kubectl apply -k kubernetes/`. In Rancher that should show Ready 2/2 once the **engine** is healthy and `minipay-api:1.0.0` is loaded.
