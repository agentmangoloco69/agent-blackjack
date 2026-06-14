"""Single-hand game engine."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .card import Shoe
from .hand import Hand
from .rules import RuleSet
from .strategy import Action, get_action
from .counting import HiLoCounter
from .deviations import get_deviation, should_take_insurance


@dataclass
class HandResult:
    bet: float
    net: float              # net profit/loss for this hand (positive = won)
    outcome: str            # 'win', 'loss', 'push', 'blackjack', 'surrender'
    running_count: int = 0
    true_count: float = 0.0


@dataclass
class RoundResult:
    hands: List[HandResult] = field(default_factory=list)
    insurance_net: float = 0.0

    @property
    def total_net(self) -> float:
        return sum(h.net for h in self.hands) + self.insurance_net


def play_hand(
    shoe: Shoe,
    rules: RuleSet,
    bet: float,
    counter: Optional[HiLoCounter] = None,
    use_deviations: bool = False,
) -> RoundResult:
    """Play one complete round and return the result."""

    def deal_card(hand: Hand) -> None:
        card = shoe.deal()
        hand.add(card)
        if counter:
            counter.update(card)

    # --- Initial deal ---
    player = Hand(bet=bet)
    dealer = Hand()
    deal_card(player); deal_card(dealer)
    deal_card(player); deal_card(dealer)

    dealer_upcard = dealer.cards[0].value # hole-card hidden
    dealer_upcard_key = min(dealer_upcard, 11)  # 10 for J/Q/K/10, 11 for Ace

    result = RoundResult()
    true_count = counter.true_count(shoe.decks_remaining) if counter else 0.0

    # --- Insurance (dealer shows Ace) ---
    insurance_bet = 0.0
    if dealer.cards[0].rank == 'A':
        take_ins = (
            should_take_insurance(true_count)
            if (counter and use_deviations)
            else False
        )
        if take_ins:
            insurance_bet = bet / 2

    # --- Dealer peek check (only when dealer_peeks = True, i.e. US rules) ---
    # When dealer shows Ace or 10-value and peeks, BJ is resolved before player acts.
    # When dealer_peeks = False (European no-peek), player acts first and may lose
    # extra bets (doubles/splits) to a dealer BJ discovered at the end.
    dealer_shows_natural = dealer.cards[0].rank == 'A' or dealer.cards[0].value == 10

    if rules.dealer_peeks and dealer_shows_natural and dealer.is_blackjack:
        # Dealer has BJ — resolve immediately before player acts
        if counter:
            counter.update(dealer.cards[1])
        if player.is_blackjack:
            # Both have BJ → push; insurance (if taken) pays 2:1
            if insurance_bet:
                result.insurance_net = insurance_bet * 2
            result.hands.append(HandResult(bet=bet, net=0.0, outcome='push',
                                           running_count=counter.running_count if counter else 0,
                                           true_count=true_count))
        else:
            # Only dealer has BJ → player loses flat bet; insurance pays 2:1
            if insurance_bet:
                result.insurance_net = insurance_bet * 2
            else:
                result.insurance_net = -insurance_bet if insurance_bet else 0.0
            result.hands.append(HandResult(bet=bet, net=-bet, outcome='loss',
                                           running_count=counter.running_count if counter else 0,
                                           true_count=true_count))
        return result

    # --- Player blackjack (dealer either peeked & has no BJ, or no-peek game) ---
    if player.is_blackjack:
        if counter:
            counter.update(dealer.cards[1])
        if dealer.is_blackjack:
            # No-peek game: both revealed simultaneously — push; insurance pays
            if insurance_bet:
                result.insurance_net = insurance_bet * 2
            result.hands.append(HandResult(bet=bet, net=0.0, outcome='push',
                                           running_count=counter.running_count if counter else 0,
                                           true_count=true_count))
        else:
            if insurance_bet:
                result.insurance_net = -insurance_bet
            payout = bet * rules.blackjack_pays
            result.hands.append(HandResult(bet=bet, net=payout, outcome='blackjack',
                                           running_count=counter.running_count if counter else 0,
                                           true_count=true_count))
        return result

    # Insurance lost (dealer peeked, no BJ, or no-peek game and player has no BJ)
    if insurance_bet:
        result.insurance_net = -insurance_bet

    # --- Play all player hands (handles splits) ---
    hand_results = _play_player_hands(
        shoe, rules, player, dealer_upcard_key, counter, use_deviations, true_count
    )

    # --- No-peek: check for dealer BJ after player has acted ---
    # Player may have doubled or split — they lose ALL bets to a dealer BJ.
    if not rules.dealer_peeks and dealer.is_blackjack:
        if counter:
            counter.update(dealer.cards[1])
        for hand in hand_results:
            if hand.surrendered:
                result.hands.append(HandResult(
                    bet=hand.bet, net=-(hand.bet / 2), outcome='surrender',
                    running_count=counter.running_count if counter else 0,
                    true_count=true_count,
                ))
            else:
                # No-peek: lose the full bet (including doubles/splits)
                loss = 0.0 if hand.is_free_bet else -hand.bet
                result.hands.append(HandResult(
                    bet=hand.bet, net=loss, outcome='loss',
                    running_count=counter.running_count if counter else 0,
                    true_count=true_count,
                ))
        return result

    # --- Dealer plays ---
    if counter:
        counter.update(dealer.cards[1])  # count hole card now
    _play_dealer(shoe, dealer, rules, counter)

    # --- Settle ---
    for hand in hand_results:
        if hand.surrendered:
            result.hands.append(HandResult(
                bet=hand.bet, net=-(hand.bet / 2), outcome='surrender',
                running_count=counter.running_count if counter else 0,
                true_count=true_count,
            ))
            continue
        if hand.is_bust:
            # Free-bet split hand: casino absorbs the loss
            net = 0.0 if hand.is_free_bet else -(hand.bet)
            outcome = 'loss'
        else:
            net, outcome = _settle(hand, dealer, rules)
        result.hands.append(HandResult(
            bet=hand.bet, net=net, outcome=outcome,
            running_count=counter.running_count if counter else 0,
            true_count=true_count,
        ))

    return result


def _play_player_hands(
    shoe: Shoe,
    rules: RuleSet,
    initial_hand: Hand,
    dealer_upcard: int,
    counter: Optional[HiLoCounter],
    use_deviations: bool,
    true_count: float,
) -> List[Hand]:
    """Recursively play hand, handling splits. Returns list of final hands."""

    def deal_to(hand: Hand):
        card = shoe.deal()
        hand.add(card)
        if counter:
            counter.update(card)

    queue: List[Tuple[Hand, int]] = [(initial_hand, 0)]  # (hand, split_depth)
    finished: List[Hand] = []

    while queue:
        hand, depth = queue.pop(0)

        is_split_aces = (
            hand.split_from is not None and
            hand.cards[0].rank == 'A'
        )

        # After splitting aces, one card is already dealt — no further action allowed
        if is_split_aces:
            finished.append(hand)
            continue

        # First action opportunity
        while True:
            can_split = (
                hand.is_pair and
                depth < rules.max_splits and
                not is_split_aces
            )
            can_double = len(hand.cards) == 2 and (depth == 0 or rules.double_after_split)
            can_surrender = len(hand.cards) == 2 and depth == 0

            # Deviation override
            action = None
            if use_deviations and counter:
                is_pair_tens = hand.is_pair and hand.cards[0].value == 10
                action = get_deviation(
                    player_total=hand.value,
                    dealer_upcard=dealer_upcard,
                    true_count=true_count,
                    is_pair_of_tens=is_pair_tens,
                    is_soft=hand.is_soft,
                    is_pair=hand.is_pair,
                )

            if action is None:
                action = get_action(
                    hand, dealer_upcard, rules,
                    can_surrender=can_surrender,
                    can_double=can_double,
                    can_split=can_split,
                    is_free_bet_hand=hand.is_free_bet,
                )

            if action == Action.SURRENDER and can_surrender:
                hand.surrendered = True
                break

            if action == Action.SPLIT and can_split:
                # Create two new hands from the pair.
                # h1 inherits the player's original bet responsibility.
                # h2 is a free bet (casino covers losses) for non-10 pairs in Free Bet BJ.
                card1 = hand.cards[0]
                card2 = hand.cards[1]
                is_free = rules.free_bet and card1.value != 10

                h1 = Hand(bet=hand.bet, is_free_bet=hand.is_free_bet)
                h2 = Hand(bet=hand.bet, is_free_bet=is_free)
                h1.split_from = hand
                h2.split_from = hand
                h1.add(card1); deal_to(h1)
                h2.add(card2); deal_to(h2)
                queue.insert(0, (h1, depth + 1))
                queue.insert(1, (h2, depth + 1))
                # IMPORTANT: do NOT add the original hand to finished —
                # it has been replaced by h1 and h2. Use continue to skip
                # the finished.append(hand) at the bottom of the outer loop.
                hand = None
                break

            if action == Action.DOUBLE and can_double:
                if rules.free_bet and hand.value in (9, 10, 11) and not hand.is_soft:
                    # Free double: casino covers extra bet
                    hand.free_double_bet = hand.bet
                else:
                    hand.bet *= 2
                hand.doubled = True
                deal_to(hand)
                break

            if action == Action.STAND:
                break

            # HIT
            deal_to(hand)
            if hand.is_bust:
                break

        if hand is not None:   # hand=None means it was split; h1/h2 are in queue instead
            finished.append(hand)

    return finished


def _play_dealer(shoe: Shoe, dealer: Hand, rules: RuleSet, counter: Optional[HiLoCounter]):
    """Dealer draws according to house rules."""
    while True:
        v = dealer.value
        if v > 21:
            break
        if v > 17:
            break
        if v == 17:
            if not (rules.dealer_hits_soft_17 and dealer.is_soft):
                break
        card = shoe.deal()
        dealer.add(card)
        if counter:
            counter.update(card)


def _settle(player_hand: Hand, dealer: Hand, rules: RuleSet) -> Tuple[float, str]:
    """Compare non-bust player hand to dealer. Return (net, outcome)."""
    pv = player_hand.value
    dv = dealer.value

    # Total win payout includes casino-matched free double bet (0 for regular hands)
    win_amount = player_hand.bet + player_hand.free_double_bet

    if dealer.is_bust:
        # Free Bet Blackjack: dealer bust on exactly 22 = push for all player hands
        if rules.free_bet and dv == 22:
            return (0.0, 'push')
        return (win_amount, 'win')

    if pv > dv:
        return (win_amount, 'win')
    if pv < dv:
        # Free-bet split hand: casino absorbs the loss
        loss = 0.0 if player_hand.is_free_bet else -player_hand.bet
        return (loss, 'loss')
    return (0.0, 'push')
