from __future__ import annotations

from .types import Level


def walk_book(levels: tuple[Level, ...], qty: float) -> tuple[float, float]:
    """Return executed_qty and VWAP for a market order walking visible L2 levels."""
    if qty <= 0:
        return 0.0, 0.0

    remaining = qty
    notional = 0.0
    executed = 0.0

    for level in levels:
        if remaining <= 1e-12:
            break
        take = min(remaining, level.size)
        notional += take * level.price
        executed += take
        remaining -= take

    if executed <= 0:
        return 0.0, 0.0
    return executed, notional / executed


def available_depth(levels: tuple[Level, ...]) -> float:
    return sum(level.size for level in levels)


def bps(value: float) -> float:
    return value * 1e-4
