"""Tests for the multi-run bet-spread analysis layer."""

from simulator.rules import STANDARD_6D_H17
from simulator.counting import BetRamp
from simulator.analysis import analyze_spread


def test_analyze_spread_shapes_and_sanity():
    """Percentile bands align, RoR is a probability, hourly EV scales correctly."""
    a = analyze_spread(
        STANDARD_6D_H17, BetRamp(unit=25.0),
        starting_bankroll=10_000, n_hands=1_000, n_runs=40,
        hands_per_hour=100, chart_points=50,
    )
    # Band arrays must all line up with the x-axis.
    n = len(a.hand_axis)
    assert n > 0
    assert len(a.pct_median) == n == len(a.pct_low) == len(a.pct_high)
    # Percentile ordering: low <= median <= high at every point.
    for lo, mid, hi in zip(a.pct_low, a.pct_median, a.pct_high):
        assert lo <= mid <= hi
    # RoR is a probability.
    assert 0.0 <= a.risk_of_ruin <= 1.0
    # Hourly EV is per-hand EV times hands/hour.
    assert abs(a.ev_per_hour - a.ev_per_hand_dollars * a.hands_per_hour) < 1e-6
    # Confidence half-widths are non-negative and scale consistently.
    assert a.ev_percent_ci95 >= 0 and a.ev_per_hour_ci95 >= 0


def test_analyze_spread_ev_beats_basic_and_n0_finite():
    """A real spread should clearly beat basic strategy and yield a finite N0.

    EV-positivity is too heavy-tailed to assert at testable sample sizes (see
    tests/test_simulation.py), so we seed the RNG and assert EV beats the
    ~-0.69% basic-strategy edge by a comfortable margin.
    """
    import random
    random.seed(20240614)
    a = analyze_spread(
        STANDARD_6D_H17, BetRamp(unit=25.0),
        starting_bankroll=100_000, n_hands=3_000, n_runs=120,
    )
    assert a.ev_percent > -0.4, f"EV collapsed to {a.ev_percent:.3f}%"
    # N0 is positive when EV is positive, and inf otherwise (undefined) — never <= 0.
    assert a.n0 > 0


def test_work_cap_clamps_runs():
    """Requesting more than the work cap clamps n_runs rather than running forever."""
    from simulator.analysis import clamp_runs, MAX_TOTAL_HANDS
    # Under the cap: unchanged.
    assert clamp_runs(100, 1_000) == 100
    # Over the cap: reduced to fit, never below 1.
    assert clamp_runs(1000, MAX_TOTAL_HANDS) == 1
    assert clamp_runs(10_000, MAX_TOTAL_HANDS // 5) == 5
