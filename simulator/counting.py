from dataclasses import dataclass, field
from typing import Dict
from .card import Card


@dataclass
class HiLoCounter:
    running_count: int = 0

    def update(self, card: Card):
        self.running_count += card.hi_lo

    def true_count(self, decks_remaining: float) -> float:
        if decks_remaining <= 0:
            return 0.0
        # A human counter estimates decks remaining by looking at the discard tray.
        # They can only do so to the nearest half-deck (0.5, 1.0, 1.5, 2.0, ...).
        # Round to nearest 0.5 before dividing — anything less precise isn't realistic.
        estimated_decks = max(0.5, round(decks_remaining * 2) / 2)
        return self.running_count / estimated_decks

    def reset(self):
        self.running_count = 0


@dataclass
class BetRamp:
    """Maps true count to a bet multiplier (in units of min bet).

    Default is a 1-2-3-4-6 spread starting at TC+1, common for 6-deck games.
    """
    unit: float = 25.0
    ramp: Dict[int, float] = field(default_factory=lambda: {
        -99: 1,   # negative counts: bet minimum
        0:   1,
        1:   2,
        2:   3,
        3:   4,
        4:   6,
        5:   8,
    })

    def bet_size(self, true_count: float) -> float:
        tc = int(true_count)
        # find highest ramp key <= tc
        applicable = [k for k in self.ramp if k <= tc]
        if not applicable:
            return self.unit
        return self.ramp[max(applicable)] * self.unit
