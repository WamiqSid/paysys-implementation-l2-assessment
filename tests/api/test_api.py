import time

AUTH = {"X-API-Key": "minipay-dev-key"}


def test_health_ok(client):
    start = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert elapsed < 0.5


def test_live_ok(client):
    assert client.get("/live").status_code == 200


def test_missing_api_key(client):
    response = client.get("/api/payments/1")
    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_invalid_api_key(client):
    response = client.get("/api/payments/1", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_create_customer_and_payment_success(client):
    created = client.post(
        "/api/customers",
        headers=AUTH,
        json={"customer_ref": "CUST-NEW", "name": "New Co"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]
    payment = client.post(
        "/api/payments",
        headers=AUTH,
        json={"customer_id": customer_id, "amount": "99.99", "transaction_ref": "TXN-NEW-1"},
    )
    assert payment.status_code == 201
    body = payment.json()
    assert body["status"] == "SUCCESS"
    assert body["transaction_ref"] == "TXN-NEW-1"
    assert "id" in body and "created_at" in body
    fetched = client.get(f"/api/payments/{body['id']}", headers=AUTH)
    assert fetched.status_code == 200
    assert float(fetched.json()["amount"]) == 99.99


def test_invalid_and_missing_fields(client):
    missing = client.post("/api/payments", headers=AUTH, json={})
    assert missing.status_code == 422
    invalid = client.post(
        "/api/payments",
        headers=AUTH,
        json={"customer_id": client.customer_id, "amount": "-5"},
    )
    assert invalid.status_code == 422


def test_unknown_resources(client):
    assert client.get("/api/payments/99999", headers=AUTH).status_code == 404
    assert client.get("/api/customers/99999", headers=AUTH).status_code == 404
    empty = client.get("/api/search", params={"q": "DOES-NOT-EXIST"}, headers=AUTH)
    assert empty.status_code == 200
    assert empty.json()["count"] == 0


def test_customer_payments(client):
    response = client.get(f"/api/customers/{client.customer_id}/payments", headers=AUTH)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_idempotent_payment_replay(client):
    payload = {"customer_id": client.customer_id, "amount": "15.00", "transaction_ref": "TXN-IDEMP"}
    first = client.post("/api/payments", headers={**AUTH, "Idempotency-Key": "pay-1"}, json=payload)
    second = client.post("/api/payments", headers={**AUTH, "Idempotency-Key": "pay-1"}, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_idempotency_conflict(client):
    headers = {**AUTH, "Idempotency-Key": "pay-conflict"}
    first = client.post("/api/payments", headers=headers, json={"customer_id": client.customer_id, "amount": "15.00"})
    conflict = client.post("/api/payments", headers=headers, json={"customer_id": client.customer_id, "amount": "20.00"})
    assert first.status_code == 201
    assert conflict.status_code == 409


def test_failed_sentinel_amount(client):
    response = client.post("/api/payments", headers=AUTH, json={"customer_id": client.customer_id, "amount": "13.13"})
    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"
    assert response.json()["failure_code"] == "AMOUNT_REJECTED"


def test_duplicate_search_is_safe_by_default(client):
    response = client.get("/api/search", params={"q": "TXN-DUP"}, headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["duplicate_ref"] is True


def test_buggy_search_returns_500_on_duplicates(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("BUGGY_SEARCH", "true")
    get_settings.cache_clear()
    try:
        response = client.get("/api/search", params={"q": "TXN-DUP"}, headers=AUTH)
        assert response.status_code == 500
        assert response.json()["code"] == "DUPLICATE_REF_LOOKUP"
    finally:
        monkeypatch.setenv("BUGGY_SEARCH", "false")
        get_settings.cache_clear()


def test_stuck_ops_endpoint(client):
    response = client.get("/api/ops/stuck", headers=AUTH)
    assert response.status_code == 200
    refs = {row["transaction_ref"] for row in response.json()}
    assert "TXN-STUCK" in refs
