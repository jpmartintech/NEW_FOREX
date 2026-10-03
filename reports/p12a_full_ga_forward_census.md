# P12A — Full GA Forward Census, P08 2019 Q1

## Alcance e integridad

Se evaluó el archivo GA congelado de P08 Q1 sobre el forward `[2019-01-01, 2019-04-01)`, sin repetir el GA y sin excluir estrategias por haber fallado en P03–P05. El archivo contiene exactamente 100.000 hashes únicos y cada definición se reconstruyó con `StrategyDefinition`; se verificó el hash canónico contra el archivo y la auditoría de selección.

- Archivo GA SHA256: `0dd44f144ce30751df5956ce94db2d04944e99dce8c106bc5c46177f0e87b6cb`.
- Auditoría de selección SHA256: `d9c52c45a1eae6251d78bf39d3226a2870d9c75c45559def2cca7a35dd7b14e7`.
- Configuración P12A SHA256: `971cf2a1d10e4aeebe471e4d3936776bc761a1d6a9fa1ea533ba2193e7b15cb5`.
- Resultado Parquet SHA256: `32e06dad8a9eec5bf9717abb225436f03128099dda81e6453c7393f4bf2e4cf9`.
- 50 chunks de 2.000 estrategias; 21,76 s de ejecución; checkpoint por chunk.
- Holdout no utilizado; última fecha cargada limitada a `2019-04-01` exclusiva.

## Censo forward

| Medida | Resultado |
|---|---:|
| Estrategias evaluadas | 100.000 |
| Estrategias con cero operaciones | 35.817 (35,82%) |
| Expectancy forward positiva | 32.535 (32,54%) |
| Retorno forward positivo | 32.237 (32,24%) |
| Expectancy media R | +0,03554 |
| Expectancy mediana R | 0 |
| Retorno medio | -0,4277% |
| Retorno mediano | 0 |
| PF infinito | 4.477 |
| Operaciones medias por estrategia | 26,32 |

Un PF infinito no se considera evidencia suficiente: 4.477 casos son compatibles con ausencia de pérdidas y, frecuentemente, muy pocas operaciones. Las filas con cero operaciones se mantienen y tienen expectancy y retorno cero. Con costes ×2, la expectancy media pasa a **-0,01975 R**.

## Filtros históricos: aceptadas frente a rechazadas

La auditoría original contiene 2.489 `PASS` y 97.511 `FAIL`; ningún filtro forward fue añadido.

| Grupo | N | Exp. forward media | Exp. forward positiva | Retorno medio | Ops medias | Cero operaciones |
|---|---:|---:|---:|---:|---:|---:|
| PASS original | 2.489 | -0,00044 R | 45,64% | -0,4131% | 9,52 | 2,09% |
| FAIL original | 97.511 | +0,03646 R | 32,20% | -0,4281% | 26,75 | 36,68% |

La selección histórica aumenta la fracción de expectancy positiva, pero no produce retorno medio forward positivo. La media de los rechazados está influida por estrategias con resultados positivos muy escasos; la mediana global de expectancy es cero.

## Relación entre historia y forward

Correlaciones descriptivas con expectancy forward:

| Métrica histórica | Correlación |
|---|---:|
| Fitness/archive (= expectancy training) | +0,0372 |
| Expectancy training | +0,0372 |
| Expectancy development WF | -0,2077 |
| PF development | -0,0603 |
| Operaciones development | -0,0691 |
| Operaciones forward | -0,0913 |
| Retorno forward | +0,3755 |

Los deciles completos están en `historical_metric_deciles.csv`. Patrones principales: los deciles intermedios de fitness/training 4–7 tienen entre 47,32% y 55,05% de expectancy forward positiva; el decil superior extremo tiene solo 0,44% y 0,0044 operaciones medias. El decil superior de expectancy development tiene expectancy forward media **-0,04644 R** y 32,52% positiva. El decil superior de PF development tiene **-0,05390 R** forward medio y 36,00% positiva. Los rankings históricos extremos no ordenan robustamente el forward.

## Operaciones y tamaño de muestra

| Operaciones forward | Estrategias | Exp. positiva | Exp. media R | Retorno medio |
|---|---:|---:|---:|---:|
| 0 | 35.817 | 0,00% | 0,0000 | 0,0000% |
| 1–5 | 13.739 | 55,77% | +0,23950 | +0,1272% |
| 6–20 | 15.123 | 61,36% | +0,11559 | +0,6597% |
| 21–50 | 16.138 | 47,71% | -0,04241 | -0,6912% |
| 51–100 | 12.744 | 47,37% | -0,03380 | -1,1341% |
| >100 | 6.439 | 28,84% | -0,05734 | -4,4857% |

Los resultados positivos de muestras pequeñas no son evidencia robusta. A partir de 21 operaciones la expectancy y el retorno medios son negativos; el grupo de más de 100 operaciones es el más débil.

## Dependencia y duplicación conductual

Las 100.000 definiciones son únicas, pero solo hay 48.090 firmas forward exactas usando `(n_trades, expectancy_R, return, max_drawdown)`. Hay 51.910 filas que comparten firma con otra; la firma de cero operaciones agrupa 35.817 estrategias. Esto impide tratar el censo como 100.000 observaciones independientes. Evidencia: `behavioral_dependence.json`.

## Limitaciones

El forward es un único trimestre y el universo fue producido por un mismo GA sobre datos compartidos. Las estrategias no son observaciones independientes; PF infinito, cero operaciones y retornos de una sola operación generan colas y discontinuidades. El censo describe la relación entre propiedades históricas y ese trimestre, pero no valida edge de mercado, no sustituye P04/P05/P06 y no autoriza filtros retrospectivos.

Artefacto principal: `reports/p12a_artifacts/full_forward_census.parquet`. Supporting artifacts: chunks, checkpoint, manifest, `accepted_vs_rejected.csv`, `historical_metric_deciles.csv`, `operation_buckets.csv`, `correlations_with_forward_expectancy.csv` y `behavioral_dependence.json`.
