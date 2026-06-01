from typing import List, Optional
from .card import Card


class Hand:
    def __init__(self, bet: float = 1.0, is_free_bet: bool = False):
        self.cards: List[Card] = []
        self.bet = bet
        self.is_free_bet = is_free_bet   # True if this hand resulted from a free split/double
        self.free_double_bet: float = 0  # extra bet covered by casino on free double
        self.doubled: bool = False
        self.surrendered: bool = False
        self.split_from: Optional['Hand'] = None

    def add(self, card: Card):
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = 0
        aces = 0
        for card in self.cards:
            if card.rank == 'A':
                aces += 1
                total += 11
            else:
                total += card.value
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        # A hand is soft if it contains at least one ace that can count as 11
        # without busting. Compute the hard total (every ace = 1); the hand is
        # soft if promoting ONE ace from 1 to 11 (adding 10) stays <= 21.
        # This is correct for multi-ace hands (e.g. A,4,A = hard 6 -> soft 16).
        has_ace = any(card.rank == 'A' for card in self.cards)
        if not has_ace:
            return False
        hard_total = sum(1 if card.rank == 'A' else card.value for card in self.cards)
        return hard_total + 10 <= 21

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_pair(self) -> bool:
        if len(self.cards) != 2:
            return False
        return self.cards[0].value == self.cards[1].value

    @property
    def pair_rank(self) -> Optional[str]:
        if not self.is_pair:
            return None
        r = self.cards[0].rank
        # normalise 10-value cards to '10' for strategy lookup
        return r if r not in ('J', 'Q', 'K') else '10'

    @property
    def can_split(self) -> bool:
        return self.is_pair

    def __str__(self) -> str:
        cards_str = ' '.join(str(c) for c in self.cards)
        return f"[{cards_str}] = {self.value}"
