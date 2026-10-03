# P10.1 — Factory Decision Audit

## Alcance

Auditoría derivada exclusivamente de `reports/p10_factory_diagnostics.md` y de sus artefactos congelados. No se ejecutó el control nulo, no se lanzó una generación GA, no se cambiaron filtros o políticas y el holdout 2023–2026 permanece sellado.

## Cifras reproducibles

Los siguientes agregados son la suma de los resultados de las ventanas de cada generación en `reports/p09_artifacts/portfolio_horizons_30_60_90.csv`. Son ventanas independientes desde cada nacimiento; no deben interpretarse como una única cartera continua sin reinicio entre generaciones.

| Horizonte | Operaciones | Resultado agregado | DD máximo observado |
|---:|---:|---:|---:|
| 30 días | 93 | -13.8970% | 5.4933% |
| 60 días | 180 | -3.0574% | 5.4933% |
| 90 días | 283 | -15.4749% | 8.4445% |

La cartera completa contiene 293 operaciones. La diferencia entre 283 operaciones a 90 días y 293 totales se debe a operaciones posteriores al horizonte de 90 días dentro de algunos trimestres.

| Horizonte | Slots | Activas | Expectancy positiva | Porcentaje activo |
|---:|---:|---:|---:|---:|
| 30 días | 80 | 48 | 15 | 31.25% |
| 60 días | 80 | 66 | 28 | 42.42% |
| 90 días | 80 | 76 | 31 | 40.79% |

En la cohorte completa hay 80 slots de selección, 77 hashes con operaciones y 30 slots con retorno individual positivo, un 37.5% de los slots. Las fracciones no son evidencia de ventaja: incluyen muestras muy pequeñas y estrategias sin operaciones en determinados horizontes.

### Bruto frente a neto

La reconciliación de `execution_decomposition.csv`, en unidades R de operación, es:

| Medida | Total |
|---|---:|
| Resultado bruto implícito | -3.777559 R |
| Resultado neto | -34.308180 R |
| Diferencia bruto-neto | -30.530621 R |
| Coste total registrado | 0.043950 unidades de precio |

El bruto implícito se obtiene de `result_R + transaction_cost/risk`, según el contrato del ledger. No es una descomposición de comisiones, spread y slippage: esos componentes no están identificados por operación. La comparación de cartera reproduce además -16.9898% baseline frente a -28.7591% con costes ×2.

La pérdida, por tanto, ya está presente antes de duplicar costes: el baseline es negativo. Los costes agravan materialmente la pérdida, pero no son su origen único.

### Contribución individual

Las cinco mayores contribuciones negativas y positivas se toman directamente de `portfolio_strategy_contributions.csv`:

| Grupo | Hash (prefijo) | Operaciones | P&L cartera |
|---|---|---:|---:|
| Peor | `ad61c8b3` | 7 | -0.032209 |
| Peor | `b739367a` | 7 | -0.031421 |
| Peor | `7422b5c9` | 5 | -0.028861 |
| Peor | `4404aa9f` | 6 | -0.028319 |
| Peor | `c02abb4c` | 6 | -0.028319 |
| Mejor | `a276705e` | 5 | +0.021189 |
| Mejor | `d4a0dfa4` | 3 | +0.021727 |
| Mejor | `6f5d8cd8` | 9 | +0.023027 |
| Mejor | `3553ae12` | 4 | +0.029790 |
| Mejor | `d2bc3c4c` | 7 | +0.033462 |

Las cinco peores suman aproximadamente -0.149129 de P&L, mientras las cinco mejores suman +0.129195. Las mejores no compensan a las peores.

### Generaciones e individuo frente a cartera

Las 16 generaciones produjeron cinco estrategias cada una; no hubo generación con cero estrategias. Hubo 12 generaciones negativas y 4 positivas. Las peores carteras trimestrales fueron 2021Q2 (-7.19%), 2020Q3 (-7.21%) y 2019Q2 (-4.77%); las mejores 2022Q4 (+9.93%), 2020Q1 (+8.55%) y 2020Q4 (+4.27%). La tabla completa está en `generation_diagnostics.csv`.

La suma de retornos individuales por slot es aproximadamente -17.0489%, frente a -16.9898% de la cartera consolidada. La diferencia es pequeña en este conjunto, pero las magnitudes no son idénticas: la cartera aplica equity compuesta, riesgo por operación y límite de posiciones simultáneas; sumar retornos individuales no sustituye la simulación de cartera. El máximo de solapamiento fue cuatro posiciones y el límite agregado congelado fue 0.025.

## Suficiencia de muestra

No hay suficiente muestra para evaluar razonablemente una vida operativa de 30, 60 o 90 días por estrategia individual. Los horizontes contienen, en promedio, aproximadamente 1.16, 2.25 y 3.54 operaciones por estrategia respectivamente. Que 60 o 90 días tenga más estrategias con expectancy positiva no resuelve esta insuficiencia.

## Revisión del control B

El commit `e7c4562` congeló `p10-null-control-v1` con SHA256 `d443e5a7aa7933c8f52a9acc00e7ee39b4edfdda9f9e4984d7e404537e55e6ca`. El control B exige una fábrica completa bajo un generador de señales nulo, manteniendo ventanas, restricciones, costes, semillas y 100.000 evaluaciones por generación. Su estimación conservadora es 15 generaciones × 100.000 = **1.500.000 evaluaciones adicionales**, sin contar el coste del generador nulo y sus backtests. No se ejecutó y no debe confundirse con el control A.

## Experimento mínimo recomendado

El experimento mínimo informativo es el control A, sin repetir GA:

1. Usar las auditorías P08/P09 conservadas y el conjunto de candidatos elegibles de cada una de las 16 generaciones.
2. Para cada generación y cada una de 100 réplicas, seleccionar uniformemente cinco candidatos sin reemplazo con semillas derivadas de `20261010` según una regla documentada.
3. Ejecutar el backtester forward real solo sobre esos 8.000 candidatos (16 × 100 × 5), usando las velas autorizadas, costes baseline y costes ×2.
4. Construir cada cartera con riesgo 0.005 por operación, límite agregado 0.025 y la misma regla de solapamiento P08/P09.
5. Registrar por réplica y generación: operaciones, expectancy R, PF finito, retorno, DD, rachas y costes ×2; registrar también agregados de 30/60/90 días.
6. Comparar la fábrica real contra la distribución aleatoria emparejada por generación: diferencia de retorno y expectancy, DD, porcentaje de generaciones positivas y percentil de la fábrica real dentro de las 100 réplicas. Reportar intervalos empíricos y el porcentaje de réplicas que supera al resultado real; no cambiar ningún umbral histórico.

Este diseño contrasta **ranking/selección frente a azar dentro del universo elegible**, no el proceso GA completo. El control B solo sería necesario para estudiar la generación y selección bajo un mundo nulo.

## Decisión

**A.** La pérdida aparece antes de costes: el baseline ya es -16.9898%; los costes ×2 la agravan.

**B.** Hay una señal descriptiva débil y no certificable: el agregado de 60 días es menos negativo que 30 y 90 días, pero la muestra media es de 1.16–3.54 operaciones por estrategia.

**C.** El problema aparece en ambos niveles. La mayoría de generaciones son negativas y las cinco peores estrategias concentran una pérdida importante; la construcción de cartera añade efectos de compounding, solapamiento y riesgo, aunque el retorno individual agregado es muy similar al de cartera.

**D.** El experimento mínimo es el control A emparejado por generación, con 100 selecciones aleatorias de cinco candidatos elegibles y 8.000 backtests forward. Solo después, si procede, debe presupuestarse el control B de al menos 1.500.000 evaluaciones.
