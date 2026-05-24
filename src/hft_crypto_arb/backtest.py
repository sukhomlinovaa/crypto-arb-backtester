from __future__ import annotations

from dataclasses import asdict

from .config import BacktestConfig
from .execution import ExecutionSimulator
from .feed import MarketDataSequencer
from .market import generate_events
from .metrics import summarize, trades_frame
from .portfolio import Portfolio
from .replay import replay_equity
from .strategy import CrossVenueArbStrategy
from .types import MetricSummary, Trade


def run_backtest(cfg: BacktestConfig) -> tuple[list[Trade], MetricSummary]:
    events = generate_events(cfg)
    books = MarketDataSequencer(venues=tuple(cfg.venues.keys())).normalize(events)
    strategy = CrossVenueArbStrategy(cfg)
    portfolio = Portfolio(cfg)
    executor = ExecutionSimulator(cfg, books)

    trades: list[Trade] = []
    for book in books:
        signal = strategy.on_book(book)
        if signal is None:
            continue
        trade = executor.execute(signal, portfolio)
        if trade is not None:
            trades.append(trade)

    live = replay_equity(trades)
    replay = replay_equity(trades)
    if not live.equals(replay):
        raise AssertionError("Replay mismatch")

    return trades, summarize(trades, portfolio)


def run_backtest_report(cfg: BacktestConfig) -> dict:
    trades, summary = run_backtest(cfg)
    return {
        "summary": asdict(summary),
        "trades_head": trades_frame(trades).head(10).to_dict(orient="records"),
    }
