"""Precise, simulation-based Risk of Ruin (bootstrap) — optional alternative.

The dashboard and :func:`simulator.analysis.analyze_spread` report RoR with the
fast analytic closed form ``exp(-2*mu*B/sigma^2)``. This module keeps the
*precise* simulation approach available for when you want a distribution-faithful
estimate instead of the closed-form approximation.

It estimates lifetime Risk of Ruin empirically: resample the real per-round
results a simulation produced (preserving the fat tails from splits/doubles) and
walk each trial's bankroll until it busts (<= 0) or "escapes" to a bankroll high
enough that its remaining ruin probability is negligible. RoR is busts / trials.
Trials still running at the step cap contribute their residual analytic ruin
probability, so the estimate isn't biased by the cap. It reproduces the analytic
formula to within ~1% (validated against both the formula and direct
card-dealing simulations).

Requires numpy.

Example
-------
    from simulator import RuleSet
    from simulator.counting import BetRamp
    from simulator.ruin_simulation import precise_risk_of_ruin

    ror = precise_risk_of_ruin(RuleSet(), BetRamp(unit=25.0), bankroll=10_000)
    print(f"{ror*100:.2f}%")
"""

import math
import random
from collections import defaultdict
from typing import Optional, Tuple

import numpy as np

from .rules import RuleSet
from .counting import BetRamp
from .simulator import run_simulation


def build_round_net_pool(
    rules: RuleSet,
    bet_ramp: BetRamp,
    n_hands: int = 1_000_000,
    use_deviations: bool = True,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, float, float]:
    """Run one large no-bust simulation; return (per_round_nets, mean, variance).

    A huge starting bankroll prevents bankruptcy from truncating the sample, so
    the per-round net distribution is unbiased.
    """
    if seed is not None:
        random.seed(seed)
    result = run_simulation(
        rules, n_hands=n_hands, starting_bankroll=10 ** 12,
        bet_ramp=bet_ramp, use_counting=True, use_deviations=use_deviations,
    )
    by_round = defaultdict(float)
    for rec in result.records:
        by_round[rec.hand_num] += rec.net
    pool = np.fromiter(by_round.values(), dtype=float)
    mu = float(pool.mean()) if pool.size else 0.0
    var = float(pool.var()) if pool.size else 0.0
    return pool, mu, var


def simulate_ruin(
    pool: np.ndarray, bankroll: float, mu: float, var: float,
    n_trials: int = 5000, escape_eps: float = 0.005,
    chunk: int = 6000, max_steps: int = 40_000,
    seed: Optional[int] = None,
) -> float:
    """Lifetime Risk of Ruin by bootstrap over a pool of real per-round results.

    Args:
        pool: Per-round net outcomes to resample from.
        bankroll: Starting bankroll.
        mu: Target per-round edge ($). The pool is shifted to this mean, so you
            can evaluate RoR at a different edge (e.g. an EV confidence bound)
            while keeping the real shape/variance.
        var: Per-round variance ($^2).
        n_trials: Number of independent bankroll walks.
        escape_eps: A trial "escapes" once its remaining ruin probability drops
            below this (derived from exp(-2*mu*b/var)).
        chunk: Steps simulated per vectorised batch.
        max_steps: Cap on steps per trial; survivors get a residual analytic tail.
    """
    if pool.size == 0 or var <= 0:
        return 1.0 if mu <= 0 else 0.0
    if mu <= 0:
        return 1.0  # a non-positive edge means eventual ruin is certain

    # Shift the pool to the target edge, preserving its shape and variance.
    pool = pool - pool.mean() + mu

    escape_level = var / (2 * mu) * math.log(1 / escape_eps)
    if bankroll >= escape_level:
        return math.exp(-2 * mu * bankroll / var)

    rng = np.random.default_rng(seed)
    bank = np.full(n_trials, float(bankroll))
    active = np.ones(n_trials, dtype=bool)
    ruined = np.zeros(n_trials, dtype=bool)

    steps = 0
    while active.any() and steps < max_steps:
        idx = np.nonzero(active)[0]
        draws = rng.choice(pool, size=(idx.size, chunk))
        cum = bank[idx][:, None] + np.cumsum(draws, axis=1)
        ruin_hit = cum <= 0
        esc_hit = cum >= escape_level
        any_ruin = ruin_hit.any(axis=1)
        any_esc = esc_hit.any(axis=1)
        # First-passage: whichever of ruin/escape happens first within the chunk.
        first_ruin = np.where(any_ruin, ruin_hit.argmax(axis=1), chunk + 1)
        first_esc = np.where(any_esc, esc_hit.argmax(axis=1), chunk + 1)
        became_ruined = any_ruin & (first_ruin <= first_esc)
        became_escaped = any_esc & (first_esc < first_ruin)
        ruined[idx[became_ruined]] = True
        active[idx[became_ruined | became_escaped]] = False
        still = ~(became_ruined | became_escaped)
        bank[idx[still]] = cum[still, -1]
        steps += chunk

    # Trials still alive at the cap: add their residual (analytic) ruin probability.
    residual = float(np.exp(-2 * mu * bank[active] / var).sum()) if active.any() else 0.0
    return (int(ruined.sum()) + residual) / n_trials


def precise_risk_of_ruin(
    rules: RuleSet,
    bet_ramp: BetRamp,
    bankroll: float = 10_000.0,
    n_hands: int = 1_000_000,
    use_deviations: bool = True,
    n_trials: int = 5000,
    seed: Optional[int] = None,
) -> float:
    """Convenience: build a per-round pool from a fresh sim, then bootstrap RoR."""
    pool, mu, var = build_round_net_pool(
        rules, bet_ramp, n_hands=n_hands, use_deviations=use_deviations, seed=seed,
    )
    return simulate_ruin(pool, bankroll, mu, var, n_trials=n_trials, seed=seed)
