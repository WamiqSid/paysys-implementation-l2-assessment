#!/usr/bin/env python3
"""MiniPay L2 support CLI.

Examples:
  python support_tool.py --transaction TXN00004999
  python support_tool.py --transaction TXN00004999 --json
  python support_tool.py --stuck
  python support_tool.py --health
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipay_support.analyzer import analyze_transaction, render_text
from minipay_support.client import MiniPayClient, SupportClientError
from minipay_support.config import SupportSettings

log = logging.getLogger("minipay.support")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MiniPay L2 diagnostic tool")
    parser.add_argument("--transaction", help="transaction_ref to inspect")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--stuck", action="store_true", help="summarise PROCESSING payments older than 15 minutes")
    parser.add_argument("--failed", action="store_true", help="summarise recent FAILED payments")
    parser.add_argument("--health", action="store_true", help="check API and database dependencies")
    parser.add_argument("--verbose", action="store_true")
    return parser


def emit(data: dict, as_json: bool, text: str | None = None) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(text if text is not None else json.dumps(data, indent=2, default=str))


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    if not any([args.transaction, args.stuck, args.failed, args.health]):
        parser.print_help()
        return 4

    settings = SupportSettings()
    client = MiniPayClient(settings.minipay_api_url, settings.minipay_api_key, settings.minipay_timeout_seconds)

    try:
        if args.health:
            payload = client.health()
            emit(payload, args.json, text=f"API {payload['live']}\nOPS {payload['ops']}")
            if payload.get("ops", {}).get("database") == "up" or payload.get("live", {}).get("status") == "ok":
                return 0
            return 3

        if args.stuck:
            rows = client.stuck()
            payload = {"count": len(rows), "items": [analyze_transaction(r) for r in rows]}
            text = f"Stuck PROCESSING payments: {len(rows)}\n" + "\n".join(
                f"- {r.get('transaction_ref')} id={r.get('id')} created={r.get('created_at')}" for r in rows[:20]
            )
            emit(payload, args.json, text=text)
            return 2 if rows else 0

        if args.failed:
            rows = client.failed()
            payload = {"count": len(rows), "items": [analyze_transaction(r) for r in rows]}
            text = f"Recent FAILED payments: {len(rows)}\n" + "\n".join(
                f"- {r.get('transaction_ref')} {r.get('failure_code')}" for r in rows[:20]
            )
            emit(payload, args.json, text=text)
            return 2 if rows else 0

        search = client.search(args.transaction)
        items = search.get("items") or []
        if not items:
            emit({"transaction_ref": args.transaction, "count": 0}, args.json, text="Transaction not found")
            return 1
        report = analyze_transaction(items[0], duplicate_count=max(search.get("count") or len(items), 1))
        report["matches"] = items
        emit(report, args.json, text=render_text(report))
        if report.get("highest_severity") in {"critical", "warning"}:
            return 2
        return 0
    except SupportClientError as exc:
        log.error("%s", exc)
        emit({"error": str(exc)}, args.json, text=str(exc))
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(run())
