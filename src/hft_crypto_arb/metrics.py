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

    return pd.Series(
        [value for _, value in points],
        index=[ts for ts, _ in points],
        dtype=float,
    )


def summarize(trades: Sequence[Trade], portfolio: Portfolio) -> MetricSummary:
    if not trades:
        return MetricSummary(
            n_trades=0,
            net_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            win_rate=0.0,
            avg_pnl=0.0,
            avg_expected_edge_bps=0.0,
            avg_edge_decay=0.0,
            max_drawdown=0.0,
            turnover=0.0,
        )

    pnls = [trade.realized_net_pnl for trade in trades]
    curve = equity_curve(trades)
    drawdown = curve - curve.cummax()

    return MetricSummary(
        n_trades=len(trades),
        net_pnl=sum(pnls),
        gross_profit=sum(pnl for pnl in pnls if pnl > 0),
        gross_loss=sum(pnl for pnl in pnls if pnl < 0),
        win_rate=sum(1 for pnl in pnls if pnl > 0) / len(pnls),
        avg_pnl=sum(pnls) / len(pnls),
        avg_expected_edge_bps=sum(t.expected_edge_bps for t in trades) / len(trades),
        avg_edge_decay=sum(t.edge_decay_bps for t in trades) / len(trades),
        max_drawdown=float(drawdown.min()),
        turnover=portfolio.turnover,
    )


def trades_frame(trades: Sequence[Trade]) -> pd.DataFrame:
    rows = []

    for trade in trades:
        rows.append(
            {
                "signal_id": trade.signal_id,
                "signal_ts_ns": trade.signal_ts_ns,
                "fill_ts_ns": trade.fill_ts_ns,
                "direction": trade.direction.value,
                "qty": trade.qty,
                "buy_venue": trade.buy_fill.venue,
                "sell_venue": trade.sell_fill.venue,
                "buy_vwap": trade.buy_fill.vwap,
                "sell_vwap": trade.sell_fill.vwap,
                "buy_notional": trade.buy_fill.notional,
                "sell_notional": trade.sell_fill.notional,
                "buy_fee": trade.buy_fill.fee,
                "sell_fee": trade.sell_fill.fee,
                "expected_pnl": trade.expected_net_pnl,
                "realized_pnl": trade.realized_net_pnl,
                "edge_decay": trade.edge_decay,
                "expected_edge_bps": trade.expected_edge_bps,
                "realized_edge_bps": trade.realized_edge_bps,
                "edge_decay_bps": trade.edge_decay_bps,
                "status": trade.status,
            }
        )

    return pd.DataFrame(rows)