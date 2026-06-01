"""
Compare EV of: Surrender 15 vs Ace  vs  Hit 15 vs Ace
Everything else identical (6D H17 DAS late surrender).
"""
import random
from simulator.card import Shoe
from simulator.hand import Hand
from simulator.rules import RuleSet
from simulator.strategy import Action, get_action, _HARD

RULES = RuleSet(num_decks=6, dealer_hits_soft_17=True,
                surrender='late', double_after_split=True)
N = 1_000_000
SEEDS = [42, 137, 999, 2024, 31415, 7, 8888, 12345, 99999, 555]


def play_dealer(shoe, dealer):
    while True:
        v = dealer.value
        if v > 21: break
        if v >= 18: break
        if v == 17:
            if not (RULES.dealer_hits_soft_17 and dealer.is_soft):
                break
        dealer.add(shoe.deal())


def settle(pv, dv, bet):
    if dv > 21: return bet
    if pv > dv: return bet
    if pv < dv: return -bet
    return 0.0


def simulate(seed, override_15vA=None):
    """override_15vA: None=use table, 'H'=always hit, 'Su'=always surrender"""
    random.seed(seed)
    shoe = Shoe(6, 0.75)
    total_net = 0.0
    total_wager = 0.0

    for _ in range(N):
        if shoe.needs_reshuffle:
            shoe.reshuffle()

        player = Hand(bet=10.0)
        dealer = Hand()
        player.add(shoe.deal()); dealer.add(shoe.deal())
        player.add(shoe.deal()); dealer.add(shoe.deal())

        upcard_val = dealer.cards[0].value
        upcard = min(upcard_val, 10)

        if player.is_blackjack:
            if not dealer.is_blackjack:
                total_net += 15.0
            total_wager += 10.0
            continue
        if dealer.is_blackjack:
            total_net -= 10.0; total_wager += 10.0
            continue

        hands = [(player, 0)]
        final = []

        while hands:
            h, depth = hands.pop(0)
            if h.split_from is not None and h.cards[0].rank == 'A':
                final.append(h); continue
            while True:
                can_sp = h.is_pair and depth < 3
                can_db = len(h.cards) == 2 and (depth == 0 or RULES.double_after_split)
                can_su = len(h.cards) == 2 and depth == 0

                # Override: 15 vs Ace
                is_hard15_vs_ace = (
                    not h.is_soft and h.value == 15 and
                    upcard_val == 11 and len(h.cards) == 2 and depth == 0
                )

                if override_15vA and is_hard15_vs_ace:
                    if override_15vA == 'Su':
                        h.surrendered = True; break
                    else:
                        action = Action.HIT
                else:
                    action = get_action(h, upcard, RULES,
                                        can_surrender=can_su,
                                        can_double=can_db,
                                        can_split=can_sp)

                if action == Action.SURRENDER and can_su:
                    h.surrendered = True; break
                if action == Action.SPLIT and can_sp:
                    c1, c2 = h.cards[0], h.cards[1]
                    h1 = Hand(bet=h.bet); h1.split_from = h
                    h2 = Hand(bet=h.bet); h2.split_from = h
                    h1.add(c1); h1.add(shoe.deal())
                    h2.add(c2); h2.add(shoe.deal())
                    hands.insert(0, (h1, depth+1))
                    hands.insert(1, (h2, depth+1))
                    break
                if action == Action.DOUBLE and can_db:
                    h.bet *= 2; h.add(shoe.deal()); break
                if action == Action.STAND: break
                h.add(shoe.deal())
                if h.is_bust: break
            final.append(h)

        d_hand = Hand()
        d_hand.add(dealer.cards[0]); d_hand.add(dealer.cards[1])
        play_dealer(shoe, d_hand)
        dv = d_hand.value

        for h in final:
            b = h.bet
            total_wager += b
            if h.surrendered: total_net -= b / 2
            elif h.is_bust:   total_net -= b
            else:             total_net += settle(h.value, dv, b)

    return total_net / total_wager * 100


print(f"Comparing 'Surrender 15 vs A'  vs  'Hit 15 vs A'")
print(f"6D H17 DAS late surrender | {len(SEEDS)} x {N:,} hands each")
print()
print(f"{'Seed':>7}   {'Surrender EV':>13}   {'Hit EV':>8}   {'Delta (Hit-Surr)':>16}")
print("-" * 56)

surr_evs, hit_evs = [], []
for seed in SEEDS:
    s_ev = simulate(seed, override_15vA='Su')
    h_ev = simulate(seed, override_15vA='H')
    surr_evs.append(s_ev)
    hit_evs.append(h_ev)
    print(f"{seed:>7}   {s_ev:>12.4f}%   {h_ev:>7.4f}%   {h_ev - s_ev:>+15.4f}%")

avg_s = sum(surr_evs) / len(surr_evs)
avg_h = sum(hit_evs)  / len(hit_evs)
print("-" * 56)
print(f"{'AVG':>7}   {avg_s:>12.4f}%   {avg_h:>7.4f}%   {avg_h - avg_s:>+15.4f}%")
print()
if avg_h > avg_s:
    print(f"  -> HIT is better by {avg_h - avg_s:+.4f}% EV")
else:
    print(f"  -> SURRENDER is better by {avg_s - avg_h:+.4f}% EV")
print()
print("Note: overall EV difference is tiny since 15 vs A is a rare scenario")
print("(~0.35% of hands), so the per-hand delta is amplified ~300x in the table.")
