from pathlib import Path

import pandas as pd

from hft_crypto_arb.plots import make_plot_pack


def test_make_plot_pack_creates_basic_plots(tmp_path: Path):
    trades = pd.DataFrame(
        {
            "t": [1, 2, 3],
            "pnl": [1.0, -0.5, 0.25],
        }
    )

    paths = make_plot_pack(trades, tmp_path)

    names = {path.name for path in paths}

    assert "equity_curve.png" in names
    assert "drawdown.png" in names
    assert "pnl_distribution.png" in names

    for path in paths:
        assert path.exists()
        assert path.stat().st_size > 0


def test_make_plot_pack_creates_edge_plots_when_columns_exist(tmp_path: Path):
    trades = pd.DataFrame(
        {
            "t": [1, 2, 3],
            "realized_pnl": [1.0, -0.5, 0.25],
            "expected_edge_bps": [3.0, 2.0, 1.0],
            "realized_edge_bps": [1.5, -1.0, 0.5],
            "edge_decay": [0.2, 0.5, 0.1],
        }
    )

    paths = make_plot_pack(trades, tmp_path)

    names = {path.name for path in paths}

    assert "expected_vs_realized_edge.png" in names
    assert "edge_decay.png" in names