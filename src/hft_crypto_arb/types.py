from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Direction(str, Enum):
    COINBASE_TO_BINANCE = "coinbase->binance"
    BINANCE_TO_COINBASE = "binance->coinbase"


@dataclass(frozen=True, slots=True)
class Level:
    price: float
    size: float


@dataclass(frozen=True, slots=True)
class BookUpdate:
    venue: str
    symbol: str
    exchange_ts_ns: int
    recv_ts_ns: int
    sequence: int
    bids: tuple[Level, ...]
    asks: tuple[Level, ...]

    @property
    def best_bid(self) -> float:
        return self.bids[0].price

    @property
    def best_ask(self) -> float:
        return self.asks[0].price

    @property
    def mid(self) -> float:
        return 0.5 * (self.best_bid + self.best_ask)


@dataclass(frozen=True, slots=True)
class ConsolidatedBook:
    ts_ns: int
    books: Mapping[str, BookUpdate]


@dataclass(frozen=True, slots=True)
class Signal:
    signal_id: str
    ts_ns: int
    direction: Direction
    buy_venue: str
    sell_venue: str
    qty: float
    expected_buy_vwap: float
    expected_sell_vwap: float
    expected_net_pnl: float
    expected_edge_bps: float


@dataclass(frozen=True, slots=True)
class LegFill:
    venue: str
    side: str  # BUY or SELL
    qty: float
    vwap: float
    notional: float
    fee: float


@dataclass(frozen=True)
class Trade:
    signal_id: str
    signal_ts_ns: int
    fill_ts_ns: int
    direction: str
    qty: float
    buy_fill: LegFill
    sell_fill: LegFill
    expected_net_pnl: float
    realized_net_pnl: float
    edge_decay: float
    expected_edge_bps: float
    realized_edge_bps: float
    edge_decay_bps: float
    status: str
    

@dataclass(frozen=True, slots=True)
class MetricSummary:
    n_trades: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate: float
    avg_pnl: float
    avg_expected_edge_bps: float
    avg_edge_decay: float
    max_drawdown: float
    turnover: float
