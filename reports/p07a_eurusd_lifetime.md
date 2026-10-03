# P07A — EURUSD strategy lifetime analysis

## Alcance

Análisis descriptivo de la única estrategia congelada, sin modificar el `FAIL`
formal de P07:

`237d10ee505b9bf528a2036d30babb26db137e9de3852a8bb116f73799798ebd`

- Nacimiento operativo: `2019-01-01`.
- Datos: exclusivamente `procedure_validation`, `[2019-01-01, 2023-01-01)`.
- Operaciones cerradas: 57.
- Filas cargadas con timestamp `>=2023-01-01`: 0.
- Holdout y operaciones reales: no utilizados.
- Backtester M15, parámetros y reglas de P07 sin cambios.

La ejecución reproducible es `scripts/run_p07a_lifetime.py` y sus artefactos
están en [reports/p07a_artifacts](./p07a_artifacts/):

- [summary.json](./p07a_artifacts/summary.json)
- [horizons.csv](./p07a_artifacts/horizons.csv)
- [quarters.csv](./p07a_artifacts/quarters.csv)
- [operations.csv](./p07a_artifacts/operations.csv)
- [equity.svg](./p07a_artifacts/equity.svg)
- [rolling_expectancy.svg](./p07a_artifacts/rolling_expectancy.svg)

## Proveniencia

- Dataset EURUSD SHA256:
  `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Manifest P03.1 SHA256:
  `176b3b76bba6e6cb73923214225f6f5c72c3cef59a89f9f8876c54df43d4977e`.
- P04 report SHA256:
  `806d9be821b0e7d002e49322b0a0f13627180bb26171f06b82eaaf1e5876547d`.
- P07 report SHA256:
  `eaa3e464acd3c8025386aefb5aaa57ad6b82c3ddecaea54b0a65282c5bf1f745`.
- Política de riesgo: `p04-fixed-fractional-r-v1`, riesgo `0.005` por R.

## Horizontes acumulados

Cada horizonte usa únicamente operaciones cerradas antes de su fecha final.
`E×2` es expectancy neta con costes ×2; no se interpreta como una nueva
selección.

| Horizonte | Operaciones | E R | PF | Retorno | Max DD | Racha | E×2 R | PF×2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 meses | 1 | 0.0231 | inf | 0.0001 | 0.0000 | 0 | -0.0634 | 0.0000 |
| 6 meses | 4 | -0.8515 | 0.0067 | -0.0169 | 0.0170 | 3 | -0.9804 | 0.0000 |
| 9 meses | 7 | -0.5695 | 0.2969 | -0.0198 | 0.0224 | 4 | -0.6937 | 0.2415 |
| 12 meses | 10 | -0.5765 | 0.2782 | -0.0286 | 0.0287 | 4 | -0.7086 | 0.2161 |
| 18 meses | 15 | -0.6266 | 0.2424 | -0.0461 | 0.0462 | 4 | -0.7478 | 0.1915 |
| 24 meses | 26 | -0.3103 | 0.5988 | -0.0401 | 0.0771 | 8 | -0.4203 | 0.5096 |
| 36 meses | 42 | -0.2413 | 0.6990 | -0.0507 | 0.0771 | 8 | -0.3595 | 0.5967 |
| 48 meses | 57 | -0.0737 | 0.8980 | -0.0226 | 0.0771 | 8 | -0.1809 | 0.7737 |

El PF infinito de 3 meses se conserva como diagnóstico descriptivo; no se usa
como evidencia de validez.

## Trimestres naturales

| Trimestre | N | E R | PF | Retorno | DD | E×2 R | PF×2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019 Q1 | 1 | 0.0231 | inf | 0.0001 | 0.0000 | -0.0634 | 0.0000 |
| 2019 Q2 | 3 | -1.1431 | 0.0000 | -0.0170 | 0.0113 | -1.2861 | 0.0000 |
| 2019 Q3 | 3 | -0.1934 | 0.7410 | -0.0030 | 0.0057 | -0.3114 | 0.6234 |
| 2019 Q4 | 3 | -0.5929 | 0.2327 | -0.0089 | 0.0057 | -0.7432 | 0.1543 |
| 2020 Q1 | 1 | -1.1560 | 0.0000 | -0.0058 | 0.0000 | -1.3120 | 0.0000 |
| 2020 Q2 | 4 | -0.6195 | 0.2404 | -0.0124 | 0.0109 | -0.7050 | 0.1998 |
| 2020 Q3 | 4 | -1.0916 | 0.0000 | -0.0217 | 0.0162 | -1.1831 | 0.0000 |
| 2020 Q4 | 7 | 0.8138 | 2.7071 | 0.0285 | 0.0057 | 0.7176 | 2.3671 |
| 2021 Q1 | 3 | -1.0945 | 0.0000 | -0.0163 | 0.0110 | -1.1891 | 0.0000 |
| 2021 Q2 | 4 | 0.1014 | 1.1192 | 0.0018 | 0.0058 | -0.0473 | 0.9503 |
| 2021 Q3 | 2 | -0.6334 | 0.0000 | -0.0063 | 0.0061 | -0.7889 | 0.0000 |
| 2021 Q4 | 7 | 0.2972 | 1.3712 | 0.0100 | 0.0277 | 0.1658 | 1.1869 |
| 2022 Q1 | 3 | -0.5820 | 0.2014 | -0.0087 | 0.0055 | -0.6719 | 0.1503 |
| 2022 Q2 | 3 | 0.1774 | 1.2441 | 0.0025 | 0.0055 | 0.0877 | 1.1115 |
| 2022 Q3 | 3 | 0.6545 | 2.8010 | 0.0098 | 0.0055 | 0.5778 | 2.4684 |
| 2022 Q4 | 6 | 0.8633 | 3.4571 | 0.0260 | 0.0105 | 0.8011 | 3.1686 |

## Degradación y cruces temporales

- La expectancy acumulada se vuelve negativa por primera vez el
  `2019-05-02T13:00:00Z`, tras un periodo de solo cuatro operaciones; esto es
  un cruce temprano, no una prueba de degradación.
- La expectancy acumulada permanece negativa al cierre de 48 meses (`-0.0737 R`)
  y los horizontes de 6–36 meses también son negativos.
- Hay recuperación descriptiva en 2022: los cuatro trimestres no son todos
  positivos, pero Q2–Q4 sí lo son y la expectancy móvil de las últimas 10
  operaciones termina positiva (`0.9855 R`).
- Por tanto, el patrón es compatible con deterioro inicial y recuperación
  parcial, pero no permite declarar que exista o desaparezca una ventaja
  estadística. La muestra trimestral es pequeña y el análisis no realiza
  inferencia retrospectiva.

Las columnas `rolling_expectancy_10`, `rolling_expectancy_20`, `drawdown` y sus
versiones ×2 en `operations.csv` se calculan únicamente con operaciones
anteriores o iguales a cada fila. El drawdown se calcula desde máximos previos.

Los criterios formales P07 solo son aplicables al agregado completo de cuatro
años; por eso la primera fecha formal de incumplimiento es la evaluación final
`2023-01-01`, que conserva el resultado `FAIL` de P07. P04 no se compara
estadísticamente: sus distribuciones son bootstrap condicionadas a la selección
y usan un horizonte de operaciones distinto.
