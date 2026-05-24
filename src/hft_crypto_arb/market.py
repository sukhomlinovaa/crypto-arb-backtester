from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from .config import BacktestConfig
from .types import BookUpdate, Level


class SyntheticL2Market:
    """
    Deterministic L2 market generator.

    It intentionally includes small venue skews, microstructure noise, fee-sized spreads,
    occasional stale/overshoot events, duplicates, and local receive-time disorder so the
    feed handler has realistic work to do.
    """

    def __init__(self, cfg: BacktestConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)

    def generate(self) -> list[BookUpdate]:
        cfg = self.cfg
        rets = self.rng.normal(0.0, 0.00025, size=cfg.n_ticks)
        fair = 30_000.0 * np.exp(np.cumsum(rets))

        events: list[BookUpdate] = []
        seq_by_venue = {"coinbase": 0, "binance": 0}

        for i in range(cfg.n_ticks):
            exchange_ts_ns = i * cfg.tick_ns

            # Small stochastic cross-venue basis. Occasional jumps create apparent arb.
            basis = self.rng.normal(0.0, 2.0)
            if self.rng.random() < 0.015:
                basis += self.rng.choice([-1.0, 1.0]) * self.rng.uniform(8.0, 22.0)

            for venue in ("coinbase", "binance"):
                seq_by_venue[venue] += 1
                venue_bias = 0.5 * basis if venue == "binance" else -0.5 * basis
                mid = fair[i] + venue_bias + self.rng.normal(0.0, 0.35)
                spread = self.rng.uniform(1.0, 3.0)
                if self.rng.random() < 0.01:
                    spread += self.rng.uniform(5.0, 12.0)

                bids: list[Level] = []
                asks: list[Level] = []
                for lvl in range(cfg.depth):
                    px_gap = lvl * self.rng.uniform(0.5, 1.6)
                    decay = 0.72**lvl
                    bid_px = mid - spread / 2.0 - px_gap
                    ask_px = mid + spread / 2.0 + px_gap
                    bid_sz = float(self.rng.uniform(0.04, 1.20) * decay)
                    ask_sz = float(self.rng.uniform(0.04, 1.20) * decay)
                    bids.append(Level(price=float(bid_px), size=bid_sz))
                    asks.append(Level(price=float(ask_px), size=ask_sz))

                venue_network_ns = 700_000 if venue == "coinbase" else 900_000
                jitter_ns = int(self.rng.integers(0, 2_000_000))
                recv_ts_ns = exchange_ts_ns + venue_network_ns + jitter_ns
                events.append(
                    BookUpdate(
                        venue=venue,
                        symbol=cfg.symbol,
                        exchange_ts_ns=exchange_ts_ns,
                        recv_ts_ns=recv_ts_ns,
                        sequence=seq_by_venue[venue],
                        bids=tuple(bids),
                        asks=tuple(asks),
                    )
                )

                # Deterministic duplicate update with the same sequence: later receive wins.
                if self.rng.random() < 0.002:
                    events.append(
                        BookUpdate(
                            venue=venue,
                            symbol=cfg.symbol,
                            exchange_ts_ns=exchange_ts_ns,
                            recv_ts_ns=recv_ts_ns + int(self.rng.integers(1, 300_000)),
                            sequence=seq_by_venue[venue],
                            bids=tuple(bids),
                            asks=tuple(asks),
                        )
                    )

        # Simulate network disorder but keep it bounded; the sequencer sorts by receive time.
        disorder = self.rng.normal(0, 1_000_000, size=len(events)).astype(int)
        events = [
            BookUpdate(
                venue=e.venue,
                symbol=e.symbol,
                exchange_ts_ns=e.exchange_ts_ns,
                recv_ts_ns=max(0, e.recv_ts_ns + int(disorder[j])),
                sequence=e.sequence,
                bids=e.bids,
                asks=e.asks,
            )
            for j, e in enumerate(events)
        ]
        return events


def generate_events(cfg: BacktestConfig) -> list[BookUpdate]:
    return SyntheticL2Market(cfg).generate()
