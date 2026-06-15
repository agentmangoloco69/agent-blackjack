"""The optional bootstrap RoR must reproduce the analytic formula.

Uses a synthetic per-round pool (fast — no card dealing) so the bootstrap can be
checked against the closed form exp(-2*mu*B/sigma^2) it is meant to match.
"""

import math
import numpy as np
import pytest

from simulator.ruin_simulation import simulate_ruin


def _analytic(B, mu, var):
    return math.exp(-2 * mu * B / var) if mu > 0 else 1.0


@pytest.mark.parametrize("bankroll", [5_000, 10_000, 20_000])
def test_bootstrap_matches_analytic(bankroll):
    mu, sigma = 0.12, 65.0
    var = sigma ** 2
    rng = np.random.default_rng(0)
    pool = rng.normal(mu, sigma, size=200_000)
    boot = simulate_ruin(pool, bankroll, mu, var, n_trials=4000, seed=1)
    analytic = _analytic(bankroll, mu, var)
    assert abs(boot - analytic) < 0.03, f"boot {boot:.3f} vs analytic {analytic:.3f}"


def test_non_positive_edge_is_certain_ruin():
    pool = np.zeros(1000)
    assert simulate_ruin(pool, 10_000, mu=0.0, var=4000.0) == 1.0
    assert simulate_ruin(pool, 10_000, mu=-0.05, var=4000.0) == 1.0
