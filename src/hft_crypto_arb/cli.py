from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .backtest import run_backtest
from .config import BacktestConfig, load_config
from .metrics import trades_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HFT-style crypto arbitrage backtester.")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config.")
    parser.add_argument("--out", type=str, default="outputs", help="Output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config) if args.config else BacktestConfig()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    trades, summary = run_backtest(cfg)
    trades_frame(trades).to_csv(out / "trades.csv", index=False)
    (out / "summary.json").write_text(json.dumps(asdict(summary), indent=2))

    print(json.dumps(asdict(summary), indent=2))
    print(f"Saved trades to {out / 'trades.csv'}")
    print(f"Saved summary to {out / 'summary.json'}")


if __name__ == "__main__":
    main()
