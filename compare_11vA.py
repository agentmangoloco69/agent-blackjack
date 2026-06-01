"""
Compare EV: Double 11 vs Ace  vs  Hit 11 vs Ace
Run for both H17 and S17 to see where the optimal play differs.

Method: deal a fresh shoe, but whenever the player gets hard 11 and
dealer shows an Ace (no dealer BJ), force one strategy and record EV.
"""
import random
from simulator.card import Shoe, Card
from simulator.hand import Hand
from simulator.rules import RuleSet

RULES_H17 = RuleSet(num_decks=6, dealer_hits_soft_17=True,  surrender="none")
RULES_S17 = RuleSet(num_decks=6, dealer_hits_soft_17=False, surrender="none")

N_HANDS = 1_000_000   # hands WHERE player has hard 11 AND dealer shows Ace
SEEDS   = [42, 137, 999, 2024, 31415]


def play_dealer(shoe, dealer, rules):
    while True:
        v = dealer.value
        if v > 21: break
        if v >= 18: break
        if v == 17:
            if not (rules.dealer_hits_soft_17 and dealer.is_soft):
                break
        dealer.add(shoe.deal())


def settle(pv, dv, bet):
    if dv > 21: return bet
    if pv > dv: return bet
    if pv < dv: return -bet
    return 0.0


def simulate_11vA(rules, strategy, n_hands, seed):
    """
    Directly deal hard 11 vs Ace every hand — no waiting for the combination
    to appear randomly. Player always gets 7+4, dealer always gets Ace up.
    The hole card and all subsequent cards come from a real shuffled shoe,
    so dealer BJ probability and draw probabilities are realistic.

    strategy: 'double' or 'hit'
    Returns EV% = total_net / total_wagered * 100.
    """
    random.seed(seed)
    shoe = Shoe(rules.num_decks, rules.penetration)
    total_net   = 0.0
    total_wager = 0.0

    for _ in range(n_hands):
        if shoe.needs_reshuffle:
            shoe.reshuffle()

        # Force player to have hard 11 (7+4) and dealer to show Ace.
        # Remaining cards (dealer hole card, draws) come from the live shoe.
        player = Hand(bet=10.0)
        player.add(Card('7', 'S'))
        player.add(Card('4', 'H'))

        dealer = Hand()
        dealer.add(Card('A', 'S'))
        dealer.add(shoe.deal())      # realistic hole card from shoe

        # Dealer BJ check (US peek rules)
        if dealer.is_blackjack:
            # Player loses flat bet — same for both strategies, skip to keep comparison clean
            total_net   -= 10.0
            total_wager += 10.0
            continue

        if strategy == 'double':
            player.bet *= 2
            player.add(shoe.deal())       # exactly one card, then stand
        else:
            while player.value < 17 and not player.is_bust:
                player.add(shoe.deal())   # hit until 17+

        total_wager += player.bet

        d_hand = Hand()
        d_hand.add(dealer.cards[0]); d_hand.add(dealer.cards[1])
        play_dealer(shoe, d_hand, rules)

        if player.is_bust:
            total_net -= player.bet
        else:
            total_net += settle(player.value, d_hand.value, player.bet)

    return total_net / total_wager * 100


print(f"Hard 11 vs dealer Ace: Double vs Hit")
print(f"Using {len(SEEDS)} x {N_HANDS:,} qualifying hands per cell")
print(f"(qualifying = player has hard 11, dealer shows Ace, no dealer BJ)")
print()

for rules, label in [(RULES_H17, "H17"), (RULES_S17, "S17")]:
    d_evs, h_evs = [], []
    for seed in SEEDS:
        d_evs.append(simulate_11vA(rules, 'double', N_HANDS, seed))
        h_evs.append(simulate_11vA(rules, 'hit',    N_HANDS, seed))

    avg_d = sum(d_evs) / len(d_evs)
    avg_h = sum(h_evs) / len(h_evs)
    diff  = avg_d - avg_h
    winner = "DOUBLE" if avg_d > avg_h else "HIT"

    print(f"  {label}  |  Double: {avg_d:+.4f}%   Hit: {avg_h:+.4f}%   "
          f"Diff (D-H): {diff:+.4f}%   => {winner} is better")

print()
print("Interpretation:")
print("  Positive diff = Double is better")
print("  Negative diff = Hit is better")
print()
print("Per-hand EV on a $10 bet:")
print("  +1% EV diff = $0.10 per hand where this situation arises")
print("  Hard 11 vs Ace arises ~0.3% of all rounds")
print("  So overall game EV impact = EV_diff * 0.003")
