"""
Isolate the split bug by running many independent seeds and checking the
EV delta is consistently correct (splits must improve EV per original bet).

Also inspect bet accounting: when a split occurs, does the total_wagered
correctly reflect the player's actual additional outlay?
"""
import random
from simulator.card import Shoe
from simulator.hand import Hand
from simulator.rules import RuleSet
from simulator.strategy import Action, get_action


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


RULES = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none', double_after_split=False)


def run_one(n, seed, split_enabled):
    random.seed(seed)
    shoe = Shoe(6, 0.75)
    total_net = 0.0
    total_wager = 0.0       # sum of ALL hand bets (incl. splits)
    original_wager = 0.0    # sum of ORIGINAL bets only (1 per round)

    for _ in range(n):
        if shoe.needs_reshuffle:
            shoe.reshuffle()

        player = Hand(bet=10.0)
        dealer = Hand()
        player.add(shoe.deal()); dealer.add(shoe.deal())
        player.add(shoe.deal()); dealer.add(shoe.deal())

        original_wager += 10.0     # player always bets $10 per round

        if player.is_blackjack:
            if not dealer.is_blackjack:
                total_net += 15.0
            total_wager += 10.0
            continue
        if dealer.is_blackjack:
            total_net -= 10.0
            total_wager += 10.0
            continue

        upcard = min(dealer.cards[0].value, 10)
        hands = [(player, 0)]
        final = []

        while hands:
            h, depth = hands.pop(0)
            if h.split_from is not None and h.cards[0].rank == 'A':
                final.append(h); continue
            while True:
                can_sp = h.is_pair and depth < 3 and split_enabled
                action = get_action(h, upcard, RULES, can_surrender=False,
                                    can_double=False, can_split=can_sp)
                if action == Action.SPLIT and can_sp:
                    c1, c2 = h.cards[0], h.cards[1]
                    h1 = Hand(bet=h.bet); h1.split_from = h
                    h2 = Hand(bet=h.bet); h2.split_from = h
                    h1.add(c1); h1.add(shoe.deal())
                    h2.add(c2); h2.add(shoe.deal())
                    hands.insert(0, (h1, depth+1))
                    hands.insert(1, (h2, depth+1))
                    break
                if action == Action.STAND: break
                h.add(shoe.deal())
                if h.is_bust: break
            final.append(h)

        dealer_hand = Hand()
        dealer_hand.add(dealer.cards[0]); dealer_hand.add(dealer.cards[1])
        play_dealer(shoe, dealer_hand, RULES)
        dv = dealer_hand.value

        round_net = 0.0
        for h in final:
            b = h.bet
            total_wager += b
            if h.is_bust:
                total_net -= b; round_net -= b
            else:
                gain = settle(h.value, dv, b)
                total_net += gain; round_net += gain

    ev_per_wager    = total_net / total_wager * 100
    ev_per_original = total_net / original_wager * 100
    return ev_per_wager, ev_per_original, total_wager, original_wager


N = 400_000
SEEDS = list(range(10, 110, 10))  # 10 independent seeds

print(f"Split vs No-Split: {len(SEEDS)} independent runs x {N:,} hands each")
print(f"Two EV measures: per-hand-wagered (current method) vs per-original-bet")
print()
print(f"{'Seed':>6}  {'No-split (wager)':>17}  {'Split (wager)':>14}  {'No-split (orig)':>16}  {'Split (orig)':>13}")
print('-' * 74)

wager_evs  = {'split': [], 'nosplit': []}
orig_evs   = {'split': [], 'nosplit': []}

for seed in SEEDS:
    ns_w, ns_o, _, _ = run_one(N, seed, split_enabled=False)
    sp_w, sp_o, _, _ = run_one(N, seed, split_enabled=True)
    wager_evs['nosplit'].append(ns_w); wager_evs['split'].append(sp_w)
    orig_evs['nosplit'].append(ns_o);  orig_evs['split'].append(sp_o)
    print(f"{seed:>6}  {ns_w:>16.3f}%  {sp_w:>13.3f}%  {ns_o:>15.3f}%  {sp_o:>12.3f}%")

def avg(lst): return sum(lst) / len(lst)

ns_w_avg = avg(wager_evs['nosplit']); sp_w_avg = avg(wager_evs['split'])
ns_o_avg = avg(orig_evs['nosplit']);  sp_o_avg = avg(orig_evs['split'])
print('-' * 74)
print(f"{'AVG':>6}  {ns_w_avg:>16.3f}%  {sp_w_avg:>13.3f}%  {ns_o_avg:>15.3f}%  {sp_o_avg:>12.3f}%")
print()
print(f"Delta (split minus no-split):")
print(f"  Per hand wagered:    {sp_w_avg - ns_w_avg:+.3f}%  (expected ~+0.45%)")
print(f"  Per original bet:    {sp_o_avg - ns_o_avg:+.3f}%  (expected ~+0.45%)")
print()
print("NOTE: 'per original bet' = total net / (n_rounds * $10), which is the")
print("correct EV metric — measures profit relative to what the player put at")
print("risk BEFORE the round started, not including additional split outlays.")
