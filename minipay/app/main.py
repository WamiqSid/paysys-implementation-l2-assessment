import logging
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import Session

from . import services
from .auth import require_api_key
from .config import Settings, get_settings
from .database import Base, engine, get_db
from .schemas import (
    CustomerCreate,
    CustomerOut,
    PaymentCreate,
    PaymentOut,
    SearchResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("minipay")

app = FastAPI(title="MiniPay", version="1.0.0")
STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def on_startup() -> None:
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level.upper())
    Base.metadata.create_all(bind=engine)
    log.info("minipay started database=%s buggy_search=%s", settings.database_url.split("://")[0], settings.buggy_search)


@app.exception_handler(MultipleResultsFound)
async def duplicate_search_handler(request: Request, exc: MultipleResultsFound):
    log.exception("transaction search returned multiple rows path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "DUPLICATE_REF_LOOKUP"},
    )


@app.get("/live")
def live():
    return {"status": "ok", "service": "minipay-api"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        services.db_ping(db)
    except Exception:
        log.exception("database health check failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable")
    return {"status": "ok", "service": "minipay-api", "database": "up", "time": datetime.utcnow().isoformat()}


@app.post("/api/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    try:
        row = services.create_customer(db, payload.customer_ref, payload.name)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="customer_ref already exists")
    return row


@app.get("/api/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    row = services.get_customer(db, customer_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")
    return row


@app.get("/api/customers/{customer_id}/payments", response_model=list[PaymentOut])
def customer_payments(customer_id: int, db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    try:
        return services.list_customer_payments(db, customer_id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")


@app.post("/api/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        row, replay = services.create_payment(
            db,
            customer_id=payload.customer_id,
            amount=payload.amount,
            transaction_ref=payload.transaction_ref,
            idempotency_key=idempotency_key,
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer not found")
    except ValueError as exc:
        if str(exc) == "idempotency_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key or transaction_ref already used with a different payload",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if replay:
        # Same payload replayed — return the original resource.
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=PaymentOut.model_validate(row).model_dump(mode="json"),
        )
    return row


@app.get("/api/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    row = services.get_payment(db, payment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return row


@app.get("/api/search", response_model=SearchResponse)
def search_payments(
    q: str = Query(..., min_length=1, description="transaction_ref"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: str = Depends(require_api_key),
):
    try:
        rows = services.search_by_ref(db, q, buggy=settings.buggy_search)
    except MultipleResultsFound:
        raise
    return SearchResponse(
        query=q,
        count=len(rows),
        duplicate_ref=len(rows) > 1,
        items=[PaymentOut.model_validate(r) for r in rows],
    )


@app.get("/api/ops/stuck", response_model=list[PaymentOut])
def ops_stuck(
    minutes: int = Query(15, ge=1, le=1440),
    db: Session = Depends(get_db),
    _: str = Depends(require_api_key),
):
    return services.list_stuck(db, minutes=minutes)


@app.get("/api/ops/failed", response_model=list[PaymentOut])
def ops_failed(db: Session = Depends(get_db), _: str = Depends(require_api_key)):
    return services.list_failed(db)


@app.get("/api/ops/health")
def ops_health(db: Session = Depends(get_db), _: str = Depends(require_api_key), settings: Settings = Depends(get_settings)):
    services.db_ping(db)
    return {
        "api": "up",
        "database": "up",
        "buggy_search": settings.buggy_search,
        "time": datetime.utcnow().isoformat(),
    }


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
