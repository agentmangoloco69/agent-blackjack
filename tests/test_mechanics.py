"""
Focused mechanics validation: bet accounting on splits/doubles, soft-hand
classification, and dealer drawing. These guard the EV-critical paths.
"""
import random
from simulator.card import Card, Shoe
from simulator.hand import Hand
from simulator.rules import RuleSet, STANDARD_6D_H17
from simulator.engine import play_hand, _play_dealer, _settle
from simulator.strategy import Action, get_action


# ── is_soft correctness (the multi-ace bug) ─────────────────────────────────

def _hand(*ranks):
    h = Hand()
    for r in ranks:
        h.add(Card(r, 'S'))
    return h

def test_soft_single_ace():
    assert _hand('A', '6').is_soft          # soft 17
    assert _hand('A', '6').value == 17

def test_soft_multi_ace_low():
    # A,4,A = hard 6, promote one ace -> 16, soft
    h = _hand('A', '4', 'A')
    assert h.value == 16
    assert h.is_soft

def test_soft_multi_ace_three():
    # A,A,A,4 = hard 7, promote one ace -> 17, soft
    h = _hand('A', 'A', 'A', '4')
    assert h.value == 17
    assert h.is_soft

def test_hard_after_ace_forced_low():
    # A,5,7 = 13, ace must be 1 (11+5+7=23 busts), so hard
    h = _hand('A', '5', '7')
    assert h.value == 13
    assert not h.is_soft

def test_soft_21_is_soft():
    # A,A,9 = 21 with one ace as 11 -> soft 21
    h = _hand('A', 'A', '9')
    assert h.value == 21
    assert h.is_soft


# ── Double bet accounting ────────────────────────────────────────────────────

def test_double_doubles_the_bet_and_takes_one_card():
    """Force a double scenario and verify bet doubles, exactly one card drawn."""
    # Player 5+6 = 11 vs dealer 5 -> double. Use a controlled shoe.
    class StackShoe(Shoe):
        def __init__(self, cards):
            self._stack = list(cards)
            self.num_decks = 6
            self.penetration = 0.99
            self._cards = []
            self._dealt = 0
        @property
        def needs_reshuffle(self): return False
        def deal(self):
            return self._stack.pop(0)
        @property
        def decks_remaining(self): return 5.0

    # deal order: player, dealer, player, dealer, then player's double card, then dealer draws
    cards = [Card('5','S'), Card('5','H'),   # player 5, dealer 5
             Card('6','S'), Card('9','H'),   # player 6 (=11), dealer 9 (=14)
             Card('K','S'),                  # player double card -> 21
             Card('8','D')]                  # dealer draws -> 22 bust
    shoe = StackShoe(cards)
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none')
    result = play_hand(shoe, rules, bet=10.0)
    # Player doubled to 21, dealer busts -> win 2x bet = +20
    assert len(result.hands) == 1
    assert result.hands[0].bet == 20.0, f"bet should be 20 after double, got {result.hands[0].bet}"
    assert result.hands[0].net == 20.0, f"net should be +20, got {result.hands[0].net}"


# ── Split bet accounting ─────────────────────────────────────────────────────

def test_split_creates_two_independent_bets():
    """Splitting 8,8 must produce two hands, each with the original bet."""
    class StackShoe(Shoe):
        def __init__(self, cards):
            self._stack = list(cards)
            self.num_decks = 6; self.penetration = 0.99
            self._cards = []; self._dealt = 0
        @property
        def needs_reshuffle(self): return False
        def deal(self): return self._stack.pop(0)
        @property
        def decks_remaining(self): return 5.0

    # player 8,8 vs dealer 6. Split -> each 8 gets a card.
    cards = [
        Card('8','S'), Card('6','H'),    # player 8, dealer 6
        Card('8','D'), Card('10','H'),   # player 8 (pair), dealer hole 10 (=16)
        Card('K','S'),                   # h1: 8 -> 18
        Card('Q','D'),                   # h2: 8 -> 18
        Card('5','C'),                   # dealer draws 6+10+5 = 21
    ]
    shoe = StackShoe(cards)
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=True, surrender='none',
                    double_after_split=True, max_splits=3)
    result = play_hand(shoe, rules, bet=10.0)
    # Two hands, each bet 10. Both 18 vs dealer 21 -> both lose -> net -20 total.
    assert len(result.hands) == 2, f"expected 2 hands, got {len(result.hands)}"
    assert all(h.bet == 10.0 for h in result.hands), "each split hand keeps original bet"
    assert result.total_net == -20.0, f"both 18 lose to 21, net should be -20, got {result.total_net}"


def test_split_aces_one_card_each():
    """Split aces get exactly one card each and cannot draw more."""
    class StackShoe(Shoe):
        def __init__(self, cards):
            self._stack = list(cards)
            self.num_decks = 6; self.penetration = 0.99
            self._cards = []; self._dealt = 0
        @property
        def needs_reshuffle(self): return False
        def deal(self): return self._stack.pop(0)
        @property
        def decks_remaining(self): return 5.0

    cards = [
        Card('A','S'), Card('9','H'),    # player A, dealer 9
        Card('A','D'), Card('8','H'),    # player A (pair aces), dealer hole 8 (=17)
        Card('5','S'),                   # ace 1 -> A,5 = soft 16, stands (no more cards)
        Card('6','D'),                   # ace 2 -> A,6 = soft 17, stands
        # dealer has 17, stands
    ]
    shoe = StackShoe(cards)
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=False, surrender='none')
    result = play_hand(shoe, rules, bet=10.0)
    assert len(result.hands) == 2, "split aces -> 2 hands"
    # Hand1 A,5=16 vs 17 lose; Hand2 A,6=17 vs 17 push -> net -10
    assert result.total_net == -10.0, f"got {result.total_net}"


# ── Dealer drawing rules ─────────────────────────────────────────────────────

def test_dealer_hits_soft_17_when_h17():
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=True)
    dealer = _hand('A', '6')   # soft 17
    # Append a card so dealer draws: use a tiny shoe
    class OneCard(Shoe):
        def __init__(self, c):
            self.c=c; self.num_decks=6; self.penetration=0.99
            self._cards=[]; self._dealt=0
        @property
        def needs_reshuffle(self): return False
        def deal(self): return self.c.pop(0)
    shoe = OneCard([Card('3','S')])   # soft 17 -> hits -> 20, stands
    _play_dealer(shoe, dealer, rules, None)
    assert dealer.value == 20

def test_dealer_stands_soft_17_when_s17():
    rules = RuleSet(num_decks=6, dealer_hits_soft_17=False)
    dealer = _hand('A', '6')   # soft 17
    class NoCard(Shoe):
        def __init__(self):
            self.num_decks=6; self.penetration=0.99; self._cards=[]; self._dealt=0
        @property
        def needs_reshuffle(self): return False
        def deal(self): raise AssertionError("dealer should not draw on S17")
    _play_dealer(NoCard(), dealer, rules, None)
    assert dealer.value == 17
