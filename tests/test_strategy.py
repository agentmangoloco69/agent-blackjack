import pytest
from simulator.card import Card
from simulator.hand import Hand
from simulator.rules import RuleSet, STANDARD_6D_H17
from simulator.strategy import Action, get_action


def make_hand(*ranks):
    h = Hand()
    for rank in ranks:
        suit = '♠'
        h.add(Card(rank, suit))
    return h


rules = STANDARD_6D_H17


def test_always_split_aces():
    h = make_hand('A', 'A')
    assert get_action(h, 10, rules) == Action.SPLIT


def test_always_split_eights():
    h = make_hand('8', '8')
    assert get_action(h, 10, rules) == Action.SPLIT


def test_never_split_tens():
    h = make_hand('K', 'Q')
    assert get_action(h, 6, rules) == Action.STAND


def test_double_11_vs_10():
    h = make_hand('7', '4')
    assert get_action(h, 10, rules) == Action.DOUBLE


def test_stand_hard_17():
    h = make_hand('10', '7')
    assert get_action(h, 7, rules) == Action.STAND


def test_hit_hard_8():
    h = make_hand('5', '3')
    assert get_action(h, 6, rules) == Action.HIT


def test_surrender_16_vs_10():
    h = make_hand('9', '7')
    assert get_action(h, 10, rules) == Action.SURRENDER


def test_soft_18_double_vs_6():
    h = make_hand('A', '7')
    assert h.is_soft
    assert get_action(h, 6, rules) == Action.DOUBLE


def test_soft_19_stand():
    h = make_hand('A', '8')
    assert get_action(h, 6, rules) == Action.STAND
