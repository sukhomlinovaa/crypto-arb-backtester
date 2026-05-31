from pathlib import Path

import pandas as pd

from hft_crypto_arb.plots import make_plot_pack


def main() -> None:
    trades_path = Path("outputs/trades.csv")

    if not trades_path.exists():
        raise FileNotFoundError(
            "Could not find outputs/trades.csv. "
            "Run the backtest first."
        )

    trades = pd.read_csv(trades_path)
    paths = make_plot_pack(trades, Path("outputs/plots"))

    for path in paths:
        print(path)


if __name__ == "__main__":
    main()