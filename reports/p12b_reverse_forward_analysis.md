# P12B — Reverse Forward Analysis

## Alcance y dataset

P12B es exploratorio y retrospectivo sobre el único forward P08 Q1. No repite el GA, no modifica P08–P12A y no accede al holdout. El dataset combina `reports/p12a_artifacts/full_forward_census.parquet` con la auditoría histórica P08; la unión es uno-a-uno sobre 100.000 hashes.

- Dataset consolidado: 100.000 filas, 100.000 hashes y payloads únicos.
- Dataset SHA256: `17ad0bad9d661cf1560af2846b97a61539e8be30434ed387673564d901acbcbc`.
- Fuente P12A SHA256: `32e06dad8a9eec5bf9717abb225436f03128099dda81e6453c7393f4bf2e4cf9`.
- Auditoría histórica SHA256: `d9c52c45a1eae6251d78bf39d3226a2870d9c75c45559def2cca7a35dd7b14e7`.
- Win rate histórica: no disponible en los artefactos conservados; queda explícitamente como ausente.
- Métricas por años históricas reproducibles: disponibles para 2.489 candidatos pre-cualificados; para el resto no se inventaron valores.

Las variables predictoras son exclusivamente training, development WF, filtros históricos, estructura y complejidad. Los resultados forward se mantienen separados y no se usan para reconstruir ninguna variable histórica.

## Clasificación forward

| Grupo | Definición | N | Exp. forward media | Retorno medio | Ops medias | Exp. positiva con costes ×2 |
|---|---|---:|---:|---:|---:|---:|
| A | Sin operaciones | 35.817 | 0,0000 R | 0,0000% | 0,00 | 0,00% |
| B | Activa, expectancy ≤0 | 31.648 | -0,29828 R | -3,6388% | 49,24 | 0,00% |
| C | Expectancy >0, retorno ≤0 | 298 | +0,00195 R | -0,0817% | 62,73 | 0,00% |
| D | Expectancy >0 y retorno >0 | 32.237 | +0,40306 R | +2,2464% | 32,74 | 77,78% |

Las categorías son descriptivas y conservan las variables continuas originales. El grupo D no constituye una cohorte robusta: contiene muchas estrategias con pocas operaciones y firmas conductuales compartidas.

## Embudo PASS/FAIL

La auditoría original contiene 2.489 `PASS` y 97.511 `FAIL`; ningún filtro forward fue añadido.

| Estado histórico | N | Exp. forward positiva | Retorno forward medio | Retorno mediano | Ops medias | Cero operaciones |
|---|---:|---:|---:|---:|---:|---:|
| PASS | 2.489 | 45,64% | -0,4131% | -0,1182% | 9,52 | 2,09% |
| FAIL | 97.511 | 32,20% | -0,4281% | 0,0000% | 26,75 | 36,68% |

De los 32.237 casos del grupo D, **1.129** son PASS y **31.108** son FAIL. Esto identifica una población rechazada que merece investigación, pero no demuestra que el rechazo sea incorrecto: el retorno medio FAIL sigue siendo negativo y el trimestre es único.

Los motivos no son mutuamente excluyentes:

| Motivo histórico de rechazo | Filas afectadas | Exp. forward positiva | Retorno medio |
|---|---:|---:|---:|
| costs_x2_expectancy_R | 94.300 | 32,75% | -0,4404% |
| min_aggregate_expectancy_R | 89.670 | 32,50% | -0,3928% |
| min_dev_wf_trades | 42.751 | 9,04% | +0,0198% |
| min_profit_factor | 92.492 | 32,71% | -0,4255% |
| min_positive_years | 97.511 | 32,20% | -0,4281% |
| require_finite_profit_factor | 1.286 | 13,61% | +0,0094% |

No se puede atribuir causalidad a un motivo aislado porque una estrategia puede fallar varios criterios.

## Relaciones históricas descriptivas

| Variable histórica | Correlación con exp. forward | Correlación con retorno forward |
|---|---:|---:|
| Training expectancy | +0,0372 | +0,0497 |
| Training PF | +0,1106 | +0,0253 |
| Training operaciones | -0,0768 | -0,3270 |
| Training MaxDD | -0,1228 | -0,3712 |
| Development expectancy | -0,2077 | -0,0334 |
| Development PF | -0,0603 | -0,0707 |
| Development operaciones | -0,0691 | -0,3135 |
| Development MaxDD | -0,0340 | -0,1869 |
| Número de predicados | +0,0371 | +0,0995 |

Son relaciones exploratorias sobre estrategias dependientes, no efectos causales. La expectancy development positiva no ordenó mejor el forward; su decil superior obtuvo expectancy forward media -0,04644 R. Los deciles completos están en `historical_metric_deciles.csv` y las correlaciones en `reverse_correlations.csv`.

### Actividad y complejidad

- 0 operaciones: 35.817 estrategias, sin información de rendimiento.
- 1–5 operaciones: 55,77% con expectancy positiva, pero muestra frágil.
- 6–20: 61,36% positiva y retorno medio +0,6597%.
- 21–50: 47,71% positiva y retorno medio -0,6912%.
- 51–100: 47,37% positiva y retorno medio -1,1341%.
- >100: 28,84% positiva y retorno medio -4,4857%.

Por familia estructural, SHORT con 1–2 predicados mostró mejores promedios que LONG y que estructuras SHORT más complejas, pero esta comparación está confundida por actividad, costes y dependencia de reglas. No se propone filtrar por dirección o complejidad.

## Dependencia conductual

P12A identificó 48.090 firmas forward exactas. P12B conserva esa firma solo para diagnosticar dependencia, nunca como predictor. La firma de cero operaciones agrupa 35.817 estrategias. Existen 51.910 filas que comparten firma con otra estrategia, aunque los payloads canónicos son únicos. Los grupos más grandes y sus medias están en `top_behavioral_groups.csv`; la familia estructural en `strategy_family_summary.csv`.

Por tanto, 100.000 filas no equivalen a 100.000 observaciones independientes.

## Hipótesis candidatas para Factory V2

Estas hipótesis no modifican ninguna política histórica y requieren evaluación cronológica independiente:

1. **Actividad moderada frente a actividad extrema.** La actividad histórica y forward alta se asocia descriptivamente con peor retorno; 6–20 operaciones forward fue el grupo más favorable, mientras >100 fue el peor. Riesgo: sesgo por horizonte y costes. Prueba: pre-registrar una variable de actividad histórica y comprobarla en varias generaciones posteriores.
2. **Development WF positivo no es suficiente.** La correlación development expectancy–forward fue negativa (-0,2077) y el decil superior fue negativo forward. Riesgo: regresión a la media y selección condicionada. Prueba: replicación walk-forward cronológica con métricas congeladas.
3. **Robustez de costes como descriptor.** El grupo D conserva 77,78% de expectancy positiva con costes ×2, pero 22,22% deja de ser positiva. Riesgo: un solo trimestre y costes deterministas. Prueba: stress y forward en generaciones posteriores.
4. **Dirección y complejidad interactúan.** SHORT de baja complejidad mostró mejores medias que LONG y SHORT complejo. Riesgo: confusión por actividad y universo GA. Prueba: análisis pre-registrado por familia en generaciones posteriores con dependencia controlada.
5. **El embudo elimina una población FAIL heterogénea.** 31.108 FAIL fueron grupo D, pero su retorno medio no prueba utilidad. Riesgo: múltiples comparaciones y selección retrospectiva. Prueba: conservar una cohorte FAIL descriptiva congelada en cada generación y compararla en forward futuro, sin usarla para operar.

## Respuestas de cierre

1. Las características más asociadas descriptivamente con forward favorable fueron actividad moderada, menor MaxDD y algunas familias SHORT de baja complejidad; la señal histórica más preocupante fue el bajo poder de ordenación de development expectancy y del fitness extremo.
2. Los filtros aportan cierta separación en la fracción de expectancy positiva, pero no produjeron retorno medio positivo y descartaron una gran población FAIL con resultados favorables en Q1 2019. Esto no justifica eliminar filtros sin replicación.
3. Merece la pena comprobar las cinco hipótesis anteriores en generaciones cronológicamente posteriores, con políticas congeladas antes de ver cada forward. P12B no demuestra edge ni capacidad predictiva.

Artefacto principal: `reports/p12b_artifacts/reverse_forward_dataset.parquet`. El resto de tablas y el manifiesto reproducible están en `reports/p12b_artifacts/`.
