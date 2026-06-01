"""
Run this from the ClaudeBlackJack folder to view strategy tables:
    python show_strategy.py

Optional arguments:
    python show_strategy.py s17        -- show S17 instead of H17
    python show_strategy.py 2d         -- show 2-deck game
    python show_strategy.py freebet    -- show Free Bet Blackjack
    python show_strategy.py h17 freebet -- combine flags
"""
import sys
from simulator.rules import RuleSet
from simulator.strategy_table import print_strategy_tables

args = [a.lower() for a in sys.argv[1:]]

# Parse flags
h17        = 's17' not in args
num_decks  = 2 if '2d' in args else (1 if '1d' in args else 6)
free_bet   = 'freebet' in args
surrender  = 'nosurr' not in args

rules = RuleSet(
    num_decks=num_decks,
    dealer_hits_soft_17=h17,
    surrender='late' if surrender else 'none',
    double_after_split=True,
    free_bet=free_bet,
)

print_strategy_tables(rules, show_free_bet_hand=free_bet, colour=False)
