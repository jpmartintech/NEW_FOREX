# P07 — EURUSD procedure validation 2019–2022

## Resultado

La única estrategia superviviente de P06 fue evaluada una vez, sin GA,
recalibración ni cambios de reglas, sobre `procedure_validation`:

**FAIL — estrategia rechazada por expectancy agregada, PF, años positivos y
costes ×2.** El resultado se conserva como válido y no se sustituyó la
estrategia.

Run reproducible: `runs/p07-eurusd-procedure-validation-v1/p07_report.json`
(artefacto ignorado por Git).

## Trazabilidad y límites

- Estrategia: `237d10ee505b9bf528a2036d30babb26db137e9de3852a8bb116f73799798ebd`.
- La identidad coincide con la manifest P03.1 y el superviviente PASS de P06.
- Periodo: `[2019-01-01, 2023-01-01)` con cuatro ventanas anuales.
- Filas cargadas con timestamp `>=2023-01-01`: `0`.
- Holdout 2023–2026: no utilizado. Operaciones reales: ninguna.
- Política: `configs/procedure_validation.yaml`,
  `p07-procedure-validation-v1`, SHA256
  `7c6545eb453f69cf3de61456abad3fe00a373eef05a42ee46cf918f7d8a0c807`.
- Manifest SHA256:
  `176b3b76bba6e6cb73923214225f6f5c72c3cef59a89f9f8876c54df43d4977e`.
- P06 report SHA256:
  `110f4e273ca10c017bcda64ba5069aea18e5e0a41a8c02aaa6d3d9031488d2c1`.
- Dataset EURUSD SHA256:
  `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Riesgo: `p04-fixed-fractional-r-v1`, `0.005` por R.

La política P07 fue congelada antes de abrir el periodo y hereda los criterios
objetivos P06: 40 operaciones, expectancy estrictamente positiva, PF finito
estrictamente mayor que 1.05, al menos 3 de 4 años positivos, expectancy ×2
estrictamente positiva, identidad congelada y drawdown inferior al P95 P04
comparable. Todos son eliminatorios.

## Resultados por año

| Año | Operaciones | PF neto | Expectancy R | Retorno | Max DD | Sharpe | Racha pérdida máxima |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 10 | 0.2782 | -0.5765 | -0.0286 | 0.0287 | -1.66 | 4 |
| 2020 | 16 | 0.8100 | -0.1440 | -0.0119 | 0.0499 | -0.36 | 8 |
| 2021 | 16 | 0.8477 | -0.1290 | -0.0110 | 0.0297 | -0.28 | 5 |
| 2022 | 15 | 1.7838 | 0.3953 | 0.0296 | 0.0195 | 0.93 | 3 |

## Agregado y costes ×2

| Escenario | Operaciones | PF | Expectancy R | Retorno | Max DD | Sharpe | Racha máxima |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 57 | 0.8980 | -0.0737 | -0.0226 | 0.0771 | -0.76 | 8 |
| Costes ×2 | 57 | 0.7737 | -0.1809 | -0.0521 | 0.0938 | -1.86 | 8 |

## Aplicación de la política

| Criterio | Observado | Resultado |
|---|---:|---|
| Mínimo 40 operaciones | 57 | PASS |
| Expectancy agregada > 0 | -0.073749 R | FAIL |
| PF agregado > 1.05 | 0.898044 | FAIL |
| PF finito | 0.898044 | PASS |
| Años positivos (operaciones y expectancy > 0) ≥ 3 | 1 | FAIL |
| Expectancy con costes ×2 > 0 | -0.180943 R | FAIL |
| Identidad congelada | verificada | PASS |
| Max DD ≤ P04 P95 | 0.077130 ≤ 0.117247 | PASS |

**Decisión final: FAIL.** No se modificaron criterios después de observar los
resultados.

## Comparación descriptiva, no usada para aceptación

| Periodo | Operaciones | PF | Expectancy R | Retorno | Max DD | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| dev_train (P03.1) | 123 | 1.5058 | 0.3543 | 0.2348 | 0.0696 | 0.54 |
| development_wf (P06) | 45 | 1.1625 | 0.1213 | 0.0255 | 0.0642 | 1.03 |
| procedure_validation (P07) | 57 | 0.8980 | -0.0737 | -0.0226 | 0.0771 | -0.76 |

La comparación es descriptiva y no altera la decisión P07.

## Validación

El runner verificó hash de estrategia, manifest, ledger congelado, política,
dataset, partición y ausencia de filas del holdout. `ruff check .` y `pytest`
se ejecutaron tras la implementación; no se realizaron operaciones reales.
