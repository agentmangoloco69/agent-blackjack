"""
Systematic EV diagnosis using a stripped-down simulation that we can control precisely.
We write our own mini-engine so we can disable features cleanly.
"""
import random
from simulator.card import Shoe, Card
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


def deal_card(shoe, hand):
    hand.add(shoe.deal())


def settle(pv, dv, bet):
    if dv > 21:
        return bet
    if pv > dv:
        return bet
    if pv < dv:
        return -bet
    return 0.0


def simulate(rules, n_hands, allow_double=True, allow_split=True,
             allow_soft_strategy=True, allow_surrender=False, seed=42):
    random.seed(seed)
    shoe = Shoe(rules.num_decks, rules.penetration)
    total_net = 0.0
    total_wagered = 0.0
    bet = 10.0

    for _ in range(n_hands):
        if shoe.needs_reshuffle:
            shoe.reshuffle()

        player = Hand(bet=bet)
        dealer = Hand()
        deal_card(shoe, player); deal_card(shoe, dealer)
        deal_card(shoe, player); deal_card(shoe, dealer)

        upcard = min(dealer.cards[0].value, 10)  # 10 for J/Q/K/10, 11 for Ace... actually keep Ace as 10 for now

        # Player blackjack
        if player.is_blackjack:
            if dealer.is_blackjack:
                pass  # push
            else:
                total_net += bet * 1.5
            total_wagered += bet
            # count dealer hole card
            continue

        # Dealer blackjack (peek game)
        if dealer.is_blackjack:
            total_net -= bet
            total_wagered += bet
            continue

        # Play player hands (handle splits in a queue)
        hands = [(player, 0)]   # (hand, depth)
        final_hands = []

        while hands:
            h, depth = hands.pop(0)

            # After splitting aces: stand immediately
            if h.split_from is not None and h.cards[0].rank == 'A':
                final_hands.append((h, depth))
                continue

            while True:
                can_sp  = h.is_pair and depth < rules.max_splits
                can_db  = len(h.cards) == 2 and (depth == 0 or rules.double_after_split)
                can_su  = len(h.cards) == 2 and depth == 0 and allow_surrender

                if not allow_double:
                    can_db = False
                if not allow_split:
                    can_sp = False
                if not allow_soft_strategy and h.is_soft:
                    # treat soft hand as hard: just hit to 17
                    if h.value >= 17:
                        break
                    deal_card(shoe, h)
                    if h.is_bust:
                        break
                    continue

                action = get_action(h, upcard, rules,
                                    can_surrender=can_su,
                                    can_double=can_db,
                                    can_split=can_sp)

                if action == Action.SURRENDER:
                    h.surrendered = True
                    break

                if action == Action.SPLIT and can_sp:
                    c1, c2 = h.cards[0], h.cards[1]
                    h1 = Hand(bet=h.bet); h1.split_from = h
                    h2 = Hand(bet=h.bet); h2.split_from = h
                    h1.add(c1); deal_card(shoe, h1)
                    h2.add(c2); deal_card(shoe, h2)
                    hands.insert(0, (h1, depth+1))
                    hands.insert(1, (h2, depth+1))
                    break

                if action == Action.DOUBLE and can_db:
                    h.bet *= 2
                    deal_card(shoe, h)
                    break

                if action == Action.STAND:
                    break

                deal_card(shoe, h)
                if h.is_bust:
                    break

            final_hands.append((h, depth))

        # Dealer plays
        play_dealer(shoe, dealer, rules)
        dv = dealer.value

        for h, _ in final_hands:
            b = h.bet
            total_wagered += b
            if h.surrendered:
                total_net -= b / 2
            elif h.is_bust:
                total_net -= b
            else:
                total_net += settle(h.value, dv, b)

    return (total_net / total_wagered * 100) if total_wagered else 0


RULES_BASE  = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none',  double_after_split=False)
RULES_DAS   = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none',  double_after_split=True)
RULES_FULL  = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='late',  double_after_split=True)
N = 400_000
SEEDS = [42, 137, 999, 2024, 31415]


def avg(rules, seeds=SEEDS, **kw):
    return sum(simulate(rules, N, seed=s, **kw) for s in seeds) / len(seeds)


print(f"Each row = average of {len(SEEDS)} x {N:,} hands = {len(SEEDS)*N:,} total")
print()
print(f"{'Step':<42} {'Sim EV':>8}  {'Ref approx':>11}  {'Gap':>7}")
print('-' * 73)

e1 = avg(RULES_BASE, allow_double=False, allow_split=False)
print(f"{'1. Hard+soft hit/stand only (no dbl/spl)':<42} {e1:>7.3f}%  {'~-2.7%':>11}  {e1+2.7:>+6.3f}%")

e2 = avg(RULES_BASE, allow_double=True, allow_split=False)
print(f"{'2. + All doubles (no splits)':<42} {e2:>7.3f}%  {'~-1.1%':>11}  {e2+1.1:>+6.3f}%")

e3 = avg(RULES_BASE, allow_double=True, allow_split=True)
print(f"{'3. + Splits (no DAS, no surr)':<42} {e3:>7.3f}%  {'~-0.65%':>11}  {e3+0.65:>+6.3f}%")

e4 = avg(RULES_DAS,  allow_double=True, allow_split=True)
print(f"{'4. + DAS':<42} {e4:>7.3f}%  {'~-0.58%':>11}  {e4+0.58:>+6.3f}%")

e5 = avg(RULES_FULL, allow_double=True, allow_split=True, allow_surrender=True)
print(f"{'5. Full strategy (DAS + L-surr)':<42} {e5:>7.3f}%  {'~-0.44%':>11}  {e5+0.44:>+6.3f}%")

print()
print("Incremental gains (simulated vs expected):")
print(f"  Hit/stand baseline:  {e1:+.3f}%")
print(f"  Doubles added:       {e2-e1:+.3f}%  (expected ~+1.6%)")
print(f"  Splits added:        {e3-e2:+.3f}%  (expected ~+0.45%)")
print(f"  DAS added:           {e4-e3:+.3f}%  (expected ~+0.14%)")
print(f"  Surrender added:     {e5-e4:+.3f}%  (expected ~+0.07%)")
