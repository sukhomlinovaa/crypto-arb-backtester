from __future__ import annotations

from hashlib import blake2b

from .config import BacktestConfig
from .orderbook import available_depth, bps, walk_book
from .types import ConsolidatedBook, Direction, Signal


class CrossVenueArbStrategy:
    """Depth-aware taker/taker cross-venue arbitrage signal engine."""

    def __init__(self, cfg: BacktestConfig):
        self.cfg = cfg

    def on_book(self, book: ConsolidatedBook) -> Signal | None:
        cb = book.books["coinbase"]
        bn = book.books["binance"]
        candidates = [
            self._candidate(book.ts_ns, Direction.COINBASE_TO_BINANCE, "coinbase", cb.asks, "binance", bn.bids),
            self._candidate(book.ts_ns, Direction.BINANCE_TO_COINBASE, "binance", bn.asks, "coinbase", cb.bids),
        ]
        candidates = [c for c in candidates if c is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.expected_net_pnl)

    def _candidate(self, ts_ns, direction, buy_venue, asks, sell_venue, bids) -> Signal | None:
        cfg = self.cfg
        buy_fee = bps(cfg.venues[buy_venue].taker_fee_bps)
        sell_fee = bps(cfg.venues[sell_venue].taker_fee_bps)
        slip = bps(cfg.slippage_bps)

        max_qty_by_depth = min(available_depth(asks), available_depth(bids), cfg.max_order_qty)
        if max_qty_by_depth < cfg.min_order_qty:
            return None

        # Risk notional cap approximated by top ask before walking the book.
        max_qty_by_notional = cfg.risk_max_notional_per_trade / asks[0].price
        qty = min(max_qty_by_depth, max_qty_by_notional)
        qty = round(qty, 8)
        if qty < cfg.min_order_qty:
            return None

        buy_executed, buy_vwap_raw = walk_book(asks, qty)
        sell_executed, sell_vwap_raw = walk_book(bids, qty)
        qty = min(buy_executed, sell_executed)
        if qty < cfg.min_order_qty:
            return None

        buy_vwap = buy_vwap_raw * (1.0 + slip)
        sell_vwap = sell_vwap_raw * (1.0 - slip)
        cost = qty * buy_vwap * (1.0 + buy_fee)
        proceeds = qty * sell_vwap * (1.0 - sell_fee)
        pnl = proceeds - cost
        notional = qty * buy_vwap
        edge_bps = 10_000.0 * pnl / notional if notional > 0 else 0.0

        if edge_bps < cfg.min_net_edge_bps:
            return None

        signal_id = blake2b(
            f"{ts_ns}:{direction.value}:{qty:.8f}:{buy_vwap:.8f}:{sell_vwap:.8f}".encode(),
            digest_size=8,
        ).hexdigest()
        return Signal(
            signal_id=signal_id,
            ts_ns=ts_ns,
            direction=direction,
            buy_venue=buy_venue,
            sell_venue=sell_venue,
            qty=qty,
            expected_buy_vwap=buy_vwap,
            expected_sell_vwap=sell_vwap,
            expected_net_pnl=pnl,
            expected_edge_bps=edge_bps,
        )
