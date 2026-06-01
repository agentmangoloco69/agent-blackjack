import pytest
from simulator.card import Card
from simulator.hand import Hand


def make_hand(*rank_suit_pairs):
    h = Hand()
    for rank, suit in rank_suit_pairs:
        h.add(Card(rank, suit))
    return h


def test_hard_total():
    h = make_hand(('7', '♠'), ('9', '♥'))
    assert h.value == 16
    assert not h.is_soft


def test_soft_ace():
    h = make_hand(('A', '♠'), ('6', '♥'))
    assert h.value == 17
    assert h.is_soft


def test_ace_downgraded():
    h = make_hand(('A', '♠'), ('9', '♥'), ('5', '♦'))
    assert h.value == 15
    assert not h.is_soft


def test_blackjack():
    h = make_hand(('A', '♠'), ('K', '♥'))
    assert h.is_blackjack
    assert h.value == 21


def test_bust():
    h = make_hand(('10', '♠'), ('9', '♥'), ('5', '♦'))
    assert h.is_bust
    assert h.value == 24


def test_pair_detection():
    h = make_hand(('8', '♠'), ('8', '♥'))
    assert h.is_pair


def test_pair_ten_value():
    h = make_hand(('K', '♠'), ('J', '♥'))
    assert h.is_pair
    assert h.pair_rank == '10'
