#!/usr/bin/env bash
# Repeatable MiniPay health check for Linux hosts / containers.
set -euo pipefail

API_URL="${MINIPAY_API_URL:-http://127.0.0.1:8080}"
echo "=== MiniPay Linux health check ==="
echo "time: $(date -Is)"
echo
echo "--- os/kernel ---"
uname -a
[ -f /etc/os-release ] && cat /etc/os-release | head -n 5
echo
echo "--- cpu/memory/disk ---"
(command -v nproc >/dev/null && echo "nproc=$(nproc)") || true
(command -v free >/dev/null && free -h) || true
df -h | head
echo
echo "--- top memory processes ---"
ps -eo pid,user,pmem,rss,comm --sort=-rss 2>/dev/null | head -n 6 || true
echo
echo "--- listening ports ---"
(ss -lptn 2>/dev/null || netstat -lptn 2>/dev/null || true) | head
echo
echo "--- dns ---"
getent hosts example.com || true
echo
echo "--- application health ---"
curl -fsS "${API_URL}/live"
echo
curl -fsS "${API_URL}/health"
echo
echo "OK"
