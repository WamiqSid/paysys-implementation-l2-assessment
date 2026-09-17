# Kubernetes findings (starter manifest)

Source file: `starter/kubernetes/broken-api.yaml`  
Annotated copy: `kubernetes/broken-api.annotated.yaml`  
Replacement: `kubernetes/api.yaml` plus namespace, ConfigMap, Secret, Postgres StatefulSet.

The file was **not** silently replaced. Each defect below was identified and mapped to INCIDENT-002.

## Defects

1. **Placeholder image** `YOUR_IMAGE_HERE`  
   `kubectl describe pod` → `ErrImagePull`. No container ever runs.

2. **Readiness probe port 8081 vs `containerPort: 8080`**  
   kubelet HTTP GET never hits the process. The pod stays Unready. A Service with `publishNotReadyAddresses: false` (default) will not send traffic.

3. **Liveness probe on 8080 /health**  
   Port happens to match, but `/health` includes the database. A DB timeout restarts the API. Corrected design: liveness = `/live` (process only), readiness = `/health` (process + DB).

4. **Service selector `app: minipay-backend`**  
   Pods are labelled `app: minipay-api`. Endpoints object is empty. This alone explains “pods started, app unreachable”.

5. **Service `targetPort: 8081`**  
   Even with a fixed selector, kube-proxy would send to the wrong port.

6. **Namespace `minipay` is referenced but never created**  
   `kubectl apply -f starter/kubernetes/broken-api.yaml` fails with `namespaces "minipay" not found` on a clean cluster.

7. **Missing production controls** (not in the starter file at all)  
   No resource requests/limits, ConfigMap, Secret, PVC, rolling-update strategy, or named ports. The corrected overlay adds them.

## Fix mapping

| Starter | Corrected |
|---|---|
| `image: YOUR_IMAGE_HERE` | `minipay-api:1.0.0` with `imagePullPolicy: IfNotPresent` (Kind load) |
| readiness port 8081 | named port `http` → 8080, path `/health` |
| liveness `/health` | `/live` |
| selector `minipay-backend` | `app: minipay-api` |
| targetPort 8081 | `targetPort: http` |
| implicit namespace | `kubernetes/namespace.yaml` |
| no DB | `kubernetes/postgres.yaml` StatefulSet + 5Gi PVC |

## Operational checks after apply

```bash
kubectl -n minipay get pods -o wide
kubectl -n minipay get svc,endpoints
kubectl -n minipay logs deploy/minipay-api --tail=50
kubectl -n minipay rollout restart deploy/minipay-api
kubectl -n minipay scale deploy/minipay-api --replicas=3
```
