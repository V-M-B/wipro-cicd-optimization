from __future__ import annotations

from datetime import date

import pytest

from app.metrics import customers

AS_OF = date(2025, 3, 31)


@pytest.mark.parametrize(
    ("threshold", "expected"),
    [
        (30, {"C1": False, "C2": True, "C3": True, "C4": True, "C9": False}),
        (40, {"C1": False, "C2": True, "C3": True, "C4": False, "C9": False}),
        (60, {"C1": False, "C2": True, "C3": False, "C4": False, "C9": False}),
        (90, {"C1": False, "C2": False, "C3": False, "C4": False, "C9": False}),
        (0, {"C1": True, "C2": True, "C3": True, "C4": True, "C9": True}),
    ],
)
def test_churn_flags(tiny_orders, threshold, expected):
    assert customers.churn_flags(tiny_orders, AS_OF, threshold) == expected


def test_churn_flags_ignore_cancelled_orders(tiny_orders):
    # C2's only later order (O5, 2025-02-10) is cancelled, so their last activity is 2025-01-07.
    assert customers.churn_flags(tiny_orders, AS_OF, 50)["C2"] is True


def test_churn_flags_ignore_orders_after_as_of(tiny_orders):
    flags = customers.churn_flags(tiny_orders, date(2025, 1, 31), 20)
    assert flags == {"C1": False, "C2": True}


def test_churn_flags_reject_negative_threshold(tiny_orders):
    with pytest.raises(ValueError, match="threshold_days"):
        customers.churn_flags(tiny_orders, AS_OF, -1)


@pytest.mark.parametrize(
    ("flags", "expected"),
    [({}, 0.0), ({"a": True}, 1.0), ({"a": True, "b": False}, 0.5), ({"a": True, "b": False, "c": False}, 0.3333)],
)
def test_churn_rate(flags, expected):
    assert customers.churn_rate(flags) == expected


def test_churn_rate_tiny(tiny_orders):
    assert customers.churn_rate(customers.churn_flags(tiny_orders, AS_OF, 30)) == 0.6


def test_churn_rate_grows_as_threshold_shrinks(medium_dataset, as_of):
    rates = [customers.churn_rate(customers.churn_flags(medium_dataset.orders, as_of, t)) for t in (30, 60, 90, 180)]
    assert rates == sorted(rates, reverse=True)
    assert 0.0 < rates[-1] < rates[0] < 1.0


@pytest.mark.parametrize(
    ("margin", "retention", "discount", "expected"),
    [
        (100.0, 0.8, 0.1, 266.666667),
        (50.0, 0.0, 0.1, 0.0),
        (10.0, 0.5, 0.0, 10.0),
        (120.0, 0.9, 0.01, 981.818182),
        (0.0, 0.7, 0.05, 0.0),
        (25.0, 0.6, 0.2, 25.0),
    ],
)
def test_clv_formula(margin, retention, discount, expected):
    assert customers.clv_formula(margin, retention, discount) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize(
    ("retention", "discount", "message"),
    [(1.0, 0.1, "retention"), (-0.1, 0.1, "retention"), (0.5, -0.01, "discount_rate")],
)
def test_clv_formula_rejects_bad_inputs(retention, discount, message):
    with pytest.raises(ValueError, match=message):
        customers.clv_formula(10.0, retention, discount)


def test_clv_increases_with_retention():
    values = [customers.clv_formula(10.0, r / 10, 0.05) for r in range(10)]
    assert values == sorted(values)


def test_customer_clv_with_fixed_retention(tiny_orders):
    clv = customers.customer_clv(tiny_orders, AS_OF, gross_margin=0.3, retention=0.5, discount_rate=0.0)
    assert clv == {"C1": 33.0, "C2": 2.0, "C3": 10.5, "C9": 9.0}


def test_customer_clv_estimated_retention_zero_gives_zero(tiny_orders):
    # no customer is active in two consecutive months -> estimated retention 0
    clv = customers.customer_clv(tiny_orders, AS_OF)
    assert set(clv.values()) == {0.0}


def test_customer_clv_rejects_bad_margin(tiny_orders):
    with pytest.raises(ValueError, match="gross_margin"):
        customers.customer_clv(tiny_orders, AS_OF, gross_margin=1.5)


def test_customer_clv_on_generated_data(medium_dataset, as_of):
    clv = customers.customer_clv(medium_dataset.orders, as_of)
    assert clv
    assert all(v >= 0 for v in clv.values())
    assert 0 < customers.monthly_retention_rate(medium_dataset.orders, as_of) < 1
