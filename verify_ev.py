"""
EV verification across rulesets, using multiple independent seeds to avoid
the fixed-seed problem: when two sims use the same seed but dealer behavior
differs (H17 vs S17), the shoe diverges after the first soft-17 hand —
subsequent cards differ, so the delta is noise, not a true measurement.

Solution: run N_RUNS independent trials per ruleset, average the EVs.
"""
import random
from simulator.rules import RuleSet
from simulator.simulator import run_simulation
from simulator.stats import compute_stats

N_HANDS  = 200_000      # hands per run
N_RUNS   = 10           # independent runs per ruleset
BR       = 50_000_000   # large enough to avoid bankruptcy

configs = {
    '6D H17 DAS L-surr':     RuleSet(num_decks=6, dealer_hits_soft_17=True,  surrender='late',  double_after_split=True),
    '6D S17 DAS L-surr':     RuleSet(num_decks=6, dealer_hits_soft_17=False, surrender='late',  double_after_split=True),
    '6D H17 DAS no-surr':    RuleSet(num_decks=6, dealer_hits_soft_17=True,  surrender='none',  double_after_split=True),
    '6D H17 no-DAS no-surr': RuleSet(num_decks=6, dealer_hits_soft_17=True,  surrender='none',  double_after_split=False),
    '2D S17 DAS L-surr':     RuleSet(num_decks=2, dealer_hits_soft_17=False, surrender='late',  double_after_split=True),
}

expected = {
    '6D H17 DAS L-surr':     -0.44,
    '6D S17 DAS L-surr':     -0.28,
    '6D H17 DAS no-surr':    -0.58,
    '6D H17 no-DAS no-surr': -0.65,
    '2D S17 DAS L-surr':     -0.19,
}

print(f"Running {N_RUNS} x {N_HANDS:,} hands per ruleset ({N_RUNS * N_HANDS:,} total per config)")
print()
print(f"{'Ruleset':<28} {'Avg EV%':>8}  {'Expected':>9}  {'Gap':>7}  {'Std dev EV':>10}")
print('-' * 70)

avg_evs = {}
for name, rules in configs.items():
    evs = []
    for run in range(N_RUNS):
        seed = 1000 + run * 7  # distinct seeds per run
        random.seed(seed)
        result = run_simulation(rules, n_hands=N_HANDS, starting_bankroll=BR,
                                use_counting=False, use_deviations=False, flat_bet=10)
        s = compute_stats(result)
        evs.append(s.ev_percent)
    avg = sum(evs) / N_RUNS
    std = (sum((e - avg) ** 2 for e in evs) / N_RUNS) ** 0.5
    avg_evs[name] = avg
    exp = expected[name]
    print(f"{name:<28} {avg:>7.3f}%  {exp:>8.2f}%  {avg - exp:>+6.3f}%  {std:>9.3f}%")

print()
print("Rule-change deltas (simulated vs expected):")
h17  = avg_evs['6D H17 DAS L-surr']
s17  = avg_evs['6D S17 DAS L-surr']
ns   = avg_evs['6D H17 DAS no-surr']
ndas = avg_evs['6D H17 no-DAS no-surr']
d2   = avg_evs['2D S17 DAS L-surr']

print(f"  H17 vs S17 (DAS, L-surr):   {h17-s17:+.3f}%   (expected ~-0.16%)")
print(f"  Surrender on vs off (H17):   {h17-ns:+.3f}%   (expected ~-0.07%)")
print(f"  DAS on vs off (no-surr):     {ns-ndas:+.3f}%   (expected ~+0.14%)")
print(f"  6D vs 2D (S17 DAS L-surr):  {s17-d2:+.3f}%   (expected ~-0.09%)")
