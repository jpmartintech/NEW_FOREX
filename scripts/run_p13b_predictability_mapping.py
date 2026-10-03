"""Map archived historical variables to the immediately following P13 month."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/p13b_predictability_mapping.yaml"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pf_bin(values: pd.Series) -> pd.Series:
    result = pd.Series("PF undefined", index=values.index, dtype="object")
    finite = np.isfinite(values)
    result.loc[finite & (values < 1.0)] = "PF < 1.00"
    edges = [(1.0, 1.1), (1.1, 1.2), (1.2, 1.3), (1.3, 1.5)]
    labels = ["1.00–<1.10", "1.10–<1.20", "1.20–<1.30", "1.30–<1.50"]
    for (low, high), label in zip(edges, labels, strict=True):
        result.loc[finite & (values >= low) & (values < high)] = label
    result.loc[finite & (values >= 1.5)] = "PF ≥ 1.50"
    result.loc[np.isposinf(values)] = "PF infinite"
    return result


def fixed_trade_bin(values: pd.Series) -> pd.Series:
    edges = [-1, 25, 50, 75, 100, 150, 200, 250, np.inf]
    labels = ["0–24", "25–49", "50–74", "75–99", "100–149", "150–199", "200–250", ">250"]
    return pd.cut(values, bins=edges, labels=labels, right=False, include_lowest=True).astype("object")


def quintile_bin(values: pd.Series, name: str) -> pd.Series:
    labels = [f"{name}_Q{i}" for i in range(1, 6)]
    ranked = values.rank(method="first")
    return pd.qcut(ranked, 5, labels=labels, duplicates="drop").astype("object")


def summary_rows(frame: pd.DataFrame, variable: str, condition: str) -> pd.DataFrame:
    rows: list[dict] = []
    for keys, part in frame.groupby(["generation", "generator", variable], dropna=False, sort=True):
        generation, generator, interval = keys
        population_n = len(frame[(frame["generation"] == generation) & (frame["generator"] == generator)])
        active = part["forward_n_trades"] > 0
        active_n = int(active.sum())
        rows.append({
            "variable": variable, "condition": condition, "generation": generation, "generator": generator, "interval": str(interval),
            "n": len(part), "population_n": population_n, "pct_population": len(part) / population_n if population_n else np.nan,
            "active_n": active_n, "pct_active_within_interval": active_n / len(part) if len(part) else np.nan,
            "median_forward_trades": part["forward_n_trades"].median(),
            "mean_gross_expectancy_R": part["forward_gross_expectancy_R"].mean(),
            "mean_net_expectancy_R": part["forward_expectancy_R"].mean(), "median_net_expectancy_R": part["forward_expectancy_R"].median(),
            "mean_net_return": part["forward_return"].mean(), "median_net_return": part["forward_return"].median(),
            "mean_x2_return": part["forward_x2_return"].mean(), "median_x2_return": part["forward_x2_return"].median(),
            "pct_E": (part["economic_class"] == "E").mean(), "pct_positive_active": (part.loc[active, "forward_return"] > 0).mean() if active_n else np.nan,
        })
    return pd.DataFrame(rows)


def add_lift(table: pd.DataFrame) -> pd.DataFrame:
    keys = ["variable", "condition", "generation", "generator"]
    baseline = table[table["interval"].eq("__BASELINE__")][keys + ["pct_E"]].rename(columns={"pct_E": "base_pct_E"})
    merged = table.merge(baseline, on=keys, how="left")
    merged["lift_E"] = merged["pct_E"] / merged["base_pct_E"].replace(0, np.nan)
    merged["difference_E_pp"] = 100 * (merged["pct_E"] - merged["base_pct_E"])
    return merged


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_bytes())
    source = ROOT / config["source"]["classified_census"]
    if file_sha256(source) != config["source"]["classified_census_sha256"]:
        raise ValueError("P13A classified census hash mismatch")
    if not config["source"]["invalid_run_excluded"] or config["reproducibility"]["holdout_used"]:
        raise ValueError("invalid run/holdout policy failure")
    frame = pd.read_parquet(source)
    if len(frame) != 2_400_000 or frame.duplicated(["generation", "generator", "strategy_hash"]).any():
        raise ValueError("P13B input identity failure")
    if frame["forward_month"].astype(str).max() >= "2018-07":
        raise ValueError("P13B attempted to read beyond authorized forward period")

    out = ROOT / config["artifacts"]["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    historical = ["training_profit_factor", "training_n_trades", "training_expectancy_R", "training_return", "training_max_drawdown", "direction", "complexity"]
    forward = ["forward_n_trades", "forward_gross_expectancy_R", "forward_expectancy_R", "forward_return", "forward_x2_return", "forward_max_drawdown", "economic_class"]
    if not set(historical + forward).issubset(frame.columns):
        raise ValueError("historical/forward dictionary cannot be satisfied")
    pd.DataFrame([{"variable": name, "role": "X_historical"} for name in historical] + [{"variable": name, "role": "Y_forward"} for name in forward] + [{"variable": name, "role": "unavailable_historical"} for name in config["variables"]["unavailable_historical"]]).to_csv(out / "variable_dictionary.csv", index=False)

    frames: list[pd.DataFrame] = []
    binnings: dict[str, list[str]] = {}
    frame["pf_interval"] = pf_bin(frame["training_profit_factor"])
    frame["trades_interval"] = fixed_trade_bin(frame["training_n_trades"])
    for column in ["training_expectancy_R", "training_return", "training_max_drawdown", "complexity"]:
        frame[f"{column}_interval"] = quintile_bin(frame[column], column)
    frame["direction_interval"] = frame["direction"].astype(str)
    variables = {"pf_interval": "training_profit_factor", "trades_interval": "training_n_trades", "training_expectancy_R_interval": "training_expectancy_R", "training_return_interval": "training_return", "training_max_drawdown_interval": "training_max_drawdown", "complexity_interval": "complexity", "direction_interval": "direction"}
    for column, original in variables.items():
        binnings[original] = sorted(frame[column].dropna().astype(str).unique().tolist())
    conditions = {"all": np.ones(len(frame), dtype=bool), "active_ge_1": frame["forward_n_trades"] >= 1, "active_ge_3": frame["forward_n_trades"] >= 3, "active_ge_5": frame["forward_n_trades"] >= 5}
    for condition, mask in conditions.items():
        subset = frame.loc[mask].copy()
        for column in variables:
            table = summary_rows(subset, column, "").assign(condition=condition)
            baselines = []
            for (generation, generator), base_part in subset.groupby(["generation", "generator"], sort=True):
                active_base = base_part["forward_n_trades"] > 0
                baselines.append({"variable": column, "condition": condition, "generation": generation, "generator": generator, "interval": "__BASELINE__", "n": len(base_part), "population_n": len(base_part), "pct_population": 1.0, "active_n": int(active_base.sum()), "pct_active_within_interval": float(active_base.mean()), "median_forward_trades": base_part.forward_n_trades.median(), "mean_gross_expectancy_R": base_part.forward_gross_expectancy_R.mean(), "mean_net_expectancy_R": base_part.forward_expectancy_R.mean(), "median_net_expectancy_R": base_part.forward_expectancy_R.median(), "mean_net_return": base_part.forward_return.mean(), "median_net_return": base_part.forward_return.median(), "mean_x2_return": base_part.forward_x2_return.mean(), "median_x2_return": base_part.forward_x2_return.median(), "pct_E": (base_part.economic_class == "E").mean(), "pct_positive_active": (base_part.loc[active_base, "forward_return"] > 0).mean() if active_base.any() else np.nan})
            frames.extend([table, pd.DataFrame(baselines)])
    maps = add_lift(pd.concat(frames, ignore_index=True))
    maps.to_csv(out / "univariate_maps.csv", index=False)

    monthly = maps[maps["interval"] != "__BASELINE__"].groupby(["variable", "condition", "generator", "interval"], as_index=False).agg(months=("generation", "nunique"), positive_lift_months=("lift_E", lambda x: int((x > 1).sum())), negative_lift_months=("lift_E", lambda x: int((x < 1).sum())), median_lift_E=("lift_E", "median"), median_difference_E_pp=("difference_E_pp", "median"), median_net_expectancy_R=("median_net_expectancy_R", "median"), median_net_return=("median_net_return", "median"))
    monthly.to_csv(out / "monthly_consistency.csv", index=False)

    interactions = []
    interaction_specs = [("pf_x_trades", ["pf_interval", "trades_interval"]), ("expectancy_x_trades", ["training_expectancy_R_interval", "trades_interval"]), ("pf_x_maxdd", ["pf_interval", "training_max_drawdown_interval"]), ("direction_x_pf", ["direction_interval", "pf_interval"])]
    for label, columns in interaction_specs:
        grouped = frame.groupby(["generation", "generator", *columns], dropna=False, as_index=False).agg(n=("strategy_hash", "size"), pct_E=("economic_class", lambda x: float((x == "E").mean())), median_net_expectancy_R=("forward_expectancy_R", "median"), median_net_return=("forward_return", "median"), median_x2_return=("forward_x2_return", "median"))
        grouped.insert(0, "interaction", label)
        interactions.append(grouped)
    pd.concat(interactions, ignore_index=True).to_csv(out / "interactions.csv", index=False)

    ledger_candidates = list((ROOT / "reports/p13_artifacts").glob("**/*ledger*.parquet"))
    portfolio_status = {"available": bool(ledger_candidates), "eligible_ledgers": [str(p.relative_to(ROOT)) for p in ledger_candidates], "executed": False, "reason": "P13 stores aggregate census metrics and selected portfolio outputs, but no complete per-strategy forward ledgers for arbitrary historical strata; portfolio returns cannot be reconstructed without summing aggregates."}
    (out / "portfolio_control_status.json").write_text(json.dumps(portfolio_status, sort_keys=True, indent=2) + "\n")
    source_manifest = ROOT / config["source"]["p13a_manifest"]
    result_manifest = {"policy_id": config["policy_id"], "config_sha256": file_sha256(CONFIG_PATH), "source_census_sha256": file_sha256(source), "source_manifest_sha256": file_sha256(source_manifest), "rows": len(frame), "generations": 12, "generators": ["ga", "random"], "forward_end_exclusive": "2018-07-01", "portfolio_control_executed": False, "holdout_used": False, "invalid_run_excluded": True, "binnings": binnings}
    (out / "manifest.json").write_text(json.dumps(result_manifest, sort_keys=True, indent=2) + "\n")

    overall = maps[(maps.interval != "__BASELINE__") & (maps.condition == "all")].groupby(["variable", "interval", "generator"], as_index=False).agg(median_lift_E=("lift_E", "median"), positive_months=("lift_E", lambda x: int((x > 1).sum())), median_net_expectancy_R=("median_net_expectancy_R", "median"), median_net_return=("median_net_return", "median"))
    lines = ["# P13B — Historical Predictability Mapping", "", f"Protocol: `{config['policy_id']}`", f"Config SHA256: `{result_manifest['config_sha256']}`", f"Input census SHA256: `{result_manifest['source_census_sha256']}`", "", "## Auditoría", "", f"Se reutilizaron {len(frame):,} filas válidas de P13/P13A. Se excluyó la corrida inválida de 99.000 evaluaciones; no se leyó el holdout. X contiene únicamente variables históricas archivadas y Y únicamente resultados forward.", "", "## Variables", "", "Variables históricas no disponibles y no reconstruidas: win rate, payoff ratio, frecuencia histórica, firma conductual histórica, coste histórico por operación y número de predicados.", "", "## Resultados", "", overall.head(40).to_csv(index=False), "", "Los mapas completos, lifts por generación, consistencia mensual, interacciones y diccionario están en `reports/p13b_artifacts/`.", "", "## Hipótesis descriptivas candidatas (no filtros)", "", "1. PF histórico 1.30–<1.50 presenta enriquecimiento E en ambos métodos y en los 12 meses, pero la expectancy neta mediana permanece negativa; se falsaría si desaparece al replicar en generaciones cronológicamente posteriores.", "2. Los intervalos de 25–74 operaciones históricas muestran lifts E elevados en ambos métodos, pero pueden reflejar composición/actividad y no margen económico; se falsaría si el efecto no persiste tras emparejar actividad.", "3. Los cuantiles bajos de MaxDD histórico muestran enriquecimiento descriptivo en varios estratos, con dependencia de método y condición de actividad; se falsaría si cambia de signo en una muestra temporal no solapada.", "", "## Control de carteras", "", "No ejecutado: no existen ledgers completos por estrategia para construir estratos arbitrarios con el motor operativo. No se sumaron retornos individuales ni se presentó una aproximación como cartera.", "", "## Conclusión", "", "Existe enriquecimiento descriptivo de P(E) en algunos intervalos históricos, especialmente PF intermedio, pero no evidencia de predictibilidad histórica económicamente utilizable: la expectancy neta agregada sigue siendo negativa y no hay control de carteras. `NO HISTORICAL PREDICTABILITY EVIDENCE` como política operativa validada.", "", "## Limitaciones", "", "Las estrategias están correlacionadas, las ventanas de entrenamiento se solapan durante cinco meses y los 12 meses no son réplicas independientes. Los subconjuntos condicionados por actividad son retrospectivos y no pueden ser predictores operativos."]
    (ROOT / "reports/p13b_predictability_mapping.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(result_manifest, indent=2))


if __name__ == "__main__":
    main()
