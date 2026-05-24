from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class VenueConfig:
    taker_fee_bps: float
    maker_fee_bps: float


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    seed: int = 42
    n_ticks: int = 50_000
    tick_ns: int = 1_000_000
    depth: int = 5
    symbol: str = "BTC-USD"
    base_asset: str = "BTC"
    quote_asset: str = "USD"
    max_order_qty: float = 0.25
    min_order_qty: float = 0.001
    min_net_edge_bps: float = 1.0
    slippage_bps: float = 0.2
    risk_max_inventory_abs: float = 2.0
    risk_max_notional_per_trade: float = 20_000.0
    starting_cash_usd: float = 1_000_000.0
    latency_decision_to_order_ns: int = 2_000_000
    latency_exchange_ack_ns: int = 3_000_000
    latency_jitter_ns: int = 1_000_000
    venues: dict[str, VenueConfig] | None = None

    def __post_init__(self) -> None:
        if self.venues is None:
            object.__setattr__(
                self,
                "venues",
                {
                    "coinbase": VenueConfig(taker_fee_bps=4.0, maker_fee_bps=1.0),
                    "binance": VenueConfig(taker_fee_bps=2.0, maker_fee_bps=0.8),
                },
            )


def load_config(path: str | Path) -> BacktestConfig:
    raw: dict[str, Any] = yaml.safe_load(Path(path).read_text())
    venues = {
        name: VenueConfig(**venue_raw)
        for name, venue_raw in raw.pop("venues", {}).items()
    }
    return BacktestConfig(**raw, venues=venues)
