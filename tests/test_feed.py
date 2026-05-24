from hft_crypto_arb.feed import MarketDataSequencer
from hft_crypto_arb.types import BookUpdate, Level


def book(venue, recv, seq, bid=100.0, ask=101.0):
    return BookUpdate(
        venue=venue,
        symbol="BTC-USD",
        exchange_ts_ns=recv - 10,
        recv_ts_ns=recv,
        sequence=seq,
        bids=(Level(bid, 1.0),),
        asks=(Level(ask, 1.0),),
    )


def test_sequencer_emits_monotonic_consolidated_books():
    events = [
        book("binance", 3, 1),
        book("coinbase", 1, 1),
        book("coinbase", 2, 2),
        book("binance", 4, 2),
    ]
    out = MarketDataSequencer(("coinbase", "binance")).normalize(events)
    assert len(out) >= 2
    assert [b.ts_ns for b in out] == sorted(b.ts_ns for b in out)


def test_sequencer_ignores_stale_sequence_but_last_duplicate_wins():
    events = [
        book("coinbase", 1, 1, bid=100.0, ask=101.0),
        book("binance", 2, 1),
        book("coinbase", 3, 1, bid=102.0, ask=103.0),  # duplicate seq, later wins
        book("coinbase", 4, 0, bid=1.0, ask=2.0),      # stale ignored
        book("binance", 5, 2),
    ]
    out = MarketDataSequencer(("coinbase", "binance")).normalize(events)
    assert out[-1].books["coinbase"].best_bid == 102.0
