# HFT-Style Crypto Cross-Exchange Arbitrage Backtester

This repository contains an event-driven, deterministic Python backtester for cross-exchange crypto arbitrage. It is designed as a quant portfolio project: the goal is not to show fake free money, but to demonstrate how apparent top-of-book arbitrage decays after latency, fees, slippage, depth constraints, and risk limits.

## What this project demonstrates

- Multi-venue L2 order book simulation
- Receive-time market-data sequencing
- Duplicate and stale sequence handling
- Depth-aware signal generation
- Taker/taker fee and slippage modelling
- Latency-aware execution
- Partial fills through visible order-book depth
- Portfolio accounting by venue
- Idempotent execution by signal id
- Deterministic replay from trade records
- Quant metrics: net PnL, win rate, drawdown, turnover, edge decay

## Architecture

```text
Synthetic L2 Market Events
        ↓
MarketDataSequencer
        ↓
Consolidated Multi-Venue Book
        ↓
CrossVenueArbStrategy
        ↓
Latency-Aware ExecutionSimulator
        ↓
Portfolio Accounting
        ↓
Trade Ledger / Replay / Metrics
```

## Why this is interview-relevant

The central metric is not raw PnL. The central metric is **expected edge at signal time vs realized edge after latency**. In realistic crypto arbitrage, many apparent opportunities disappear once you model message delay, taker fees, adverse selection, and available depth.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest -q
hft-crypto-arb --config examples/config.yaml --out outputs
```

Alternative without installing:

```bash
PYTHONPATH=src python -m hft_crypto_arb.cli --config examples/config.yaml --out outputs
```

## Example output

The default config is deliberately conservative. Apparent alpha is often destroyed by latency and fees. This is a feature, not a bug: it makes the project credible.

```json
{
  "n_trades": 842,
  "net_pnl": -4463.87,
  "win_rate": 0.0107,
  "avg_expected_edge_bps": 2.53,
  "avg_edge_decay": 7.24,
  "turnover": 12898985.90
}
```

## Main files

```text
src/hft_crypto_arb/market.py      synthetic deterministic L2 market generator
src/hft_crypto_arb/feed.py        receive-time sequencer and duplicate/stale handling
src/hft_crypto_arb/strategy.py    depth-aware cross-venue arbitrage signal engine
src/hft_crypto_arb/execution.py   latency-aware two-leg execution simulator
src/hft_crypto_arb/portfolio.py   venue-level cash and inventory accounting
src/hft_crypto_arb/metrics.py     PnL, drawdown, turnover, edge-decay metrics
src/hft_crypto_arb/replay.py      deterministic replay from trade records
```

## Limitations

This is an HFT-style research simulator, not a production trading system. A real production HFT stack would require colocated connectivity, exchange-specific protocol handlers, full order-state machines, persistent audit logs, hardware/network timestamping, drop-copy reconciliation, monitoring, kill-switches, and extensive compliance controls.

## Suggested next extensions

1. Add real historical L2 data adapter.
2. Add exchange-specific latency distributions.
3. Model legging risk when one side fills and the second side fails.
4. Add maker/taker routing logic.
5. Add inventory rebalancing between venues.
6. Add scenario analysis: zero latency vs 1 ms vs 5 ms vs 20 ms.
7. Add a notebook with edge-decay plots and PnL attribution.
