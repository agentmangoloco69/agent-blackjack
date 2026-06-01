"""
Strategy table generator — produces human-readable strategy charts for any RuleSet.

Usage:
    from simulator.rules import STANDARD_6D_H17, FREE_BET_6D
    from simulator.strategy_table import print_strategy_tables

    print_strategy_tables(STANDARD_6D_H17)
    print_strategy_tables(FREE_BET_6D, show_free_bet_hand=True)
"""

from typing import Dict, List
from .rules import RuleSet
from .strategy import Action, get_action
from .hand import Hand
from .card import Card

# ── Abbreviations shown in cells ────────────────────────────────────────────
_ABBR = {
    Action.HIT:               'H',
    Action.STAND:             'S',
    Action.DOUBLE:            'D',
    Action.DOUBLE_ELSE_STAND: 'Ds',
    Action.SPLIT:             'P',
    Action.SURRENDER:         'Su',
}

# ── ANSI colours for terminal output ────────────────────────────────────────
_CLR = {
    'H':  '\033[33m',   # yellow
    'S':  '\033[32m',   # green
    'D':  '\033[34m',   # blue
    'Ds': '\033[36m',   # cyan  (Double else Stand)
    'P':  '\033[35m',   # magenta
    'Su': '\033[31m',   # red
    'reset': '\033[0m',
}

DEALER_UPCARDS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
DEALER_LABELS  = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']


# ── Hand factory helpers ─────────────────────────────────────────────────────

def _hard_hand(total: int) -> Hand:
    """Build a hard-total hand with no pair and no ace counted as 11."""
    h = Hand()
    if total <= 11:
        h.add(Card(str(total - 2), '♠'))
        h.add(Card('2', '♥'))
    else:
        h.add(Card('10', '♠'))
        h.add(Card(str(total - 10), '♥'))
    return h


def _soft_hand(total: int) -> Hand:
    """Build a soft hand: Ace + (total - 11)."""
    other = total - 11
    rank = str(other) if other != 10 else '10'
    h = Hand()
    h.add(Card('A', '♠'))
    h.add(Card(rank, '♥'))
    return h


def _pair_hand(rank: str) -> Hand:
    """Build a pair hand."""
    h = Hand()
    h.add(Card(rank, '♠'))
    h.add(Card(rank, '♥'))
    return h


# ── Core table builder ───────────────────────────────────────────────────────

def build_hard_table(rules: RuleSet, is_free_bet_hand: bool = False,
                     two_card: bool = True) -> Dict[int, List[str]]:
    """Return hard totals table: {player_total: [action_str per dealer upcard]}.

    Args:
        two_card: If True, show 2-card hand actions (doubles available).
                  If False, show 3+-card hand actions (no doubling).
                  For free-bet hands, 3-card view is more informative because
                  2-card free-bet always doubles — the nuance is in the 3+ card decisions.
    """
    table = {}
    for total in range(5, 22):
        hand = _hard_hand(total)  # always 2 cards from the factory
        row = []
        for upcard in DEALER_UPCARDS:
            if total >= 21:
                row.append('S')
            else:
                action = get_action(
                    hand, upcard, rules,
                    can_surrender=(total <= 16 and two_card),
                    can_double=two_card,
                    can_split=False,
                    is_free_bet_hand=is_free_bet_hand,
                )
                row.append(_ABBR[action])
        table[total] = row
    return table


def build_soft_table(rules: RuleSet, is_free_bet_hand: bool = False,
                     two_card: bool = True) -> Dict[int, List[str]]:
    """Return soft totals table: {soft_total: [action_str per dealer upcard]}.

    Uses the raw lookup (before can_double resolution) so that Ds appears
    as 'Ds' rather than collapsing to 'D' or 'S'.
    """
    from .strategy import _soft_lookup, _dealer_upcard_key, Action as A
    table = {}
    for total in range(13, 22):
        hand = _soft_hand(total)
        row = []
        for upcard in DEALER_UPCARDS:
            if total >= 20:          # soft 20 (A,9) and soft 21 (A,10): always stand
                row.append('S')
            elif is_free_bet_hand:
                action = get_action(
                    hand, upcard, rules,
                    can_surrender=False,
                    can_double=two_card,
                    can_split=False,
                    is_free_bet_hand=True,
                )
                row.append(_ABBR[action])
            else:
                # Show raw table value so Ds is preserved
                d = _dealer_upcard_key(upcard)
                raw = _soft_lookup(total, d, rules.dealer_hits_soft_17)
                if raw == A.DOUBLE_ELSE_STAND and not two_card:
                    row.append('S')   # 3+ card: can't double → STAND
                else:
                    row.append(_ABBR[raw])
                continue
        table[total] = row
    return table


_PAIR_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'A']
_PAIR_LABELS = ['2,2', '3,3', '4,4', '5,5', '6,6', '7,7', '8,8', '9,9', '10,10', 'A,A']

def build_pair_table(rules: RuleSet, is_free_bet_hand: bool = False) -> Dict[str, List[str]]:
    """Return pairs table: {pair_label: [action_str per dealer upcard]}."""
    table = {}
    for rank, label in zip(_PAIR_RANKS, _PAIR_LABELS):
        hand = _pair_hand(rank)
        row = []
        for upcard in DEALER_UPCARDS:
            action = get_action(
                hand, upcard, rules,
                can_surrender=False,
                can_double=True,
                can_split=True,
                is_free_bet_hand=is_free_bet_hand,
            )
            row.append(_ABBR[action])
        table[label] = row
    return table


# ── Printer ──────────────────────────────────────────────────────────────────

def _colour(cell: str) -> str:
    return f"{_CLR.get(cell, '')}{cell:>3}{_CLR['reset']}"


def _print_table(title: str, row_labels: List[str], rows: List[List[str]]):
    col_w = 4
    header = f"{'':>6}" + ''.join(f"{lbl:>{col_w}}" for lbl in DEALER_LABELS)
    sep = '-' * len(header)
    print(f"\n  {title}")
    print(f"  {sep}")
    print(f"  {header}")
    print(f"  {sep}")
    for label, row in zip(row_labels, rows):
        cells = ''.join(_colour(c) for c in row)
        print(f"  {label:>5} {cells}")
    print(f"  {sep}")
    print(f"  Legend: H=Hit  S=Stand  D=Double  P=Split  Su=Surrender")


def print_strategy_tables(rules: RuleSet, show_free_bet_hand: bool = False,
                           colour: bool = True):
    """Print all strategy tables for the given ruleset."""
    if not colour:
        global _CLR
        _CLR = {k: '' for k in _CLR}

    label = _ruleset_label(rules)
    print(f"\n{'='*60}")
    print(f"  STRATEGY TABLES -- {label}")
    print(f"{'='*60}")

    # ── Hard totals ──
    hard = build_hard_table(rules)
    _print_table(
        "HARD TOTALS (dealer upcard ->)",
        [str(t) for t in range(5, 22)],
        [hard[t] for t in range(5, 22)],
    )

    # ── Soft totals ──
    soft = build_soft_table(rules)
    _print_table(
        "SOFT TOTALS (Ace + X)",
        [f"A,{t-11}" for t in range(13, 22)],
        [soft[t] for t in range(13, 22)],
    )

    # ── Pairs ──
    pairs = build_pair_table(rules)
    _print_table(
        "PAIRS",
        _PAIR_LABELS,
        [pairs[lbl] for lbl in _PAIR_LABELS],
    )

    if show_free_bet_hand:
        print(f"\n{'-'*60}")
        print(f"  FREE BET HAND STRATEGY (losses covered by casino)")
        print(f"  NOTE: On any 2-card free-bet hand -> always DOUBLE.")
        print(f"  Tables below show 3+ card decisions (hit vs stand).")
        print(f"{'-'*60}")

        fb_hard = build_hard_table(rules, is_free_bet_hand=True, two_card=False)
        _print_table(
            "HARD TOTALS -- free bet hand (3+ cards)",
            [str(t) for t in range(5, 22)],
            [fb_hard[t] for t in range(5, 22)],
        )

        fb_soft = build_soft_table(rules, is_free_bet_hand=True, two_card=False)
        _print_table(
            "SOFT TOTALS -- free bet hand (3+ cards)",
            [f"A,{t-11}" for t in range(13, 22)],
            [fb_soft[t] for t in range(13, 22)],
        )

        fb_pairs = build_pair_table(rules, is_free_bet_hand=True)
        _print_table(
            "PAIRS -- free bet hand (always split, incl 10s)",
            _PAIR_LABELS,
            [fb_pairs[lbl] for lbl in _PAIR_LABELS],
        )


def _ruleset_label(rules: RuleSet) -> str:
    parts = [f"{rules.num_decks}D"]
    parts.append("H17" if rules.dealer_hits_soft_17 else "S17")
    if rules.surrender != "none":
        parts.append(f"L-surr" if rules.surrender == "late" else "E-surr")
    if rules.double_after_split:
        parts.append("DAS")
    if rules.free_bet:
        parts.append("FreeBet")
    if not rules.dealer_peeks:
        parts.append("NoPeek")
    return " ".join(parts)


# ── Dict export (for Dash integration later) ─────────────────────────────────

def get_all_tables(rules: RuleSet, is_free_bet_hand: bool = False) -> dict:
    """Return all tables as dicts suitable for conversion to DataFrames in Dash."""
    return {
        'hard': build_hard_table(rules, is_free_bet_hand),
        'soft': build_soft_table(rules, is_free_bet_hand),
        'pairs': build_pair_table(rules, is_free_bet_hand),
        'dealer_labels': DEALER_LABELS,
    }
