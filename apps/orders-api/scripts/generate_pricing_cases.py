#!/usr/bin/env python3
"""Generate parameterized pricing test data for orders-api.

This script contains an *independent* re-implementation of the pricing rules documented in
``PricingService`` (Python ``decimal`` with ROUND_HALF_EVEN), used as a test oracle. It writes
CSV files that JUnit ``@CsvFileSource`` tests feed through the real Java ``PricingService`` and
``ShippingPolicy``; any divergence between the Java code and the documented rules fails a test.

Output is fully deterministic (fixed seed). Re-run after changing a pricing rule:

    python scripts/generate_pricing_cases.py

Files written (relative to apps/orders-api):
    src/test/resources/generated/pricing-scenarios.csv   -> GeneratedPricingScenariosTest
    src/test/resources/generated/shipping-matrix.csv     -> GeneratedShippingMatrixTest
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

SEED = 20251025
PRICING_DATE = date(2026, 6, 15)  # fixed date passed to PricingService for every scenario

TIER_RATES = {"STANDARD": Decimal("0.00"), "SILVER": Decimal("0.05"),
              "GOLD": Decimal("0.10"), "PLATINUM": Decimal("0.15")}
BULK_TIERS = [(100, Decimal("0.12")), (50, Decimal("0.08")), (20, Decimal("0.05")), (10, Decimal("0.02"))]
TAX_RATES = {"NORTH": Decimal("0.0800"), "SOUTH": Decimal("0.0650"),
             "EAST": Decimal("0.0725"), "WEST": Decimal("0.0900")}
SHIPPING_BASE = {"NORTH": Decimal("5.99"), "SOUTH": Decimal("4.99"),
                 "EAST": Decimal("5.49"), "WEST": Decimal("6.99")}
FREE_SHIPPING_THRESHOLD = Decimal("75.00")
PER_UNIT_SURCHARGE = Decimal("0.50")
SURCHARGE_FREE_UNITS = 5

# A slice of the seeded catalog (V3__seed_reference_data.sql) for realistic prices.
CATALOG = [
    ("ELE-1001", "24.99"), ("ELE-1002", "89.50"), ("ELE-1003", "39.00"), ("ELE-1004", "249.99"),
    ("ELE-1005", "159.95"), ("ELE-1006", "7.49"), ("ELE-1007", "54.25"), ("GRO-2001", "12.75"),
    ("GRO-2002", "9.99"), ("GRO-2003", "8.45"), ("GRO-2004", "4.20"), ("GRO-2005", "3.15"),
    ("GRO-2006", "15.60"), ("GRO-2007", "1.85"), ("GRO-2008", "6.30"), ("APP-3001", "14.99"),
    ("APP-3002", "49.90"), ("APP-3003", "79.00"), ("APP-3005", "11.25"), ("APP-3007", "29.95"),
    ("HOM-4001", "6.99"), ("HOM-4002", "34.50"), ("HOM-4003", "27.75"), ("HOM-4005", "9.25"),
    ("HOM-4006", "12.10"), ("TOY-5001", "44.99"), ("TOY-5002", "18.50"), ("TOY-5004", "15.75"),
    ("TOY-5006", "12.95"), ("TOY-5007", "21.60"),
]

# Coupon spec: type|value|minSpend|maxDiscount|validFrom|expiresOn  (empty = not set)
COUPONS = [
    "NONE",
    "NONE",
    "NONE",
    "PERCENTAGE|10||||2099-12-31",
    "PERCENTAGE|10||50|||",
    "PERCENTAGE|20|200|100|||",
    "PERCENTAGE|5|||||",
    "FIXED_AMOUNT|5|25||||",
    "FIXED_AMOUNT|15|||||",
    "FIXED_AMOUNT|500|||||",
    "FREE_SHIPPING|0|30||||",
    "PERCENTAGE|15|||2020-01-01|2020-12-31",
    "PERCENTAGE|25|||2099-01-01|",
    "FIXED_AMOUNT|10|||2026-06-15|2026-06-15",
]


def r2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def bulk_rate(qty: int) -> Decimal:
    for min_qty, rate in BULK_TIERS:
        if qty >= min_qty:
            return rate
    return Decimal("0.00")


def shipping(net: Decimal, units: int, region: str, tier: str, free_coupon: bool) -> Decimal:
    if free_coupon or tier == "PLATINUM" or net >= FREE_SHIPPING_THRESHOLD:
        return Decimal("0.00")
    extra = max(0, units - SURCHARGE_FREE_UNITS)
    return r2(SHIPPING_BASE[region] + PER_UNIT_SURCHARGE * extra)


@dataclass
class Coupon:
    type: str
    value: Decimal
    min_spend: Decimal | None
    max_discount: Decimal | None
    valid_from: date | None
    expires_on: date | None

    @staticmethod
    def parse(spec: str) -> "Coupon | None":
        if spec == "NONE":
            return None
        parts = (spec.split("|") + [""] * 6)[:6]
        t, v, ms, md, vf, eo = parts
        return Coupon(t, Decimal(v), Decimal(ms) if ms else None, Decimal(md) if md else None,
                      date.fromisoformat(vf) if vf else None, date.fromisoformat(eo) if eo else None)


def price(lines: list[tuple[str, int, Decimal]], tier: str, region: str, coupon: Coupon | None):
    subtotal = Decimal("0.00")
    bulk = Decimal("0.00")
    units = 0
    for _, qty, unit in lines:
        line_sub = r2(unit * qty)
        subtotal += line_sub
        bulk += r2(line_sub * bulk_rate(qty))
        units += qty
    after_bulk = subtotal - bulk
    tier_disc = r2(after_bulk * TIER_RATES[tier])
    after_tier = after_bulk - tier_disc

    coupon_disc = Decimal("0.00")
    free_ship = False
    if coupon is not None:
        if coupon.valid_from and PRICING_DATE < coupon.valid_from:
            return ("REJECT:NOT_YET_VALID",)
        if coupon.expires_on and PRICING_DATE > coupon.expires_on:
            return ("REJECT:EXPIRED",)
        if coupon.min_spend is not None and subtotal < coupon.min_spend:
            return ("REJECT:MIN_SPEND_NOT_MET",)
        if coupon.type == "PERCENTAGE":
            coupon_disc = r2(after_tier * coupon.value / Decimal(100))
            if coupon.max_discount is not None:
                coupon_disc = min(coupon_disc, r2(coupon.max_discount))
            coupon_disc = min(coupon_disc, after_tier)
        elif coupon.type == "FIXED_AMOUNT":
            coupon_disc = min(r2(coupon.value), after_tier)
        elif coupon.type == "FREE_SHIPPING":
            free_ship = True

    net = after_tier - coupon_disc
    tax = r2(net * TAX_RATES[region])
    ship = shipping(net, units, region, tier, free_ship)
    total = net + tax + ship
    return ("OK", subtotal, bulk, tier_disc, coupon_disc, tax, ship, total)


def random_quantity(rng: random.Random) -> int:
    bucket = rng.random()
    if bucket < 0.60:
        return rng.randint(1, 5)
    if bucket < 0.80:
        return rng.choice([9, 10, 11, 15, 19, 20, 21])
    if bucket < 0.93:
        return rng.choice([30, 49, 50, 51, 75])
    return rng.choice([99, 100, 101, 150, 250])


def generate_scenarios(count: int, rng: random.Random) -> list[list[str]]:
    rows = []
    tiers = list(TIER_RATES)
    regions = list(TAX_RATES)
    for i in range(count):
        n_lines = rng.choice([1, 1, 2, 2, 3, 4])
        picks = rng.sample(CATALOG, n_lines)
        lines = [(sku, random_quantity(rng), Decimal(p)) for sku, p in picks]
        tier = tiers[i % len(tiers)]           # every tier equally represented
        region = regions[(i // len(tiers)) % len(regions)]  # and every region per tier
        coupon_spec = rng.choice(COUPONS)
        result = price(lines, tier, region, Coupon.parse(coupon_spec))
        line_spec = ";".join(f"{sku}:{q}:{p}" for sku, q, p in lines)
        if result[0] == "OK":
            outcome = "OK"
            amounts = [str(a) for a in result[1:]]
        else:
            outcome = result[0]
            amounts = [""] * 7
        rows.append([f"S{i + 1:03d}", line_spec, tier, region, coupon_spec, outcome, *amounts])
    return rows


def generate_shipping_matrix() -> list[list[str]]:
    rows = []
    tiers = ["STANDARD", "SILVER", "GOLD"]
    i = 0
    for region in SHIPPING_BASE:
        for units in (1, 6, 13):
            for net in ("74.99", "75.00"):
                tier = tiers[i % len(tiers)]
                i += 1
                rows.append([region, tier, str(units), net, str(shipping(Decimal(net), units, region, tier, False))])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenarios", type=int, default=24, help="number of pricing scenarios")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent
                        / "src" / "test" / "resources" / "generated")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    scenarios = generate_scenarios(args.scenarios, rng)
    with (args.out / "pricing-scenarios.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "lines", "tier", "region", "coupon", "outcome", "subtotal", "bulkDiscount",
                    "tierDiscount", "couponDiscount", "tax", "shipping", "total"])
        w.writerows(scenarios)

    matrix = generate_shipping_matrix()
    with (args.out / "shipping-matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "tier", "units", "net", "expectedShipping"])
        w.writerows(matrix)

    rejected = sum(1 for r in scenarios if r[5] != "OK")
    print(f"pricing-scenarios.csv: {len(scenarios)} rows ({rejected} expect a coupon rejection)")
    print(f"shipping-matrix.csv:   {len(matrix)} rows")


if __name__ == "__main__":
    main()
