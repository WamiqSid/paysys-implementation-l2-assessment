# Linux evidence

Capture host: Ubuntu WSL2 on the assessment Windows PC (`wsl -d Ubuntu`), 2026-09-17.

The MiniPay process itself was developed on Windows Python. The same commands apply inside `python:3.12-slim` or any Linux VM. Repeatable script: `evidence/healthcheck.sh` (needs a running API for the `/health` section).

## OS / kernel

```text
Linux DESKTOP-1ASMC10 6.18.33.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun 18 21:54:43 UTC 2026 x86_64 GNU/Linux

PRETTY_NAME="Ubuntu 26.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="26.04"
VERSION="26.04.1 LTS (Resolute Raccoon)"
```

## CPU, memory, disk

```text
nproc=4

               total        used        free      shared  buff/cache   available
Mem:           5.6Gi       1.3Gi       2.1Gi       6.9Mi       2.4Gi       4.3Gi
Swap:          2.0Gi          0B       2.0Gi

Filesystem      Size  Used Avail Use% Mounted on
/dev/sdd       1007G  1.5G  955G   1% /
drivers         120G  111G  8.7G  93% /usr/lib/wsl/drivers
```

The **Windows volume at 93%** is operationally important: it is a likely contributor to Rancher Desktop / image-pull failures (see `evidence/environment-blockers.md`).

## Top memory processes (WSL Ubuntu, idle)

```text
    PID USER     %MEM   RSS COMMAND
    251 root      0.5 32568 unattended-upgr
    161 root      0.5 29784 networkd-dispat
     61 root      0.2 16988 systemd-journal
      1 root      0.2 15452 systemd
     99 systemd+  0.2 14504 systemd-resolve
```

Disk by directory (home):

```text
112M	/home
112M	/home/wamiq
```

## Listening ports / DNS / connectivity

```text
ss -lptn (excerpt):
LISTEN 127.0.0.1:6443
LISTEN 127.0.0.1:6444
LISTEN *:80
LISTEN *:443
LISTEN 127.0.0.53:53

getent hosts example.com
172.66.147.243  example.com

curl -fsS -o /dev/null -w '%{http_code}\n' https://example.com
200
```

Note: `6443` listening **inside WSL** while Windows `kubectl` reported `127.0.0.1:6443` connection refused is a host-vs-VM bind issue during the Rancher Desktop crash (k3s not published to Windows). Do not treat that as an application bug.

## Application / container logs

Not captured from MiniPay pods: the cluster VM did not stay Ready. Intended commands:

```bash
kubectl -n minipay logs deploy/minipay-api --tail=100
docker compose logs api --tail=100
```

Local (no Docker) log path: uvicorn stdout on Windows after `SETUP.md` section 1.

## Repeatable health-check script

```bash
bash evidence/healthcheck.sh
# optional: MINIPAY_API_URL=http://127.0.0.1:8080 bash evidence/healthcheck.sh
```

Exits non-zero if `curl` to `/live` or `/health` fails.

## How I would investigate typical L2 issues

**High CPU**  
`top` / `pidstat 1`, identify the PID, `kubectl top pod`, then app logs and last deploy. Check for a hot loop, missing index (INCIDENT-003), or traffic spike.

**Low disk space**  
`df -h` then `du -x / | sort -n`. This workstation already showed the Windows volume at 93%. Rotate logs, prune images (`docker system prune` only when the daemon is up), expand the PVC. Database PVC is 5Gi; alert before 80%.

**Unreachable API**  
`curl /live` then `/health`. Live OK + health fail → database. Neither works → endpoints, selectors, probes (INCIDENT-002) **or** the node/engine is down (`environment-blockers.md`). Confirm DNS (`getent hosts minipay-api`).

**Repeatedly terminating process**  
`kubectl describe pod` last state / exit code, `logs --previous`. Distinguish OOMKilled from probe mismatch. On this PC, `/sbin/init exited with status 1` in Rancher logs was the **VM**, not the MiniPay container.
