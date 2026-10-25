from __future__ import annotations

import itertools

import pytest

from app.metrics import customers


@pytest.mark.parametrize(
    ("r", "f", "m", "segment"),
    [
        (5, 5, 5, "Champions"),
        (4, 4, 4, "Champions"),
        (5, 4, 5, "Champions"),
        (4, 4, 3, "Loyal"),
        (5, 5, 1, "Loyal"),
        (3, 3, 1, "Loyal"),
        (3, 5, 5, "Loyal"),
        (4, 3, 5, "Loyal"),
        (5, 1, 1, "New"),
        (5, 1, 5, "New"),
        (5, 2, 3, "Promising"),
        (4, 1, 1, "Promising"),
        (4, 2, 5, "Promising"),
        (2, 5, 5, "Can't Lose Them"),
        (1, 4, 1, "Can't Lose Them"),
        (2, 3, 3, "At Risk"),
        (1, 3, 5, "At Risk"),
        (3, 2, 2, "Needs Attention"),
        (3, 1, 5, "Needs Attention"),
        (2, 2, 2, "Hibernating"),
        (2, 1, 1, "Hibernating"),
        (1, 2, 4, "Lost"),
        (1, 1, 1, "Lost"),
    ],
)
def test_rfm_segment_rules(r, f, m, segment):
    assert customers.rfm_segment(r, f, m) == segment


@pytest.mark.parametrize(("r", "f", "m"), [(0, 1, 1), (6, 1, 1), (1, 0, 1), (1, 6, 1), (1, 1, 0), (1, 1, 6)])
def test_rfm_segment_rejects_out_of_range_scores(r, f, m):
    with pytest.raises(ValueError, match=r"score must be within 1\.\.5"):
        customers.rfm_segment(r, f, m)


def test_every_score_combination_maps_to_a_known_segment():
    seen = {customers.rfm_segment(r, f, m) for r, f, m in itertools.product(range(1, 6), repeat=3)}
    assert seen == set(customers.SEGMENTS)


def test_monetary_only_matters_for_champions():
    for r, f in itertools.product(range(1, 6), repeat=2):
        segments = {customers.rfm_segment(r, f, m) for m in range(1, 6)}
        if r >= 4 and f >= 4:
            assert segments == {"Champions", "Loyal"}
        else:
            assert len(segments) == 1


def test_segment_population_on_generated_data(medium_dataset, as_of):
    counts = customers.segment_counts(customers.rfm_scores(medium_dataset.orders, as_of))
    populated = [name for name, count in counts.items() if count > 0]
    assert len(populated) >= 7
    assert counts["Champions"] > 0
    assert counts["Lost"] > 0
