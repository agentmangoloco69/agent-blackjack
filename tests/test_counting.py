from simulator.card import Card
from simulator.counting import HiLoCounter, BetRamp


def test_hi_lo_low_cards():
    counter = HiLoCounter()
    for rank in ('2', '3', '4', '5', '6'):
        counter.update(Card(rank, '♠'))
    assert counter.running_count == 5


def test_hi_lo_high_cards():
    counter = HiLoCounter()
    for rank in ('10', 'J', 'Q', 'K', 'A'):
        counter.update(Card(rank, '♠'))
    assert counter.running_count == -5


def test_hi_lo_neutral():
    counter = HiLoCounter()
    for rank in ('7', '8', '9'):
        counter.update(Card(rank, '♠'))
    assert counter.running_count == 0


def test_true_count():
    counter = HiLoCounter()
    counter.running_count = 6
    assert counter.true_count(2.0) == 3.0


def test_bet_ramp():
    ramp = BetRamp(unit=25)
    assert ramp.bet_size(-1) == 25    # negative count -> 1 unit
    assert ramp.bet_size(1) == 50     # TC+1 -> 2 units
    assert ramp.bet_size(4) == 150    # TC+4 -> 6 units
    assert ramp.bet_size(5) == 200    # TC+5 -> 8 units
