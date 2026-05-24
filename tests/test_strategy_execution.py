from hft_crypto_arb.config import BacktestConfig, VenueConfig
from hft_crypto_arb.execution import ExecutionSimulator
from hft_crypto_arb.portfolio import Portfolio
from hft_crypto_arb.strategy import CrossVenueArbStrategy
from hft_crypto_arb.types import BookUpdate, ConsolidatedBook, Level


def cfg(**kw):
    base = dict(
        seed=1,
        n_ticks=10,
        tick_ns=1,
        depth=2,
        max_order_qty=1.0,
        min_order_qty=0.001,
        min_net_edge_bps=1.0,
        slippage_bps=0.0,
        starting_cash_usd=1_000_000.0,
        latency_decision_to_order_ns=0,
        latency_exchange_ack_ns=0,
        latency_jitter_ns=0,
        venues={
            "coinbase": VenueConfig(taker_fee_bps=0.0, maker_fee_bps=0.0),
            "binance": VenueConfig(taker_fee_bps=0.0, maker_fee_bps=0.0),
        },
    )
    base.update(kw)
    return BacktestConfig(**base)


def make_book(ts, cb_bid=99.0, cb_ask=100.0, bn_bid=103.0, bn_ask=104.0):
    return ConsolidatedBook(
        ts_ns=ts,
        books={
            "coinbase": BookUpdate(
                "coinbase", "BTC-USD", ts, ts, ts,
                bids=(Level(cb_bid, 1.0), Level(cb_bid - 1, 1.0)),
                asks=(Level(cb_ask, 1.0), Level(cb_ask + 1, 1.0)),
            ),
            "binance": BookUpdate(
                "binance", "BTC-USD", ts, ts, ts,
                bids=(Level(bn_bid, 1.0), Level(bn_bid - 1, 1.0)),
                asks=(Level(bn_ask, 1.0), Level(bn_ask + 1, 1.0)),
            ),
        },
    )


def test_strategy_detects_depth_aware_arb():
    c = cfg()
    signal = CrossVenueArbStrategy(c).on_book(make_book(1))
    assert signal is not None
    assert signal.buy_venue == "coinbase"
    assert signal.sell_venue == "binance"
    assert signal.expected_net_pnl > 0


def test_execution_applies_latency_and_realized_edge_decay():
    c = cfg(latency_decision_to_order_ns=5)
    books = [
        make_book(1, cb_ask=100.0, bn_bid=103.0),
        make_book(6, cb_ask=101.0, bn_bid=102.0),
    ]
    signal = CrossVenueArbStrategy(c).on_book(books[0])
    assert signal is not None
    portfolio = Portfolio(c)
    trade = ExecutionSimulator(c, books).execute(signal, portfolio)
    assert trade is not None
    assert trade.fill_ts_ns == 6
    assert trade.expected_net_pnl > trade.realized_net_pnl
    assert trade.edge_decay > 0


def test_execution_is_idempotent():
    c = cfg()
    books = [make_book(1)]
    signal = CrossVenueArbStrategy(c).on_book(books[0])
    assert signal is not None
    portfolio = Portfolio(c)
    executor = ExecutionSimulator(c, books)
    first = executor.execute(signal, portfolio)
    second = executor.execute(signal, portfolio)
    assert first is not None
    assert second is None
