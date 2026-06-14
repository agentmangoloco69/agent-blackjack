import random
from dataclasses import dataclass
from typing import List


RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['S', 'H', 'D', 'C']   # Spades, Hearts, Diamonds, Clubs

HI_LO_VALUES = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1,
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank in ('J', 'Q', 'K'):
            return 10
        if self.rank == 'A':
            return 11
        return int(self.rank)

    @property
    def hi_lo(self) -> int:
        return HI_LO_VALUES[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Shoe:
    def __init__(self, num_decks: int, penetration: float = 0.75):
        self.num_decks = num_decks
        self.penetration = penetration
        self._cards: List[Card] = []
        self._dealt: int = 0
        # Callbacks fired on every reshuffle — used to keep a card counter's
        # running count in lockstep with the physical shoe (reset to 0).
        self._reshuffle_callbacks = []
        self.reshuffle()

    def add_reshuffle_callback(self, callback) -> None:
        """Register a zero-arg callable invoked whenever the shoe is reshuffled."""
        self._reshuffle_callbacks.append(callback)

    def reshuffle(self):
        self._cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank in RANKS
        ]
        random.shuffle(self._cards)
        self._dealt = 0
        for cb in self._reshuffle_callbacks:
            cb()

    def deal(self) -> Card:
        # Reshuffle ONLY when physically out of cards. The penetration-based
        # reshuffle happens between rounds (callers check needs_reshuffle), so a
        # round always finishes on a single shoe — as in a real game. Reshuffling
        # mid-round would desync any registered card counter from the shoe.
        if self._dealt >= len(self._cards):
            self.reshuffle()
        card = self._cards[self._dealt]
        self._dealt += 1
        return card

    @property
    def needs_reshuffle(self) -> bool:
        return self._dealt >= len(self._cards) * self.penetration

    @property
    def cards_remaining(self) -> int:
        return len(self._cards) - self._dealt

    @property
    def decks_remaining(self) -> float:
        return self.cards_remaining / 52
