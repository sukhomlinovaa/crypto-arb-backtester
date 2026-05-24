from __future__ import annotations

from dataclasses import dataclass, field

from .config import BacktestConfig
from .types import LegFill, Trade


@dataclass(slots=True)
class VenueState:
    cash_usd: float
    base_qty: float = 0.0


@dataclass(slots=True)
class Portfolio:
    cfg: BacktestConfig
    venues: dict[str, VenueState] = field(init=False)
    realized_pnl: float = 0.0
    turnover: float = 0.0

    def __post_init__(self) -> None:
        per_venue_cash = self.cfg.starting_cash_usd / len(self.cfg.venues)
        self.venues = {
            venue: VenueState(cash_usd=per_venue_cash, base_qty=0.0)
            for venue in self.cfg.venues
        }

    @property
    def net_inventory(self) -> float:
        return sum(v.base_qty for v in self.venues.values())

    def can_apply(self, buy_fill: LegFill, sell_fill: LegFill) -> bool:
        buy_state = self.venues[buy_fill.venue]
        sell_state = self.venues[sell_fill.venue]
        required_cash = buy_fill.notional + buy_fill.fee
        if buy_state.cash_usd + 1e-9 < required_cash:
            return False
        projected_inventory = self.net_inventory + buy_fill.qty - sell_fill.qty
        if abs(projected_inventory) > self.cfg.risk_max_inventory_abs:
            return False
        # In real cross-venue arb you pre-position inventory; allow sell venue to short only up to risk limit.
        if abs(sell_state.base_qty - sell_fill.qty) > self.cfg.risk_max_inventory_abs:
            return False
        return True

    def apply(self, trade: Trade) -> None:
        buy = trade.buy_fill
        sell = trade.sell_fill
        self.venues[buy.venue].cash_usd -= buy.notional + buy.fee
        self.venues[buy.venue].base_qty += buy.qty
        self.venues[sell.venue].cash_usd += sell.notional - sell.fee
        self.venues[sell.venue].base_qty -= sell.qty
        self.realized_pnl += trade.realized_net_pnl
        self.turnover += buy.notional + sell.notional

    def mark_to_mid(self, mids: dict[str, float]) -> float:
        total = 0.0
        for venue, state in self.venues.items():
            total += state.cash_usd + state.base_qty * mids[venue]
        return total
