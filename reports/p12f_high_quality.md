# P12F — High historical quality & immediate forward economic efficiency

## Alcance y protocolo

P12F se ejecutó sobre las 100.000 estrategias originales de P08 Q1. La elegibilidad utilizó únicamente el entrenamiento 2009-01-01 ≤ *t* < 2017-01-01 y el forward se limitó a 2017Q1, 2017-01-01 ≤ *t* < 2017-04-01. No se ejecutó GA, no se consultaron trimestres posteriores ni el holdout.

Política congelada: `p12f-high-quality-v1`, commit `a8f8c47`, SHA256 `ac64ba99f586d8b1af042a1b13b1d71ae07d717e11c75726d6a1bf41d24f4926`.

Regla nueva, aplicada estrictamente: `training PF > 1.30 AND training trades > 250`.

Fuentes verificadas:

- archive SHA256: `0dd44f144ce30751df5956ce94db2d04944e99dce8c106bc5c46177f0e87b6cb`.
- selection audit SHA256: `d9c52c45a1eae6251d78bf39d3226a2870d9c75c45559def2cca7a35dd7b14e7`.
- P12D population SHA256: `614d38565fbc7ecc3347c33b515c2444e97432d6ec97f4025d96a0733f565e11`.

Se reutilizaron las métricas individuales exactas de P12D para 2017Q1. Baseline y x2 tuvieron idéntico número e identidad temporal de operaciones para las 100.000 estrategias; por ello se reconcilió el bruto en R como `2 × neto_baseline − neto_x2`. El desglose de costes sigue siendo agregado: P12E confirmó que estos artefactos no separan comisión, spread y slippage.

## Poblaciones individuales

| Grupo | Estrategias | Activas | Expectancy bruta mediana R* | Expectancy neta mediana R | Expectancy x2 mediana R | Retorno neto mediano | Positivas neto | Positivas x2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Universo | 100.000 | 59.983 | 0,0331 | 0,0000 | 0,0000 | 0,0000 | 41,84% | 29,17% |
| Filtro anterior PF≥1,05; trades≥100 | 7.517 | 7.502 | 0,0518 | 0,0025 | -0,0503 | 0,0000 | 50,27% | 42,91% |
| Nuevo PF>1,30; trades>250 | 47 | 47 | 0,1728 | 0,1198 | 0,0522 | 0,0055 | 82,98% | 76,60% |

\* Para los individuos, el bruto disponible de forma exacta y comparable es R por operación. P12D no conserva el equity curve bruto capitalizado de las 100.000 estrategias; no se inventó un retorno bruto individual.

El nuevo grupo representa 47/100.000 = 0,047%. Está anidado en el filtro anterior: las 47 cumplen PF≥1,05 y trades≥100. No son muestras independientes.

Entre estrategias activas, la expectancy bruta media/mediana del grupo nuevo fue 0,1893/0,1728 R, frente a 0,0523/0,0518 R del filtro anterior y 0,0412/0,0331 R del universo. El coste agregado medio fue 0,0618 R por operación en el grupo nuevo, frente a 0,0572 R y 0,0649 R. La mayor calidad histórica elevó claramente el margen bruto, pero no eliminó la fricción.

En el grupo nuevo, 93,62% de las estrategias activas tuvieron expectancy bruta positiva, 82,98% expectancy neta positiva y 76,60% positiva con costes x2. El 10,64% fue bruto positivo pero neto baseline negativo. El resultado es descriptivo de un único trimestre y la muestra es pequeña.

## Controles y carteras

Se generaron 1.000 carteras de cinco estrategias para cada grupo A/B/C, además de 1.000 controles uniformes del universo completo y 1.000 controles emparejados por actividad histórica. Las composiciones fueron congeladas por semilla, sin selección por forward. El motor usado fue `frozen_p08_p09_portfolio_ledger`, con riesgo 0,5% por operación y límite agregado 2,5%.

| Grupo | Mediana retorno baseline | Positivas baseline | Mediana retorno x2 | Positivas x2 | Mediana bruto | Mediana coste baseline |
|---|---:|---:|---:|---:|---:|---:|
| Universo | -1,85% | 31,8% | -5,41% | 14,0% | 1,76% | 0,0424 |
| Filtro anterior | -0,28% | 46,2% | -2,00% | 30,1% | 1,21% | 0,0166 |
| Nuevo | +2,72% | 92,2% | +1,37% | 80,8% | 4,12% | 0,0141 |
| Control uniforme | -1,85% | 32,0% | -5,39% | 14,1% | 1,76% | 0,0424 |
| Control emparejado por actividad | -1,77% | 32,0% | -5,09% | 14,5% | 1,55% | 0,0373 |

La cartera de cinco estrategias del grupo nuevo tiene mediana neta positiva tanto baseline como x2; esto no convierte el resultado en validación de edge: las 1.000 composiciones comparten población y trimestre, y el grupo elegible solo tiene 47 estrategias. Los controles no fueron elegidos por resultados forward.

El retorno bruto de cartera sí se reconstruyó mediante operaciones ejecutadas y el motor de cartera; no es la suma de retornos individuales. Para costes x2, el bruto se conserva de la misma composición y se compara con el neto x2. La reconciliación usa `PnL bruto − coste agregado = PnL neto` dentro de tolerancia `1e-12` en los artefactos tabulares.

## Diagnóstico económico

1. La exigencia histórica incrementó el margen bruto forward: la mediana de expectancy bruta activa subió a 0,1728 R y la mediana bruta de cartera a 4,12%.
2. Redujo, pero no anuló, la absorción por costes: 10,64% de los individuos activos pasó de bruto positivo a neto negativo; con x2, 17,02% tuvo bruto positivo y expectancy negativa.
3. Aumentó la supervivencia neta individual y de cartera frente al filtro anterior y al universo.
4. La mediana de las carteras nuevas fue positiva baseline (+2,72%) y x2 (+1,37%); el 80,8% sobrevivió con retorno positivo x2.
5. La actividad es suficiente para construir carteras, pero no para tratar la evidencia individual como grande: 47 estrategias, media de 8,8 operaciones forward por estrategia y un único trimestre.
6. El resultado no demuestra edge. Puede reflejar selección sobre una población histórica extrema, dependencia entre estrategias y condiciones específicas de 2017Q1.

## Limitaciones y trazabilidad

- No se dispone de desglose separado de comisión, spread y slippage; solo `transaction_cost` agregado.
- El retorno bruto capitalizado individual de las 100.000 filas no está archivado en P12D; se reporta como no disponible, mientras que el bruto R y el bruto de carteras sí están reconciliados.
- Las carteras comparten estrategias y mercado; los percentiles no son probabilidades confirmatorias.
- Las 47 estrategias elegibles son un subconjunto muy pequeño y anidado en el filtro anterior.
- El análisis no utiliza 2017Q2 ni ningún periodo posterior para ajustar la regla.

Artefactos reproducibles:

- `individual_population.parquet`: SHA256 `7cfcdcf6fb71ccbb655c6fa7c70c1469b90fc2f070b6cb7935e6a38f8a3a1232`.
- `eligibility.parquet`: SHA256 `07293efae9f6603197ad3b431ccf751722eb22dfc24e7f660d72262b88767633`.
- `portfolio_compositions.jsonl`: SHA256 `cda40f50a2b18c714ba5eb1e5e7a26f5c82c601eaa679dd4c9249d01baa7e6d5`.
- `portfolio_results.csv`: SHA256 `5d3f6060a4c4cff3879b7242048fb8b8d5c59de41de136805c76a8492077fa83`.

Conclusión: el filtro PF>1,30 y trades>250 identifica en 2017Q1 una subpoblación con mayor expectancy bruta y mejor supervivencia neta que los dos referentes. La evidencia es económicamente favorable en este trimestre, pero no establece generalización, robustez ni edge; requiere replicación temporal congelada para poder evaluarse fuera de muestra.
