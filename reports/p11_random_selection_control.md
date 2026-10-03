# P11 — Random Selection Control A

## Alcance y disponibilidad

Se auditó el universo preservado de P08/P09 antes de ejecutar el control. Las 16 generaciones conservan archivo GA completo de 100.000 filas, auditoría de selección, hashes canónicos, payload ejecutable de cada candidato elegible, cinco hashes seleccionados y configuración forward. Los candidatos se reconstruyeron con `StrategyDefinition` y se verificó que el hash canónico coincidiera. Los universos elegibles tenían entre 1.364 y 6.839 candidatos; después de excluir las cinco estrategias NEW_FOREX siempre quedaron al menos 1.359 candidatos.

No se repitió el GA. No se utilizaron ledgers forward preexistentes para los controles: se generaron causalmente con el backtester congelado. Evidencia: `reports/p11_artifacts/availability_audit.json`.

## Protocolo congelado

El protocolo `p11-random-selection-control-a-v1` se congeló antes de la ejecución en `configs/random_selection_control.yaml`.

- Commit de congelación: `cbc7732`.
- SHA256 de configuración: `11db3cdca55d5e33fdcb6d7ef65dfe382a30d58b88f93cbdf0ae057c895aab9f`.
- 100 réplicas por generación, 16 generaciones, cinco estrategias por réplica.
- Universo elegible de la misma generación, excluyendo las cinco seleccionadas por NEW_FOREX.
- Muestreo uniforme sin reemplazo, semillas `20261010 + generation_index * 1000 + replicate_index`.
- Forward, M15, costes baseline/×2, riesgo 0.005 y límite agregado 0.025 idénticos a P08/P09.
- No se cargaron filas desde 2023.

La ejecución produjo 1.600 carteras trimestrales. Son 8.000 slots estrategia-forward muestreados; se ejecutaron 7.168 backtests únicos y se reutilizaron de forma determinista los ledgers de candidatos repetidos entre réplicas. Esta memoización no cambia las selecciones ni sus resultados. Se generaron 100 trayectorias rolling, una selección por generación y réplica.

## Resultados agregados de carteras trimestrales

Media y mediana sobre las 1.600 carteras independientes por generación:

| Escenario | Retorno medio | Retorno mediano | Expectancy R media | PF medio | DD medio | Bruto R medio | Neto R medio |
|---|---:|---:|---:|---:|---:|---:|---:|
| Control baseline | -0.50% | -1.14% | -0.0190 | 1.0469 | 6.42% | 2.8167 | -1.2111 |
| Control costes ×2 | -2.48% | -2.64% | -0.0835 | 0.9379 | 7.34% | 2.8167 | -5.2389 |

El resultado real NEW_FOREX agregado fue -16.9898% baseline y -28.7591% con costes ×2, con DD de 29.15% y 38.90%, respectivamente. El 98.625% de las carteras aleatorias baseline superó el retorno real; con costes ×2, el 100% superó el retorno real. La comparación trimestral completa está en `comparison_by_generation.csv`.

El resultado bruto de los controles es positivo en promedio, pero el neto es negativo; esto refleja sensibilidad a costes y no evidencia de edge. El resultado bruto de la cohorte real se reconcilia en P10 como -3.777559 R frente a -34.308180 R netos, pero la cartera real y los controles no deben compararse usando una suma simple de R como sustituto de su equity curve.

## Trayectorias rolling

Las 100 trayectorias rolling respetan el orden cronológico de las generaciones y el motor de cartera original.

| Escenario | Retorno medio control | Mediana control | Operaciones medias | DD medio | Retorno real | Controles que superan al real | Percentil descriptivo real |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | -9.86% | -11.46% | 988.45 | 30.22% | -16.99% | 62% | 38 |
| Costes ×2 | -34.63% | -35.67% | 988.45 | 42.46% | -28.76% | 32% | 68 |

El percentil es la fracción de trayectorias con retorno inferior o igual al real. La aparente diferencia entre la comparación trimestral y la rolling no es un error: los controles aleatorios generan muchas más operaciones en promedio que la cartera real (988 frente a 293), y el límite de riesgo, el solapamiento y la composición de las 16 generaciones cambian la trayectoria compuesta. Por ello las 1.600 carteras trimestrales no son 1.600 observaciones independientes y no se debe elegir una semilla retrospectivamente.

## Comparación por generación

El control aleatorio superó al resultado real baseline en las siguientes fracciones de 100 réplicas:

| Generación | Real | Control medio | Control mediano | Fracción superior al real |
|---|---:|---:|---:|---:|
| 2019Q1 | -2.60% | -2.01% | -1.84% | 57% |
| 2019Q2 | -4.77% | -3.50% | -3.98% | 66% |
| 2019Q3 | -1.56% | 8.77% | 8.39% | 97% |
| 2019Q4 | -3.74% | -7.88% | -7.32% | 14% |
| 2020Q1 | 8.55% | 11.82% | 11.41% | 71% |
| 2020Q2 | -6.30% | -12.48% | -12.17% | 8% |
| 2020Q3 | -7.21% | -5.36% | -5.48% | 65% |
| 2020Q4 | 4.27% | 2.66% | 2.40% | 34% |
| 2021Q1 | -1.85% | 2.94% | 3.12% | 85% |
| 2021Q2 | -7.19% | -0.77% | -0.82% | 95% |
| 2021Q3 | -0.85% | 2.54% | 3.11% | 75% |
| 2021Q4 | -0.96% | -6.39% | -6.04% | 8% |
| 2022Q1 | -2.98% | -3.51% | -3.17% | 47% |
| 2022Q2 | -2.66% | -1.28% | -1.53% | 65% |
| 2022Q3 | 3.34% | 8.24% | 7.13% | 78% |
| 2022Q4 | 9.93% | -1.77% | -1.91% | 1% |

La tabla no es una prueba de independencia: las generaciones comparten arquitectura, datos y restricciones, y el universo elegible se deriva de la misma búsqueda GA histórica.

## Limitaciones e interpretación

Este control A mide el valor añadido de escoger cinco candidatos concretos frente a cinco candidatos elegibles aleatorios del mismo universo. No mide el valor de generar el universo ni reproduce el mundo nulo completo B. La actividad operativa desigual es un confusor importante: los controles aleatorios tienen más operaciones y, por tanto, más exposición a costes y a la regla de riesgo agregado.

El resultado diagnóstico es desfavorable para la selección final en la comparación trimestral baseline, pero no demuestra que no exista edge de mercado ni que el control aleatorio sea una cartera operable superior. Tampoco autoriza modificar P08/P09 ni seleccionar una nueva semilla. El holdout permanece sellado.

Artefactos principales: `control_metrics.csv`, `control_by_generation.csv`, `comparison_by_generation.csv`, `rolling_summary.csv`, `summary.json`, `manifest.json` y `ledgers_*.parquet`.
