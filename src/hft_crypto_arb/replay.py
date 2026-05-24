from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .types import Trade


def replay_equity(trades: Sequence[Trade]) -> pd.Series:
    total = 0.0
    points: list[tuple[int, float]] = []
    for trade in trades:
        total += float(trade.realized_net_pnl)
        points.append((int(trade.fill_ts_ns), total))
    return pd.Series([v for _, v in points], index=[t for t, _ in points], dtype=float)
