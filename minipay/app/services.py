from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Select, select, text
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, selectinload

from .models import Callback, Customer, Transaction

FAIL_SENTINEL = Decimal("13.13")


def get_customer(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def create_customer(db: Session, customer_ref: str, name: str) -> Customer:
    existing = db.scalar(select(Customer).where(Customer.customer_ref == customer_ref))
    if existing:
        raise ValueError("customer_ref_conflict")
    row = Customer(customer_ref=customer_ref, name=name, created_at=datetime.utcnow())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _load_payment(db: Session, tx_id: int) -> Transaction | None:
    return db.scalar(
        select(Transaction).options(selectinload(Transaction.callbacks)).where(Transaction.id == tx_id)
    )


def find_by_idempotency(db: Session, key: str) -> Transaction | None:
    return db.scalar(
        select(Transaction)
        .options(selectinload(Transaction.callbacks))
        .where(Transaction.transaction_ref == key)
        .order_by(Transaction.id.asc())
        .limit(1)
    )


def create_payment(
    db: Session,
    customer_id: int,
    amount: Decimal,
    transaction_ref: str | None,
    idempotency_key: str | None,
) -> tuple[Transaction, bool]:
    customer = get_customer(db, customer_id)
    if customer is None:
        raise LookupError("customer_not_found")

    lookup_keys = [k for k in (idempotency_key, transaction_ref) if k]
    seen: set[str] = set()
    for key in lookup_keys:
        if key in seen:
            continue
        seen.add(key)
        existing = find_by_idempotency(db, key)
        if existing:
            if existing.customer_id == customer_id and existing.amount == amount:
                return existing, True
            raise ValueError("idempotency_conflict")

    ref = transaction_ref or idempotency_key or f"TXN-API-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    tx = Transaction(
        transaction_ref=ref,
        customer_id=customer_id,
        amount=amount,
        status="PROCESSING",
        created_at=now,
        completed_at=None,
        failure_code=None,
    )
    db.add(tx)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("constraint_violation") from exc

    _settle(db, tx, now)
    db.commit()
    db.refresh(tx)
    loaded = _load_payment(db, tx.id)
    assert loaded is not None
    return loaded, False


def _settle(db: Session, tx: Transaction, started: datetime) -> None:
    if tx.amount == FAIL_SENTINEL:
        tx.status = "FAILED"
        tx.failure_code = "AMOUNT_REJECTED"
        tx.completed_at = datetime.utcnow()
        db.add(
            Callback(
                transaction_id=tx.id,
                attempt_no=1,
                http_status=500,
                callback_status="FAILED",
                attempted_at=tx.completed_at,
            )
        )
        return

    tx.status = "SUCCESS"
    tx.failure_code = None
    tx.completed_at = datetime.utcnow()
    db.add(
        Callback(
            transaction_id=tx.id,
            attempt_no=1,
            http_status=200,
            callback_status="SUCCESS",
            attempted_at=tx.completed_at,
        )
    )


def get_payment(db: Session, payment_id: int) -> Transaction | None:
    return _load_payment(db, payment_id)


def list_customer_payments(db: Session, customer_id: int) -> list[Transaction]:
    if get_customer(db, customer_id) is None:
        raise LookupError("customer_not_found")
    stmt: Select[tuple[Transaction]] = (
        select(Transaction)
        .options(selectinload(Transaction.callbacks))
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.id.desc())
    )
    return list(db.scalars(stmt).unique())


def search_by_ref(db: Session, transaction_ref: str, buggy: bool) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.callbacks))
        .where(Transaction.transaction_ref == transaction_ref)
        .order_by(Transaction.id.asc())
    )
    if buggy:
        # INCIDENT-001 defect: assumes transaction_ref is unique.
        try:
            return [db.scalars(stmt).unique().one()]
        except NoResultFound:
            return []
    return list(db.scalars(stmt).unique())


def list_stuck(db: Session, minutes: int = 15, limit: int = 50) -> list[Transaction]:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.callbacks))
        .where(Transaction.status == "PROCESSING", Transaction.created_at < cutoff)
        .order_by(Transaction.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique())


def list_failed(db: Session, limit: int = 50) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.callbacks))
        .where(Transaction.status == "FAILED")
        .order_by(Transaction.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique())


def db_ping(db: Session) -> bool:
    db.execute(text("SELECT 1"))
    return True
