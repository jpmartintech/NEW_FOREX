# P12C — Temporal Hypothesis Validation

## Protocolo e integridad

Se auditaron y evaluaron en orden cronológico las 15 generaciones P09 posteriores a P08 Q1: 2019Q2–2022Q4. Cada generación conserva 100.000 filas de archivo GA, 100.000 filas de auditoría, hashes canónicos y definiciones ejecutables. No se repitió el GA ni se sustituyó ningún universo por finalistas.

- Protocolo congelado: commit `600e50c`.
- Configuración SHA256: `3ac952bfbfdd057b3b012a78ac413e52dbe388132ad9afdfe1c146af0c6d32e4`.
- Evaluación: 1.500.000 estrategias, 300 chunks, baseline y costes ×2.
- Control aleatorio: 1.500 carteras (100 por generación), cinco estrategias uniformes del archivo completo, semillas desde `20261212`.
- Todas las carteras se construyeron con el motor de cartera original, riesgo 0.005 y límite agregado 0.025.
- Holdout: no utilizado; fecha forward máxima exclusiva `2023-01-01`.
- Tiempo total: 444,64 s.

Variables históricas disponibles: payload, dirección, complejidad, training, development WF, costes ×2 y decisiones/checks de aceptación. El win rate histórico no está conservado para todas las estrategias y no se reconstruyó. Las métricas anuales solo son utilizables para los candidatos pre-cualificados por el runner P09; los demás se dejaron como ausentes.

## Hipótesis congeladas

Se extrajeron literalmente de P12B:

1. “**Actividad moderada frente a actividad extrema.** La actividad histórica y forward alta se asocia descriptivamente con peor retorno.”
2. “**Development WF positivo no es suficiente.**”
3. “**Robustez de costes como descriptor.**”
4. “**Dirección y complejidad interactúan.**”
5. “**El embudo elimina una población FAIL heterogénea.**”

Para evitar usar forward como predictor, P12C operacionalizó H1 con buckets de `development_n_trades` (0, 1–5, 6–20, 21–50, 51–100, >100), H2 con `development_expectancy_R > 0`, H3 con `development_x2_expectancy_R > 0`, H4 con dirección y 1–2/3–4 predicados, y H5 con PASS/FAIL histórico. Estas reglas quedaron congeladas antes de los resultados.

## Resultado global del universo

Sobre las 1.500.000 filas temporales, 316.333 tuvieron expectancy forward positiva y el retorno medio individual fue **-1,0171%**. Las observaciones no son independientes: cada generación comparte datos, GA, gramática y firmas conductuales.

### PASS frente a FAIL

| Grupo | N | Expectancy positiva | Retorno medio | Exp. positiva con costes ×2 |
|---|---:|---:|---:|---:|
| PASS | 48.479 | 44,44% | -0,1955% | 39,14% |
| FAIL | 1.451.521 | 20,31% | -1,0446% | 14,84% |

El filtro PASS conserva más fracción favorable y mejor retorno medio individual, pero ambos retornos medios siguen negativos. Esto es una asociación descriptiva y no demuestra que el filtro sea causalmente correcto.

## Validación temporal de las hipótesis

### H1 — Actividad histórica moderada

Agregado sobre las 15 generaciones, clasificando exclusivamente por operaciones development:

| Development trades | N | Exp. positiva | Retorno medio | Exp. positiva ×2 |
|---|---:|---:|---:|---:|
| 0 | 437.774 | 1,28% | -0,0028% | 1,27% |
| 1–5 | 238.441 | 6,72% | -0,0050% | 6,59% |
| 6–20 | 60.335 | 28,91% | -0,0484% | 27,50% |
| 21–50 | 65.936 | 43,48% | -0,0920% | 39,82% |
| 51–100 | 66.397 | 42,17% | -0,3554% | 35,77% |
| >100 | 631.117 | 34,95% | -2,3620% | 23,22% |

La actividad extrema alta conserva el peor retorno, pero el bucket 21–50 tiene mayor fracción de expectancy positiva que 6–20. La hipótesis queda **parcialmente apoyada para evitar actividad extrema alta**, no para seleccionar un intervalo óptimo.

### H2 — Development positivo no es suficiente

Las estrategias con development expectancy positiva tuvieron 27,86% de expectancy forward positiva y retorno medio -0,3633%; las no positivas, 19,81% y -1,1402%. La dirección de la separación es favorable a H2, pero ambos grupos son negativos y la relación no certifica capacidad predictiva. Evidencia: **débilmente favorable, no concluyente**.

### H3 — Robustez de costes

Las estrategias con development expectancy ×2 positiva tuvieron 23,10% forward positiva y retorno medio -0,1005%; las no robustas, 20,86% y -1,1210%. La separación persiste, pero la mayoría sigue siendo negativa y solo 20,90% del grupo robusto mantiene expectancy positiva con costes ×2. Evidencia: **favorable como descriptor de riesgo, no como aceptación suficiente**.

### H4 — Dirección y complejidad

| Familia | N | Exp. positiva | Retorno medio | Exp. positiva ×2 |
|---|---:|---:|---:|---:|
| LONG, 1–2 predicados | 225.664 | 28,00% | -2,7513% | 19,40% |
| LONG, 3–4 predicados | 395.903 | 16,22% | -0,3303% | 13,50% |
| SHORT, 1–2 predicados | 297.366 | 31,29% | -1,9709% | 20,21% |
| SHORT, 3–4 predicados | 581.067 | 16,50% | -0,3235% | 13,26% |

La ventaja descriptiva de baja complejidad en expectancy positiva no se traduce en retorno medio positivo; las familias de 1–2 predicados tienen peores retornos por su mezcla de actividad y exposición. H4 es **inconcluyente y probablemente confundida**.

### H5 — Población FAIL

PASS supera a FAIL en expectancy positiva (44,44% frente a 20,31%) y en retorno medio (-0,20% frente a -1,04%). La diferencia es estable como descripción del embudo, pero FAIL sigue conteniendo una población favorable y el retorno PASS no es positivo. H5 queda **apoyada como heterogeneidad del embudo**, no como razón para eliminar o invertir filtros.

## Carteras y control aleatorio

Las carteras originales de cinco estrategias se evaluaron con ledgers y riesgo reales; no se sumaron métricas individuales. El control aleatorio usa cinco estrategias del archivo completo y 100 réplicas por generación.

| Escenario | Retorno medio cartera original | Retorno medio control | Control supera a original | DD medio original | DD medio control |
|---|---:|---:|---:|---:|---:|
| Baseline | -0,930% | -4,858% | 35,47% | 4,11% | 9,85% |
| Costes ×2 | -1,847% | -9,795% | 24,27% | 4,57% | 13,17% |

La cartera original supera al control aleatorio en la mayoría de réplicas, aunque sigue teniendo retorno medio negativo. La comparación no convierte 1.500 controles en observaciones independientes: existe dependencia temporal y reutilización del universo GA.

Por generación, la ventaja del procedimiento original no es uniforme. Los artefactos `original_portfolio_by_generation.csv` y `random_control_summary.csv` conservan retornos, DD, operaciones y costes ×2 por trimestre. Los censos individuales y grupos de hipótesis están en `hypothesis_by_generation.csv`.

## Dependencia conductual

Cada generación tiene aproximadamente 42.847–48.859 firmas forward exactas entre 100.000 estrategias; la firma dominante agrupa entre 33.559 y 49.060 filas. La dependencia impide interpretar los tamaños nominales como evidencia equivalente a millones de observaciones independientes. Evidencia: `dependence_by_generation.csv`.

## Conclusiones y limitaciones

- H1 conserva una señal descriptiva contra actividad histórica extrema alta, pero no identifica un rango rentable estable.
- H2 y H3 muestran separación favorable, pero no retorno positivo consistente; permanecen inconcluyentes para aceptación.
- H4 no es estable al separar retorno de expectancy y está confundida por actividad y dirección.
- H5 confirma que PASS es una población históricamente más favorable, pero FAIL contiene oportunidades descriptivas y PASS tampoco produce retorno medio positivo.
- Las carteras originales superan al control aleatorio en promedio y en drawdown, aunque permanecen negativas.

No se modificó ningún filtro, umbral ni estrategia histórica. Ninguna hipótesis se convierte en política Factory V2 sin validación pre-registrada en generaciones aún posteriores. P12C no demuestra edge.

Artefactos: `reports/p12c_artifacts/`, incluyendo censos Parquet por generación, checkpoints, carteras originales, controles aleatorios, tablas de hipótesis y manifiesto.
