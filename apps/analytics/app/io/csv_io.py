"""CSV import/export for customers, products and orders, with row-level validation.

Readers collect *all* row errors (up to ``max_errors``) and raise a single
:class:`CsvValidationError`, so a bad upload can be fixed in one pass.

Orders are stored one row per order line; header fields (customer, status,
created_at, coupon, total) are repeated on every row of the same order and must
agree. An order without lines is written as one row with empty line fields.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TextIO

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

CUSTOMER_COLUMNS = ("id", "name", "email", "tier", "region")
PRODUCT_COLUMNS = ("id", "sku", "name", "category", "unit_price", "active")
ORDER_COLUMNS = (
    "order_id",
    "customer_id",
    "status",
    "created_at",
    "coupon_code",
    "total",
    "sku",
    "quantity",
    "unit_price",
)
ORDER_HEADER_FIELDS = ("customer_id", "status", "created_at", "coupon_code", "total")
TRUE_VALUES = frozenset({"true", "1", "yes", "y", "t"})
FALSE_VALUES = frozenset({"false", "0", "no", "n", "f"})


@dataclass(frozen=True)
class RowError:
    line: int
    field: str | None
    message: str

    def __str__(self) -> str:
        where = f"line {self.line}" + (f", {self.field}" if self.field else "")
        return f"{where}: {self.message}"

    def as_dict(self) -> dict[str, object]:
        return {"line": self.line, "field": self.field, "message": self.message}


class CsvValidationError(ValueError):
    def __init__(self, errors: list[RowError]):
        self.errors = errors
        preview = "; ".join(str(e) for e in errors[:3])
        more = f" (+{len(errors) - 3} more)" if len(errors) > 3 else ""
        super().__init__(f"{len(errors)} CSV validation error(s): {preview}{more}")


class _FieldError(ValueError):
    pass


# --------------------------------------------------------------------------- parsers


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise _FieldError(f"expected a boolean, got {raw!r}")


def parse_float(raw: str, *, minimum: float | None = 0.0) -> float:
    try:
        value = float(raw.strip())
    except ValueError:
        raise _FieldError(f"expected a number, got {raw!r}") from None
    if not math.isfinite(value):
        raise _FieldError(f"expected a finite number, got {raw!r}")
    if minimum is not None and value < minimum:
        raise _FieldError(f"must be >= {minimum:g}, got {raw!r}")
    return value


def parse_int(raw: str, *, minimum: int | None = 1) -> int:
    text = raw.strip()
    try:
        value = int(text)
    except ValueError:
        raise _FieldError(f"expected an integer, got {raw!r}") from None
    if minimum is not None and value < minimum:
        raise _FieldError(f"must be >= {minimum}, got {raw!r}")
    return value


def parse_datetime(raw: str) -> datetime:
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise _FieldError(f"expected an ISO-8601 datetime, got {raw!r}") from None


def parse_enum[E: Enum](raw: str, enum_type: type[E]) -> E:
    text = raw.strip().upper()
    try:
        return enum_type(text)
    except ValueError:
        allowed = ", ".join(m.value for m in enum_type)
        raise _FieldError(f"expected one of {allowed}, got {raw!r}") from None


def parse_email(raw: str) -> str:
    text = raw.strip()
    local, sep, domain = text.partition("@")
    if not sep or not local or "." not in domain or domain.startswith(".") or domain.endswith(".") or " " in text:
        raise _FieldError(f"invalid email address {raw!r}")
    return text


def parse_required(raw: str) -> str:
    text = raw.strip()
    if not text:
        raise _FieldError("must not be empty")
    return text


# --------------------------------------------------------------------------- reading


class _Collector:
    def __init__(self, max_errors: int):
        self.errors: list[RowError] = []
        self.max_errors = max_errors
        self.count = 0  # total errors seen, including those beyond max_errors

    def add(self, line: int, field: str | None, message: str) -> None:
        self.count += 1
        if len(self.errors) < self.max_errors:
            self.errors.append(RowError(line, field, message))

    def field(self, row: dict[str, str], line: int, name: str, parser: Callable[[str], object]) -> object:
        try:
            return parser(row.get(name) or "")
        except _FieldError as exc:
            self.add(line, name, str(exc))
            return None

    def raise_if_any(self) -> None:
        if self.errors:
            raise CsvValidationError(self.errors)


def _rows(source: str | TextIO, required: tuple[str, ...], collector: _Collector) -> list[tuple[int, dict[str, str]]]:
    stream = io.StringIO(source) if isinstance(source, str) else source
    reader = csv.DictReader(stream)
    header = [h.strip() for h in (reader.fieldnames or [])]
    if not header:
        collector.add(1, None, "missing header row")
        collector.raise_if_any()
    reader.fieldnames = header
    missing = [c for c in required if c not in header]
    if missing:
        collector.add(1, None, f"missing required column(s): {', '.join(missing)}")
        collector.raise_if_any()
    rows: list[tuple[int, dict[str, str]]] = []
    for row in reader:
        line = reader.line_num
        if None in row:
            collector.add(line, None, "too many fields")
            continue
        if all(not (v or "").strip() for v in row.values()):
            continue  # ignore blank lines
        rows.append((line, row))
    return rows


def read_customers(source: str | TextIO, *, max_errors: int = 100) -> list[Customer]:
    col = _Collector(max_errors)
    customers: list[Customer] = []
    seen: dict[str, int] = {}
    for line, row in _rows(source, CUSTOMER_COLUMNS, col):
        before = col.count
        cid = col.field(row, line, "id", parse_required)
        name = col.field(row, line, "name", parse_required)
        email = col.field(row, line, "email", parse_email)
        tier = col.field(row, line, "tier", lambda s: parse_enum(s, CustomerTier))
        region = col.field(row, line, "region", lambda s: parse_enum(s, Region))
        if isinstance(cid, str):
            if cid in seen:
                col.add(line, "id", f"duplicate id {cid!r} (first seen on line {seen[cid]})")
            else:
                seen[cid] = line
        if col.count == before:
            customers.append(Customer(id=cid, name=name, email=email, tier=tier, region=region))  # type: ignore[arg-type]
    col.raise_if_any()
    return customers


def read_products(source: str | TextIO, *, max_errors: int = 100) -> list[Product]:
    col = _Collector(max_errors)
    products: list[Product] = []
    seen_ids: dict[str, int] = {}
    seen_skus: dict[str, int] = {}
    for line, row in _rows(source, PRODUCT_COLUMNS, col):
        before = col.count
        pid = col.field(row, line, "id", parse_required)
        sku = col.field(row, line, "sku", parse_required)
        name = col.field(row, line, "name", parse_required)
        category = col.field(row, line, "category", lambda s: parse_enum(s, Category))
        price = col.field(row, line, "unit_price", parse_float)
        active = col.field(row, line, "active", parse_bool)
        for value, seen, fname in ((pid, seen_ids, "id"), (sku, seen_skus, "sku")):
            if isinstance(value, str):
                if value in seen:
                    col.add(line, fname, f"duplicate {fname} {value!r} (first seen on line {seen[value]})")
                else:
                    seen[value] = line
        if col.count == before:
            products.append(
                Product(id=pid, sku=sku, name=name, category=category, unitPrice=price, active=active)  # type: ignore[arg-type]
            )
    col.raise_if_any()
    return products


def read_orders(source: str | TextIO, *, max_errors: int = 100) -> list[Order]:
    col = _Collector(max_errors)
    headers: dict[str, dict[str, object]] = {}
    raw_headers: dict[str, tuple[int, tuple[str, ...]]] = {}
    lines: dict[str, list[OrderLine]] = {}
    skus: dict[str, set[str]] = {}
    invalid: set[str] = set()
    for line, row in _rows(source, ORDER_COLUMNS, col):
        before = col.count
        oid = col.field(row, line, "order_id", parse_required)
        if not isinstance(oid, str):
            continue
        header_raw = tuple((row.get(f) or "").strip() for f in ORDER_HEADER_FIELDS)
        if oid in raw_headers:
            first_line, first_raw = raw_headers[oid]
            for fname, a, b in zip(ORDER_HEADER_FIELDS, first_raw, header_raw, strict=True):
                if a != b:
                    col.add(line, fname, f"inconsistent with line {first_line} for order {oid!r}: {b!r} != {a!r}")
        else:
            raw_headers[oid] = (line, header_raw)
            customer_id = col.field(row, line, "customer_id", parse_required)
            status = col.field(row, line, "status", lambda s: parse_enum(s, OrderStatus))
            created = col.field(row, line, "created_at", parse_datetime)
            total = col.field(row, line, "total", parse_float)
            coupon = (row.get("coupon_code") or "").strip() or None
            headers[oid] = {
                "customerId": customer_id,
                "status": status,
                "createdAt": created,
                "total": total,
                "couponCode": coupon,
            }
            lines[oid] = []
            skus[oid] = set()
        sku_raw = (row.get("sku") or "").strip()
        qty_raw = (row.get("quantity") or "").strip()
        price_raw = (row.get("unit_price") or "").strip()
        if sku_raw or qty_raw or price_raw:
            sku = col.field(row, line, "sku", parse_required)
            qty = col.field(row, line, "quantity", parse_int)
            price = col.field(row, line, "unit_price", parse_float)
            if isinstance(sku, str):
                if sku in skus[oid]:
                    col.add(line, "sku", f"duplicate sku {sku!r} in order {oid!r}")
                skus[oid].add(sku)
            if col.count == before:
                lines[oid].append(OrderLine(sku=sku, quantity=qty, unitPrice=price))  # type: ignore[arg-type]
        if col.count != before:
            invalid.add(oid)
    col.raise_if_any()
    return [Order(id=oid, lines=lines[oid], **h) for oid, h in headers.items() if oid not in invalid]  # type: ignore[arg-type]


# --------------------------------------------------------------------------- writing


def _write(columns: tuple[str, ...], rows: Iterable[Iterable[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def _num(value: float) -> str:
    return repr(float(value))


def write_customers(customers: Iterable[Customer]) -> str:
    return _write(CUSTOMER_COLUMNS, ((c.id, c.name, c.email, c.tier.value, c.region.value) for c in customers))


def write_products(products: Iterable[Product]) -> str:
    return _write(
        PRODUCT_COLUMNS,
        ((p.id, p.sku, p.name, p.category.value, _num(p.unitPrice), "true" if p.active else "false") for p in products),
    )


def write_orders(orders: Iterable[Order]) -> str:
    def rows() -> Iterable[tuple[object, ...]]:
        for o in orders:
            head = (o.id, o.customerId, o.status.value, o.createdAt.isoformat(), o.couponCode or "", _num(o.total))
            if not o.lines:
                yield (*head, "", "", "")
            for line in o.lines:
                yield (*head, line.sku, line.quantity, _num(line.unitPrice))

    return _write(ORDER_COLUMNS, rows())
