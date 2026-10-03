"""Run frozen P11 Control A using the preserved eligible candidate universes."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from new_forex.backtest.evaluator import evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame, validate_ledger
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.random_control import load_policy, sample_excluding, seed_for
from new_forex.walk_forward.rolling_factory import generation_windows
from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "random_selection_control.yaml"
OUTPUT = ROOT / "reports" / "p11_artifacts"
PILOT = ROOT / "runs" / "p08-rolling-2019-q1-v3"
HISTORICAL = ROOT / "runs" / "p09-rolling-historical-v1"
EMPTY_LEDGER_COLUMNS = ["entry_timestamp", "exit_timestamp", "result_R"]


def generation_dirs() -> list[tuple[str, Path]]:
    return [("2019Q1", PILOT)] + [(p.name, p) for p in sorted(HISTORICAL.iterdir()) if (p / "generation.json").exists()]


def window_for(label: str) -> tuple[str, str]:
    birth = pd.Period(label, freq="Q").start_time.strftime("%Y-%m-%d")
    end = (pd.Period(label, freq="Q").start_time + pd.DateOffset(months=3)).strftime("%Y-%m-%d")
    return birth, end


def load_candidates(path: Path) -> tuple[dict[str, StrategyDefinition], set[str]]:
    candidates: dict[str, StrategyDefinition] = {}
    with (path / "selection_audit.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["acceptance"]["decision"] != "PASS":
                continue
            strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
            if strategy.canonical_hash != row["strategy_hash"]:
                raise ValueError(f"candidate hash mismatch in {path}")
            candidates[row["strategy_hash"]] = strategy
    selected = {row["strategy_hash"] for row in json.loads((path / "finalists.json").read_text())}
    if len(selected) != 5 or not selected <= candidates.keys() or len(candidates) - len(selected) < 5:
        raise ValueError(f"invalid frozen candidate universe in {path}")
    return candidates, selected


def metric(row: dict) -> dict:
    return {key: row[key] for key in ("n_trades", "mean_r", "profit_factor", "return", "max_dd", "sharpe", "max_consec_losses")}


def main() -> None:
    policy = load_policy(CONFIG)
    if policy.generations != 16 or policy.replicates != 100 or policy.selection_size != 5:
        raise ValueError("unexpected frozen P11 dimensions")
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    access.assert_range("2019-01-01", "2023-01-01")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = OUTPUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}
    generations = generation_dirs()
    if len(generations) != policy.generations:
        raise ValueError("unexpected number of P11 generations")
    frozen_candidates = {label: load_candidates(path) for label, path in generations}
    # The P08 runner is the frozen pre-holdout market constructor. Its end is exclusive.
    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2023-01-01")
    summary_path = OUTPUT / "random_selection_results.jsonl"
    trajectory_path = OUTPUT / "rolling_trajectories.jsonl"
    existing = {json.loads(line)["generation"] for line in summary_path.open()} if summary_path.exists() else set()
    all_generation_results: list[dict] = []
    generation_ledgers: dict[str, dict[str, dict[str, pd.DataFrame]]] = {}
    for generation_index, (label, _path) in enumerate(generations):
        if label in checkpoint["completed"] and label in existing:
            continue
        candidates, excluded = frozen_candidates[label]
        eligible = sorted(candidates)
        windows = generation_windows(window_for(label)[0])
        forward_window = _window(market, *windows["forward"])
        generation_ledgers[label] = {"baseline": {}, "costs_x2": {}}
        strategies_needed: set[str] = set()
        selections: list[dict] = []
        for replicate in range(policy.replicates):
            seed = seed_for(policy.seed_base, generation_index, replicate)
            selected = sample_excluding(eligible, excluded, seed=seed, size=policy.selection_size)
            selections.append({"replicate": replicate, "seed": seed, "selected": selected})
            strategies_needed.update(selected)
        strategy_map = {key: candidates[key] for key in strategies_needed}
        for strategy_hash, strategy in strategy_map.items():
            for name, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
                rich = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=multiplier, window=forward_window)
                ledger = _ledger_frame(rich.trades, strategy, market)
                validate_ledger(ledger, strategy, rich.metrics)
                generation_ledgers[label][name][strategy_hash] = ledger
        pd.DataFrame([r for name in ("baseline", "costs_x2") for h, frame in generation_ledgers[label][name].items()
                      for r in frame.assign(scenario=name).to_dict("records")]).to_parquet(
                          OUTPUT / f"ledgers_{label}.parquet", index=False)
        rows = []
        for selection in selections:
            row = {"generation": label, "replicate": selection["replicate"], "seed": selection["seed"],
                   "selected": list(selection["selected"])}
            for name in ("baseline", "costs_x2"):
                ledgers = [(h, generation_ledgers[label][name][h]) for h in selection["selected"]]
                portfolio = portfolio_ledger(ledgers)
                row[name] = portfolio_metrics(portfolio)
            rows.append(row)
        with summary_path.open("a") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        checkpoint["completed"].append(label)
        checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
        all_generation_results.extend(rows)
    # Reload every generation's cached ledgers to make resume and trajectory construction idempotent.
    for _generation_index, (label, _path) in enumerate(generations):
        if label not in checkpoint["completed"]:
            raise RuntimeError(f"generation {label} did not complete")
        candidates, excluded = frozen_candidates[label]
        cached = pd.read_parquet(OUTPUT / f"ledgers_{label}.parquet")
        generation_ledgers[label] = {"baseline": {}, "costs_x2": {}}
        for (scenario, strategy_hash), frame in cached.groupby(["scenario", "strategy_hash"], sort=False):
            generation_ledgers[label][scenario][strategy_hash] = frame.drop(columns=["scenario", "strategy_hash"]).assign(strategy_hash=strategy_hash)
    # One rolling trajectory per replicate, plus the real frozen trajectory for comparison.
    with trajectory_path.open("w") as handle:
        for replicate in range(policy.replicates):
            row = {"replicate": replicate}
            for name in ("baseline", "costs_x2"):
                ledgers = []
                for generation_index, (label, _path) in enumerate(generations):
                    candidates, excluded = frozen_candidates[label]
                    selected = sample_excluding(sorted(candidates), excluded,
                                                seed=seed_for(policy.seed_base, generation_index, replicate), size=policy.selection_size)
                    ledgers.extend((h, generation_ledgers[label][name].get(
                        h, pd.DataFrame(columns=EMPTY_LEDGER_COLUMNS))) for h in selected)
                row[name] = portfolio_metrics(portfolio_ledger(ledgers))
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {"policy_id": policy.policy_id, "policy_sha256": policy.sha256,
                "config_sha256": file_sha256(CONFIG), "generations": len(generations),
                "replicates": policy.replicates, "strategy_forward_evaluations": 8000,
                "holdout_used": False, "summary_sha256": file_sha256(summary_path),
                "trajectory_sha256": file_sha256(trajectory_path)}
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
