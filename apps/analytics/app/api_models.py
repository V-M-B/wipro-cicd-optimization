"""Request bodies for the HTTP API (wrapping the generated shared-schema models)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.generated.schemas import Customer, Order, Product

GranularityParam = Literal["day", "week", "month"]


class OrdersRequest(BaseModel):
    orders: list[Order]


class RevenueRequest(BaseModel):
    orders: list[Order]
    customers: list[Customer] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)
    granularity: GranularityParam = "month"
    fill_gaps: bool = False


class TopProductsRequest(BaseModel):
    orders: list[Order]
    products: list[Product] = Field(default_factory=list)
    n: int = Field(default=10, ge=0, le=1000)
    by: Literal["revenue", "units", "orders"] = "revenue"


class AbcRequest(BaseModel):
    orders: list[Order]
    products: list[Product] = Field(default_factory=list)
    a: float = 0.8
    b: float = 0.95


class AffinityRequest(BaseModel):
    orders: list[Order]
    min_support: float = 0.01
    min_confidence: float = 0.0
    limit: int = Field(default=50, ge=0, le=10_000)


class AsOfRequest(BaseModel):
    orders: list[Order]
    as_of: date


class RetentionRequest(BaseModel):
    orders: list[Order]
    mode: Literal["active", "rolling"] = "active"
    end: date | None = None


class ChurnRequest(BaseModel):
    orders: list[Order]
    as_of: date
    threshold_days: int = Field(default=90, ge=0)


class ClvRequest(BaseModel):
    orders: list[Order]
    as_of: date
    gross_margin: float = 0.3
    retention: float | None = None
    discount_rate: float = 0.01


class SmoothRequest(BaseModel):
    values: list[float]
    method: Literal["sma", "wma", "ema", "holt"] = "sma"
    window: int = 7
    alpha: float = 0.3
    beta: float = 0.1
    horizon: int = 0


class AnomalyRequest(BaseModel):
    values: list[float]
    method: Literal["zscore", "iqr", "rolling"] = "zscore"
    threshold: float = 3.0
    k: float = 1.5
    window: int = 7


class FunnelRequest(BaseModel):
    orders: list[Order]
    customers: list[Customer] = Field(default_factory=list)
    by_region: bool = False


class CsvRequest(BaseModel):
    content: str
