# P12G — Fixed cohort forward decay

## Protocolo

P12G mantiene sin cambios las 47 estrategias de P12F (`training PF > 1.30` y `training trades > 250`) y reutiliza exactamente sus 1.000 composiciones `high_quality` de cinco estrategias. No hubo remuestreo, nuevas estrategias ni reselección por trimestre.

El protocolo quedó congelado en `126f46db`, configuración `p12g-fixed-cohort-v1`, SHA256 `c19797497c16271d8afed24b843ed9ee52cb84274de29ea83e2273381c03b5a1`.

Se evaluaron 2017Q1–2019Q1, con baseline y costes ×2, riesgo 0,5% por operación y límite agregado 2,5%. P12D aportó las métricas individuales longitudinales; las carteras se reconstruyeron con el motor operativo y ledgers reales. No se accedió a 2019Q2 ni al holdout.

## Resultados individuales

| Trimestre | Operaciones | Expectancy bruta mediana R | Expectancy neta mediana R | Expectancy x2 mediana R | Retorno neto mediano | Coste R/op |
|---|---:|---:|---:|---:|---:|---:|
| 2017Q1 | 414 | 0,1728 | 0,1198 | 0,0522 | 0,551% | 0,0618 |
| 2017Q2 | 839 | 0,0588 | 0,0064 | -0,0527 | 0,057% | 0,0777 |
| 2017Q3 | 553 | -0,1923 | -0,2446 | -0,2993 | -1,364% | 0,0691 |
| 2017Q4 | 554 | -0,2727 | -0,3599 | -0,4233 | -1,550% | 0,0837 |
| 2018Q1 | 575 | ~0,0000 | -0,0448 | -0,1331 | -0,360% | 0,0531 |
| 2018Q2 | 279 | -0,5000 | -0,5637 | -0,6119 | -1,225% | 0,0797 |
| 2018Q3 | 720 | 0,0208 | -0,0996 | -0,2155 | -0,878% | 0,0788 |
| 2018Q4 | 409 | -0,1509 | -0,2088 | -0,2579 | -0,907% | 0,0728 |
| 2019Q1 | 425 | 0,0909 | 0,0056 | -0,0535 | 0,021% | 0,0913 |

Las 47 estrategias estuvieron activas en todos los trimestres. La actividad no desaparece; el deterioro aparece primero en la expectancy bruta desde 2017Q3 y se agrava por costes. 2017Q1 sí es excepcional: fue el único trimestre con expectancy bruta mediana claramente positiva y neta mediana robusta.

## Carteras originales

Cada fila resume 1.000 composiciones fijas de cinco estrategias, no nuevas muestras.

| Trimestre | Mediana retorno baseline | Carteras positivas | Mediana retorno x2 | Carteras positivas x2 | Mediana bruto | Mediana MaxDD baseline |
|---|---:|---:|---:|---:|---:|---:|
| 2017Q1 | +2,72% | 92,2% | +1,37% | 80,8% | +4,12% | 3,19% |
| 2017Q2 | +2,24% | 75,6% | -1,51% | 30,4% | +5,98% | 10,26% |
| 2017Q3 | -7,61% | 1,0% | -9,49% | 0,3% | -5,67% | 9,26% |
| 2017Q4 | -10,27% | 0,2% | -12,44% | 0,1% | -7,99% | 10,33% |
| 2018Q1 | -2,05% | 27,7% | -3,59% | 15,6% | -0,52% | 5,33% |
| 2018Q2 | -7,10% | 0,0% | -8,06% | 0,0% | -6,17% | 7,82% |
| 2018Q3 | -4,58% | 12,9% | -7,61% | 5,2% | -1,48% | 9,63% |
| 2018Q4 | -5,52% | 0,7% | -7,00% | 0,1% | -4,00% | 6,67% |
| 2019Q1 | +0,90% | 62,9% | -1,24% | 31,5% | +3,02% | 3,98% |

La mediana de la trayectoria acumulada baseline fue positiva en 2017Q1 y 2017Q2 (+2,72% y +4,99%), cruzó a negativa en 2017Q3 (-3,44%) y terminó 2019Q1 en -27,79%. Con costes ×2 cruzó a negativa ya en 2017Q2 (-0,27%) y terminó en -40,11%.

El 0% de las 1.000 trayectorias terminó positivo en baseline o x2. El MaxDD mediano final fue 32,56% baseline y 41,63% x2.

## Respuestas del análisis

1. **¿2017Q1 es excepcional?** Sí. Q1 y, en menor medida, Q2 son los únicos trimestres con carteras medianas positivas baseline; Q1 es el único con margen individual neto claramente alto.
2. **¿Cuándo se vuelve negativa la mediana?** La cartera trimestral baseline se vuelve negativa en 2017Q3; la trayectoria acumulada x2 ya es negativa en 2017Q2.
3. **¿Qué causa el deterioro?** Desde 2017Q3 domina la expectancy bruta negativa. En Q2 la expectancy bruta aún es positiva, pero los costes ×2 vuelven negativa la mediana; posteriormente costes y señal bruta negativa actúan conjuntamente.
4. **¿Hay dependencia conductual?** Sí existe dependencia medible entre las 47: `dependence.csv` registra firmas repetidas por trimestre. Las composiciones comparten además una población de solo 47 estrategias, por lo que las 1.000 carteras no son observaciones independientes.
5. **¿Cómo evoluciona retorno y MaxDD?** La mediana acumulada baseline pasa de +4,99% tras Q2 a -13,07% tras Q4 y -27,79% en 2019Q1; el MaxDD final mediano es 32,56%. El escenario x2 termina en -40,11% y 41,63% de MaxDD.

## Limitaciones

- Es un único cohort histórico y una única secuencia de mercado; el análisis es exploratorio.
- No se eliminaron estrategias perdedoras ni se alteró la composición.
- El coste se conserva agregado; no se puede separar comisión, spread y slippage.
- El retorno bruto individual capitalizado no está archivado para las 47 en P12D; el bruto de cartera sí se reconstruyó desde operaciones y se reconcilió con baseline/x2.
- La evidencia de persistencia es negativa para este cohort, pero no prueba que toda regla de calidad histórica falle fuera de esta muestra.

## Artefactos y trazabilidad

Los artefactos contienen 423 filas individuales (47 × 9), 18.000 filas de cartera (1.000 × 9 × 2), 2.000 trayectorias y 18 ledgers agregados por trimestre/coste. Incluyen checkpoint, equivalencia P12F Q1, hashes de fuentes y ausencia de holdout.

Hashes de resultados: `individual_quarterly.parquet` `c87a913c0cdf4d7e12dc623ef620727fb10dc5455f16680f1acff6c5cff61a12`; `portfolio_quarterly.csv` `32a2a5b9ca264e35b3d15f4a505c591306a2bd2b08368e53f780229e89f54bf9`; `trajectories.csv` `fef5e9b4c8b8dd0aa3435d5fdae625bfa9cda453fdf48394f2c329d727b17126`.
