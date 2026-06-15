"""
Illustrious 18 + Fab 4 deviations (Hi-Lo, indices for 6-deck H17).

Each entry: (player_total_or_code, dealer_upcard, threshold, direction, action)
  - direction '+': deviate when true_count >= threshold
  - direction '-': deviate when true_count <= threshold
  - player_total_or_code: integer total, or special strings:
      'INSURANCE' — take insurance
      'SOFT_18'   — soft 18 (A,7)
      'SOFT_19'   — soft 19 (A,8)
"""

from typing import List, Tuple, Optional
from .strategy import Action

DeviationEntry = Tuple[object, int, float, str, Action]

ILLUSTRIOUS_18: List[DeviationEntry] = [
    # (player_total, dealer_upcard, index, direction, action)
    ('INSURANCE', 0,  3.0, '+', Action.HIT),  # 'HIT' placeholder — engine interprets as "take insurance"
    (16, 10,  0.0, '+', Action.STAND),
    (15, 10,  4.0, '+', Action.STAND),
    (20,  5,  5.0, '+', Action.SPLIT),         # split 10s vs 5 at TC>=+5
    (20,  6,  4.0, '+', Action.SPLIT),         # split 10s vs 6 at TC>=+4
    (10, 10,  4.0, '+', Action.DOUBLE),
    (12,  3,  2.0, '+', Action.STAND),
    (12,  2,  3.0, '+', Action.STAND),
    (11, 11,  1.0, '+', Action.DOUBLE),
    (9,   2,  1.0, '+', Action.DOUBLE),
    (10, 11,  4.0, '+', Action.DOUBLE),
    (9,   7,  3.0, '+', Action.DOUBLE),         # double 9v7 at TC>=+3
    (16,  9,  5.0, '+', Action.STAND),
    (13,  2, -1.0, '-', Action.HIT),
    (12,  4,  0.0, '+', Action.STAND),
    (12,  5, -2.0, '-', Action.HIT),
    (12,  6, -1.0, '-', Action.HIT),
    (13,  3, -2.0, '-', Action.HIT),
]

# Fab 4 surrenders (late surrender deviations)
FAB_4: List[DeviationEntry] = [
    (14, 10,  3.0, '+', Action.SURRENDER),
    (15, 10,  0.0, '+', Action.SURRENDER),
    (15, 11,  1.0, '+', Action.SURRENDER),
    (15,  9,  2.0, '+', Action.SURRENDER),
]

ALL_DEVIATIONS = ILLUSTRIOUS_18 + FAB_4


def get_deviation(
    player_total: int,
    dealer_upcard: int,
    true_count: float,
    is_pair_of_tens: bool = False,
    is_soft: bool = False,
    is_pair: bool = False,
) -> Optional[Action]:
    """Return deviation action if applicable, else None (use basic strategy).

    The Illustrious 18 / Fab 4 entries here are all *hard-total* deviations, so:
      - Soft hands never deviate (a soft 16 is A,5 — not the hard 16 the table
        means). Returning None lets basic strategy hit it correctly.
      - Pair hands defer to basic-strategy split logic, EXCEPT the explicit
        split-tens deviation (total_code 20), which is keyed on is_pair_of_tens.
    """
    if is_soft:
        return None
    for total_code, upcard, threshold, direction, action in ALL_DEVIATIONS:
        if upcard != dealer_upcard:
            continue
        if total_code == 'INSURANCE':
            continue  # handled separately in engine
        if total_code == 20:
            if not is_pair_of_tens:
                continue
        elif is_pair:
            # Hard-total deviation, but this is a pair — let basic strategy
            # decide whether to split (e.g. don't "stand 12" on a pair of 6s).
            continue
        if isinstance(total_code, int) and total_code != player_total:
            continue
        if direction == '+' and true_count >= threshold:
            return action
        if direction == '-' and true_count <= threshold:
            return action
    return None


def should_take_insurance(true_count: float) -> bool:
    """Take insurance when true count >= +3."""
    return true_count >= 3.0
