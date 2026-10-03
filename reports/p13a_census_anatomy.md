# P13A — Full Census Economic Anatomy

Protocol: `p13a-census-anatomy-v1`
Config SHA256: `f05af029b785d16b3e9358d98a8f041933e567876f4a26ec1eb4dbb397b0aad9`
Source census SHA256: `a5f371d49db1dc7354182ea1d401aa8533936201c763d435b7930905794c8ec5`

## Integridad

Se analizaron 2,400,000 filas válidas: 12 generaciones, 100.000 estrategias por generador y generación. La corrida inválida de 99.000 evaluaciones está excluida. Holdout: no utilizado.

## Clasificación económica

Cero exacto se trata como no positivo; la inactividad se clasifica exclusivamente por `forward_n_trades == 0`, no por expectancy.

generator,A,B,C,D,E
ga,328262,462772,61992,48694,298280
random,246987,494692,92340,74830,291151


## Reconciliación

El bruto se define como `2 × baseline_R − costes_x2_R`; la identidad se verifica fila a fila. El único coste disponible es `transaction_cost` agregado por operación; no se inventa un desglose de spread/comisión/slippage.

## Resultados agregados

- **GA**: activo 72.64%; retorno baseline positivo 28.91%; positivo con costes ×2 24.86%; expectancy bruta media activa 0.0083 R; neta baseline -0.0715 R; operaciones medias activas 13.05.
- **RANDOM**: activo 79.42%; retorno baseline positivo 30.50%; positivo con costes ×2 24.26%; expectancy bruta media activa 0.0006 R; neta baseline -0.0660 R; operaciones medias activas 20.46.

Las clases globales son A=575,249, B=957,464, C=154,332, D=123,524, E=589,431. El grupo E contiene 589,431 filas que no pasan retrospectivamente el filtro PF > 1.30 y trades > 250; esta observación no se usa como regla.

Los detalles reproducibles están en `reports/p13a_artifacts/`: censo clasificado, distribuciones P01–P99, eficiencia de costes, grupo E, comparación GA/Random, diagnóstico del filtro e identidades repetidas.

## Interpretación

La comparación GA/Random se presenta por generación y no trata las estrategias correlacionadas como observaciones independientes. El grupo E se analiza retrospectivamente y sus rasgos históricos no se convierten en predictores.

### Respuestas obligatorias

1. Hay estrategias positivas en ambas poblaciones, pero la fracción que sobrevive a costes ×2 es minoritaria; las cifras exactas por mes están en `classification_by_generation.csv`.
2. El déficit económico combina actividad insuficiente, margen bruto pequeño y fricción; `cost_efficiency.csv` cuantifica qué parte del bruto positivo cruza a neto no positivo.
3. GA y Random producen distribuciones diferentes por generación, con entrenamiento solapado; la comparación no es una prueba de independencia.
4. El grupo E se caracteriza en `historical_by_class.csv`; las propiedades comunes son descriptivas y no validan un predictor.
5. El filtro original se audita en `filter_diagnosis.csv`; no se propone umbral alternativo ni se inicia una nueva fábrica.

## Limitaciones

El censo contiene estrategias correlacionadas y los 12 meses comparten cinco meses de entrenamiento. No se accede a 2023–2026 y no se repite el GA.
