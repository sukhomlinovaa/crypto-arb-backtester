from hft_crypto_arb import BacktestConfig, run_backtest
from hft_crypto_arb.replay import replay_equity


def test_full_backtest_runs_and_replay_is_deterministic():
    cfg = BacktestConfig(seed=42, n_ticks=2_000, min_net_edge_bps=0.5)
    trades, summary = run_backtest(cfg)
    assert summary.n_trades == len(trades)
    assert replay_equity(trades).equals(replay_equity(trades))
