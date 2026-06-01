"""
2M-hand EV check on the H17 baseline, compared to Wong's published house edge.

Baseline ruleset (matches RuleSet defaults):
  6 decks, dealer Hits Soft 17 (H17), Double After Split allowed,
  Late Surrender, Blackjack pays 3:2, dealer peeks (US rules).

Stanford Wong (Professional Blackjack) / standard combinatorial analysis put
the house edge for 6-deck H17 DAS + late surrender at about -0.49% to -0.55%.
(H17 DAS no-surrender is ~-0.62%; late surrender returns ~+0.08%.)
"""
import random
from simulator.rules import RuleSet
from simulator.simulator import run_simulation
from simulator.stats import compute_stats

RULES = RuleSet(num_decks=6, dealer_hits_soft_17=True,
                surrender="late", double_after_split=True)

HANDS_PER_RUN = 200_000
N_RUNS        = 10            # 10 x 200k = 2,000,000 hands
BANKROLL      = 50_000_000    # large enough to never go broke
SEEDS         = [1000 + i * 7 for i in range(N_RUNS)]

WONG_EXPECTED = -0.51   # mid-point of accepted range for 6D H17 DAS LS

print("=" * 60)
print("  2,000,000-HAND EV CHECK  —  6D H17 DAS Late Surrender")
print("=" * 60)
print(f"  Pure basic strategy (no counting, no deviations)")
print(f"  {N_RUNS} runs x {HANDS_PER_RUN:,} hands")
print()

evs = []
for seed in SEEDS:
    random.seed(seed)
    result = run_simulation(RULES, n_hands=HANDS_PER_RUN, starting_bankroll=BANKROLL,
                            use_counting=False, use_deviations=False, flat_bet=10)
    s = compute_stats(result)
    evs.append(s.ev_percent)
    print(f"  seed {seed:>5}:  EV = {s.ev_percent:+.4f}%")

avg = sum(evs) / len(evs)
var = sum((e - avg) ** 2 for e in evs) / len(evs)
std = var ** 0.5
stderr = std / (len(evs) ** 0.5)

print()
print("-" * 60)
print(f"  Average EV over 2M hands:  {avg:+.4f}%")
print(f"  Std dev across runs:        {std:.4f}%")
print(f"  Standard error of mean:    ±{stderr:.4f}%")
print(f"  95% confidence interval:   [{avg - 1.96*stderr:+.4f}%, {avg + 1.96*stderr:+.4f}%]")
print()
print(f"  Wong / reference expected:  {WONG_EXPECTED:+.2f}%")
print(f"  Difference from reference:  {avg - WONG_EXPECTED:+.4f}%")
print("-" * 60)

if abs(avg - WONG_EXPECTED) < 0.10:
    print("  RESULT: Within 0.10% of reference — EXCELLENT match.")
elif abs(avg - WONG_EXPECTED) < 0.20:
    print("  RESULT: Within 0.20% of reference — good, within sim noise.")
else:
    print("  RESULT: Gap exceeds 0.20% — investigate further.")
