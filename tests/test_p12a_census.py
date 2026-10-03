import numpy as np

from new_forex.backtest.semantics import AGG


def census_metrics(agg: np.ndarray) -> dict:
    n = agg[:, AGG["n_trades"]].astype(int)
    total = agg[:, AGG["sum_r"]]
    wins = agg[:, AGG["gross_win_r"]]
    losses = agg[:, AGG["gross_loss_r"]]
    pf = np.divide(wins, losses, out=np.full(len(n), np.nan), where=losses != 0)
    pf[(losses == 0) & (wins > 0)] = np.inf
    pf[(losses == 0) & (wins <= 0)] = 0.0
    return {"n_trades": n, "expectancy_R": np.divide(total, n, out=np.zeros(len(n)), where=n != 0), "profit_factor": pf}


def test_census_metrics_do_not_treat_zero_trade_infinite_pf_as_valid() -> None:
    agg = np.zeros((3, len(AGG)))
    agg[0, AGG["n_trades"]] = 0
    agg[1, AGG["n_trades"]] = 1
    agg[1, AGG["gross_win_r"]] = 1
    agg[2, AGG["n_trades"]] = 1
    agg[2, AGG["gross_loss_r"]] = 1
    result = census_metrics(agg)
    assert result["profit_factor"][0] == 0
    assert np.isinf(result["profit_factor"][1])
    assert result["profit_factor"][2] == 0
    assert result["expectancy_R"][0] == 0
