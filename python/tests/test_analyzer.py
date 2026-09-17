from datetime import datetime, timedelta

from minipay_support.analyzer import analyze_transaction, render_text


def test_stuck_processing_is_critical():
    created = datetime(2026, 9, 14, 10, 0, 0)
    now = created + timedelta(minutes=20)
    report = analyze_transaction(
        {
            "transaction_ref": "TXN1",
            "status": "PROCESSING",
            "amount": "10.00",
            "customer_id": 1,
            "created_at": created.isoformat(),
            "completed_at": None,
            "callbacks": [],
        },
        now=now,
    )
    assert report["highest_severity"] == "critical"
    assert report["findings"][0]["code"] == "STUCK_PROCESSING"


def test_success_without_callback_is_recon_gap():
    report = analyze_transaction(
        {
            "transaction_ref": "TXN2",
            "status": "SUCCESS",
            "created_at": "2026-09-14T10:00:00",
            "completed_at": "2026-09-14T10:00:08",
            "callbacks": [{"callback_status": "FAILED", "attempt_no": 1}],
        }
    )
    codes = {f["code"] for f in report["findings"]}
    assert "RECONCILIATION_GAP" in codes


def test_duplicate_ref_is_critical():
    report = analyze_transaction(
        {
            "transaction_ref": "TXN00004999",
            "status": "SUCCESS",
            "created_at": "2026-09-14T10:00:00",
            "completed_at": "2026-09-14T10:00:05",
            "callbacks": [{"callback_status": "SUCCESS"}],
        },
        duplicate_count=2,
    )
    assert report["findings"][0]["code"] == "DUPLICATE_TRANSACTION_REF"
    assert "duplicate" in render_text(report).lower()


def test_healthy_success():
    report = analyze_transaction(
        {
            "transaction_ref": "TXN3",
            "status": "SUCCESS",
            "created_at": "2026-09-14T10:00:00",
            "completed_at": "2026-09-14T10:00:03",
            "callbacks": [{"callback_status": "SUCCESS", "attempt_no": 1}],
        }
    )
    assert report["highest_severity"] == "info"
    assert report["findings"] == []
