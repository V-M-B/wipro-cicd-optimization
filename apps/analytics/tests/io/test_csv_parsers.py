from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.generated.schemas import Category, OrderStatus, Region
from app.io import csv_io


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("TRUE", True), (" yes ", True), ("1", True), ("y", True), ("false", False), ("0", False),
     ("No", False), ("f", False)],
)  # fmt: skip
def test_parse_bool(raw, expected):
    assert csv_io.parse_bool(raw) is expected


@pytest.mark.parametrize("raw", ["", "maybe", "2", "truee"])
def test_parse_bool_invalid(raw):
    with pytest.raises(ValueError, match="expected a boolean"):
        csv_io.parse_bool(raw)


@pytest.mark.parametrize(("raw", "expected"), [("0", 0.0), ("12.5", 12.5), (" 3 ", 3.0), ("1e2", 100.0)])
def test_parse_float(raw, expected):
    assert csv_io.parse_float(raw) == expected


@pytest.mark.parametrize(
    ("raw", "message"),
    [("abc", "expected a number"), ("", "expected a number"), ("nan", "finite"), ("inf", "finite"), ("-1", ">= 0")],
)
def test_parse_float_invalid(raw, message):
    with pytest.raises(ValueError, match=message):
        csv_io.parse_float(raw)


def test_parse_float_without_minimum_accepts_negative():
    assert csv_io.parse_float("-2.5", minimum=None) == -2.5


@pytest.mark.parametrize(("raw", "expected"), [("1", 1), (" 42 ", 42), ("007", 7)])
def test_parse_int(raw, expected):
    assert csv_io.parse_int(raw) == expected


@pytest.mark.parametrize(("raw", "message"), [("0", ">= 1"), ("-3", ">= 1"), ("1.5", "integer"), ("x", "integer")])
def test_parse_int_invalid(raw, message):
    with pytest.raises(ValueError, match=message):
        csv_io.parse_int(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2025-03-01T10:15:00", datetime(2025, 3, 1, 10, 15)),
        ("2025-03-01", datetime(2025, 3, 1)),
        ("2025-03-01T10:15:00Z", datetime(2025, 3, 1, 10, 15, tzinfo=UTC)),
        ("2025-03-01T10:15:00+05:30", datetime(2025, 3, 1, 10, 15, tzinfo=timezone(timedelta(hours=5, minutes=30)))),
    ],
)
def test_parse_datetime(raw, expected):
    assert csv_io.parse_datetime(raw) == expected


@pytest.mark.parametrize("raw", ["", "yesterday", "2025-13-01", "01/03/2025"])
def test_parse_datetime_invalid(raw):
    with pytest.raises(ValueError, match="ISO-8601"):
        csv_io.parse_datetime(raw)


@pytest.mark.parametrize(
    ("raw", "enum_type", "expected"),
    [("north", Region, Region.NORTH), (" PAID ", OrderStatus, OrderStatus.PAID), ("Toys", Category, Category.TOYS)],
)
def test_parse_enum(raw, enum_type, expected):
    assert csv_io.parse_enum(raw, enum_type) is expected


def test_parse_enum_invalid_lists_allowed_values():
    with pytest.raises(ValueError, match="expected one of NORTH, SOUTH, EAST, WEST"):
        csv_io.parse_enum("CENTRAL", Region)


@pytest.mark.parametrize("raw", ["a@b.co", "first.last+tag@example.com", "ops@mail.retail.example"])
def test_parse_email(raw):
    assert csv_io.parse_email(raw) == raw


@pytest.mark.parametrize(
    "raw",
    ["", "plainaddress", "@example.com", "a@", "a@example", "a@.com", "a@b.", "a b@c.com", "a@b..com", "a@@b.com"],
)
def test_parse_email_invalid(raw):
    with pytest.raises(ValueError, match="invalid email"):
        csv_io.parse_email(raw)


def test_parse_required():
    assert csv_io.parse_required("  x ") == "x"
    with pytest.raises(ValueError, match="must not be empty"):
        csv_io.parse_required("   ")


def test_row_error_formatting():
    assert str(csv_io.RowError(3, "email", "bad")) == "line 3, email: bad"
    assert str(csv_io.RowError(1, None, "missing header row")) == "line 1: missing header row"


def test_validation_error_message_truncates():
    errors = [csv_io.RowError(i, "f", "bad") for i in range(2, 7)]
    exc = csv_io.CsvValidationError(errors)
    assert str(exc).startswith("5 CSV validation error(s): line 2, f: bad")
    assert str(exc).endswith("(+2 more)")
    assert isinstance(exc, ValueError)
