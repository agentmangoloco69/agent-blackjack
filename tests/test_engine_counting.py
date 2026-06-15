"""Deterministic guard: every dealt card is counted exactly once.

Regression for a hole-card bug: the dealer's hole card was counted at deal time
AND again when revealed (double-counted), while also leaking into the round's
deviation count. After the fix, the running count must equal the Hi-Lo sum of
every card dealt in the round — each counted exactly once.
"""

from simulator.card import Card, Shoe
from simulator.rules import RuleSet
from simulator.counting import HiLoCounter
from simulator.engine import play_hand


class RecordingStackShoe(Shoe):
    """A shoe that deals a fixed, known sequence and records what it dealt."""
    def __init__(self, cards):
        self._stack = list(cards)
        self.dealt_cards = []
        self.num_decks = 6
        self.penetration = 0.99
        self._cards = []
        self._dealt = 0
        self._reshuffle_callbacks = []

    @property
    def needs_reshuffle(self):
        return False

    @property
    def decks_remaining(self):
        return 5.0

    def deal(self):
        card = self._stack.pop(0)
        self.dealt_cards.append(card)
        return card


def test_every_card_counted_exactly_once():
    # Player 10,7 = 17 (stands vs 9). Dealer up 9, hole 6 = 15, draws 5 -> 20.
    # Deal order: player, dealer-up, player, dealer-hole, then dealer draws.
    cards = [Card('10', 'S'), Card('9', 'H'),   # player 10, dealer up 9
             Card('7', 'S'), Card('6', 'H'),    # player 7 (=17), dealer hole 6
             Card('5', 'D')]                     # dealer draw -> 20
    shoe = RecordingStackShoe(cards)
    counter = HiLoCounter()
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none')

    play_hand(shoe, rules, bet=10.0, counter=counter, use_deviations=False)

    expected = sum(c.hi_lo for c in shoe.dealt_cards)
    assert counter.running_count == expected, (
        f"running count {counter.running_count} != Hi-Lo sum {expected} "
        f"of {[str(c) for c in shoe.dealt_cards]} — a card was double-counted or missed"
    )


def test_hole_card_not_leaked_into_round_true_count():
    """The true count recorded for the round must exclude the unseen hole card.

    Visible at decision time: 10(-1), 9(0), 7(0) -> running count -1, over ~5
    decks -> true count -0.2. If the hole card (6 = +1) leaked in, the running
    count would be 0 and the true count 0.0.
    """
    cards = [Card('10', 'S'), Card('9', 'H'),
             Card('7', 'S'), Card('6', 'H'),
             Card('5', 'D')]
    shoe = RecordingStackShoe(cards)
    counter = HiLoCounter()
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none')
    result = play_hand(shoe, rules, bet=10.0, counter=counter, use_deviations=False)

    recorded_tc = result.hands[0].true_count
    assert abs(recorded_tc - (-0.2)) < 1e-9, (
        f"round true count {recorded_tc} should be -0.2 (count -1 / 5 decks); "
        f"a value near 0 means the hole card leaked into player decisions"
    )
