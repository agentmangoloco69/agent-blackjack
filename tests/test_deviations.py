"""Deterministic guards for deviation lookup (Illustrious 18 / Fab 4).

The Illustrious 18 / Fab 4 entries are all HARD-total deviations. A lookup bug
once applied them to soft hands and pairs by matching on raw hand value — e.g.
standing on a soft 16 (A,5) or a pair of 6s (12) — which cratered EV on the big
high-count bets. These tests pin the correct gating behaviour.
"""

from simulator.deviations import get_deviation
from simulator.strategy import Action


def test_hard_16_vs_10_stands_at_high_count():
    # Canonical I18: stand 16 v 10 at TC >= 0.
    assert get_deviation(16, 10, true_count=2.0) == Action.STAND
    # Below threshold: no deviation (basic strategy decides).
    assert get_deviation(16, 10, true_count=-1.0) is None


def test_soft_hands_never_deviate():
    # A soft 16 (A,5) must NOT match the hard-16 stand deviation.
    assert get_deviation(16, 10, true_count=5.0, is_soft=True) is None
    # A soft 15 likewise.
    assert get_deviation(15, 10, true_count=5.0, is_soft=True) is None


def test_pairs_defer_to_basic_strategy():
    # A pair of 6s (value 12) must NOT trigger the hard "stand 12 v 4" deviation —
    # basic strategy should be left to split it.
    assert get_deviation(12, 4, true_count=5.0, is_pair=True) is None
    # But the same hard total as a non-pair DOES deviate.
    assert get_deviation(12, 4, true_count=5.0, is_pair=False) == Action.STAND


def test_split_tens_deviation_requires_pair_of_tens():
    # Split 10s v 6 at TC >= 4 — only when it's actually a pair of tens.
    assert get_deviation(20, 6, true_count=4.0, is_pair_of_tens=True) == Action.SPLIT
    # A 20 that isn't a pair of tens (e.g. it just shouldn't fire) stays None.
    assert get_deviation(20, 6, true_count=4.0, is_pair_of_tens=False) is None


def test_negative_direction_deviation():
    # 12 v 5: stand normally, but HIT at TC <= -2 ('-' direction).
    assert get_deviation(12, 5, true_count=-3.0) == Action.HIT
    assert get_deviation(12, 5, true_count=0.0) is None
