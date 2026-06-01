from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .hand import Hand
    from .rules import RuleSet


class Action(Enum):
    HIT = auto()
    STAND = auto()
    DOUBLE = auto()          # Double; if not allowed → HIT
    DOUBLE_ELSE_STAND = auto()  # Ds: Double; if not allowed → STAND
    SPLIT = auto()
    SURRENDER = auto()


# ---------------------------------------------------------------------------
# Standard basic strategy tables (6-deck, H17 — most common US game)
# Keys: (player_total_or_pair_rank, dealer_upcard_value)
# Dealer upcard values: 2–9, 10 (all ten-value), 11 (Ace)
# ---------------------------------------------------------------------------

# Hard totals: player hard total -> dealer upcard -> action
# (totals 4-8 always HIT, 17+ always STAND — handled in logic)
_HARD = {
    9:  {2: Action.HIT,    3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    10: {2: Action.DOUBLE, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.DOUBLE, 8: Action.DOUBLE, 9: Action.DOUBLE,
         10: Action.HIT,  11: Action.HIT},
    11: {2: Action.DOUBLE, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.DOUBLE, 8: Action.DOUBLE, 9: Action.DOUBLE,
         10: Action.DOUBLE, 11: Action.DOUBLE},  # 11 vs A: Double (6D H17)
    12: {2: Action.HIT,   3: Action.HIT,    4: Action.STAND,  5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
    13: {2: Action.STAND, 3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
    14: {2: Action.STAND, 3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
    15: {2: Action.STAND, 3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.SURRENDER, 11: Action.HIT},
    16: {2: Action.STAND, 3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,    8: Action.HIT,    9: Action.SURRENDER,
         10: Action.SURRENDER, 11: Action.SURRENDER},
}

# Soft totals base table.
# Soft 18 (A,7) vs 2 is DOUBLE — this matches both H17 and S17 for 6-deck games
# and is confirmed correct by Blackjack Apprenticeship.
# S17 has one additional override: soft 19 (A,8) vs 6 → DOUBLE.
_SOFT_H17 = {
    13: {2: Action.HIT,    3: Action.HIT,    4: Action.HIT,    5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    14: {2: Action.HIT,    3: Action.HIT,    4: Action.HIT,    5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    15: {2: Action.HIT,    3: Action.HIT,    4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    16: {2: Action.HIT,    3: Action.HIT,    4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    17: {2: Action.HIT,    3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    18: {2: Action.DOUBLE_ELSE_STAND, 3: Action.DOUBLE_ELSE_STAND,
         4: Action.DOUBLE_ELSE_STAND, 5: Action.DOUBLE_ELSE_STAND,
         6: Action.DOUBLE_ELSE_STAND, 7: Action.STAND, 8: Action.STAND,
         9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    19: {2: Action.STAND,  3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND,  7: Action.STAND,  8: Action.STAND,  9: Action.STAND,
         10: Action.STAND, 11: Action.STAND},
    # 20+ always stand
}

# S17 differs from H17 in one cell (6-deck):
# soft 19 (A,8) vs 6: H17=STAND → S17=DOUBLE
# (soft 18 vs 2 no longer differs — both H17 and S17 now correctly double)
_SOFT_S17_OVERRIDES = {
    (19, 6): Action.DOUBLE,
}

# Keep backward-compatible alias used in _lookup_action
_SOFT = _SOFT_H17


def _soft_lookup(soft_total: int, d: int, dealer_hits_soft_17: bool) -> Action:
    """Look up soft-total action, applying S17 overrides where applicable."""
    if not dealer_hits_soft_17:
        override = _SOFT_S17_OVERRIDES.get((soft_total, d))
        if override is not None:
            return override
    return _SOFT_H17.get(soft_total, {}).get(d, Action.HIT)

# Pairs: pair card value -> dealer upcard -> action
_PAIRS = {
    2:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.SPLIT,  8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    3:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.SPLIT,  8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    4:  {2: Action.HIT,    3: Action.HIT,    4: Action.HIT,    5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    5:  {2: Action.DOUBLE, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE,
         6: Action.DOUBLE, 7: Action.DOUBLE, 8: Action.DOUBLE, 9: Action.DOUBLE,
         10: Action.HIT,  11: Action.HIT},
    6:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.HIT,    8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    7:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.SPLIT,  8: Action.HIT,    9: Action.HIT,
         10: Action.HIT,  11: Action.HIT},
    8:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.SPLIT,  8: Action.SPLIT,  9: Action.SPLIT,
         10: Action.SPLIT, 11: Action.SPLIT},
    9:  {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,
         6: Action.SPLIT,  7: Action.STAND,  8: Action.SPLIT,  9: Action.SPLIT,
         10: Action.STAND, 11: Action.STAND},
    10: {2: Action.STAND,  3: Action.STAND,  4: Action.STAND,  5: Action.STAND,
         6: Action.STAND,  7: Action.STAND,  8: Action.STAND,  9: Action.STAND,
         10: Action.STAND, 11: Action.STAND},
    11: {2: Action.SPLIT,  3: Action.SPLIT,  4: Action.SPLIT,  5: Action.SPLIT,  # Aces
         6: Action.SPLIT,  7: Action.SPLIT,  8: Action.SPLIT,  9: Action.SPLIT,
         10: Action.SPLIT, 11: Action.SPLIT},
}

# ---------------------------------------------------------------------------
# Free Bet Blackjack strategy overrides
# Free doubles allowed on hard 9, 10, 11 only
# Free splits allowed on all pairs except 10-value
# Push 22 changes some strategy vs dealer 2
# ---------------------------------------------------------------------------
_FREE_BET_HARD_OVERRIDES = {
    # Hard 9: free double vs 2 (unlike standard where 9v2 is HIT)
    (9, 2): Action.DOUBLE,
    # Hard 11: free double vs Ace (unlike standard H17 where 11vA is HIT)
    (11, 11): Action.DOUBLE,
}

_FREE_BET_PAIR_OVERRIDES = {
    # 10-value pairs: never split in free bet (no free split for 10s)
    # Pairs 2-9 and Aces: always split (free) against everything
    # These are already mostly SPLIT in standard, but some edge cases differ
}


def _dealer_upcard_key(dealer_upcard_value: int) -> int:
    """Normalise dealer upcard to lookup key.
    J/Q/K already have value=10 from Card.value, so they map to 10 naturally.
    Ace has value=11 and must stay 11 — it has its own column in the tables.
    """
    return min(dealer_upcard_value, 11)   # only cap at 11, preserving Ace≠10


# ---------------------------------------------------------------------------
# Free-bet hand strategy (casino covers losses — losses = $0)
#
# Source: Wizard of Odds Free Bet Blackjack analysis.
#
# Key principle: busting costs nothing, so you should hit/double more
# aggressively than in a real-money hand. The strategy below reflects that:
#
# Hard totals (2-card: DOUBLE everything — worst case is $0 loss):
#   - D on all vs all dealer upcards when first 2 cards
#
# Hard totals (3+ cards — can't double, just hit/stand):
#   - Always HIT 4–16 (free to bust)
#   - Hard 17: HIT vs dealer 7, 8, 9, 10, A  (dealer likely has 17+ anyway)
#              STAND vs dealer 2–6
#   - Hard 18: HIT vs dealer 9, 10, A
#              STAND vs dealer 2–8
#   - Hard 19+: STAND
#
# Soft totals (2-card: DOUBLE everything)
# Soft totals (3+ cards):
#   - Soft 17 or less: HIT
#   - Soft 18: HIT vs 9, 10, A; STAND vs 2-8
#   - Soft 19+: STAND
#
# Pairs: Always SPLIT (free, losses covered, resplit = more free wins)
# Surrender: Never (no point — you can't lose)
# ---------------------------------------------------------------------------

_FB_HARD_3PLUS = {
    # total -> dealer upcard -> action  (for 3+ card hands, can't double)
    17: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND,
         6: Action.STAND, 7: Action.HIT,   8: Action.HIT,   9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
    18: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND,
         6: Action.STAND, 7: Action.STAND, 8: Action.STAND, 9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
}

_FB_SOFT_3PLUS = {
    # soft total -> dealer upcard -> action (for 3+ card soft hands)
    18: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND,
         6: Action.STAND, 7: Action.STAND, 8: Action.STAND, 9: Action.HIT,
         10: Action.HIT, 11: Action.HIT},
}


def _get_free_bet_hand_action(hand: 'Hand', dealer_upcard_value: int,
                               can_double: bool, can_split: bool) -> Action:
    """
    Optimal strategy when this hand's losses are covered by the casino.
    (Source: Wizard of Odds Free Bet Blackjack strategy.)
    """
    d = _dealer_upcard_key(dealer_upcard_value)

    # Always split pairs — free, and extra wins cost the player nothing
    if hand.is_pair and can_split:
        return Action.SPLIT

    # 2-card hands: always double (worst case is $0 loss — no reason not to)
    if can_double and len(hand.cards) == 2:
        return Action.DOUBLE

    # 3+ card hands — lookup tables above
    if hand.is_soft and hand.value <= 21:
        total = hand.value
        if total >= 19:
            return Action.STAND
        if total <= 17:
            return Action.HIT
        return _FB_SOFT_3PLUS.get(total, {}).get(d, Action.STAND)

    total = hand.value
    if total >= 19:
        return Action.STAND
    if total <= 16:
        return Action.HIT
    return _FB_HARD_3PLUS.get(total, {}).get(d, Action.STAND)


def get_action(hand: 'Hand', dealer_upcard_value: int, rules: 'RuleSet',
               can_surrender: bool = True, can_double: bool = True,
               can_split: bool = True, is_free_bet_hand: bool = False) -> Action:
    """Return the basic strategy action for the given hand and dealer upcard.

    Args:
        is_free_bet_hand: True when this hand's losses are covered by the casino
            (a free-bet split hand in Free Bet Blackjack). Uses an aggressive
            strategy since busting or losing costs the player nothing.
    """
    # Free-bet split hand: use aggressive free-bet strategy (losses = $0)
    if is_free_bet_hand:
        return _get_free_bet_hand_action(hand, dealer_upcard_value, can_double, can_split)

    d = _dealer_upcard_key(dealer_upcard_value)

    # Pairs — checked before surrender (e.g. always split 8s even vs 10)
    if hand.is_pair and can_split:
        pair_val = hand.cards[0].value  # 11 for Aces, 10 for ten-value, else rank value
        # Only cap J/Q/K (value=10) — Aces stay at 11
        if pair_val != 11:
            pair_val = min(pair_val, 10)
        action = _PAIRS.get(pair_val, {}).get(d, Action.HIT)
        if rules.free_bet and pair_val != 10:
            action = Action.SPLIT       # always free split non-10 pairs in Free Bet mode
        if action == Action.SPLIT:
            return Action.SPLIT

    # Surrender check (only on first two cards, after pair split check)
    if can_surrender and rules.surrender != "none" and len(hand.cards) == 2:
        action = _lookup_action(hand, d, rules)
        if action == Action.SURRENDER:
            return Action.SURRENDER

    # Soft totals
    if hand.is_soft and hand.value <= 21:
        soft_total = hand.value         # already computed with best ace
        if soft_total >= 20:
            return Action.STAND
        action = _soft_lookup(soft_total, d, rules.dealer_hits_soft_17)

        # Resolve Ds (Double else Stand) and D (Double else Hit)
        if action == Action.DOUBLE_ELSE_STAND:
            if can_double and not rules.free_bet:
                action = Action.DOUBLE
            else:
                action = Action.STAND   # "otherwise STAND"
        elif action == Action.DOUBLE:
            if not can_double or rules.free_bet:
                action = Action.HIT     # "otherwise HIT"

        return action

    # Hard totals
    total = hand.value
    if total <= 8:
        return Action.HIT
    if total >= 17:
        return Action.STAND

    action = _HARD.get(total, {}).get(d, Action.HIT)

    if rules.free_bet:
        override = _FREE_BET_HARD_OVERRIDES.get((total, d))
        if override:
            action = override
        # Free doubles only on hard 9/10/11; otherwise convert double->hit
        if action == Action.DOUBLE and total not in (9, 10, 11):
            action = Action.HIT

    if action == Action.DOUBLE and not can_double:
        action = Action.HIT
    # Surrender falls back to HIT whenever surrender isn't available:
    # either the rule is off, or this isn't a fresh 2-card hand (e.g. post-hit 16).
    if action == Action.SURRENDER and (rules.surrender == "none" or not can_surrender):
        action = Action.HIT

    return action


def _lookup_action(hand: 'Hand', d: int, rules: 'RuleSet') -> Action:
    """Raw lookup without can_* guards, for surrender pre-check."""
    if hand.is_soft and hand.value <= 21:
        return _SOFT.get(hand.value, {}).get(d, Action.HIT)
    total = hand.value
    if total <= 8:
        return Action.HIT
    if total >= 17:
        return Action.STAND
    return _HARD.get(total, {}).get(d, Action.HIT)
