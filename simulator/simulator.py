"""Monte Carlo simulation runner."""

from dataclasses import dataclass, field
from typing import List, Optional
from .rules import RuleSet
from .card import Shoe
from .counting import HiLoCounter, BetRamp
from .engine import play_hand, HandResult


@dataclass
class HandRecord:
    hand_num: int
    bet: float
    net: float
    outcome: str
    bankroll: float
    running_count: int
    true_count: float


@dataclass
class SimResult:
    records: List[HandRecord] = field(default_factory=list)
    rules: Optional[RuleSet] = None
    n_hands: int = 0
    starting_bankroll: float = 0.0


def run_simulation(
    rules: RuleSet,
    n_hands: int = 10_000,
    starting_bankroll: float = 10_000.0,
    bet_ramp: Optional[BetRamp] = None,
    use_counting: bool = True,
    use_deviations: bool = True,
    flat_bet: Optional[float] = None,
) -> SimResult:
    """
    Run a Monte Carlo simulation of n_hands.

    Args:
        rules: Casino rule configuration.
        n_hands: Number of hands to simulate.
        starting_bankroll: Starting bankroll in dollars.
        bet_ramp: Bet ramp for count-based betting. Defaults to 1-2-3-4-6 spread.
        use_counting: Whether to use Hi-Lo counting for bet sizing.
        use_deviations: Whether to apply Illustrious 18 / Fab 4 deviations.
        flat_bet: Override bet size (ignores ramp). Useful for EV calculation.
    """
    if bet_ramp is None:
        bet_ramp = BetRamp()

    shoe = Shoe(num_decks=rules.num_decks, penetration=rules.penetration)
    counter = HiLoCounter() if use_counting else None
    if counter:
        # Reset the running count whenever the shoe reshuffles (incl. the
        # between-rounds reshuffle below), keeping the count synced to the shoe.
        shoe.add_reshuffle_callback(counter.reset)
    bankroll = starting_bankroll
    result = SimResult(rules=rules, n_hands=n_hands, starting_bankroll=starting_bankroll)

    for i in range(n_hands):
        if bankroll <= 0:
            break

        if shoe.needs_reshuffle:
            shoe.reshuffle()   # reshuffle callback resets the counter

        true_count = counter.true_count(shoe.decks_remaining) if counter else 0.0

        if flat_bet is not None:
            bet = flat_bet
        elif use_counting:
            bet = min(bet_ramp.bet_size(true_count), bankroll)
        else:
            bet = min(bet_ramp.unit, bankroll)

        round_result = play_hand(shoe, rules, bet, counter, use_deviations)
        net = round_result.total_net
        bankroll += net

        for hand in round_result.hands:
            result.records.append(HandRecord(
                hand_num=i + 1,
                bet=hand.bet,
                net=hand.net,
                outcome=hand.outcome,
                bankroll=bankroll,
                running_count=hand.running_count,
                true_count=hand.true_count,
            ))

    return result
