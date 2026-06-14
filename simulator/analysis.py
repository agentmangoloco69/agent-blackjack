"""Multi-run analysis layer for bet-spread evaluation.

Sits on top of the single-run :func:`run_simulation`. Runs many independent
simulations of the same game/spread to produce:

  * Simulation-based Risk of Ruin (fraction of runs whose bankroll hits <= 0)
  * Expected value (per hand %, per hand $, per hour $)
  * N0 (hands needed for cumulative EV to equal one standard deviation)
  * Percentile bankroll bands (median + 10th/90th) for a trajectory chart

The single-run engine is left untouched — this module only orchestrates it.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .rules import RuleSet
from .counting import BetRamp
from .simulator import run_simulation, SimResult


# Hard cap on total work to keep the UI responsive: n_runs * n_hands.
MAX_TOTAL_HANDS = 1_000 * 100_000


def clamp_runs(n_runs: int, n_hands: int) -> int:
    """Reduce n_runs so that n_runs * n_hands stays within MAX_TOTAL_HANDS."""
    if n_hands > 0 and n_runs * n_hands > MAX_TOTAL_HANDS:
        return max(1, MAX_TOTAL_HANDS // n_hands)
    return n_runs


@dataclass
class SpreadAnalysis:
    """Aggregated results across many simulation runs."""
    n_runs: int
    n_hands: int
    starting_bankroll: float

    # Expected value
    ev_per_hand_dollars: float   # mean net $ per round
    ev_percent: float            # mean net as % of total wagered
    ev_per_hour: float           # ev_per_hand_dollars * hands_per_hour
    hands_per_hour: int

    # Risk
    risk_of_ruin: float          # fraction of runs that went broke (0..1)
    n0: float                    # hands for cumulative EV == 1 std dev
    std_dev_per_hand: float      # std dev of per-round net ($)

    # Percentile bankroll bands (all same length == len(hand_axis))
    hand_axis: List[int] = field(default_factory=list)
    pct_median: List[float] = field(default_factory=list)
    pct_low: List[float] = field(default_factory=list)    # 10th percentile
    pct_high: List[float] = field(default_factory=list)    # 90th percentile


def _round_series(result: SimResult, n_hands: int, starting_bankroll: float
                  ) -> Tuple[List[float], List[float], List[float]]:
    """Collapse per-hand records into per-round series for one run.

    Splits produce several records sharing one ``hand_num``; we sum their nets
    and wagers so each round contributes a single data point.

    Returns ``(round_nets, round_wagers, bankroll_by_round)`` where
    ``bankroll_by_round`` always has length ``n_hands`` (padded after ruin /
    early stop with the final bankroll, which is <= 0 on a ruined run).
    """
    round_nets: List[float] = []
    round_wagers: List[float] = []
    bankroll_by_round: List[float] = []

    cur_hand_num = None
    cur_net = 0.0
    cur_wager = 0.0
    cur_bankroll = starting_bankroll

    def flush():
        if cur_hand_num is not None:
            round_nets.append(cur_net)
            round_wagers.append(cur_wager)
            bankroll_by_round.append(cur_bankroll)

    for rec in result.records:
        if rec.hand_num != cur_hand_num:
            flush()
            cur_hand_num = rec.hand_num
            cur_net = 0.0
            cur_wager = 0.0
        cur_net += rec.net
        cur_wager += rec.bet
        cur_bankroll = rec.bankroll
    flush()

    # Pad the trajectory out to n_hands so every run aligns on the same x-axis.
    if bankroll_by_round:
        last = bankroll_by_round[-1]
    else:
        last = starting_bankroll
    while len(bankroll_by_round) < n_hands:
        bankroll_by_round.append(last)

    return round_nets, round_wagers, bankroll_by_round


def _percentile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolation percentile of an already-sorted list. q in [0,1]."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def analyze_spread(
    rules: RuleSet,
    bet_ramp: BetRamp,
    starting_bankroll: float = 10_000.0,
    n_hands: int = 5_000,
    n_runs: int = 300,
    hands_per_hour: int = 100,
    use_deviations: bool = True,
    chart_points: int = 200,
) -> SpreadAnalysis:
    """Run ``n_runs`` independent simulations and aggregate the results.

    Args:
        rules: Casino rule configuration.
        bet_ramp: The bet spread to evaluate.
        starting_bankroll: Bankroll each run starts with.
        n_hands: Hands (rounds) per run.
        n_runs: Number of independent runs.
        hands_per_hour: Used to convert per-hand EV into hourly EV.
        use_deviations: Whether to apply Illustrious 18 / Fab 4 deviations.
        chart_points: Number of x-axis samples in the percentile bands.
    """
    # Clamp total work.
    n_runs = clamp_runs(n_runs, n_hands)

    ruined = 0
    # Streaming accumulators for per-round net (EV / variance).
    net_sum = 0.0
    net_sumsq = 0.0
    net_count = 0
    wager_sum = 0.0

    # Matrix of bankroll trajectories: n_runs rows x n_hands cols.
    trajectories: List[List[float]] = []

    for _ in range(n_runs):
        result = run_simulation(
            rules=rules,
            n_hands=n_hands,
            starting_bankroll=starting_bankroll,
            bet_ramp=bet_ramp,
            use_counting=True,
            use_deviations=use_deviations,
        )
        round_nets, round_wagers, bankroll_by_round = _round_series(
            result, n_hands, starting_bankroll
        )

        for v in round_nets:
            net_sum += v
            net_sumsq += v * v
        net_count += len(round_nets)
        wager_sum += sum(round_wagers)

        if min(bankroll_by_round) <= 0:
            ruined += 1

        trajectories.append(bankroll_by_round)

    # --- EV / variance ---
    if net_count:
        ev_per_hand = net_sum / net_count
        variance = max(0.0, net_sumsq / net_count - ev_per_hand ** 2)
        std_dev = variance ** 0.5
    else:
        ev_per_hand = 0.0
        std_dev = 0.0
    ev_percent = (net_sum / wager_sum * 100) if wager_sum else 0.0
    ev_per_hour = ev_per_hand * hands_per_hour

    # N0 = (std / ev)^2  — hands for cumulative EV to equal one std dev.
    if ev_per_hand > 0 and std_dev > 0:
        n0 = (std_dev / ev_per_hand) ** 2
    else:
        n0 = float('inf')

    risk_of_ruin = ruined / n_runs if n_runs else 0.0

    # --- Percentile bands (downsample x-axis to chart_points) ---
    hand_axis: List[int] = []
    pct_median: List[float] = []
    pct_low: List[float] = []
    pct_high: List[float] = []

    if trajectories:
        step = max(1, n_hands // chart_points)
        sample_idx = list(range(0, n_hands, step))
        if sample_idx and sample_idx[-1] != n_hands - 1:
            sample_idx.append(n_hands - 1)

        for i in sample_idx:
            col = sorted(t[i] for t in trajectories)
            hand_axis.append(i + 1)
            pct_median.append(_percentile(col, 0.5))
            pct_low.append(_percentile(col, 0.10))
            pct_high.append(_percentile(col, 0.90))

    return SpreadAnalysis(
        n_runs=n_runs,
        n_hands=n_hands,
        starting_bankroll=starting_bankroll,
        ev_per_hand_dollars=ev_per_hand,
        ev_percent=ev_percent,
        ev_per_hour=ev_per_hour,
        hands_per_hour=hands_per_hour,
        risk_of_ruin=risk_of_ruin,
        n0=n0,
        std_dev_per_hand=std_dev,
        hand_axis=hand_axis,
        pct_median=pct_median,
        pct_low=pct_low,
        pct_high=pct_high,
    )
