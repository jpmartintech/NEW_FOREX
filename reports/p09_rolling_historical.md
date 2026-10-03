# P09 — Rolling Factory Historical Evaluation

## Alcance y política

Se evaluó `p08-rolling-factory-v1` en las 15 generaciones posteriores al
piloto P08 2019Q1: 2019Q2–Q4, 2020Q1–Q4, 2021Q1–Q4 y 2022Q1–Q4. No se modificó
la política.

- Política SHA256: `73f7bb0649c814a0ec076fff9d9e3413ba480fb31eca765ed18b860f6e1c72ed`.
- Cada generación: training móvil de 8 años, development WF de 2 años,
  forward del trimestre siguiente.
- 100.000 evaluaciones GA únicas por generación, semillas
  `20261003 + índice trimestral`.
- Máximo 5 activas, riesgo individual `0.005`, cap agregado `0.025`.
- La selección de cada generación solo usó su training/development anterior al
  nacimiento; el forward se abrió después de congelar hashes.
- Holdout 2023–2026: no utilizado. Filas forward fuera de su trimestre: 0.

Los artefactos pesados completos de cada generación están en
`runs/p09-rolling-historical-v1/<trimestre>/`. Los artefactos consolidados están
en [reports/p09_artifacts](./p09_artifacts/): checkpoint, resultados de las
generaciones, ledger de cartera, ledger ×2, tablas 30/60/90 y costes ×2.

## Tabla de las 16 generaciones

Q1-2019 es el piloto previamente observado; las restantes son la evaluación
P09. `ops` es el número de operaciones de cartera. `pos/neg` cuenta estrategias
individuales forward con retorno estrictamente positivo/negativo.

| Generación | Tipo | Seleccionadas | Ops | Pos/neg | Retorno cartera | DD cartera | Retorno cartera ×2 |
|---|---|---:|---:|---:|---:|---:|---:|
| 2019Q1 | piloto | 5 | 19 | 2/3 | -0.0260 | 0.0532 | -0.0380 |
| 2019Q2 | P09 | 5 | 16 | 1/4 | -0.0477 | 0.0629 | -0.0601 |
| 2019Q3 | P09 | 5 | 7 | 1/3 | -0.0156 | 0.0125 | -0.0189 |
| 2019Q4 | P09 | 5 | 13 | 1/4 | -0.0374 | 0.0507 | -0.0470 |
| 2020Q1 | P09 | 5 | 16 | 4/1 | 0.0855 | 0.0206 | 0.0736 |
| 2020Q2 | P09 | 5 | 20 | 0/5 | -0.0630 | 0.0579 | -0.0730 |
| 2020Q3 | P09 | 5 | 27 | 1/4 | -0.0721 | 0.0844 | -0.0868 |
| 2020Q4 | P09 | 5 | 9 | 4/1 | 0.0427 | 0.0066 | 0.0373 |
| 2021Q1 | P09 | 5 | 21 | 2/3 | -0.0185 | 0.0477 | -0.0253 |
| 2021Q2 | P09 | 5 | 20 | 1/3 | -0.0719 | 0.0696 | -0.0839 |
| 2021Q3 | P09 | 5 | 32 | 2/3 | -0.0085 | 0.0549 | -0.0271 |
| 2021Q4 | P09 | 5 | 25 | 2/3 | -0.0096 | 0.0313 | -0.0249 |
| 2022Q1 | P09 | 5 | 21 | 1/4 | -0.0298 | 0.0387 | -0.0407 |
| 2022Q2 | P09 | 5 | 5 | 0/4 | -0.0266 | 0.0212 | -0.0285 |
| 2022Q3 | P09 | 5 | 8 | 4/1 | 0.0334 | 0.0032 | 0.0319 |
| 2022Q4 | P09 | 5 | 34 | 4/1 | 0.0993 | 0.0496 | 0.0891 |

Hubo 5 estrategias elegibles y activas en cada generación; no se produjo el
caso de cero supervivientes. La distribución individual fue negativa en la
mayoría de trimestres, aunque hubo recuperaciones en 2020Q1, 2020Q4, 2022Q3 y
2022Q4.

## Cartera conjunta

La cartera se construyó por eventos, no sumando retornos individuales. Cada
entrada conserva su equity de entrada y cada salida aplica `0.005 × result_R`;
las posiciones simultáneas se cuentan contra el cap `0.025`, con salidas
procesadas antes de nuevas entradas en el mismo timestamp y entrada/salida de
una misma operación procesada causalmente.

| Escenario | Operaciones | Estrategias/hash activos | Retorno | PnL | Max DD |
|---|---:|---:|---:|---:|---:|
| Baseline | 293 | 77 | -0.1699 | -0.1699 | 0.2915 |
| Costes ×2 | 293 | 77 | -0.2876 | -0.2876 | 0.3890 |

El ledger conjunto no contiene duplicados por `(strategy_hash, entry_timestamp,
exit_timestamp)`. El número 77 de hashes activos refleja la rotación trimestral,
no un aumento del cap simultáneo, que permaneció en 5 estrategias.

## Horizontes 30/60/90 días

Los resultados completos por generación y horizonte están en
[portfolio_horizons_30_60_90.csv](./p09_artifacts/portfolio_horizons_30_60_90.csv).
Cada fila se calcula desde el nacimiento de su generación usando solo salidas
anteriores a `birth + horizon`; las ventanas sin operaciones se conservan como
cero. Los costes ×2 por estrategia y trimestre están en
[forward_costs_x2.json](./p09_artifacts/forward_costs_x2.json), incluida la
cartera ×2 consolidada.

## Integridad y reanudación

- Checkpoint: [checkpoint.json](./p09_artifacts/checkpoint.json), 15/15
  generaciones completadas.
- La primera incidencia fue una comparación incorrecta del límite exclusivo
  `2023-01-01`; Q2-2019 se conservó sin repetirlo.
- La segunda incidencia fue una salida en el mismo timestamp que su entrada al
  consolidar la cartera; se corrigió el orden causal y no se repitió ninguna
  generación válida.
- La generación Q4-2022 termina exactamente en `2023-01-01` de forma exclusiva;
  no abre el holdout.
- El piloto P08 Q1-2019 se leyó del run congelado v3 y permaneció intacto.
- El orquestador es idempotente: salta generaciones presentes y verificadas,
  registra fallos y solo avanza el checkpoint después de validar presupuesto,
  hashes, ventana y ledgers.

## Validación

La implementación y sus pruebas cubren calendario, checkpoint, posiciones
simultáneas, cap de riesgo, operaciones de mismo timestamp y duplicados.
`ruff check .` y `pytest -q` se ejecutaron antes del cierre; no se ejecutaron
operaciones reales ni se accedió a 2023–2026.
