from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _pnl_column(trades: pd.DataFrame) -> str:
    if "realized_pnl" in trades.columns:
        return "realized_pnl"
    if "pnl" in trades.columns:
        return "pnl"
    raise KeyError("Expected trades to contain either 'realized_pnl' or 'pnl'.")


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_equity_curve(trades: pd.DataFrame, out_dir: Path) -> Path:
    pnl_col = _pnl_column(trades)
    equity = trades[pnl_col].cumsum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(equity.values)
    ax.set_title("Equity curve")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Cumulative PnL")
    ax.grid(True, alpha=0.3)

    return _save(fig, out_dir / "equity_curve.png")


def plot_drawdown(trades: pd.DataFrame, out_dir: Path) -> Path:
    pnl_col = _pnl_column(trades)
    equity = trades[pnl_col].cumsum()
    drawdown = equity - equity.cummax()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(drawdown.values)
    ax.set_title("Drawdown")
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Drawdown")
    ax.grid(True, alpha=0.3)

    return _save(fig, out_dir / "drawdown.png")


def plot_pnl_distribution(trades: pd.DataFrame, out_dir: Path) -> Path:
    pnl_col = _pnl_column(trades)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(trades[pnl_col], bins=50)
    ax.set_title("Trade PnL distribution")
    ax.set_xlabel("PnL per trade")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.3)

    return _save(fig, out_dir / "pnl_distribution.png")


def plot_expected_vs_realized_edge(trades: pd.DataFrame, out_dir: Path) -> Path | None:
    required = {"expected_edge_bps", "realized_edge_bps"}
    if not required.issubset(trades.columns):
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(
        trades["expected_edge_bps"],
        trades["realized_edge_bps"],
        alpha=0.5,
        s=12,
    )
    ax.axhline(0, linewidth=1)
    ax.axvline(0, linewidth=1)
    ax.set_title("Expected vs realized edge")
    ax.set_xlabel("Expected edge at signal time, bps")
    ax.set_ylabel("Realized edge after latency, bps")
    ax.grid(True, alpha=0.3)

    return _save(fig, out_dir / "expected_vs_realized_edge.png")


def plot_edge_decay(trades: pd.DataFrame, out_dir: Path) -> Path | None:
    if "edge_decay_bps" in trades.columns:
        values = trades["edge_decay_bps"]
        ylabel = "Expected edge - realized edge, bps"
    elif "edge_decay" in trades.columns:
        values = trades["edge_decay"]
        ylabel = "Expected PnL - realized PnL"
    else:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(values.values)
    ax.axhline(0, linewidth=1)
    ax.set_title("Edge decay")
    ax.set_xlabel("Trade number")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    return _save(fig, out_dir / "edge_decay.png")


def make_plot_pack(trades: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    """
    Create diagnostic plots from the trade ledger.

    Basic plots require a PnL column:
    - realized_pnl, preferred
    - pnl, fallback

    Edge plots are created only when the required edge columns exist.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if trades.empty:
        return []

    paths: list[Path] = [
        plot_equity_curve(trades, out_dir),
        plot_drawdown(trades, out_dir),
        plot_pnl_distribution(trades, out_dir),
    ]

    optional_paths = [
        plot_expected_vs_realized_edge(trades, out_dir),
        plot_edge_decay(trades, out_dir),
    ]

    paths.extend(path for path in optional_paths if path is not None)
    return paths