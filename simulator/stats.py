"""Statistics calculations from simulation results."""

import math
from dataclasses import dataclass
from typing import List
from .simulator import SimResult, HandRecord


@dataclass
class SimStats:
    n_hands: int
    total_wagered: float
    total_net: float
    ev_percent: float           # expected value as % of amount wagered
    win_rate: float             # fraction of hands won
    loss_rate: float
    push_rate: float
    blackjack_rate: float
    surrender_rate: float
    std_dev_per_hand: float
    risk_of_ruin: float         # approximate probability of going broke
    final_bankroll: float
    min_bankroll: float
    max_bankroll: float


def compute_stats(result: SimResult) -> SimStats:
    records: List[HandRecord] = result.records
    if not records:
        return SimStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                        result.starting_bankroll, result.starting_bankroll, result.starting_bankroll)

    n = len(records)
    total_wagered = sum(r.bet for r in records)
    total_net = sum(r.net for r in records)
    ev_percent = (total_net / total_wagered * 100) if total_wagered else 0

    outcomes = [r.outcome for r in records]
    win_rate = outcomes.count('win') / n
    loss_rate = outcomes.count('loss') / n
    push_rate = outcomes.count('push') / n
    bj_rate = outcomes.count('blackjack') / n
    sur_rate = outcomes.count('surrender') / n

    nets = [r.net for r in records]
    mean_net = total_net / n
    variance = sum((x - mean_net) ** 2 for x in nets) / n
    std_dev = math.sqrt(variance)

    bankrolls = [r.bankroll for r in records]
    final_bankroll = bankrolls[-1]
    min_bankroll = min(bankrolls)
    max_bankroll = max(bankrolls)

    ror = _risk_of_ruin(result.starting_bankroll, mean_net, std_dev)

    return SimStats(
        n_hands=n,
        total_wagered=total_wagered,
        total_net=total_net,
        ev_percent=ev_percent,
        win_rate=win_rate,
        loss_rate=loss_rate,
        push_rate=push_rate,
        blackjack_rate=bj_rate,
        surrender_rate=sur_rate,
        std_dev_per_hand=std_dev,
        risk_of_ruin=ror,
        final_bankroll=final_bankroll,
        min_bankroll=min_bankroll,
        max_bankroll=max_bankroll,
    )


def _risk_of_ruin(bankroll: float, mean_net: float, std_dev: float) -> float:
    """
    Approximation using the gambler's ruin formula for normally distributed outcomes.
    RoR ≈ exp(-2 * bankroll * |EV| / variance)
    Only meaningful when EV is negative (house edge) or marginal positive.
    """
    if std_dev == 0:
        return 0.0
    variance = std_dev ** 2
    if mean_net >= 0:
        # Positive EV — RoR is near zero but not exactly (use conservative bound)
        return max(0.0, math.exp(-2 * bankroll * abs(mean_net) / variance))
    return math.exp(2 * bankroll * mean_net / variance)
