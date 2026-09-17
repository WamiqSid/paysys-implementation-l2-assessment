# Python L2 support utility

```bash
pip install -r python/requirements.txt
export MINIPAY_API_URL=http://127.0.0.1:8080
export MINIPAY_API_KEY=minipay-dev-key

python python/support_tool.py --transaction TXN00000001
python python/support_tool.py --transaction TXN00004999 --json
python python/support_tool.py --stuck
python python/support_tool.py --failed
python python/support_tool.py --health
python -m pytest python/tests -q
```

Exit codes: `0` clean, `1` not found, `2` anomalies, `3` dependency/API failure, `4` usage error.

Configuration is environment-based (`MINIPAY_API_URL`, `MINIPAY_API_KEY`, `MINIPAY_TIMEOUT_SECONDS`). Credentials are never hard-coded in source.
