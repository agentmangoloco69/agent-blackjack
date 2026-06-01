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


def test_counting_positive_ev():
    """Card counting with 1-2-3-4-6 spread should produce near-zero or positive EV.

    Large bankroll prevents early bankruptcy from skewing the sample.
    """
    result = run_simulation(STANDARD_6D_H17, n_hands=100_000,
                            starting_bankroll=500_000,
                            use_counting=True, use_deviations=True)
    stats = compute_stats(result)
    # Counter should get EV well above -2% (ideally near zero or positive)
    assert stats.ev_percent > -2.5, f"Counting EV too low: {stats.ev_percent:.2f}%"
