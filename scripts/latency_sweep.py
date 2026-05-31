from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from hft_crypto_arb.backtest import run_backtest
from hft_crypto_arb.config import BacktestConfig, VenueConfig, load_config


DEFAULT_LATENCIES_MS = [0, 1, 2, 5, 10, 20, 50, 100]


def zero_fee_venues(cfg: BacktestConfig) -> dict[str, VenueConfig]:
    return {
        venue: VenueConfig(taker_fee_bps=0.0, maker_fee_bps=0.0)
        for venue in cfg.venues
    }


def with_latency_ms(cfg: BacktestConfig, latency_ms: float) -> BacktestConfig:
    """
    Use deterministic total latency.

    We set exchange ack and jitter to zero so that each experiment changes
    exactly one thing: total decision-to-fill delay.
    """
    return replace(
        cfg,
        latency_decision_to_order_ns=int(latency_ms * 1_000_000),
        latency_exchange_ack_ns=0,
        latency_jitter_ns=0,
    )


def with_no_costs(cfg: BacktestConfig) -> BacktestConfig:
    return replace(
        cfg,
        slippage_bps=0.0,
        venues=zero_fee_venues(cfg),
    )


def with_no_fees(cfg: BacktestConfig) -> BacktestConfig:
    return replace(
        cfg,
        venues=zero_fee_venues(cfg),
    )


def with_no_slippage(cfg: BacktestConfig) -> BacktestConfig:
    return replace(
        cfg,
        slippage_bps=0.0,
    )


def run_one(cfg: BacktestConfig, label: str) -> dict:
    trades, summary = run_backtest(cfg)
    row = asdict(summary)
    row["scenario"] = label
    row["latency_total_ms"] = (
        cfg.latency_decision_to_order_ns
        + cfg.latency_exchange_ack_ns
        + cfg.latency_jitter_ns
    ) / 1_000_000
    row["slippage_bps"] = cfg.slippage_bps
    row["coinbase_taker_fee_bps"] = cfg.venues["coinbase"].taker_fee_bps
    row["binance_taker_fee_bps"] = cfg.venues["binance"].taker_fee_bps
    row["n_trades_exported"] = len(trades)
    return row


def run_latency_sweep(cfg: BacktestConfig, latencies_ms: list[float]) -> pd.DataFrame:
    rows = []

    for latency_ms in latencies_ms:
        experiment_cfg = with_latency_ms(cfg, latency_ms)
        row = run_one(experiment_cfg, label=f"latency_{latency_ms:g}ms")
        row["latency_ms"] = latency_ms
        rows.append(row)

    return pd.DataFrame(rows)


def run_cost_sanity_checks(cfg: BacktestConfig) -> pd.DataFrame:
    """
    These checks answer a key question:

    Are we losing only because of latency, or also because of transaction costs?
    """
    default_latency_ms = (
        cfg.latency_decision_to_order_ns + cfg.latency_exchange_ack_ns
    ) / 1_000_000

    scenarios = [
        (
            "zero_latency_no_costs",
            with_no_costs(with_latency_ms(cfg, 0)),
        ),
        (
            "zero_latency_fees_only",
            with_no_slippage(with_latency_ms(cfg, 0)),
        ),
        (
            "zero_latency_slippage_only",
            with_no_fees(with_latency_ms(cfg, 0)),
        ),
        (
            "zero_latency_default_costs",
            with_latency_ms(cfg, 0),
        ),
        (
            "default_latency_no_costs",
            with_no_costs(with_latency_ms(cfg, default_latency_ms)),
        ),
        (
            "default_latency_default_costs",
            with_latency_ms(cfg, default_latency_ms),
        ),
    ]

    rows = [run_one(scenario_cfg, label=name) for name, scenario_cfg in scenarios]
    return pd.DataFrame(rows)


def save_line_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    ylabel: str,
    path: Path,
) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df[x], df[y], marker="o")

    for latency_ms, label in [
        (0, "0 ms"),
        (5, "5 ms"),
        (20, "20 ms"),
    ]:
        if latency_ms in set(df[x]):
            ax.axvline(latency_ms, linestyle="--", linewidth=1)
            ax.text(
                latency_ms,
                ax.get_ylim()[1],
                label,
                rotation=90,
                va="top",
                ha="right",
            )

    ax.set_title(title)
    ax.set_xlabel("Latency, ms")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

    return path


def make_latency_plots(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    return [
        save_line_plot(
            df,
            x="latency_ms",
            y="net_pnl",
            title="Latency vs net PnL",
            ylabel="Net PnL",
            path=out_dir / "latency_vs_net_pnl.png",
        ),
        save_line_plot(
            df,
            x="latency_ms",
            y="win_rate",
            title="Latency vs win rate",
            ylabel="Win rate",
            path=out_dir / "latency_vs_win_rate.png",
        ),
        save_line_plot(
            df,
            x="latency_ms",
            y="avg_edge_decay",
            title="Latency vs average edge decay",
            ylabel="Average edge decay, bps",
            path=out_dir / "latency_vs_edge_decay.png",
        ),
        save_line_plot(
            df,
            x="latency_ms",
            y="n_trades",
            title="Latency vs number of trades",
            ylabel="Number of trades",
            path=out_dir / "latency_vs_n_trades.png",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="examples/config.yaml")
    parser.add_argument("--out", default="outputs/research")
    parser.add_argument(
        "--latencies-ms",
        nargs="*",
        type=float,
        default=DEFAULT_LATENCIES_MS,
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    latency_df = run_latency_sweep(cfg, args.latencies_ms)
    sanity_df = run_cost_sanity_checks(cfg)

    latency_csv = out_dir / "latency_sweep.csv"
    sanity_csv = out_dir / "cost_sanity_checks.csv"

    latency_df.to_csv(latency_csv, index=False)
    sanity_df.to_csv(sanity_csv, index=False)

    plot_paths = make_latency_plots(latency_df, out_dir)

    summary = {
        "latency_sweep_csv": str(latency_csv),
        "cost_sanity_csv": str(sanity_csv),
        "plots": [str(path) for path in plot_paths],
    }

    print(json.dumps(summary, indent=2))
    print()
    print("Latency sweep:")
    print(latency_df[["latency_ms", "n_trades", "net_pnl", "win_rate", "avg_expected_edge_bps", "avg_edge_decay"]])
    print()
    print("Cost sanity checks:")
    print(sanity_df[["scenario", "n_trades", "net_pnl", "win_rate", "avg_expected_edge_bps", "avg_edge_decay"]])


if __name__ == "__main__":
    main()