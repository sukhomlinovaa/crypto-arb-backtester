"""HFT-style cross-exchange crypto arbitrage backtester."""

from .backtest import run_backtest
from .config import BacktestConfig

__all__ = ["BacktestConfig", "run_backtest"]
