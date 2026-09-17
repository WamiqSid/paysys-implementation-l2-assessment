from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _age_minutes(created_at: str | datetime | None, now: datetime | None = None) -> float | None:
    created = _parse_dt(created_at)
    if created is None:
        return None
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if created.tzinfo:
        created = created.replace(tzinfo=None)
    return max(0.0, (current - created).total_seconds() / 60.0)


def analyze_transaction(tx: dict[str, Any], duplicate_count: int = 1, now: datetime | None = None) -> dict[str, Any]:
    """Return findings and a recommended next action. Pure function, unit-tested."""
    findings: list[dict[str, str]] = []
    callbacks = tx.get("callbacks") or []
    status = (tx.get("status") or "").upper()
    age = _age_minutes(tx.get("created_at"), now=now)
    success_callbacks = [c for c in callbacks if str(c.get("callback_status")).upper() == "SUCCESS"]
    failed_callbacks = [c for c in callbacks if str(c.get("callback_status")).upper() == "FAILED"]

    if duplicate_count > 1:
        findings.append(
            {
                "severity": "critical",
                "code": "DUPLICATE_TRANSACTION_REF",
                "message": f"transaction_ref appears on {duplicate_count} rows",
                "next_action": "Stop treating the ref as a unique key. Identify the intended row by id, then clean duplicates and add a unique constraint after backfill.",
            }
        )

    if status == "PROCESSING" and age is not None and age > 15:
        findings.append(
            {
                "severity": "critical",
                "code": "STUCK_PROCESSING",
                "message": f"Still PROCESSING after {age:.1f} minutes",
                "next_action": "Check upstream processor logs for this ref, confirm no callback was lost, then replay or fail the payment with an operator note.",
            }
        )
    elif status == "PROCESSING":
        findings.append(
            {
                "severity": "info",
                "code": "IN_FLIGHT",
                "message": "Payment is still within the processing window",
                "next_action": "Wait for completion and re-query. If it exceeds 15 minutes, escalate as stuck.",
            }
        )

    if status == "FAILED":
        code = tx.get("failure_code") or "UNKNOWN"
        findings.append(
            {
                "severity": "warning",
                "code": "PAYMENT_FAILED",
                "message": f"Payment failed ({code}) after {len(callbacks)} callback attempt(s)",
                "next_action": "Confirm the failure with the processor. If it is transient (UPSTREAM_ERROR), retry from a controlled tool; do not insert a second live payment for the same customer instruction.",
            }
        )

    if status == "SUCCESS" and not success_callbacks:
        findings.append(
            {
                "severity": "critical",
                "code": "RECONCILIATION_GAP",
                "message": "Transaction is SUCCESS but no SUCCESS callback exists",
                "next_action": "Treat as a notification gap. Re-send the merchant callback once, then watch reconciliation counts.",
            }
        )

    if failed_callbacks and not success_callbacks and status == "SUCCESS":
        findings.append(
            {
                "severity": "warning",
                "code": "CALLBACK_RETRIES_FAILED",
                "message": f"{len(failed_callbacks)} failed callback attempt(s) on a successful payment",
                "next_action": "Inspect callback URL/auth and retry the latest failed attempt.",
            }
        )

    severity_rank = {"critical": 3, "warning": 2, "info": 1}
    findings.sort(key=lambda f: severity_rank.get(f["severity"], 0), reverse=True)
    top = findings[0] if findings else {
        "severity": "info",
        "code": "HEALTHY",
        "message": "No anomalies detected",
        "next_action": "No action required. Share the transaction timeline with the requester.",
    }
    return {
        "transaction_ref": tx.get("transaction_ref"),
        "status": status,
        "amount": tx.get("amount"),
        "customer_id": tx.get("customer_id"),
        "created_at": tx.get("created_at"),
        "completed_at": tx.get("completed_at"),
        "failure_code": tx.get("failure_code"),
        "callback_attempts": len(callbacks),
        "duplicate_count": duplicate_count,
        "age_minutes": None if age is None else round(age, 2),
        "findings": findings,
        "recommended_action": top["next_action"],
        "highest_severity": top["severity"],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "MiniPay L2 diagnostic",
        "=====================",
        f"Reference : {report.get('transaction_ref')}",
        f"Status    : {report.get('status')}",
        f"Amount    : {report.get('amount')}",
        f"Customer  : {report.get('customer_id')}",
        f"Created   : {report.get('created_at')}",
        f"Completed : {report.get('completed_at')}",
        f"Failure   : {report.get('failure_code')}",
        f"Callbacks : {report.get('callback_attempts')}",
        f"Age (min) : {report.get('age_minutes')}",
        "",
        "Findings:",
    ]
    if not report.get("findings"):
        lines.append("  none")
    for item in report.get("findings") or []:
        lines.append(f"  [{item['severity'].upper()}] {item['code']}: {item['message']}")
    lines.extend(["", "Recommended action:", f"  {report.get('recommended_action')}"])
    return "\n".join(lines)
