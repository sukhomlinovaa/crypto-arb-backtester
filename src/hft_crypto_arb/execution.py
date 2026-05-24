from __future__ import annotations

from bisect import bisect_left
import random

from .config import BacktestConfig
from .orderbook import bps, walk_book
from .portfolio import Portfolio
from .types import ConsolidatedBook, LegFill, Signal, Trade


class LatencyModel:
    def __init__(self, cfg: BacktestConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed + 10_000)

    def sample_ns(self) -> int:
        jitter = self.rng.randint(0, max(0, self.cfg.latency_jitter_ns))
        return self.cfg.latency_decision_to_order_ns + self.cfg.latency_exchange_ack_ns + jitter


class ExecutionSimulator:
    """Latency-aware, idempotent two-leg taker execution simulator."""

    def __init__(self, cfg: BacktestConfig, books: list[ConsolidatedBook]):
        self.cfg = cfg
        self.books = books
        self.book_times = [book.ts_ns for book in books]
        self.latency = LatencyModel(cfg)
        self.seen_signal_ids: set[str] = set()

    def execute(self, signal: Signal, portfolio: Portfolio) -> Trade | None:
        if signal.signal_id in self.seen_signal_ids:
            return None
        self.seen_signal_ids.add(signal.signal_id)

        fill_after_ns = signal.ts_ns + self.latency.sample_ns()
        i = bisect_left(self.book_times, fill_after_ns)
        if i >= len(self.books):
            return None

        fill_book = self.books[i]
        buy_book = fill_book.books[signal.buy_venue]
        sell_book = fill_book.books[signal.sell_venue]
        qty = signal.qty

        buy_qty, buy_vwap_raw = walk_book(buy_book.asks, qty)
        sell_qty, sell_vwap_raw = walk_book(sell_book.bids, qty)
        executed_qty = min(buy_qty, sell_qty)
        if executed_qty < self.cfg.min_order_qty:
            return None

        if abs(executed_qty - qty) > 1e-9:
            buy_qty, buy_vwap_raw = walk_book(buy_book.asks, executed_qty)
            sell_qty, sell_vwap_raw = walk_book(sell_book.bids, executed_qty)

        slip = bps(self.cfg.slippage_bps)
        buy_vwap = buy_vwap_raw * (1.0 + slip)
        sell_vwap = sell_vwap_raw * (1.0 - slip)

        buy_fee_rate = bps(self.cfg.venues[signal.buy_venue].taker_fee_bps)
        sell_fee_rate = bps(self.cfg.venues[signal.sell_venue].taker_fee_bps)

        buy_notional = executed_qty * buy_vwap
        sell_notional = executed_qty * sell_vwap
        buy_fee = buy_notional * buy_fee_rate
        sell_fee = sell_notional * sell_fee_rate

        buy_fill = LegFill(
            venue=signal.buy_venue,
            side="BUY",
            qty=executed_qty,
            vwap=buy_vwap,
            notional=buy_notional,
            fee=buy_fee,
        )
        sell_fill = LegFill(
            venue=signal.sell_venue,
            side="SELL",
            qty=executed_qty,
            vwap=sell_vwap,
            notional=sell_notional,
            fee=sell_fee,
        )

        realized = (sell_notional - sell_fee) - (buy_notional + buy_fee)
        trade = Trade(
            signal_id=signal.signal_id,
            signal_ts_ns=signal.ts_ns,
            fill_ts_ns=fill_book.ts_ns,
            direction=signal.direction,
            qty=executed_qty,
            buy_fill=buy_fill,
            sell_fill=sell_fill,
            expected_net_pnl=signal.expected_net_pnl,
            realized_net_pnl=realized,
            edge_decay=signal.expected_net_pnl - realized,
            status="FILLED" if abs(executed_qty - signal.qty) < 1e-9 else "PARTIAL",
        )
        if not portfolio.can_apply(buy_fill, sell_fill):
            return None
        portfolio.apply(trade)
        return trade
