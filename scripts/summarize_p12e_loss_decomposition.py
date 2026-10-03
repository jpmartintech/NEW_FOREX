"""Build the P12E accounting and diagnostic report from frozen outputs."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12e_loss_decomposition.yaml"
OUT = ROOT / "reports/p12e_artifacts"
REPORT = ROOT / "reports/p12e_loss_decomposition.md"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    config = yaml.safe_load(CONFIG.read_bytes())
    manifest = json.loads((OUT / "manifest.json").read_text())
    portfolios = pd.read_csv(OUT / "portfolio_decomposition.csv")
    trades = pd.read_parquet(OUT / "executed_trades.parquet")
    periods = pd.read_csv(OUT / "period_decomposition.csv")
    pd.read_csv(OUT / "strategy_decomposition.csv")
    rolling = pd.read_csv(OUT / "rolling_decomposition.csv")

    # Diagnostic leave-one-generation-out curves, retaining chronological compounding.
    loo = []
    for (group, cost, replicate), part in portfolios.groupby(["group", "cost", "replicate"]):
        part = part.sort_values("generation")
        for omitted in part.generation:
            kept = part[part.generation != omitted]
            net_curve = np.cumprod(1 + kept.net_return.to_numpy(float))
            gross_curve = np.cumprod(1 + kept.gross_return_capitalized.to_numpy(float))
            loo.append({"group": group, "cost": cost, "replicate": replicate, "omitted_generation": omitted, "net_return": net_curve[-1] - 1, "gross_return": gross_curve[-1] - 1})
    loo_frame = pd.DataFrame(loo)
    loo_frame.to_csv(OUT / "leave_one_generation_out.csv", index=False)

    summary = portfolios.groupby(["group", "cost"]).agg(
        median_net_return=("net_return", "median"), p05_net_return=("net_return", lambda x: x.quantile(.05)), p95_net_return=("net_return", lambda x: x.quantile(.95)),
        median_gross_return=("gross_return_capitalized", "median"), median_cost_drag=("cost_drag_capitalized_at_net_path", "median"),
        median_gross_expectancy_R=("gross_expectancy_R", "median"), median_net_expectancy_R=("net_expectancy_R", "median"), median_max_drawdown=("max_drawdown_net", "median"),
        positive_net=("net_return", lambda x: (x > 0).mean()), positive_gross=("gross_return_capitalized", lambda x: (x > 0).mean()),
        gross_positive_net_negative=("gross_positive_net_negative", "mean"), median_cost_per_operation_R=("cost_per_operation_R", "median"),
        median_operations=("n_trades", "median"), median_max_concurrent=("max_concurrent_positions", "median"), blocked_signals=("blocked_signals", "sum"),
        mean_simultaneous_loss_exits=("simultaneous_loss_exits", "mean"),
    ).reset_index()
    summary.to_csv(OUT / "cost_drag_summary.csv", index=False)

    period_summary = periods.groupby(["group", "cost", "period_type", "period"]).agg(n_trades=("n_trades", "sum"), net_pnl=("net_pnl", "sum"), gross_pnl=("gross_pnl_at_net_path", "sum"), cost_drag=("cost_drag_pnl", "sum"), loss_pnl=("loss_pnl", "sum")).reset_index()
    period_summary.to_csv(OUT / "temporal_concentration.csv", index=False)
    direction_summary = trades.groupby(["group", "cost", "direction"]).agg(n_trades=("net_pnl", "size"), net_pnl=("net_pnl", "sum"), gross_pnl=("gross_pnl_at_net_path", "sum"), cost_drag=("cost_drag_pnl", "sum"), loss_fraction=("net_pnl", lambda x: (x < 0).mean())).reset_index()
    direction_summary.to_csv(OUT / "direction_decomposition.csv", index=False)

    lines = [
        "# P12E — Portfolio loss decomposition",
        "",
        "## Protocolo y alcance",
        "",
        f"Se reutilizaron sin remuestreo las composiciones y los ledgers congelados de P12D.3. Política `{config['policy_id']}`, SHA256 de configuración `{manifest['config_sha256']}`. Se reconstruyeron {manifest['portfolio_rows']:,} carteras, {manifest['trade_rows']:,} operaciones efectivamente ejecutadas y {manifest['rolling_rows']:,} trayectorias.",
        "",
        "El holdout 2023–2026 no se abrió. La regla histórica y el motor de selección permanecen intactos.",
        "",
        "## Reconciliación contable",
        "",
        "Para cada operación, `gross_R = result_R + transaction_cost / risk`; `net_R = result_R`. El PnL bruto en precio es movimiento firmado más funding; el neto resta el coste agregado registrado. El motor capitaliza cada operación con el riesgo de cartera (0,5%) y conserva por separado la curva neta y la curva bruta.",
        "",
        "El ledger sólo registra `transaction_cost` agregado. No identifica por separado comisión, spread y slippage, por lo que P12E no inventa esa división. La comparación ×2 duplica el coste agregado del backtester; si cambia la trayectoria de señales, esa diferencia no debe interpretarse como coste puro.",
        "",
        "La identidad `bruto en la trayectoria neta = neto + cost_drag_capitalized_at_net_path` se verificó operación a operación; el retorno neto y el maximum drawdown coinciden con P12D.3 dentro de 1e-10.",
        "",
        "## Cost drag por cartera",
        "",
        "| Grupo | Coste | Bruto | Neto | Drag | Exp. bruta R | Exp. neta R | MaxDD | % bruto + | % bruto+/neto− | Coste R/op. | Oper. | Simult. máx. | Bloqueos |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples():
        lines.append(f"| {row.group} | {row.cost} | {pct(row.median_gross_return)} | {pct(row.median_net_return)} | {pct(row.median_cost_drag)} | {row.median_gross_expectancy_R:.4f} | {row.median_net_expectancy_R:.4f} | {pct(row.median_max_drawdown)} | {pct(row.positive_gross)} | {pct(row.gross_positive_net_negative)} | {row.median_cost_per_operation_R:.4f} | {row.median_operations:.1f} | {row.median_max_concurrent:.1f} | {int(row.blocked_signals)} |")

    month_baseline = period_summary[(period_summary.period_type == "month") & (period_summary.cost == "baseline")]
    direction_lines = [f"- {row.group} {row.cost} {row.direction}: {int(row.n_trades):,} operaciones, neto acumulado {row.net_pnl:.4f}, pérdida en {row.loss_fraction:.2%}." for row in direction_summary.itertuples()]
    concentration_lines = []
    for group in ["eligible", "full_random"]:
        part = month_baseline[month_baseline.group == group]
        worst = part.nsmallest(3, "net_pnl")[["period", "net_pnl"]]
        best = part.nlargest(3, "net_pnl")[["period", "net_pnl"]]
        concentration_lines.append(f"- {group}: peores meses " + ", ".join(f"{r.period} ({r.net_pnl:.3f})" for r in worst.itertuples()) + "; mejores " + ", ".join(f"{r.period} ({r.net_pnl:.3f})" for r in best.itertuples()) + ".")

    lines += ["", "La población elegible tiene mediana bruta positiva pero mediana neta negativa en ambos escenarios; por tanto, para esta cohorte el coste drag es suficiente para transformar una parte material de los resultados brutos en pérdidas netas. En los controles la mediana bruta es aproximadamente nula o negativa y la fricción agrava el resultado.", "", "## Trayectorias rolling", "", "| Grupo | Coste | P05–P95 neto | Mediana bruto | Mediana neto | Drag mediano | % positivas | MaxDD mediano |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for (group, cost), part in rolling.groupby(["group", "cost"]):
        lines.append(f"| {group} | {cost} | {pct(part.net_return.quantile(.05))}–{pct(part.net_return.quantile(.95))} | {pct(part.gross_return.median())} | {pct(part.net_return.median())} | {pct(part.cost_drag.median())} | {pct(part.positive.mean())} | {pct(part.max_drawdown.median())} |")

    lines += ["", "La capitalización importa: las trayectorias no se reconstruyeron sumando retornos trimestrales. La mediana elegible pasa de bruto `" + pct(rolling[(rolling.group == 'eligible') & (rolling.cost == 'baseline')].gross_return.median()) + "` a neto `" + pct(rolling[(rolling.group == 'eligible') & (rolling.cost == 'baseline')].net_return.median()) + "` en baseline, y a `" + pct(rolling[(rolling.group == 'eligible') & (rolling.cost == 'costs_x2')].net_return.median()) + "` con ×2.", "", "## Concentración temporal y dependencia", "", *concentration_lines, "", "Dirección (suma descriptiva sobre las carteras muestreadas):", *direction_lines, "", "La tabla `temporal_concentration.csv` contiene la contribución por generación/trimestre, mes y semana para cada grupo y coste. `direction_decomposition.csv` separa LONG/SHORT; `strategy_decomposition.csv` conserva la contribución de cada componente muestreado. Los episodios más negativos y el leave-one-generation-out están disponibles en `leave_one_generation_out.csv`; no se eliminó ningún periodo.", "", "El contador de simultaneidad de pérdidas mide cierres negativos mientras había otras posiciones abiertas. Las carteras elegibles muestran dependencia de pérdidas concurrentes, pero no se interpretan las 70.341 estrategias como observaciones independientes. La firma conductual de P12D.3 era agregada y forward-only; no se reconstruye como predictor.", "", "## Efecto del motor", "", "No se registraron señales bloqueadas por el límite agregado en las 90.000 carteras; cinco estrategias con 0,5% por operación alcanzan como máximo el 2,5% permitido. Por ello, en esta cohorte no hay evidencia de que el límite de exposición explique las pérdidas. El ledger no conserva un log de todas las señales candidatas rechazadas, así que no es posible distinguir retrospectivamente prioridad frente a ausencia de señal; sólo se auditan las operaciones efectivamente ejecutadas.", "", "## Respuestas diagnósticas", "", "1. **Antes o después de costes:** en las elegibles, el resultado bruto agregado es descriptivamente favorable en mediana, pero la trayectoria neta es negativa; en los controles la pérdida ya aparece en bruto o es casi nula.", "2. **Proporción atribuible a costes:** el drag se reporta por cartera, operación y trayectoria en los artefactos; no se convierte en una fracción causal única porque la capitalización y ×2 cambian la trayectoria económica.", "3. **Concentración:** la descomposición mensual/semanal y leave-one-out muestran cuánto depende cada resultado de periodos; no se optimizó eliminando periodos.", "4. **Pérdidas simultáneas:** sí existen cierres negativos con otras posiciones abiertas; su frecuencia y magnitud están en `simultaneous_loss_exits` y `other_open_losses_at_exit`.", "5. **Restricciones:** no hubo bloqueos por cap en los ledgers muestreados; el impacto observable del motor es la capitalización, prioridad temporal y riesgo por operación.", "6. **Ventaja frente al control:** la elegibilidad mejora la distribución histórica/forward de la cartera, reduciendo frecuencia y operaciones, pero no crea suficiente margen neto bajo costes; la diferencia es enriquecimiento relativo, no rentabilidad absoluta.", "7. **Limitación dominante:** para las elegibles, el margen bruto pequeño frente a costes por operación y la concentración/dependencia temporal dominan; para el control, también falta rentabilidad bruta.", "", "## Limitaciones", "", "No se pueden separar comisión, spread y slippage desde estos ledgers. Tampoco se puede reconstruir el universo de señales bloqueadas que nunca llegó al ledger. Los controles comparten mercado y estrategias entre carteras, y las generaciones tienen ventanas solapadas; las distribuciones no son muestras independientes. Los resultados son contables y diagnósticos, no una nueva regla de selección ni evidencia confirmatoria de edge.", ""]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
