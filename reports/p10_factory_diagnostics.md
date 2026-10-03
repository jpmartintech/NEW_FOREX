# P10 — Rolling Factory Diagnostics

## Alcance e integridad

Diagnóstico descriptivo de los artefactos congelados de P08/P09. No se ejecutó GA, no se modificaron estrategias ni políticas históricas y no se leyó el holdout. La política P08 conserva SHA256 `73f7bb0649c814a0ec076fff9d9e3413ba480fb31eca765ed18b860f6e1c72ed`.

La reproducción coincide exactamente: baseline **-16.9897586%**, maximum drawdown **29.1497340%**, costes ×2 **-28.7591429%**, maximum drawdown ×2 **38.9005187%** y **293 operaciones**. El ledger consolidado tiene 0 duplicados, fecha máxima `2022-12-21 17:00:00+00:00` y 0 filas desde 2023. Evidencia: `reports/p10_artifacts/integrity.json`.

## Descomposición por generación

Los candidatos elegibles son las filas `PASS` de la auditoría preservada; la selección mantuvo el límite congelado de cinco estrategias. Métricas netas de los ledgers forward:

| Generación | Elegibles | Sel. | Ops | Exp. R | PF | Retorno | DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019Q1 piloto | 2489 | 5 | 19 | -0.2690 | 0.6991 | -2.59% | 5.32% |
| 2019Q2 | 2493 | 5 | 16 | -0.6053 | 0.3677 | -4.77% | 6.29% |
| 2019Q3 | 3344 | 5 | 7 | -0.4441 | 0.4332 | -1.56% | 1.25% |
| 2019Q4 | 6839 | 5 | 13 | -0.5786 | 0.4016 | -3.72% | 5.07% |
| 2020Q1 | 6713 | 5 | 16 | 1.0435 | 2.9071 | 8.58% | 2.06% |
| 2020Q2 | 6165 | 5 | 20 | -0.6448 | 0.3112 | -6.29% | 5.79% |
| 2020Q3 | 2849 | 5 | 27 | -0.5457 | 0.4420 | -7.19% | 8.44% |
| 2020Q4 | 1750 | 5 | 9 | 0.9445 | 2.8571 | 4.28% | 0.66% |
| 2021Q1 | 2369 | 5 | 21 | -0.1728 | 0.7586 | -1.84% | 4.77% |
| 2021Q2 | 3056 | 5 | 20 | -0.7426 | 0.2584 | -7.20% | 6.96% |
| 2021Q3 | 3253 | 5 | 32 | -0.0431 | 0.9469 | -0.85% | 5.49% |
| 2021Q4 | 1868 | 5 | 25 | -0.0669 | 0.9224 | -0.96% | 3.13% |
| 2022Q1 | 1364 | 5 | 21 | -0.2784 | 0.6700 | -2.98% | 3.87% |
| 2022Q2 | 2074 | 5 | 5 | -1.0703 | 0.0000 | -2.66% | 2.12% |
| 2022Q3 | 1921 | 5 | 8 | 0.8440 | 4.9360 | 3.34% | 0.32% |
| 2022Q4 | 2421 | 5 | 34 | 0.5743 | 2.4256 | 9.93% | 4.96% |

Artefacto completo: `reports/p10_artifacts/generation_diagnostics.csv`.

## Degradación temporal

Se calcularon horizontes acumulados de 30, 60 y 90 días por estrategia y nacimiento, además de trimestres naturales. En promedio contienen 1.16, 2.25 y 3.54 operaciones; por tanto no permiten afirmar degradación estadística. La expectancy media R fue -0.1404, +0.0757 y -0.0795 respectivamente, con muestras insuficientes. Las métricas de training y development WF proceden de la auditoría de selección y no fueron alteradas usando forward posterior. Evidencia: `strategy_diagnostics.csv`, `strategy_horizons_30_60_90.csv` y `strategy_quarters.csv`.

## Ejecución y cartera

El ledger expone `transaction_cost` total por operación y `risk`; no expone comisiones, spread y slippage como componentes identificables. Por ello solo se reconcilia coste total y resultado bruto implícito; no se fabrican componentes a partir de supuestos. Evidencia: `execution_decomposition.csv` y `configs/costs.yaml`.

La cartera tiene 77 hashes activos, máximo cuatro posiciones simultáneas y respeta el límite congelado de riesgo agregado 0.025 con 0.005 por operación. Las peores contribuciones fueron `ad61c8b3`, `b739367a`, `7422b5c9`, `4404aa9f` y `c02abb4c`; las mejores `d2bc3c4c`, `3553ae12`, `6f5d8cd8`, `d4a0dfa4` y `a276705e`. Los peores trimestres fueron 2019Q2, 2020Q3 y 2021Q2; los mejores, 2022Q4, 2020Q1 y 2020Q4. El deterioro aparece ya en baseline, no solo al duplicar costes. Detalle: `portfolio_strategy_contributions.csv`, `portfolio_overlap.csv` y `generation_diagnostics.csv`.

## Control nulo

Antes de cualquier resultado nulo se congeló `configs/p10_null_control.yaml` (`p10-null-control-v1`, SHA256 `d443e5a7aa7933c8f52a9acc00e7ee39b4edfdda9f9e4984d7e404537e55e6ca`).

- **A — selección aleatoria del mismo universo:** 100 réplicas por generación, cinco candidatos elegibles sin reemplazo, semillas desde `20261010`, conservando ventanas, presupuesto, costes y ejecución. No se ejecutó: los ledgers forward preservados solo existen para los seleccionados; producir hasta 8.000 ledgers aleatorios exigiría backtesting adicional y no se presenta una muestra parcial como resultado.
- **B — fábrica null completa:** no ejecutada. La propuesta conserva restricciones y presupuesto y requiere al menos 1.500.000 evaluaciones adicionales para las 15 generaciones no piloto, además de un generador de señales nulo congelado antes de interpretar resultados. A no se presenta como equivalente a B. Evidencia: `null_control_b_estimate.json`.

## Limitaciones y conclusión

P10 es descriptiva y no certifica ni invalida estrategias. Los datos son compatibles con selección que no generaliza al forward, concentración trimestral de pérdidas y amplificación por costes; no permiten identificar por separado los componentes de ejecución ni estimar el control nulo completo sin nuevas ejecuciones. No se alteraron políticas históricas ni se abrió el holdout.
