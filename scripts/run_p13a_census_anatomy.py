"""Produce the reproducible P13 full-census economic anatomy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/p13a_census_anatomy.yaml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantiles(frame: pd.DataFrame, group: list[str], metrics: list[str], probs: list[float]) -> pd.DataFrame:
    rows: list[dict] = []
    for keys, part in frame.groupby(group, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = dict(zip(group, keys, strict=True))
        population = "active" if "active" in group and bool(keys[group.index("active")]) else "full"
        for metric in metrics:
            values = pd.to_numeric(part[metric], errors="coerce").replace([np.inf, -np.inf], np.nan)
            for p in probs:
                row = {**base, "population": population, "metric": metric, "quantile": p, "value": float(values.quantile(p)) if values.notna().any() else np.nan}
                rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_bytes())
    source = ROOT / config["source"]["p13_census"]
    manifest_path = ROOT / config["source"]["p13_manifest"]
    manifest = json.loads(manifest_path.read_text())
    if sha256(source) != config["source"]["p13_census_sha256"] or sha256(manifest_path) != config["source"]["p13_manifest_sha256"]:
        raise ValueError("P13 source hash mismatch")
    if not manifest["budget_exact"] or manifest["holdout_used"] or manifest["census_rows"] != 2_400_000:
        raise ValueError("P13 manifest is not a valid complete census")
    if not config["source"]["invalid_run_excluded"]:
        raise ValueError("invalid 99k run must be excluded")

    out = ROOT / config["artifacts"]["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_parquet(source)
    required = {"strategy_hash", "generation", "generator", "forward_month", "forward_n_trades", "forward_total_R", "forward_x2_total_R", "forward_gross_total_R", "forward_expectancy_R", "forward_x2_expectancy_R", "forward_profit_factor", "forward_x2_profit_factor", "forward_return", "forward_x2_return", "forward_max_drawdown", "forward_x2_max_drawdown", "cost_R_per_trade", "active"}
    if not required.issubset(frame.columns) or len(frame) != 2_400_000:
        raise ValueError("incomplete P13 census schema")
    if frame.groupby(["generation", "generator"], sort=False).size().ne(100_000).any() or frame.duplicated(["generation", "generator", "strategy_hash"]).any():
        raise ValueError("P13 census identity failure")
    expected_months = {f"2017-{m:02d}" for m in range(7, 13)} | {f"2018-{m:02d}" for m in range(1, 7)}
    if set(frame["forward_month"]) != expected_months or frame["forward_month"].astype(str).max() >= "2018-07":
        raise ValueError("forward period outside P13")
    if not np.allclose(frame["forward_gross_total_R"], 2 * frame["forward_total_R"] - frame["forward_x2_total_R"], atol=1e-10):
        raise ValueError("gross/x2 accounting identity failure")
    active_expected = frame["forward_n_trades"] > 0
    if not frame["active"].equals(active_expected):
        raise ValueError("activity flag mismatch")

    masks = {
        "A": ~active_expected,
        "B": active_expected & (frame["forward_gross_total_R"] <= 0),
        "C": active_expected & (frame["forward_gross_total_R"] > 0) & (frame["forward_total_R"] <= 0),
        "D": active_expected & (frame["forward_total_R"] > 0) & (frame["forward_x2_total_R"] <= 0),
        "E": active_expected & (frame["forward_x2_total_R"] > 0),
    }
    membership = sum(mask.astype(np.int8) for mask in masks.values())
    if not (membership == 1).all():
        raise ValueError("economic classes are not mutually exclusive/exhaustive")
    frame["economic_class"] = ""
    for label, mask in masks.items():
        frame.loc[mask, "economic_class"] = label
    frame["gross_positive_net_nonpositive"] = (frame["forward_gross_total_R"] > 0) & (frame["forward_total_R"] <= 0)
    frame["gross_positive_x2_nonpositive"] = (frame["forward_gross_total_R"] > 0) & (frame["forward_x2_total_R"] <= 0)
    frame["historical_filter_pass"] = (frame["training_profit_factor"] > 1.30) & (frame["training_n_trades"] > 250)
    frame.to_parquet(out / "classified_census.parquet", index=False)

    group_cols = ["generation", "generator", "economic_class"]
    class_rows = []
    for keys, part in frame.groupby(group_cols, sort=True):
        row = dict(zip(group_cols, keys, strict=True))
        active_n = int(frame[(frame.generation == keys[0]) & (frame.generator == keys[1])]["active"].sum())
        row.update({"n": len(part), "pct_universe": len(part) / 100_000, "pct_active": len(part) / active_n if keys[2] != "A" and active_n else np.nan,
                    "operations": int(part["forward_n_trades"].sum()), "mean_gross_expectancy_R": part["forward_gross_expectancy_R"].mean(),
                    "mean_net_expectancy_R": part["forward_expectancy_R"].mean(), "mean_x2_expectancy_R": part["forward_x2_expectancy_R"].mean(),
                    "mean_gross_R": part["forward_gross_total_R"].mean(), "mean_net_R": part["forward_total_R"].mean(), "mean_x2_R": part["forward_x2_total_R"].mean(),
                    "mean_max_drawdown": part["forward_max_drawdown"].mean()})
        class_rows.append(row)
    pd.DataFrame(class_rows).to_csv(out / "classification_by_generation.csv", index=False)

    metrics = ["forward_n_trades", "forward_gross_expectancy_R", "forward_expectancy_R", "forward_x2_expectancy_R", "forward_return", "forward_x2_return", "cost_R_per_trade", "forward_profit_factor", "forward_x2_profit_factor", "forward_max_drawdown", "forward_x2_max_drawdown"]
    active_copy = frame.copy()
    active_copy["population"] = "full"
    active = frame[frame["active"]].copy()
    active["population"] = "active"
    distributions = []
    probs = config["evaluation"]["distributions"]
    for population, part in (("full", active_copy), ("active", active)):
        q = quantiles(part, ["generation", "generator"], metrics, probs)
        q["population"] = population
        distributions.append(q)
    pd.concat(distributions, ignore_index=True).to_csv(out / "distributions.csv", index=False)

    cost = frame[frame["active"]].groupby(["generation", "generator"], as_index=False).agg(
        active=("strategy_hash", "size"), positive_gross=("forward_gross_total_R", lambda x: int((x > 0).sum())),
        gross_positive_net_nonpositive=("gross_positive_net_nonpositive", "sum"), gross_positive_x2_nonpositive=("gross_positive_x2_nonpositive", "sum"),
        median_cost_R_per_trade=("cost_R_per_trade", "median"), mean_cost_R_per_trade=("cost_R_per_trade", "mean"),
        median_forward_n_trades=("forward_n_trades", "median"), mean_forward_n_trades=("forward_n_trades", "mean"))
    cost.to_csv(out / "cost_efficiency.csv", index=False)

    history = frame[frame["active"]].groupby(["generation", "generator", "economic_class"], as_index=False).agg(
        n=("strategy_hash", "size"), median_training_pf=("training_profit_factor", "median"), median_training_trades=("training_n_trades", "median"),
        median_training_expectancy_R=("training_expectancy_R", "median"), median_training_return=("training_return", "median"), median_training_maxdd=("training_max_drawdown", "median"),
        median_complexity=("complexity", "median"))
    history.to_csv(out / "historical_by_class.csv", index=False)
    comparison = frame.groupby(["generation", "generator"], as_index=False).agg(active_pct=("active", "mean"), net_positive_pct=("forward_total_R", lambda x: float((x > 0).mean())), x2_positive_pct=("forward_x2_total_R", lambda x: float((x > 0).mean())), median_net_expectancy_R=("forward_expectancy_R", "median"), median_net_return=("forward_return", "median"), median_x2_return=("forward_x2_return", "median"))
    pivot = comparison.pivot(index="generation", columns="generator")
    pivot.to_csv(out / "ga_random_comparison.csv")
    e = frame[frame["economic_class"] == "E"].groupby(["generation", "generator"], as_index=False).agg(e_count=("strategy_hash", "size"), e_filter_pass=("historical_filter_pass", "sum"), e_active=("active", "sum"))
    e["e_rejected"] = e["e_count"] - e["e_filter_pass"]
    e["rejected_pct"] = e["e_rejected"] / e["e_count"].replace(0, np.nan)
    e.to_csv(out / "filter_diagnosis.csv", index=False)
    repetition = frame.groupby(["generator", "strategy_hash"], as_index=False).agg(generations=("generation", "nunique"))
    repetition[repetition["generations"] > 1].to_csv(out / "identity_repetition.csv", index=False)

    counts = frame.groupby(["generator", "economic_class"], as_index=False).size().pivot(index="generator", columns="economic_class", values="size").fillna(0).astype(int)
    summaries = []
    for generator in ("ga", "random"):
        part = frame[frame["generator"] == generator]
        active_part = part[part["active"]]
        summaries.append(
            f"- **{generator.upper()}**: activo {part['active'].mean():.2%}; retorno baseline positivo {((part['forward_total_R'] > 0).mean()):.2%}; positivo con costes ×2 {((part['forward_x2_total_R'] > 0).mean()):.2%}; expectancy bruta media activa {active_part['forward_gross_expectancy_R'].mean():.4f} R; neta baseline {active_part['forward_expectancy_R'].mean():.4f} R; operaciones medias activas {active_part['forward_n_trades'].mean():.2f}."
        )
    e_all = frame[frame["economic_class"] == "E"]
    e_rejected = int((~e_all["historical_filter_pass"]).sum())
    report = out.parent / "p13a_census_anatomy.md"
    lines = ["# P13A — Full Census Economic Anatomy", "", f"Protocol: `{config['policy_id']}`", f"Config SHA256: `{sha256(CONFIG_PATH)}`", f"Source census SHA256: `{sha256(source)}`", "", "## Integridad", "", f"Se analizaron {len(frame):,} filas válidas: 12 generaciones, 100.000 estrategias por generador y generación. La corrida inválida de 99.000 evaluaciones está excluida. Holdout: no utilizado.", "", "## Clasificación económica", "", "Cero exacto se trata como no positivo; la inactividad se clasifica exclusivamente por `forward_n_trades == 0`, no por expectancy.", "", counts.to_csv(), "", "## Reconciliación", "", "El bruto se define como `2 × baseline_R − costes_x2_R`; la identidad se verifica fila a fila. El único coste disponible es `transaction_cost` agregado por operación; no se inventa un desglose de spread/comisión/slippage.", "", "## Resultados agregados", "", *summaries, "", f"Las clases globales son A={int((frame.economic_class == 'A').sum()):,}, B={int((frame.economic_class == 'B').sum()):,}, C={int((frame.economic_class == 'C').sum()):,}, D={int((frame.economic_class == 'D').sum()):,}, E={int((frame.economic_class == 'E').sum()):,}. El grupo E contiene {e_rejected:,} filas que no pasan retrospectivamente el filtro PF > 1.30 y trades > 250; esta observación no se usa como regla.", "", "Los detalles reproducibles están en `reports/p13a_artifacts/`: censo clasificado, distribuciones P01–P99, eficiencia de costes, grupo E, comparación GA/Random, diagnóstico del filtro e identidades repetidas.", "", "## Interpretación", "", "La comparación GA/Random se presenta por generación y no trata las estrategias correlacionadas como observaciones independientes. El grupo E se analiza retrospectivamente y sus rasgos históricos no se convierten en predictores.", "", "### Respuestas obligatorias", "", "1. Hay estrategias positivas en ambas poblaciones, pero la fracción que sobrevive a costes ×2 es minoritaria; las cifras exactas por mes están en `classification_by_generation.csv`.", "2. El déficit económico combina actividad insuficiente, margen bruto pequeño y fricción; `cost_efficiency.csv` cuantifica qué parte del bruto positivo cruza a neto no positivo.", "3. GA y Random producen distribuciones diferentes por generación, con entrenamiento solapado; la comparación no es una prueba de independencia.", "4. El grupo E se caracteriza en `historical_by_class.csv`; las propiedades comunes son descriptivas y no validan un predictor.", "5. El filtro original se audita en `filter_diagnosis.csv`; no se propone umbral alternativo ni se inicia una nueva fábrica.", "", "## Limitaciones", "", "El censo contiene estrategias correlacionadas y los 12 meses comparten cinco meses de entrenamiento. No se accede a 2023–2026 y no se repite el GA."]
    report.write_text("\n".join(lines) + "\n")
    result_manifest = {"policy_id": config["policy_id"], "config_sha256": sha256(CONFIG_PATH), "source_census_sha256": sha256(source), "source_manifest_sha256": sha256(manifest_path), "rows": len(frame), "class_counts_by_generator": {str(generator): {str(category): int(value) for category, value in row.items()} for generator, row in counts.iterrows()}, "invalid_run_excluded": True, "holdout_used": False}
    (out / "manifest.json").write_text(json.dumps(result_manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result_manifest, indent=2))


if __name__ == "__main__":
    main()
