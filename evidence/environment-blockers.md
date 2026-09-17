# Workstation blockers (time lost on Docker / Kubernetes)

This file records **environment failures**, not MiniPay application defects. The manifests, SQL, CLI, and tests were completed without a healthy container runtime. A live Kind/K3s/Rancher demo is still the preferred close-out; until the VM stays up it cannot be completed on this PC.

**Date:** 2026-09-17  
**Host:** Windows 10 (`10.0.19045`), kubectl context `rancher-desktop`  
**Engine:** Rancher Desktop 1.24 (`docker` client `29.6.2-rd`, Kubernetes enabled, k3s 1.36.4, VM memory **2 GB**)

Instructions allow documenting the attempt, commands, blockers, and the operational procedure that would be used once the cluster is healthy (`INSTRUCTIONS.md` §2).

## What was attempted

```text
docker build -t minipay-api:1.0.0 ./minipay
kubectl apply -k kubernetes/
kubectl -n minipay get pods
```

`kubectl apply -k kubernetes/` **did** create `deployment.apps/minipay-api` and `statefulset.apps/minipay-db` while the API server was briefly up. Pods never became Ready.

## Timeline of errors (actual output)

### 1. Docker daemon not reachable (Hyper-V socket)

```text
ERROR: Error response from daemon: failed to connect to the backend: timed out dialing Hyper-V socket
```

**Cause:** the Docker CLI talks to Rancher Desktop’s Linux VM over a Hyper-V / WSL socket. The VM was hung or restarting, so the client timed out. This is **not** a Dockerfile error.

**Effect:** `minipay-api:1.0.0` was never built. The Deployment uses `image: minipay-api:1.0.0` and `imagePullPolicy: IfNotPresent`, so pods cannot start without that local image.

### 2. Apply succeeded; pods stuck

```text
NAME                           READY   STATUS              RESTARTS   AGE
minipay-api-…                  0/1     ContainerCreating   0          1s
minipay-db-0                   0/1     Pending             0          1s
```

**Cause (API):** ContainerCreating with no local image and a dying runtime.  
**Cause (DB):** Pending is typical when the node is not Ready or the PVC cannot bind (storage provisioner lives in the same VM).

This is **different** from INCIDENT-002 (wrong Service selector / probe ports). Those defects are in `starter/kubernetes/broken-api.yaml` and are already diagnosed. Here the overlay applied, but the **node/engine** could not run containers.

### 3. Docker named pipe gone

```text
failed to connect to the docker API at npipe:////./pipe/docker_engine
The system cannot find the file specified.
```

**Cause:** Rancher Desktop GUI still running, but the engine process that creates `\\.\pipe\docker_engine` had stopped. `docker version` showed **Client only** (no Server).

### 4. Kubernetes API refused

```text
dial tcp 127.0.0.1:6443: connectex: No connection could be made because the target machine actively refused it.
```

**Cause:** k3s was not listening on the Windows loopback. `--validate=false` would not help.

### 5. Backend state ERROR / STARTING, WSL distro crash-loop

Observed with `rdctl`:

```text
{"vmState":"ERROR","locked":false}
```

Then after restart: `vmState: STARTING` while `wsl -l -v` showed:

```text
rancher-desktop         Stopped
rancher-desktop-data    Stopped
Ubuntu                  Running
```

Logs (`%LOCALAPPDATA%\rancher-desktop\logs\`):

- `wsl.log`: `/sbin/init exited with status 1`
- `background.log`: Win32 socket proxy crash-loop; “A second instance was started”
- `k8s.log`: `Error: connect ECONNREFUSED 172.17.92.124:6443` then brief recovery, then VM die

**Cause:** the `rancher-desktop` WSL distro would not stay Running. Starting it with `wsl -d rancher-desktop -- echo hello` brought it up briefly; it stopped again within minutes.

## Root causes (environment)

| Factor | Why it wasted time |
|---|---|
| Rancher Desktop VM **2 GB RAM** | Too small for dockerd + k3s + Postgres StatefulSet + 2 API replicas. OOM / init crash looks like “Kubernetes is broken”. |
| Windows / WSL disk pressure | Ubuntu WSL `df` showed the Windows driver volume at **93% used, ~8.7 GB free**. Image pulls and k3s airgap cache fail or hang in that state. |
| Second Rancher Desktop instance | Log line “A second instance was started” races the backend. |
| Apply **before** `docker build` | Even a healthy cluster would ImagePull/ContainerCreating without `minipay-api:1.0.0`. |
| Hyper-V socket vs named-pipe | Same outage, two symptoms: timeout while the VM is wedged; missing pipe after it dies. |

## What is **not** the MiniPay bug

- FastAPI probes (`/live`, `/health`) and corrected selectors in `kubernetes/api.yaml`
- SQL scripts, Python CLI, pytest, Playwright (those run on the host Python/Node path)
- INCIDENT-002 starter YAML defects (documented separately)

## Recovery that was tried

1. `rdctl shutdown` + `wsl --shutdown` + relaunch Rancher Desktop → backend stuck `STARTING`.
2. `rdctl start --kubernetes.enabled=true` → no settings change, no recover.
3. Manual `wsl -d rancher-desktop` → Running, then Stopped again.

**Recommended on this PC (when wrapping live K8s):**

1. Close extra Rancher windows; keep one.
2. Preferences → Virtual Machine: **≥ 6 GB** RAM.
3. Free ≥ 20 GB on `C:` (Windows volume was ~93% full).
4. Wait until UI shows Kubernetes Running; confirm:

   ```powershell
   docker version          # must print a Server section
   kubectl get nodes       # Ready
   ```

5. Then:

   ```powershell
   docker build -t minipay-api:1.0.0 ./minipay
   kubectl apply -k kubernetes/
   kubectl -n minipay rollout status deploy/minipay-api
   ```

6. If the distro still crash-loops: Rancher Desktop → Troubleshooting → Reset Kubernetes (or Factory Reset). That wipes the cluster; rebuild the image afterward.

## Evaluator path without this workstation

Clone the repo on a Linux VM or a PC with working Docker:

```bash
docker compose up --build -d
docker compose --profile seed run --rm seed
# or Kind path in kubernetes/README.md
```

## Scoring note

Per `SCORING.md`, Kubernetes (15) and Rancher (5) prefer a working demonstration. This file is the **partial-credit investigation** of why the live demo could not be finished here: runtime, not application YAML.
