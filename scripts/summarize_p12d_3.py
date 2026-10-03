"""Create the reproducible P12D.3 cross-generation report."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/p12d_3_artifacts"
REPORT = ROOT / "reports/p12d_3_cross_generation.md"
CONFIG = ROOT / "configs/p12d_3_cross_generation.yaml"
P09 = ROOT / "runs/p09-rolling-historical-v1"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def fmt(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.4f}"


def main() -> None:
    config = yaml.safe_load(CONFIG.read_bytes())
    manifest = json.loads((OUT / "manifest.json").read_text())
    eligibility = pd.read_csv(OUT / "eligibility_by_generation.csv")
    summary = pd.read_csv(OUT / "generation_summary.csv")
    portfolios = pd.read_csv(OUT / "portfolio_results.csv")
    pd.read_csv(OUT / "individual_by_generation.csv")
    dependence = pd.read_csv(OUT / "dependence_by_generation.csv")
    trajectories = pd.read_csv(OUT / "rolling_trajectories.csv")
    windows = []
    for label in config["generations"]:
        generation = json.loads((P09 / label / "generation.json").read_text())
        windows.append((label, generation["windows"]["training"], generation["windows"]["development_wf"], generation["windows"]["forward"]))

    non_original = portfolios[portfolios.group != "original_p09"]
    lines = [
        "# P12D.3 — Cross-generation rule replication",
        "",
        "## Alcance y protocolo",
        "",
        "Se replicó exploratoriamente, sin repetir el GA, la regla congelada `training Profit Factor >= 1.05` y `training trades >= 100` sobre las 15 generaciones P09 (2019 Q2–2022 Q4). La elegibilidad usa exclusivamente las métricas del entrenamiento específico de cada generación. Cada generación tiene 1.000 carteras elegibles de cinco estrategias y 1.000 controles uniformes del universo completo; además se conservaron controles emparejados por actividad histórica y el benchmark descriptivo de los cinco finalistas P09.",
        "",
        f"- Política: `{config['policy_id']}`; SHA256 de configuración: `{manifest['config_sha256']}`.",
        f"- Generaciones: {manifest['generations']}; registros de población elegible: {manifest['eligible_total_records']:,}.",
        f"- Filas de carteras: {manifest['portfolio_rows']:,}; trayectorias: {manifest['trajectory_rows']:,}.",
        "- Costes: baseline y multiplicador ×2. Riesgo: 0.5% por operación y límite agregado 2.5%, con el motor de cartera congelado.",
        "- Holdout: no utilizado; el acceso se limitó a procedure_validation (2019–2022). No hubo operaciones reales.",
        "",
        "La unidad de replicación interpretativa es la generación/trimestre. Las 1.000 carteras dentro de una generación no son experimentos independientes: comparten mercado, población y estrategias. Las trayectorias también comparten componentes entre réplicas.",
        "",
        "## Elegibilidad por generación",
        "",
        "| Generación | Población | Elegibles | % | Universo actividad (n≥100) | Insuficiente |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in eligibility.itertuples():
        lines.append(f"| {row.generation} | {int(row.total):,} | {int(row.eligible):,} | {row.eligible_pct:.2%} | {int(getattr(row, 'activity_matched_universe', 0)):,} | {'sí' if row.insufficient else 'no'} |")

    lines += ["", "## Ventanas exactas y hashes de entrada", "", "| Generación | Training | Development | Forward | Hash P12C combinado |", "|---|---|---|---|---|"]
    for label, training, development, forward in windows:
        lines.append(f"| {label} | {training[0]} ≤ t < {training[1]} | {development[0]} ≤ t < {development[1]} | {forward[0]} ≤ t < {forward[1]} | `{manifest['p12c_source_sha256'][label]}` |")
    lines.append(f"Cada generación conserva {manifest['p12c_part_counts'][config['generations'][0]]} partes P12C; los hashes se calculan sobre nombre y bytes de todas sus partes ordenadas. Los hashes canónicos de los 15 archivos GA están en `manifest.json`.")

    lines += ["", "Todas las generaciones que entraron en el muestreo tenían al menos cinco elegibles; no se completó ninguna cartera artificialmente.", "", "## Resumen de carteras por generación", "", "| Generación | Grupo | Coste | Mediana retorno | P05–P95 | % positivas | Exp. R media | MaxDD medio | Operaciones medias |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in summary.sort_values(["generation", "cost", "group"]).itertuples():
        lines.append(f"| {row.generation} | {row.group} | {row.cost} | {row.median_return:.2%} | {row.p05_return:.2%}–{row.p95_return:.2%} | {row.positive_fraction:.2%} | {row.mean_expectancy_R:.4f} | {row.mean_max_drawdown:.2%} | {row.mean_n_trades:.1f} |")

    lines += ["", "## Comparación consolidada", ""]
    for cost in ["baseline", "costs_x2"]:
        part = non_original[non_original.cost == cost]
        medians = part.groupby(["generation", "group"])["return"].median().unstack()
        eligible_medians = medians.get("eligible", pd.Series(dtype=float))
        full_medians = medians.get("full_random", pd.Series(dtype=float))
        lines.append(f"### {cost}")
        lines.append("")
        lines.append(f"- Generaciones con al menos cinco elegibles: **{int((eligibility.eligible >= 5).sum())}/15**.")
        lines.append(f"- Mediana elegible positiva: **{int((eligible_medians > 0).sum())}/15**.")
        lines.append(f"- Mediana elegible superior al control completo: **{int((eligible_medians > full_medians).sum())}/15**.")
        lines.append(f"- Mediana de las medianas por generación: elegible **{fmt(eligible_medians.median())}**, control completo **{fmt(full_medians.median())}**.")
        eligible_positive = part[part.group == "eligible"].groupby("generation").apply(lambda x: (x["return"] > 0).mean(), include_groups=False).median()
        full_positive = part[part.group == "full_random"].groupby("generation").apply(lambda x: (x["return"] > 0).mean(), include_groups=False).median()
        lines.append(f"- Mediana de carteras rentables: elegible **{pct(eligible_positive)}**; control completo **{pct(full_positive)}**.")
        lines.append("")

    lines += ["## Trayectorias rolling", "", "| Grupo | Coste | Mediana retorno acumulado | P05–P95 | % positivas | Mediana MaxDD |", "|---|---|---:|---:|---:|---:|"]
    for (group, cost), part in trajectories.groupby(["group", "cost"]):
        lines.append(f"| {group} | {cost} | {part.cumulative_return.median():.2%} | {part.cumulative_return.quantile(.05):.2%}–{part.cumulative_return.quantile(.95):.2%} | {part.positive.mean():.2%} | {part.max_drawdown.median():.2%} |")

    lines += ["", "## Actividad y dependencia", "", "Las tablas individuales en `individual_by_generation.csv` separan población completa, elegible y no elegible, y conservan actividad, retorno y expectancy con ambos costes. Las firmas conductuales se usan sólo como diagnóstico: `dependence_by_generation.csv` muestra el número de firmas sobre el forward agregado de las elegibles y la concentración de la firma dominante; no se usaron para seleccionar componentes.", "", "| Generación | Elegibles | Firmas | Duplicados | Mayor firma |", "|---|---:|---:|---:|---:|"]
    for row in dependence.itertuples():
        lines.append(f"| {row.generation} | {int(row.eligible):,} | {int(row.unique_signatures):,} | {int(row.duplicate_rows):,} | {int(row.largest_signature):,} |")

    lines += ["", "## Respuestas operativas", "", f"1. **Existencia:** la regla identifica al menos cinco estrategias en {int((eligibility.eligible >= 5).sum())}/15 generaciones; esto no implica que sean rentables.", "2. **Enriquecimiento:** debe juzgarse comparando las medianas y fracciones positivas elegibles frente a `full_random` en la tabla y CSV; una ventaja en una sola métrica no se interpreta como edge.", "3. **Carteras y costes:** la comparación baseline frente a ×2 y las trayectorias muestran si cualquier diferencia sobrevive a costes; ×2 es el análisis económico más exigente.", "4. **Consistencia:** se reporta el recuento de generaciones donde la mediana elegible supera al control; no se promedian percentiles trimestrales para sustituir trayectorias.", "5. **Dependencia:** la reutilización de estrategias, mercado y ventanas solapadas reduce el número efectivo de observaciones; los resultados son exploratorios.", "6. **Interpretación:** la existencia de ganadoras individuales, el enriquecimiento de la población, la rentabilidad de carteras elegibles y la rentabilidad de trayectorias son afirmaciones distintas y se mantienen separadas.", "", "## Trazabilidad y limitaciones", "", "Los ledgers ricos se generaron causalmente con las definiciones archivadas y se guardaron por generación/coste para los componentes muestreados. Las estadísticas individuales de toda la población se reutilizan de P12C; no se presentan como nuevos backtests completos fuera de sus artefactos de origen. PF infinito por ausencia de pérdidas se conserva en los ledgers y se excluye de medias de PF cuando corresponde. La exposición y la prioridad de señales se calculan mediante el motor de cartera; no se suman retornos individuales.", "", "Los artefactos incluyen composiciones, ledgers, resultados individuales, resultados de cartera, trayectorias, resúmenes, firmas, hashes de archivos GA y manifiesto. Cualquier diferencia material entre archivos de entrada y sus hashes debe invalidar la reproducción.", ""]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
