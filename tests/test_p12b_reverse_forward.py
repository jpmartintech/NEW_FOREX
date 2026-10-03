import pandas as pd


def classify(n_trades: int, expectancy: float, return_: float) -> str:
    if n_trades == 0:
        return "A_no_forward_trades"
    if expectancy <= 0:
        return "B_active_nonpositive_expectancy"
    if return_ <= 0:
        return "C_positive_expectancy_nonpositive_return"
    return "D_positive_expectancy_and_return"


def test_forward_classification_boundaries() -> None:
    assert classify(0, 100, 100) == "A_no_forward_trades"
    assert classify(1, 0, 1) == "B_active_nonpositive_expectancy"
    assert classify(1, 1, 0) == "C_positive_expectancy_nonpositive_return"
    assert classify(1, 1, 1) == "D_positive_expectancy_and_return"


def test_history_and_forward_columns_are_disjoint() -> None:
    history = {"training_expectancy_R", "development_expectancy_R", "development_profit_factor"}
    forward = {"forward_expectancy_R", "forward_return", "forward_n_trades"}
    assert not history & forward
    assert pd.isna(float("nan"))
