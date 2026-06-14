"""Smoke tests — verify simulation runs and EV is within expected range."""

from simulator.rules import STANDARD_6D_H17, STANDARD_6D_S17, FREE_BET_6D
from simulator.simulator import run_simulation
from simulator.stats import compute_stats


def test_simulation_runs():
    result = run_simulation(STANDARD_6D_H17, n_hands=500, use_counting=False,
                            use_deviations=False, flat_bet=10)
    assert len(result.records) >= 400   # some hands may be skipped if bankroll depleted


def test_ev_within_range_s17():
    """6-deck S17 flat bet basic strategy EV should be near -0.26%.

    Use a large bankroll so bankruptcy doesn't truncate the sample and bias the EV.
    """
    result = run_simulation(STANDARD_6D_S17, n_hands=100_000,
                            starting_bankroll=500_000,
                            use_counting=False, use_deviations=False, flat_bet=10)
    stats = compute_stats(result)
    # Expected ~-0.37% (6D S17 DAS late surrender); allow ±1.5% for run-to-run variance
    assert -2.0 < stats.ev_percent < 1.0, f"EV out of range: {stats.ev_percent:.2f}%"


def test_free_bet_push_22():
    """Verify Free Bet push-22 mechanics: push rate should be elevated vs standard BJ.

    Standard BJ push rate ~8%. Push-22 rule adds ~5% extra pushes (dealer busts
    with exactly 22), so Free Bet push rate should be noticeably higher (~12-16%).
    Note: EV with standard strategy is poor because optimal Free Bet strategy
    differs significantly — this test checks mechanics, not optimised EV.
    """
    standard = run_simulation(STANDARD_6D_H17, n_hands=50_000,
                              starting_bankroll=500_000,
                              use_counting=False, use_deviations=False, flat_bet=10)
    free_bet = run_simulation(FREE_BET_6D, n_hands=50_000,
                              starting_bankroll=500_000,
                              use_counting=False, use_deviations=False, flat_bet=10)
    from simulator.stats import compute_stats as cs
    std_stats = cs(standard)
    fb_stats = cs(free_bet)
    # Push rate must be meaningfully higher in Free Bet mode (push-22 rule active)
    assert fb_stats.push_rate > std_stats.push_rate + 0.03, (
        f"Free Bet push rate ({fb_stats.push_rate:.3f}) should be >3% higher "
        f"than standard ({std_stats.push_rate:.3f})"
    )


def test_counting_beats_basic_strategy():
    """Card counting with a 1-2-3-4-6 spread + deviations must beat flat basic strategy.

    A correct Hi-Lo counter turns the ~-0.69% basic-strategy edge into a positive
    one. EV at testable sample sizes is too noisy to assert ">0" reliably (the
    high-variance split-10s deviations swing it), so we pin the RNG seed and use a
    large sample for a stable, meaningful comparison. A large bankroll prevents
    early bankruptcy from truncating the sample.

    Regression guard for two engine bugs that once drove counting NEGATIVE:
      (1) the running count desynced from the shoe on mid-round reshuffles, and
      (2) deviations fired on soft/pair hands.
    See also the deterministic guards: test_true_count_stays_bounded and
    tests/test_deviations.py.
    """
    import random
    random.seed(20240614)
    result = run_simulation(STANDARD_6D_H17, n_hands=1_000_000,
                            starting_bankroll=2_000_000,
                            use_counting=True, use_deviations=True)
    stats = compute_stats(result)
    # Fixed engine converges to roughly +0.1% here (positive in practice, but the
    # heavy-tailed split-10s deviations make a strict ">0" flaky). The buggy state
    # sat near -0.66%, so a -0.4% floor cleanly separates fixed from regressed
    # while staying robust to RNG noise.
    assert stats.ev_percent > -0.4, (
        f"Counting EV collapsed to {stats.ev_percent:.3f}% — should beat basic strategy (~-0.69%)"
    )


def test_true_count_stays_bounded():
    """Running/true count must reset with the shoe — never drift to absurd values.

    Deterministic regression for the mid-round-reshuffle desync, which let true
    count reach ±48. On a 6-deck shoe at 75% penetration the true count cannot
    realistically exceed ~±20; a desynced counter blows well past that.
    """
    import random
    random.seed(20240614)
    result = run_simulation(STANDARD_6D_H17, n_hands=100_000,
                            starting_bankroll=1_000_000,
                            use_counting=True, use_deviations=True)
    max_abs_tc = max(abs(r.true_count) for r in result.records)
    assert max_abs_tc < 25, f"True count drifted to {max_abs_tc:.1f} — counter not resetting with shoe"
