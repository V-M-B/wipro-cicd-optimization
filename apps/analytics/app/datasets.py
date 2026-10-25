"""Deterministic synthetic retail data generator.

All randomness flows through a single seeded :class:`random.Random` instance and
all dates are injected through :class:`DatasetConfig`, so the same configuration
always yields identical data (no wall clock, no global random state).
"""

from __future__ import annotations

import bisect
import itertools
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

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

FIRST_NAMES = (
    "Aarav", "Ananya", "Arjun", "Diya", "Ishaan", "Kavya", "Meera", "Nikhil",
    "Priya", "Rahul", "Riya", "Rohan", "Sanya", "Tanvi", "Vikram", "Zara",
    "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Jamie", "Robin",
)  # fmt: skip
LAST_NAMES = (
    "Sharma", "Iyer", "Patel", "Reddy", "Nair", "Gupta", "Menon", "Rao",
    "Singh", "Das", "Kapoor", "Joshi", "Bose", "Shah", "Pillai", "Verma",
)  # fmt: skip
PRODUCT_NOUNS: dict[Category, tuple[str, ...]] = {
    Category.ELECTRONICS: ("Headphones", "Charger", "Speaker", "Monitor", "Keyboard", "Router"),
    Category.GROCERY: ("Rice", "Coffee", "Tea", "Lentils", "Olive Oil", "Oats"),
    Category.APPAREL: ("T-Shirt", "Jacket", "Sneakers", "Scarf", "Jeans", "Cap"),
    Category.HOME: ("Lamp", "Cushion", "Kettle", "Blender", "Rug", "Curtains"),
    Category.TOYS: ("Puzzle", "Robot Kit", "Board Game", "Plush Bear", "Blocks", "Kite"),
}
ADJECTIVES = ("Classic", "Premium", "Eco", "Smart", "Compact", "Deluxe", "Basic", "Pro")
PRICE_RANGES: dict[Category, tuple[float, float]] = {
    Category.ELECTRONICS: (25.0, 1500.0),
    Category.GROCERY: (1.5, 40.0),
    Category.APPAREL: (8.0, 220.0),
    Category.HOME: (10.0, 600.0),
    Category.TOYS: (5.0, 150.0),
}
TIER_WEIGHTS: dict[CustomerTier, float] = {
    CustomerTier.STANDARD: 60.0,
    CustomerTier.SILVER: 25.0,
    CustomerTier.GOLD: 10.0,
    CustomerTier.PLATINUM: 5.0,
}
TIER_ACTIVITY: dict[CustomerTier, float] = {
    CustomerTier.STANDARD: 1.0,
    CustomerTier.SILVER: 1.5,
    CustomerTier.GOLD: 2.5,
    CustomerTier.PLATINUM: 4.0,
}
REGION_WEIGHTS: dict[Region, float] = {
    Region.NORTH: 30.0,
    Region.SOUTH: 25.0,
    Region.EAST: 25.0,
    Region.WEST: 20.0,
}
COUPONS: dict[str, float] = {"SAVE10": 0.10, "WELCOME5": 0.05, "VIP20": 0.20}

# Status mix depends on order age (days before the dataset end date).
_StatusMix = tuple[tuple[OrderStatus, float], ...]
RECENT_STATUS_MIX: _StatusMix = (
    (OrderStatus.CREATED, 45.0),
    (OrderStatus.PAID, 40.0),
    (OrderStatus.CANCELLED, 15.0),
)
MID_STATUS_MIX: _StatusMix = (
    (OrderStatus.PAID, 15.0),
    (OrderStatus.SHIPPED, 55.0),
    (OrderStatus.DELIVERED, 20.0),
    (OrderStatus.CANCELLED, 10.0),
)
OLD_STATUS_MIX: _StatusMix = (
    (OrderStatus.DELIVERED, 91.0),
    (OrderStatus.CANCELLED, 8.0),
    (OrderStatus.SHIPPED, 1.0),
)
RECENT_AGE_DAYS = 3
MID_AGE_DAYS = 12


@dataclass(frozen=True)
class DatasetConfig:
    """Parameters of a synthetic dataset. Identical configs give identical data."""

    seed: int = 42
    n_customers: int = 200
    n_products: int = 50
    n_orders: int = 1_000
    start: date = date(2025, 1, 1)
    end: date = date(2025, 12, 31)
    max_lines: int = 5
    coupon_rate: float = 0.12
    bundle_rate: float = 0.25

    def __post_init__(self) -> None:
        if self.n_customers < 1:
            raise ValueError("n_customers must be >= 1")
        if self.n_products < 2:
            raise ValueError("n_products must be >= 2")
        if self.n_orders < 0:
            raise ValueError("n_orders must be >= 0")
        if self.end < self.start:
            raise ValueError("end must not be before start")
        if self.max_lines < 1:
            raise ValueError("max_lines must be >= 1")
        if not 0.0 <= self.coupon_rate <= 1.0:
            raise ValueError("coupon_rate must be within [0, 1]")
        if not 0.0 <= self.bundle_rate <= 1.0:
            raise ValueError("bundle_rate must be within [0, 1]")

    @property
    def span_days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass
class Dataset:
    config: DatasetConfig
    customers: list[Customer] = field(default_factory=list)
    products: list[Product] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)

    def customer_index(self) -> dict[str, Customer]:
        return {c.id: c for c in self.customers}

    def product_index(self) -> dict[str, Product]:
        return {p.sku: p for p in self.products}


def _weighted(rng: random.Random, mix: _StatusMix) -> OrderStatus:
    values = [p[0] for p in mix]
    weights = [p[1] for p in mix]
    return rng.choices(values, weights=weights, k=1)[0]


def status_mix_for_age(age_days: int) -> _StatusMix:
    """Status distribution used for an order created ``age_days`` before the end date."""
    if age_days < RECENT_AGE_DAYS:
        return RECENT_STATUS_MIX
    if age_days < MID_AGE_DAYS:
        return MID_STATUS_MIX
    return OLD_STATUS_MIX


def generate_customers(rng: random.Random, n: int) -> list[Customer]:
    tiers = list(TIER_WEIGHTS)
    tier_w = list(TIER_WEIGHTS.values())
    regions = list(REGION_WEIGHTS)
    region_w = list(REGION_WEIGHTS.values())
    customers: list[Customer] = []
    for i in range(1, n + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        customers.append(
            Customer(
                id=f"C{i:06d}",
                name=f"{first} {last}",
                email=f"{first.lower()}.{last.lower()}{i}@example.com",
                tier=rng.choices(tiers, weights=tier_w, k=1)[0],
                region=rng.choices(regions, weights=region_w, k=1)[0],
            )
        )
    return customers


def generate_products(rng: random.Random, n: int) -> list[Product]:
    categories = list(Category)
    products: list[Product] = []
    for i in range(1, n + 1):
        category = categories[(i - 1) % len(categories)]
        low, high = PRICE_RANGES[category]
        # log-uniform prices: many cheap items, few expensive ones
        price = round(low * (high / low) ** rng.random(), 2)
        products.append(
            Product(
                id=f"P{i:05d}",
                sku=f"{category.value[:3]}-{i:05d}",
                name=f"{rng.choice(ADJECTIVES)} {rng.choice(PRODUCT_NOUNS[category])}",
                category=category,
                unitPrice=price,
                active=rng.random() > 0.05,
            )
        )
    return products


def generate_orders(
    rng: random.Random,
    customers: list[Customer],
    products: list[Product],
    config: DatasetConfig,
) -> list[Order]:
    span = config.span_days
    # Customer activity is heavy-tailed and boosted by tier. Each customer has an
    # acquisition day and a finite active lifetime, which produces realistic
    # cohorts, recency spread and churn.
    activity = [rng.paretovariate(1.6) * TIER_ACTIVITY[c.tier] for c in customers]
    cum_activity = list(itertools.accumulate(activity))
    acquisition = [int(span * rng.random() ** 1.3) for _ in customers]
    lifetime = [max(1, int(rng.expovariate(1 / 150))) for _ in customers]

    # Product popularity: Zipf-like over a shuffled ranking.
    ranking = list(range(len(products)))
    rng.shuffle(ranking)
    popularity = [0.0] * len(products)
    for rank, idx in enumerate(ranking, start=1):
        popularity[idx] = 1.0 / rank**0.9
    cum_popularity = list(itertools.accumulate(popularity))
    total_activity = cum_activity[-1]
    total_popularity = cum_popularity[-1]
    n_products = len(products)
    coupon_codes = list(COUPONS)

    drafts: list[tuple[datetime, str, list[OrderLine], str | None, float]] = []
    for _ in range(config.n_orders):
        ci = min(bisect.bisect_left(cum_activity, rng.random() * total_activity), len(customers) - 1)
        first_day = acquisition[ci]
        window = max(1, min(lifetime[ci], span - first_day))
        day = first_day + int(rng.random() * window)
        seconds = int(rng.random() * 86_400)
        created = datetime.combine(config.start + timedelta(days=day), time()) + timedelta(seconds=seconds)

        n_lines = 1 + min(config.max_lines - 1, int(rng.expovariate(0.9)))
        quantities: dict[int, int] = {}
        for _line in range(n_lines):
            pi = min(bisect.bisect_left(cum_popularity, rng.random() * total_popularity), n_products - 1)
            quantities[pi] = quantities.get(pi, 0) + 1 + min(9, int(rng.expovariate(1.2)))
            if rng.random() < config.bundle_rate:
                # products are sold in natural pairs (0,1), (2,3), ... -> basket affinity
                partner = pi ^ 1
                if partner < n_products:
                    quantities.setdefault(partner, 1)
        lines: list[OrderLine] = []
        gross = 0.0
        for pi in sorted(quantities):
            product = products[pi]
            unit = product.unitPrice
            if rng.random() < 0.08:  # occasional promotional price
                unit = round(unit * 0.9, 2)
            qty = quantities[pi]
            gross += qty * unit
            lines.append(OrderLine(sku=product.sku, quantity=qty, unitPrice=unit))
        coupon = rng.choice(coupon_codes) if rng.random() < config.coupon_rate else None
        discount = COUPONS[coupon] if coupon else 0.0
        total = round(gross * (1.0 - discount), 2)
        drafts.append((created, customers[ci].id, lines, coupon, total))

    drafts.sort(key=lambda d: (d[0], d[1]))
    orders: list[Order] = []
    for i, (created, customer_id, lines, coupon, total) in enumerate(drafts, start=1):
        age = (config.end - created.date()).days
        orders.append(
            Order(
                id=f"O{i:07d}",
                customerId=customer_id,
                status=_weighted(rng, status_mix_for_age(age)),
                lines=lines,
                couponCode=coupon,
                createdAt=created,
                total=total,
            )
        )
    return orders


def generate_dataset(config: DatasetConfig | None = None, **overrides: object) -> Dataset:
    """Generate customers, products and orders for ``config`` (or defaults + overrides)."""
    if config is None:
        config = DatasetConfig(**overrides)  # type: ignore[arg-type]
    elif overrides:
        raise TypeError("pass either a config or keyword overrides, not both")
    rng = random.Random(config.seed)
    customers = generate_customers(rng, config.n_customers)
    products = generate_products(rng, config.n_products)
    orders = generate_orders(rng, customers, products, config)
    return Dataset(config=config, customers=customers, products=products, orders=orders)
