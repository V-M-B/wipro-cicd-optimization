"""FastAPI application exposing the analytics metrics.

Metric endpoints are POSTs that accept lists of the generated shared-schema
models. Invalid metric parameters (``ValueError``) are returned as HTTP 422.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Annotated

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api_models import (
    AbcRequest,
    AffinityRequest,
    AnomalyRequest,
    AsOfRequest,
    ChurnRequest,
    ClvRequest,
    CsvRequest,
    FunnelRequest,
    OrdersRequest,
    RetentionRequest,
    RevenueRequest,
    SmoothRequest,
    TopProductsRequest,
)
from app.datasets import DatasetConfig, generate_dataset
from app.io import csv_io
from app.metrics import customers as cust
from app.metrics import funnel as fun
from app.metrics import products as prod
from app.metrics import revenue as rev
from app.metrics import timeseries as ts

revenue_router = APIRouter(prefix="/revenue", tags=["revenue"])
products_router = APIRouter(prefix="/products", tags=["products"])
customers_router = APIRouter(prefix="/customers", tags=["customers"])
timeseries_router = APIRouter(prefix="/timeseries", tags=["timeseries"])
funnel_router = APIRouter(prefix="/funnel", tags=["funnel"])
csv_router = APIRouter(prefix="/csv", tags=["csv"])


# --------------------------------------------------------------------------- revenue


@revenue_router.post("/summary")
def revenue_summary(req: RevenueRequest) -> dict[str, object]:
    return rev.revenue_summary(req.orders, req.customers, req.products, req.granularity)


@revenue_router.post("/by-period")
def revenue_by_period(req: RevenueRequest) -> dict[str, float]:
    return rev.revenue_by_period(req.orders, req.granularity, fill_gaps=req.fill_gaps)


@revenue_router.post("/by-region")
def revenue_by_region(req: RevenueRequest) -> dict[str, float]:
    return rev.revenue_by_region(req.orders, req.customers)


@revenue_router.post("/by-category")
def revenue_by_category(req: RevenueRequest) -> dict[str, float]:
    return rev.revenue_by_category(req.orders, req.products)


@revenue_router.post("/aov")
def revenue_aov(req: RevenueRequest) -> dict[str, object]:
    return {
        "average_order_value": rev.average_order_value(req.orders),
        "by_region": rev.aov_by_region(req.orders, req.customers),
    }


@revenue_router.post("/coupons")
def revenue_coupons(req: OrdersRequest) -> dict[str, dict[str, float]]:
    return rev.coupon_usage(req.orders)


# --------------------------------------------------------------------------- products


@products_router.post("/top")
def products_top(req: TopProductsRequest) -> list[dict[str, object]]:
    return [s.as_dict() for s in prod.top_products(req.orders, req.products, req.n, req.by)]


@products_router.post("/abc")
def products_abc(req: AbcRequest) -> dict[str, object]:
    classes = prod.abc_for_products(req.orders, req.products, req.a, req.b)
    values = {sku: s.revenue for sku, s in prod.product_sales(req.orders, req.products).items()}
    return {"classes": classes, "summary": prod.abc_summary(classes, values)}


@products_router.post("/affinity")
def products_affinity(req: AffinityRequest) -> list[dict[str, object]]:
    rules = prod.affinity_rules(req.orders, req.min_support, req.min_confidence)
    return [r.as_dict() for r in rules[: req.limit]]


# --------------------------------------------------------------------------- customers


@customers_router.post("/rfm")
def customers_rfm(req: AsOfRequest) -> dict[str, object]:
    records = cust.rfm_scores(req.orders, req.as_of)
    return {"customers": [r.as_dict() for r in records], "segments": cust.segment_counts(records)}


@customers_router.post("/retention")
def customers_retention(req: RetentionRequest) -> dict[str, object]:
    matrix = cust.cohort_retention(req.orders, req.mode, end=req.end)
    return {**matrix.as_dict(), "average": cust.average_retention_curve(matrix)}


@customers_router.post("/churn")
def customers_churn(req: ChurnRequest) -> dict[str, object]:
    flags = cust.churn_flags(req.orders, req.as_of, req.threshold_days)
    return {"flags": flags, "churn_rate": cust.churn_rate(flags)}


@customers_router.post("/clv")
def customers_clv(req: ClvRequest) -> dict[str, object]:
    values = cust.customer_clv(req.orders, req.as_of, req.gross_margin, req.retention, req.discount_rate)
    return {"clv": values, "total": round(sum(values.values()), 2)}


# --------------------------------------------------------------------------- timeseries


@timeseries_router.post("/smooth")
def timeseries_smooth(req: SmoothRequest) -> dict[str, object]:
    if req.method == "sma":
        return {"values": ts.simple_moving_average(req.values, req.window)}
    if req.method == "wma":
        return {"values": ts.weighted_moving_average(req.values, req.window)}
    if req.method == "ema":
        return {"values": ts.exponential_smoothing(req.values, req.alpha)}
    fitted, forecast = ts.holt_linear(req.values, req.alpha, req.beta, req.horizon)
    return {"values": fitted, "forecast": forecast}


@timeseries_router.post("/anomalies")
def timeseries_anomalies(req: AnomalyRequest) -> dict[str, object]:
    if req.method == "zscore":
        found = ts.zscore_anomalies(req.values, req.threshold)
    elif req.method == "iqr":
        found = ts.iqr_anomalies(req.values, req.k)
    else:
        found = ts.rolling_zscore_anomalies(req.values, req.window, req.threshold)
    return {"anomalies": [a.as_dict() for a in found], "count": len(found)}


@timeseries_router.post("/week-over-week")
def timeseries_wow(req: OrdersRequest) -> list[dict[str, object]]:
    return ts.week_over_week(ts.daily_revenue(req.orders))


# --------------------------------------------------------------------------- funnel


@funnel_router.post("")
def order_funnel(req: FunnelRequest) -> dict[str, object]:
    stages = fun.funnel(req.orders)
    body: dict[str, object] = {
        "stages": [s.as_dict() for s in stages],
        "status_counts": fun.status_counts(req.orders),
        "cancellation_rate": fun.cancellation_rate(req.orders),
        "bottleneck": fun.bottleneck(stages),
    }
    if req.by_region:
        body["by_region"] = {
            region: [s.as_dict() for s in group]
            for region, group in fun.funnel_by_region(req.orders, req.customers).items()
        }
    return body


# --------------------------------------------------------------------------- csv


def _validate_csv(reader: Callable[[str], Sequence[object]], content: str) -> dict[str, object]:
    try:
        records = reader(content)
    except csv_io.CsvValidationError as exc:
        return {"valid": False, "count": 0, "errors": [e.as_dict() for e in exc.errors]}
    return {"valid": True, "count": len(records), "errors": []}


@csv_router.post("/customers/validate")
def csv_customers(req: CsvRequest) -> dict[str, object]:
    return _validate_csv(csv_io.read_customers, req.content)


@csv_router.post("/products/validate")
def csv_products(req: CsvRequest) -> dict[str, object]:
    return _validate_csv(csv_io.read_products, req.content)


@csv_router.post("/orders/validate")
def csv_orders(req: CsvRequest) -> dict[str, object]:
    return _validate_csv(csv_io.read_orders, req.content)


# --------------------------------------------------------------------------- app


def create_app() -> FastAPI:
    application = FastAPI(title="RetailOps analytics", version=__version__)

    @application.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @application.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "analytics", "version": __version__}

    @application.get("/demo", tags=["meta"])
    def demo(
        seed: Annotated[int, Query()] = 42,
        n_orders: Annotated[int, Query(ge=0, le=20_000)] = 500,
        n_customers: Annotated[int, Query(ge=1, le=5_000)] = 100,
        n_products: Annotated[int, Query(ge=2, le=1_000)] = 40,
        start: Annotated[date, Query()] = date(2025, 1, 1),
        end: Annotated[date, Query()] = date(2025, 12, 31),
    ) -> dict[str, object]:
        """Generate a deterministic synthetic dataset and return a dashboard summary."""
        config = DatasetConfig(
            seed=seed, n_orders=n_orders, n_customers=n_customers, n_products=n_products, start=start, end=end
        )
        ds = generate_dataset(config)
        records = cust.rfm_scores(ds.orders, end)
        return {
            "config": {
                "seed": seed,
                "n_orders": n_orders,
                "n_customers": n_customers,
                "n_products": n_products,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "revenue": rev.revenue_summary(ds.orders, ds.customers, ds.products, "month"),
            "top_products": [s.as_dict() for s in prod.top_products(ds.orders, ds.products, 5)],
            "funnel": [s.as_dict() for s in fun.funnel(ds.orders)],
            "cancellation_rate": fun.cancellation_rate(ds.orders),
            "segments": cust.segment_counts(records),
        }

    for router in (revenue_router, products_router, customers_router, timeseries_router, funnel_router, csv_router):
        application.include_router(router)
    return application


app = create_app()
