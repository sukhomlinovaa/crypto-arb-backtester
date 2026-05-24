from hft_crypto_arb.orderbook import walk_book
from hft_crypto_arb.types import Level


def test_walk_book_partial_depth_vwap():
    levels = (Level(100.0, 1.0), Level(101.0, 2.0))
    qty, vwap = walk_book(levels, 2.0)
    assert qty == 2.0
    assert vwap == 100.5


def test_walk_book_insufficient_depth_partial_fill():
    levels = (Level(100.0, 0.5),)
    qty, vwap = walk_book(levels, 2.0)
    assert qty == 0.5
    assert vwap == 100.0
