"""Load synthetic MiniPay data (same distribution as database/generate_data.py).

Usage:
  python seed.py
  python seed.py --customers 1000 --transactions 50000
  python seed.py --reset
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Allow `python seed.py` from the minipay directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.models import Callback, Customer, Transaction

random.seed(42)
BASE = datetime(2026, 9, 1, 0, 0, 0)


def build_rows(n_customers: int, n_tx: int):
    customers = [
        {"id": i, "customer_ref": f"CUST{i:06d}", "name": f"Customer {i}", "created_at": BASE}
        for i in range(1, n_customers + 1)
    ]
    transactions = []
    callbacks = []
    cb_id = 1
    for i in range(1, n_tx + 1):
        ref_num = i if i % 5000 else i - 1
        created = BASE + timedelta(seconds=random.randint(0, 10 * 86400))
        r = random.random()
        if r < 0.82:
            status = "SUCCESS"
            completed = created + timedelta(seconds=random.randint(1, 90))
            failure = None
        elif r < 0.95:
            status = "FAILED"
            completed = created + timedelta(seconds=random.randint(1, 120))
            failure = "UPSTREAM_ERROR"
        else:
            status = "PROCESSING"
            completed = None
            failure = None
        transactions.append(
            {
                "id": i,
                "transaction_ref": f"TXN{ref_num:08d}",
                "customer_id": random.randint(1, n_customers),
                "amount": Decimal(str(round(random.uniform(100, 100000), 2))),
                "status": status,
                "created_at": created,
                "completed_at": completed,
                "failure_code": failure,
            }
        )
        if status in ("SUCCESS", "FAILED"):
            cb_success = status == "SUCCESS" and random.random() < 0.94
            attempts = 1 if cb_success else random.randint(1, 3)
            for a in range(1, attempts + 1):
                ok = cb_success and a == attempts
                callbacks.append(
                    {
                        "id": cb_id,
                        "transaction_id": i,
                        "attempt_no": a,
                        "http_status": 200 if ok else random.choice([500, 502, 503]),
                        "callback_status": "SUCCESS" if ok else "FAILED",
                        "attempted_at": (completed or created) + timedelta(seconds=a * 5),
                    }
                )
                cb_id += 1
    return customers, transactions, callbacks


def reset_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed(n_customers: int, n_tx: int) -> None:
    customers, transactions, callbacks = build_rows(n_customers, n_tx)
    db = SessionLocal()
    try:
        if db.query(Transaction).count() > 0:
            print("data already present; use --reset to reload")
            return
        print(f"inserting {len(customers)} customers, {len(transactions)} transactions, {len(callbacks)} callbacks")
        db.bulk_insert_mappings(Customer, customers)
        db.bulk_insert_mappings(Transaction, transactions)
        db.bulk_insert_mappings(Callback, callbacks)
        db.commit()
        dialect = engine.dialect.name
        if dialect == "postgresql":
            db.execute(text("SELECT setval('customers_id_seq', (SELECT MAX(id) FROM customers))"))
            db.execute(text("SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions))"))
            db.execute(text("SELECT setval('callbacks_id_seq', (SELECT MAX(id) FROM callbacks))"))
            db.commit()
        elif dialect == "sqlite":
            has_seq = db.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            ).first()
            if has_seq:
                for table in ("customers", "transactions", "callbacks"):
                    db.execute(
                        text(
                            "INSERT OR REPLACE INTO sqlite_sequence(name, seq) "
                            f"SELECT '{table}', COALESCE(MAX(id), 0) FROM {table}"
                        )
                    )
                db.commit()
        print("seed complete")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=int, default=int(os.getenv("SEED_CUSTOMERS", "1000")))
    parser.add_argument("--transactions", type=int, default=int(os.getenv("SEED_TRANSACTIONS", "50000")))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset:
        reset_schema()
    else:
        Base.metadata.create_all(bind=engine)
    seed(args.customers, args.transactions)


if __name__ == "__main__":
    main()
