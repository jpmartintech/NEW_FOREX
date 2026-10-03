# P06 — EURUSD frozen walk-forward

## Resultado

Evaluación ejecutada después de congelar `p06-frozen-wf-v1`: 25 estrategias
P03.1, cuatro ventanas anuales de `development_wf`, sin recalibración. Hubo
**1 superviviente y 24 rechazos**. El resultado no se usó para cambiar ningún
umbral ni estrategia.

Run reproducible: `runs/p06-eurusd-frozen-wf-v1/p06_report.json` (artefacto
ignorado por Git).

## Contrato y trazabilidad

- Intervalo: `[2015-01-01, 2019-01-01)`, ventanas WF1–WF4 con semántica `[start,end)`.
- Backtester: reglas y parámetros de `finalist_manifest.json`, ejecución M15,
  warm-up causal disponible antes de cada ventana y operaciones contabilizadas
  solo dentro de ella.
- Filas cargadas con timestamp `>= 2019-01-01`: `0`.
- `procedure_validation`: no utilizado. Holdout final: sellado y no utilizado.
- Política: `configs/wf_acceptance.yaml`, SHA256
  `c62cf8368dcdf40fb183f6b8158ac5ade1b3c77e9941bfceb05d5405636f412c`.
- Manifest SHA256:
  `176b3b76bba6e6cb73923214225f6f5c72c3cef59a89f9f8876c54df43d4977e`.
- P04 report SHA256:
  `806d9be821b0e7d002e49322b0a0f13627180bb26171f06b82eaaf1e5876547d`.
- Dataset EURUSD SHA256:
  `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Política de riesgo: `p04-fixed-fractional-r-v1`, riesgo `0.005` por R.
  Los límites de drawdown P95 son los máximos por estrategia entre moving,
  stationary y period-block de P04; definición y unidades son comparables.

## Criterios congelados

Todos son eliminatorios y simultáneos: mínimo 40 operaciones, expectancy
agregada estrictamente positiva, PF agregado estrictamente mayor que 1.05 y
finito, al menos 3 de 4 años positivos, expectancy positiva con costes ×2,
identidad congelada y drawdown no superior al límite P95 P04. Un año sin
operaciones no es positivo. PF infinito nunca se acepta.

## Tabla de resultados

Cada celda anual es `operaciones / PF / expectancy_R`. La columna agregada es
`operaciones / PF / expectancy_R / max_drawdown / Sharpe`; `x2 E` es la
expectancy con costes ×2. Los hashes se muestran con 12 caracteres; el JSON
contiene los hashes completos.

| strategy hash | 2015 n/PF/E | 2016 n/PF/E | 2017 n/PF/E | 2018 n/PF/E | agregado n/PF/E/DD/Sharpe | x2 E | veredicto |
|---|---:|---:|---:|---:|---:|---:|---|
| cc279c65c5d3 | 15/1.498/0.361 | 18/0.347/-0.653 | 12/0.682/-0.302 | 19/1.829/0.596 | 64/1.025/0.021/0.107/0.20 | -0.099 | FAIL |
| b54372484deb | 9/0.466/-0.742 | 14/0.440/-0.527 | 11/2.071/0.667 | 13/1.160/0.123 | 47/0.880/-0.109/0.103/-0.92 | -0.219 | FAIL |
| 4149f839e1a0 | 10/0.500/-0.436 | 18/0.160/-0.676 | 28/0.743/-0.202 | 11/1.040/0.025 | 67/0.579/-0.327/0.123/-4.12 | -0.448 | FAIL |
| a682454dce46 | 4/1.825/0.440 | 4/0.610/-0.309 | 8/0.607/-0.314 | 9/1.450/0.267 | 25/1.024/0.017/0.034/0.19 | -0.047 | FAIL |
| 654dabe1dd0a | 14/1.070/0.056 | 14/0.592/-0.386 | 17/0.250/-0.734 | 15/1.378/0.286 | 60/0.755/-0.214/0.094/-2.19 | -0.310 | FAIL |
| db7ea9a6c895 | 14/1.433/0.335 | 14/0.592/-0.386 | 16/0.247/-0.741 | 15/1.287/0.233 | 59/0.826/-0.154/0.091/-1.51 | -0.249 | FAIL |
| ae4500021ef7 | 14/1.433/0.335 | 14/0.592/-0.386 | 16/0.247/-0.741 | 15/0.886/-0.101 | 59/0.735/-0.238/0.099/-2.35 | -0.334 | FAIL |
| 84af58ecc117 | 10/1.746/0.483 | 10/0.000/-1.107 | 5/0.000/-1.009 | 6/0.374/-0.493 | 31/0.478/-0.460/0.091/-5.23 | -0.572 | FAIL |
| a7ff887fc614 | 4/0.605/-0.311 | 13/0.331/-0.603 | 19/1.037/0.025 | 10/1.789/0.421 | 46/0.868/-0.095/0.069/-1.09 | -0.169 | FAIL |
| 678fe62bb059 | 13/0.715/-0.243 | 14/0.592/-0.386 | 17/0.250/-0.734 | 15/1.378/0.286 | 59/0.680/-0.284/0.102/-3.04 | -0.380 | FAIL |
| 63775ca4b9b1 | 14/1.262/0.161 | 10/0.274/-0.699 | 14/1.061/0.042 | 11/1.579/0.348 | 49/0.991/-0.007/0.040/-0.07 | -0.068 | FAIL |
| 44f67d911388 | 14/1.070/0.056 | 14/0.592/-0.386 | 17/0.250/-0.734 | 15/1.378/0.286 | 60/0.755/-0.214/0.094/-2.19 | -0.310 | FAIL |
| 717c0e7579e3 | 10/1.223/0.168 | 8/0.000/-1.126 | 18/1.830/0.568 | 12/1.221/0.144 | 48/1.126/0.096/0.050/0.88 | -0.015 | FAIL |
| e6cd43f593a4 | 10/0.188/-0.638 | 14/1.259/0.169 | 9/1.746/0.440 | 14/0.909/-0.057 | 47/0.973/-0.018/0.051/-0.21 | -0.077 | FAIL |
| c556ff13e18c | 20/0.406/-0.412 | 14/0.635/-0.222 | 33/1.318/0.164 | 12/0.694/-0.247 | 79/0.819/-0.113/0.055/-1.47 | -0.188 | FAIL |
| bd991a2c7e7a | 14/1.262/0.161 | 10/0.274/-0.699 | 14/1.061/0.042 | 13/1.194/0.130 | 51/0.933/-0.048/0.040/-0.52 | -0.110 | FAIL |
| c1b40570d38d | 2/1.773/0.401 | 6/0.338/-0.618 | 11/1.377/0.232 | 2/0.000/-1.086 | 21/0.838/-0.120/0.028/-1.38 | -0.240 | FAIL |
| 4ac107175e58 | 10/3.885/0.896 | 11/1.058/0.039 | 3/0.000/-1.061 | 10/4.278/1.047 | 34/1.988/0.490/0.031/5.18 | 0.439 | FAIL |
| 237d10ee505b | 13/1.013/0.009 | 9/0.000/-1.107 | 11/1.603/0.397 | 12/2.629/0.911 | 45/1.162/0.121/0.064/1.03 | 0.025 | PASS |
| 0e3cc7c77d39 | 14/0.946/-0.041 | 9/1.714/0.425 | 7/0.289/-0.534 | 4/4.166/0.865 | 34/1.133/0.087/0.032/0.91 | 0.032 | FAIL |
| 2ed8479f04bf | 3/0.913/-0.062 | 4/0.610/-0.309 | 8/0.406/-0.474 | 9/1.450/0.267 | 24/0.835/-0.117/0.037/-1.38 | -0.181 | FAIL |
| e812b58085c5 | 8/0.178/-0.786 | 8/1.509/0.352 | 7/1.666/0.382 | 13/0.011/-1.011 | 36/0.543/-0.387/0.068/-4.19 | -0.497 | FAIL |
| b38b77f92c7f | 8/0.178/-0.786 | 8/1.509/0.352 | 7/1.666/0.382 | 13/0.011/-1.011 | 36/0.543/-0.387/0.068/-4.19 | -0.497 | FAIL |
| 683524d9ec90 | 14/1.364/0.247 | 13/0.443/-0.505 | 13/1.191/0.128 | 13/1.521/0.344 | 53/1.079/0.057/0.035/0.58 | -0.006 | FAIL |
| 2cae16426778 | 14/1.364/0.247 | 13/0.443/-0.505 | 13/1.191/0.128 | 14/1.353/0.243 | 54/1.050/0.036/0.035/0.37 | -0.027 | FAIL |

## Incidencias y validación

La ejecución inicial detectó dos validaciones de infraestructura (formato de
fecha de la manifest y tipo temporal del filtro PyArrow); se corrigieron antes
del run válido. No hubo incidencia estadística, acceso posterior a 2019 ni
operaciones reales. El runner valida hashes de estrategia, manifest, ledgers,
configuración P06, P04 y dataset.

`ruff check .`: PASS. `PYTHONPATH=src pytest -q`: PASS esperado del repositorio
(215 passed, 2 skipped; los skips corresponden a datasets no presentes).
