"""
Trace a single blackjack hand step by step.

Run from the ClaudeBlackJack folder:
    python trace_hand.py

Optional: fix the random seed so you see the same hand every time:
    python trace_hand.py 42

Change the number to get a different hand:
    python trace_hand.py 99
    python trace_hand.py 7
"""
import sys
import random
from simulator.card import Shoe, Card
from simulator.hand import Hand
from simulator.rules import STANDARD_6D_H17
from simulator.strategy import Action, get_action
from simulator.strategy_table import DEALER_LABELS

# -- Config ------------------------------------------------------------------
RULES = STANDARD_6D_H17
BET   = 25.0
SEED  = int(sys.argv[1]) if len(sys.argv) > 1 else random.randint(1, 9999)

ACTION_NAMES = {
    Action.HIT:               "HIT",
    Action.STAND:             "STAND",
    Action.DOUBLE:            "DOUBLE DOWN",
    Action.DOUBLE_ELSE_STAND: "DOUBLE (else Stand)",
    Action.SPLIT:             "SPLIT",
    Action.SURRENDER:         "SURRENDER",
}

# -- Helpers ------------------------------------------------------------------
def sep(char="-", n=52):
    print(char * n)

def show_hand(label, hand, hide_hole=False):
    if hide_hole and len(hand.cards) >= 2:
        cards = f"{hand.cards[0]}  [hidden]"
        print(f"  {label:<12}  {cards}")
    else:
        cards = "  ".join(str(c) for c in hand.cards)
        value  = hand.value
        soft   = " (soft)" if hand.is_soft else ""
        bust   = "  *** BUST ***" if hand.is_bust else ""
        print(f"  {label:<12}  {cards}   =  {value}{soft}{bust}")

def upcard_label(card):
    return "A" if card.rank == "A" else str(card.value)

def play_dealer(shoe, dealer):
    print()
    sep()
    print("  DEALER'S TURN")
    sep()
    show_hand("Dealer", dealer)
    while True:
        v = dealer.value
        if v > 21:
            break
        if v >= 18:
            break
        if v == 17:
            if not (RULES.dealer_hits_soft_17 and dealer.is_soft):
                break
        card = shoe.deal()
        dealer.add(card)
        if RULES.dealer_hits_soft_17 and v == 17 and dealer.is_soft:
            reason = "soft 17 - dealer must hit (H17 rule)"
        else:
            reason = f"total {v} - dealer must hit"
        print(f"  Dealer hits  ({reason})  -> draws {card}")
        show_hand("Dealer", dealer)

def settle(pv, dv, bet):
    if dv > 21:
        return (bet, "WIN  (dealer busted)")
    if pv > dv:
        return (bet, "WIN")
    if pv < dv:
        return (-bet, "LOSS")
    return (0.0, "PUSH")

# -- Main --------------------------------------------------------------------─
random.seed(SEED)
shoe = Shoe(RULES.num_decks, RULES.penetration)

print()
sep("=")
print(f"  BLACKJACK HAND TRACE  |  seed={SEED}  |  bet=${BET:.0f}")
print(f"  Rules: {RULES.num_decks}-deck  H17  DAS  Late Surrender")
sep("=")

# -- Deal --------------------------------------------------------------------─
player = Hand(bet=BET)
dealer = Hand()
for _ in range(2):
    player.add(shoe.deal())
    dealer.add(shoe.deal())

print()
print("  INITIAL DEAL")
sep()
show_hand("Player", player)
show_hand("Dealer", dealer, hide_hole=True)
print(f"  Dealer shows: {dealer.cards[0]}")

upcard     = dealer.cards[0].value
upcard_key = min(upcard, 11)

# -- Dealer peek (US rules) --------------------------------------------------─
dealer_bj = dealer.is_blackjack
if dealer.cards[0].value in (10, 11):
    print(f"\n  Dealer peeks for blackjack ... ", end="")
    if dealer_bj:
        print("DEALER HAS BLACKJACK!")
    else:
        print("no blackjack.")

# -- Player blackjack --------------------------------------------------------─
if player.is_blackjack:
    print()
    sep("=")
    if dealer_bj:
        print("  RESULT: Both have Blackjack -> PUSH  (net $0)")
    else:
        payout = BET * RULES.blackjack_pays
        print(f"  RESULT: Player BLACKJACK -> pays 3:2 -> net +${payout:.2f}")
    sep("=")
    sys.exit()

if dealer_bj:
    print()
    sep("=")
    print(f"  RESULT: Dealer Blackjack -> player LOSES -> net -${BET:.2f}")
    sep("=")
    sys.exit()

# -- Player decisions ----------------------------------------------------------
hands_queue = [(player, 0)]   # (hand, split_depth)
final_hands = []

while hands_queue:
    hand, depth = hands_queue.pop(0)

    # Split-ace hands: already have 1 card, no further action
    if hand.split_from is not None and hand.cards[0].rank == "A":
        print(f"\n  (Split ace hand: stands with {hand})")
        final_hands.append(hand)
        continue

    hand_label = "PLAYER" if depth == 0 else f"SPLIT HAND {depth}"
    print()
    sep()
    print(f"  {hand_label}")
    sep()
    show_hand("Hand", hand)

    card_num = 0
    was_split = False

    while True:
        can_split   = hand.is_pair and depth < RULES.max_splits
        can_double  = len(hand.cards) == 2 and (depth == 0 or RULES.double_after_split)
        can_surr    = len(hand.cards) == 2 and depth == 0

        action = get_action(hand, upcard_key, RULES,
                            can_surrender=can_surr,
                            can_double=can_double,
                            can_split=can_split)

        action_str = ACTION_NAMES[action]

        # Show what the strategy recommends and why
        options = []
        if can_split:   options.append("split")
        if can_double:  options.append("double")
        if can_surr:    options.append("surrender")
        options += ["hit", "stand"]
        available = "/".join(options)

        print(f"\n  Strategy says: {action_str}")
        print(f"  (hand={hand.value}{'s' if hand.is_soft else ''}"
              f"  dealer={upcard_label(dealer.cards[0])}"
              f"  available: {available})")

        # -- Execute action --
        if action == Action.SURRENDER and can_surr:
            hand.surrendered = True
            print(f"  -> Surrendering. Lose half bet = -${BET/2:.2f}")
            break

        if action == Action.SPLIT and can_split:
            c1, c2 = hand.cards[0], hand.cards[1]
            h1 = Hand(bet=hand.bet); h1.split_from = hand
            h2 = Hand(bet=hand.bet); h2.split_from = hand
            card_a = shoe.deal(); card_b = shoe.deal()
            h1.add(c1); h1.add(card_a)
            h2.add(c2); h2.add(card_b)
            print(f"  -> Splitting {c1}{c2}:")
            print(f"     Hand A: {c1} + {card_a}  =  {h1.value}")
            print(f"     Hand B: {c2} + {card_b}  =  {h2.value}")
            hands_queue.insert(0, (h1, depth + 1))
            hands_queue.insert(1, (h2, depth + 1))
            was_split = True
            break

        if action in (Action.DOUBLE, Action.DOUBLE_ELSE_STAND) and can_double:
            hand.bet *= 2
            new_card = shoe.deal()
            hand.add(new_card)
            print(f"  -> Doubling down (bet now ${hand.bet:.0f}) -> draws {new_card}")
            show_hand("Hand", hand)
            break

        if action == Action.STAND:
            print(f"  -> Standing on {hand.value}")
            break

        # HIT
        new_card = shoe.deal()
        hand.add(new_card)
        card_num += 1
        print(f"  -> Hit #{card_num}: draws {new_card}")
        show_hand("Hand", hand)
        if hand.is_bust:
            print(f"  BUST!")
            break

    if not was_split:
        final_hands.append(hand)

# -- Dealer plays --------------------------------------------------------------
play_dealer(shoe, dealer)

# -- Settlement ----------------------------------------------------------------
print()
sep("=")
print("  SETTLEMENT")
sep("=")
show_hand("Dealer", dealer)
print()

total_net = 0.0
for i, hand in enumerate(final_hands):
    label = "Player" if len(final_hands) == 1 else f"Hand {i+1}"
    if hand.surrendered:
        net = -(hand.bet / 2)
        result = "SURRENDER"
    elif hand.is_bust:
        net = -hand.bet
        result = "BUST - LOSS"
    else:
        net, result = settle(hand.value, dealer.value, hand.bet)
    show_hand(label, hand)
    print(f"  {'':12}  -> {result}  |  bet ${hand.bet:.0f}  net {'+' if net >= 0 else ''}{net:.2f}")
    print()
    total_net += net

sep("=")
sign = "+" if total_net >= 0 else ""
print(f"  TOTAL NET:  {sign}${total_net:.2f}  (started with ${BET:.0f})")
sep("=")
print()
