from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .portfolio import Portfolio
from .types import MetricSummary, Trade


def equity_curve(trades: Sequence[Trade]) -> pd.Series:
    eq = 0.0
    points: list[tuple[int, float]] = []
    for trade in trades:
        eq += trade.realized_net_pnl
        points.append((trade.fill_ts_ns, eq))
    return pd.Series([v for _, v in points], index=[t for t, _ in points], dtype=float)


def summarize(trades: Sequence[Trade], portfolio: Portfolio) -> MetricSummary:
    if not trades:
        return MetricSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    pnls = [t.realized_net_pnl for t in trades]
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = sum(x for x in pnls if x < 0)
    curve = equity_curve(trades)
    dd = curve - curve.cummax()
    return MetricSummary(
        n_trades=len(trades),
        net_pnl=sum(pnls),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        win_rate=sum(1 for x in pnls if x > 0) / len(pnls),
        avg_pnl=sum(pnls) / len(pnls),
        avg_expected_edge_bps=sum(
            10_000.0 * t.expected_net_pnl / max(t.buy_fill.notional, 1e-12) for t in trades
        ) / len(trades),
        avg_edge_decay=sum(t.edge_decay for t in trades) / len(trades),
        max_drawdown=float(dd.min()),
        turnover=portfolio.turnover,
    )


def trades_frame(trades: Sequence[Trade]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_ts_ns": t.signal_ts_ns,
                "fill_ts_ns": t.fill_ts_ns,
                "direction": t.direction.value,
                "qty": t.qty,
                "buy_venue": t.buy_fill.venue,
                "sell_venue": t.sell_fill.venue,
                "buy_vwap": t.buy_fill.vwap,
                "sell_vwap": t.sell_fill.vwap,
                "expected_pnl": t.expected_net_pnl,
                "realized_pnl": t.realized_net_pnl,
                "edge_decay": t.edge_decay,
                "status": t.status,
                "expected_edge_bps": trade.expected_edge_bps,
                "realized_edge_bps": trade.realized_edge_bps,
                "edge_decay_bps": trade.edge_decay_bps,
                "edge_decay": trade.edge_decay,
                "realized_pnl": trade.realized_net_pnl,
            }
            for t in trades
        ]
    )
