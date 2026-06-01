from dataclasses import dataclass, field
from typing import Literal

SurrenderRule = Literal["none", "late", "early"]


@dataclass
class RuleSet:
    num_decks: int = 6
    dealer_hits_soft_17: bool = True          # H17 = True, S17 = False
    surrender: SurrenderRule = "late"
    double_after_split: bool = True
    resplit_aces: bool = False
    max_splits: int = 3                        # max times a hand can be split
    blackjack_pays: float = 1.5               # 3:2 = 1.5, 6:5 = 1.2
    penetration: float = 0.75                  # fraction of shoe dealt before reshuffle
    free_bet: bool = False                     # Free Bet Blackjack variant
    dealer_peeks: bool = True                  # US rules: dealer checks for BJ before player acts
                                               # False = European no-peek: player acts first,
                                               # loses all doubles/splits to a dealer BJ

    def __post_init__(self):
        assert self.num_decks in (1, 2, 4, 6, 8), "num_decks must be 1, 2, 4, 6, or 8"
        assert 0.5 <= self.penetration <= 0.95
        assert self.blackjack_pays in (1.5, 1.2)


# Common presets
# All use the RuleSet defaults unless overridden:
#   surrender="late", double_after_split=True, blackjack_pays=1.5, dealer_peeks=True
STANDARD_6D_H17 = RuleSet(num_decks=6, dealer_hits_soft_17=True)
STANDARD_6D_S17 = RuleSet(num_decks=6, dealer_hits_soft_17=False)
STANDARD_2D_S17 = RuleSet(num_decks=2, dealer_hits_soft_17=False)
FREE_BET_6D     = RuleSet(num_decks=6, dealer_hits_soft_17=True, free_bet=True)
