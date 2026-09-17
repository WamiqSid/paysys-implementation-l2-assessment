import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "api-tests.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["API_KEY"] = "minipay-dev-key"
os.environ["BUGGY_SEARCH"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Callback, Customer, Transaction  # noqa: E402

AUTH = {"X-API-Key": "minipay-dev-key"}


@pytest.fixture
def client():
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.utcnow()
    customer = Customer(customer_ref="CUST-TEST-1", name="Test Customer", created_at=now)
    db.add(customer)
    db.flush()
    db.add_all(
        [
            Transaction(
                transaction_ref="TXN-OK",
                customer_id=customer.id,
                amount=Decimal("25.50"),
                status="SUCCESS",
                created_at=now - timedelta(minutes=5),
                completed_at=now - timedelta(minutes=4),
            ),
            Transaction(
                transaction_ref="TXN-DUP",
                customer_id=customer.id,
                amount=Decimal("10.00"),
                status="SUCCESS",
                created_at=now - timedelta(minutes=30),
                completed_at=now - timedelta(minutes=29),
            ),
            Transaction(
                transaction_ref="TXN-DUP",
                customer_id=customer.id,
                amount=Decimal("11.00"),
                status="FAILED",
                created_at=now - timedelta(minutes=20),
                completed_at=now - timedelta(minutes=19),
                failure_code="UPSTREAM_ERROR",
            ),
            Transaction(
                transaction_ref="TXN-STUCK",
                customer_id=customer.id,
                amount=Decimal("40.00"),
                status="PROCESSING",
                created_at=now - timedelta(minutes=45),
            ),
        ]
    )
    db.flush()
    ok = db.query(Transaction).filter(Transaction.transaction_ref == "TXN-OK").one()
    db.add(Callback(transaction_id=ok.id, attempt_no=1, http_status=200, callback_status="SUCCESS", attempted_at=now))
    db.commit()
    customer_id = customer.id
    db.close()
    with TestClient(app) as test_client:
        test_client.customer_id = customer_id
        yield test_client
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
