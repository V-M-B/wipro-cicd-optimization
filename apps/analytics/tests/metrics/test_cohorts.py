from __future__ import annotations

from datetime import date

import pytest

from app.metrics import customers
from tests.factories import make_order


@pytest.fixture
def cohort_orders():
    """A: Jan, Feb, Apr | B: Jan | C: Feb, Mar | D: Mar (+ a cancelled May order for B)."""
    return [
        make_order("O1", "A", day="2025-01-05"),
        make_order("O2", "B", day="2025-01-20"),
        make_order("O3", "A", day="2025-02-02"),
        make_order("O4", "C", day="2025-02-14"),
        make_order("O5", "C", day="2025-03-03"),
        make_order("O6", "D", day="2025-03-30"),
        make_order("O7", "A", day="2025-04-11"),
        make_order("O8", "B", status="CANCELLED", day="2025-05-01"),
    ]


@pytest.mark.parametrize(
    ("mode", "expected_rows"),
    [
        ("active", [[1.0, 0.5, 0.0, 0.5], [1.0, 1.0, 0.0], [1.0, 0.0]]),
        ("rolling", [[1.0, 0.5, 0.5, 0.5], [1.0, 1.0, 0.0], [1.0, 0.0]]),
    ],
)
def test_cohort_retention(cohort_orders, mode, expected_rows):
    matrix = customers.cohort_retention(cohort_orders, mode)
    assert matrix.cohorts == ["2025-01", "2025-02", "2025-03"]
    assert matrix.sizes == [2, 1, 1]
    assert matrix.rows == expected_rows
    assert matrix.mode == mode


def test_cohort_retention_with_end_extends_columns(cohort_orders):
    matrix = customers.cohort_retention(cohort_orders, end=date(2025, 5, 31))
    assert matrix.row("2025-01") == [1.0, 0.5, 0.0, 0.5, 0.0]
    assert len(matrix.row("2025-03")) == 3


def test_cohort_retention_end_excludes_later_orders(cohort_orders):
    matrix = customers.cohort_retention(cohort_orders, end=date(2025, 2, 28))
    assert matrix.cohorts == ["2025-01", "2025-02"]
    assert matrix.rows == [[1.0, 0.5], [1.0]]


def test_cohort_retention_counting_cancelled_orders(cohort_orders):
    matrix = customers.cohort_retention(cohort_orders, statuses=None)
    assert matrix.row("2025-01") == [1.0, 0.5, 0.0, 0.5, 0.5]


def test_cohort_retention_empty():
    matrix = customers.cohort_retention([])
    assert matrix.as_dict() == {"mode": "active", "cohorts": [], "sizes": [], "rows": []}


def test_cohort_retention_rejects_unknown_mode(cohort_orders):
    with pytest.raises(ValueError, match="mode must be one of"):
        customers.cohort_retention(cohort_orders, "cumulative")


def test_cohort_spanning_year_boundary():
    orders = [make_order("O1", "A", day="2024-12-31"), make_order("O2", "A", day="2025-01-01")]
    matrix = customers.cohort_retention(orders)
    assert matrix.cohorts == ["2024-12"]
    assert matrix.rows == [[1.0, 1.0]]


def test_average_retention_curve(cohort_orders):
    matrix = customers.cohort_retention(cohort_orders)
    assert customers.average_retention_curve(matrix) == [1.0, 0.5, 0.0, 0.5]


def test_average_retention_curve_empty():
    assert customers.average_retention_curve(customers.RetentionMatrix(mode="active")) == []


def test_monthly_retention_rate(cohort_orders):
    assert customers.monthly_retention_rate(cohort_orders) == 0.3333


def test_monthly_retention_rate_empty():
    assert customers.monthly_retention_rate([]) == 0.0


def test_generated_matrix_shape(medium_dataset):
    matrix = customers.cohort_retention(medium_dataset.orders)
    assert len(matrix.cohorts) == 12
    widths = [len(row) for row in matrix.rows]
    assert widths == list(range(12, 0, -1))
    assert all(row[0] == 1.0 for row in matrix.rows)


def test_generated_rolling_dominates_active(medium_dataset):
    active = customers.cohort_retention(medium_dataset.orders, "active")
    rolling = customers.cohort_retention(medium_dataset.orders, "rolling")
    for a_row, r_row in zip(active.rows, rolling.rows, strict=True):
        assert all(r >= a for a, r in zip(a_row, r_row, strict=True))
