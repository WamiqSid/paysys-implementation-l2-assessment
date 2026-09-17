from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    customer_ref: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_ref: str
    name: str
    created_at: datetime


class PaymentCreate(BaseModel):
    customer_id: int
    amount: Decimal = Field(gt=0)
    transaction_ref: str | None = Field(default=None, max_length=50)


class CallbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_no: int
    http_status: int | None
    callback_status: str
    attempted_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_ref: str
    customer_id: int
    amount: Decimal
    status: str
    created_at: datetime
    completed_at: datetime | None
    failure_code: str | None
    callbacks: list[CallbackOut] = []


class SearchResponse(BaseModel):
    query: str
    count: int
    duplicate_ref: bool
    items: list[PaymentOut]


class ErrorBody(BaseModel):
    detail: str
    code: str | None = None
