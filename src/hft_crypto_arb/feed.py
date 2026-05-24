from __future__ import annotations

from collections.abc import Iterable

from .types import BookUpdate, ConsolidatedBook


class MarketDataSequencer:
    """Normalizes multi-venue L2 book updates into a monotonic consolidated stream."""

    def __init__(self, venues: tuple[str, ...]):
        self.venues = venues
        self.latest: dict[str, BookUpdate] = {}
        self.last_sequence: dict[str, int] = {venue: -1 for venue in venues}
        self.last_emitted_ts = -1

    def normalize(self, events: Iterable[BookUpdate]) -> list[ConsolidatedBook]:
        normalized: list[ConsolidatedBook] = []
        # Receive-time order approximates how an event-driven system sees the world.
        for event in sorted(events, key=lambda e: (e.recv_ts_ns, e.venue, e.sequence)):
            last_seq = self.last_sequence.get(event.venue, -1)
            if event.sequence < last_seq:
                # Stale packet; ignore.
                continue

            # Same sequence is allowed: last received update wins.
            self.last_sequence[event.venue] = event.sequence
            self.latest[event.venue] = event

            if all(venue in self.latest for venue in self.venues):
                ts_ns = max(book.recv_ts_ns for book in self.latest.values())
                if ts_ns <= self.last_emitted_ts:
                    ts_ns = self.last_emitted_ts + 1
                self.last_emitted_ts = ts_ns
                normalized.append(ConsolidatedBook(ts_ns=ts_ns, books=dict(self.latest)))
        return normalized
