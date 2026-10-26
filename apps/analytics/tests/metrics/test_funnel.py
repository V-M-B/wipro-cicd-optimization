from __future__ import annotations

import pytest

from app.generated.schemas import OrderStatus
from app.metrics import funnel
from tests.factories import make_order


def _orders(statuses):
    return [make_order(f"O{i}", status=s) for i, s in enumerate(statuses)]


def test_status_counts(tiny_orders):
    assert funnel.status_counts(tiny_orders) == {
        "CREATED": 1,
        "PAID": 1,
        "SHIPPED": 1,
        "DELIVERED": 4,
        "CANCELLED": 1,
    }


def test_status_counts_empty_has_all_keys():
    assert funnel.status_counts([]) == {s.value: 0 for s in OrderStatus}


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({"DELIVERED": 3}, {"CREATED": 3, "PAID": 3, "SHIPPED": 3, "DELIVERED": 3}),
        ({"CREATED": 2, "PAID": 1}, {"CREATED": 3, "PAID": 1, "SHIPPED": 0, "DELIVERED": 0}),
        ({"CANCELLED": 4}, {"CREATED": 4, "PAID": 0, "SHIPPED": 0, "DELIVERED": 0}),
        ({"SHIPPED": 2, "CANCELLED": 1}, {"CREATED": 3, "PAID": 2, "SHIPPED": 2, "DELIVERED": 0}),
        ({}, {"CREATED": 0, "PAID": 0, "SHIPPED": 0, "DELIVERED": 0}),
    ],
)
def test_stage_reach(counts, expected):
    assert funnel.stage_reach(counts) == expected


def test_funnel_tiny(tiny_orders):
    stages = funnel.funnel(tiny_orders)
    assert [(s.stage, s.reached, s.conversion_from_previous, s.conversion_from_start) for s in stages] == [
        ("CREATED", 8, 1.0, 1.0),
        ("PAID", 6, 0.75, 0.75),
        ("SHIPPED", 5, 0.8333, 0.625),
        ("DELIVERED", 4, 0.8, 0.5),
    ]


def test_funnel_empty():
    stages = funnel.funnel([])
    assert [s.reached for s in stages] == [0, 0, 0, 0]
    assert all(s.conversion_from_start == 0.0 for s in stages)
    assert funnel.bottleneck(stages) is None


@pytest.mark.parametrize(
    ("statuses", "expected_rate"),
    [
        (["CANCELLED", "DELIVERED"], 0.5),
        (["DELIVERED"] * 3, 0.0),
        (["CANCELLED"] * 2, 1.0),
        (["CREATED", "PAID", "SHIPPED", "CANCELLED"], 0.25),
        ([], 0.0),
    ],
)
def test_cancellation_rate(statuses, expected_rate):
    assert funnel.cancellation_rate(_orders(statuses)) == expected_rate


def test_cancellation_rate_tiny(tiny_orders):
    assert funnel.cancellation_rate(tiny_orders) == 0.125


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["CANCELLED", "DELIVERED"], "PAID"),
        (["DELIVERED", "PAID", "PAID"], "SHIPPED"),
        (["DELIVERED", "SHIPPED", "SHIPPED", "SHIPPED"], "DELIVERED"),
        (["DELIVERED", "DELIVERED"], "PAID"),  # all equal -> earliest stage
    ],
)
def test_bottleneck(statuses, expected):
    assert funnel.bottleneck(funnel.funnel(_orders(statuses))) == expected


def test_bottleneck_tiny(tiny_orders):
    assert funnel.bottleneck(funnel.funnel(tiny_orders)) == "PAID"


def test_funnel_by_region(tiny_orders, tiny_customers):
    result = funnel.funnel_by_region(tiny_orders, tiny_customers)
    assert {region: [s.reached for s in stages] for region, stages in result.items()} == {
        "EAST": [1, 1, 0, 0],
        "NORTH": [3, 3, 3, 2],
        "SOUTH": [2, 1, 1, 1],
        "UNKNOWN": [1, 1, 1, 1],
        "WEST": [1, 0, 0, 0],
    }


def test_overall_conversion_tiny(tiny_orders):
    # 8 orders reach CREATED, 4 are delivered
    assert funnel.overall_conversion(funnel.funnel(tiny_orders)) == 0.5


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], 0.0),
        ([OrderStatus.CANCELLED, OrderStatus.CANCELLED], 0.0),
        ([OrderStatus.DELIVERED, OrderStatus.DELIVERED, OrderStatus.SHIPPED], 0.6667),
    ],
)
def test_overall_conversion(statuses, expected):
    assert funnel.overall_conversion(funnel.funnel(_orders(statuses))) == expected


def test_overall_conversion_without_stages():
    assert funnel.overall_conversion([]) == 0.0


def test_cancellation_by_period(tiny_orders):
    assert funnel.cancellation_by_period(tiny_orders) == {"2025-01": 0.0, "2025-02": 0.3333, "2025-03": 0.0}


def test_cancellation_by_period_rejects_bad_granularity(tiny_orders):
    with pytest.raises(ValueError, match="granularity"):
        funnel.cancellation_by_period(tiny_orders, "hour")


def test_funnel_is_monotone_on_generated_data(medium_dataset):
    stages = funnel.funnel(medium_dataset.orders)
    reached = [s.reached for s in stages]
    assert reached == sorted(reached, reverse=True)
    assert reached[0] == len(medium_dataset.orders)
    assert stages[0].as_dict()["stage"] == "CREATED"


def test_generated_cancellation_rate_is_realistic(medium_dataset):
    assert 0.03 < funnel.cancellation_rate(medium_dataset.orders) < 0.15
