"""Test data builders shared across test modules.

``tiny_*`` builders return a small hand-made dataset whose metric values were
worked out by hand (see the comments) and are asserted literally in tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time

from pydantic import BaseModel

from app.datasets import Dataset, DatasetConfig, generate_dataset
from app.generated.schemas import (
    Category,
    Customer,
    CustomerTier,
    Order,
    OrderLine,
    OrderStatus,
    Product,
    Region,
)

LineSpec = tuple[str, int, float]


def make_order(
    order_id: str,
    customer_id: str = "C1",
    status: OrderStatus | str = OrderStatus.DELIVERED,
    day: date | str = date(2025, 1, 1),
    lines: Sequence[LineSpec] = (("SKU-1", 1, 10.0),),
    total: float | None = None,
    coupon: str | None = None,
    hour: int = 12,
) -> Order:
    if isinstance(day, str):
        day = date.fromisoformat(day)
    order_lines = [OrderLine(sku=s, quantity=q, unitPrice=p) for s, q, p in lines]
    if total is None:
        total = round(sum(q * p for _, q, p in lines), 2)
    return Order(
        id=order_id,
        customerId=customer_id,
        status=OrderStatus(status),
        lines=order_lines,
        couponCode=coupon,
        createdAt=datetime.combine(day, time(hour=hour)),
        total=total,
    )


def make_customer(cid: str, region: Region = Region.NORTH, tier: CustomerTier = CustomerTier.STANDARD) -> Customer:
    return Customer(id=cid, name=f"Customer {cid}", email=f"{cid.lower()}@example.com", tier=tier, region=region)


def make_product(sku: str, category: Category = Category.HOME, price: float = 10.0, active: bool = True) -> Product:
    return Product(id=f"P-{sku}", sku=sku, name=f"Product {sku}", category=category, unitPrice=price, active=active)


def tiny_customers() -> list[Customer]:
    return [
        make_customer("C1", Region.NORTH, CustomerTier.GOLD),
        make_customer("C2", Region.SOUTH, CustomerTier.STANDARD),
        make_customer("C3", Region.EAST, CustomerTier.SILVER),
        make_customer("C4", Region.WEST, CustomerTier.PLATINUM),
    ]


def tiny_products() -> list[Product]:
    return [
        make_product("ELE-1", Category.ELECTRONICS, 100.0),
        make_product("ELE-2", Category.ELECTRONICS, 20.0),
        make_product("GRO-1", Category.GROCERY, 10.0),
        make_product("APP-1", Category.APPAREL, 50.0),
        make_product("TOY-1", Category.TOYS, 15.0),  # never sold
    ]


def tiny_orders() -> list[Order]:
    """Revenue orders total 450.00 (O5 cancelled and O6 created are excluded).

    month: 2025-01 230, 2025-02 70, 2025-03 150
    region: NORTH 330, SOUTH 20, EAST 70, UNKNOWN 30
    category: ELECTRONICS 260, GROCERY 70, APPAREL 90, UNKNOWN 30
    """
    S = OrderStatus
    return [
        make_order("O1", "C1", S.DELIVERED, "2025-01-06", [("ELE-1", 1, 100.0), ("GRO-1", 2, 10.0)]),
        make_order("O2", "C2", S.DELIVERED, "2025-01-07", [("ELE-2", 1, 20.0)]),
        make_order("O3", "C1", S.SHIPPED, "2025-01-15", [("APP-1", 2, 50.0)], total=90.0, coupon="SAVE10"),
        make_order("O4", "C3", S.PAID, "2025-02-03", [("GRO-1", 5, 10.0), ("ELE-2", 1, 20.0)]),
        make_order("O5", "C2", S.CANCELLED, "2025-02-10", [("ELE-1", 1, 100.0)]),
        make_order("O6", "C4", S.CREATED, "2025-02-20", [("APP-1", 1, 50.0)]),
        make_order("O7", "C1", S.DELIVERED, "2025-03-01", [("ELE-1", 1, 100.0), ("ELE-2", 1, 20.0)]),
        make_order("O8", "C9", S.DELIVERED, "2025-03-02", [("ZZZ-9", 1, 30.0)]),
    ]


def dump(models: Sequence[BaseModel]) -> list[dict]:
    """Serialise pydantic models to JSON-compatible dicts for API requests."""
    return [m.model_dump(mode="json") for m in models]


def large_dataset(n_orders: int, seed: int = 7, n_customers: int | None = None, n_products: int = 200) -> Dataset:
    """A large generated dataset (not cached: each slow module pays for its own data)."""
    return generate_dataset(
        DatasetConfig(
            seed=seed,
            n_orders=n_orders,
            n_customers=n_customers if n_customers is not None else max(200, n_orders // 20),
            n_products=n_products,
            start=date(2024, 1, 1),
            end=date(2025, 12, 31),
        )
    )
