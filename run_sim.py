import random
from simulator.rules import STANDARD_6D_H17
from simulator.simulator import run_simulation
from simulator.stats import compute_stats

random.seed(690)
result = run_simulation(
    STANDARD_6D_H17,
    n_hands=100_000,
    starting_bankroll=10_000_000,
    use_counting=False,
    use_deviations=False,
    flat_bet=10,
)
s = compute_stats(result)

print(f"6D H17 DAS Late Surrender — Basic Strategy — 100,000 hands")
print(f"")
print(f"  EV:              {s.ev_percent:+.3f}%")
print(f"  Total wagered:   ${s.total_wagered:,.0f}")
print(f"  Total net:       ${s.total_net:+,.0f}")
print(f"  Win rate:        {s.win_rate*100:.2f}%")
print(f"  Loss rate:       {s.loss_rate*100:.2f}%")
print(f"  Push rate:       {s.push_rate*100:.2f}%")
print(f"  Blackjack rate:  {s.blackjack_rate*100:.2f}%")
print(f"  Surrender rate:  {s.surrender_rate*100:.2f}%")
print(f"  Std dev/hand:    ${s.std_dev_per_hand:.2f}")
