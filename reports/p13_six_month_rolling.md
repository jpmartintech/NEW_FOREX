# P13 — Six-month rolling genetic factory

## Protocolo válido

La ejecución válida usa `p13-six-month-rolling-v1.1`, congelado en el commit `7977c162`. SHA256 de configuración: `d0758174ff0a4bcf89517cf708982c40a76bee247800e7dc058a43825cd1562f`.

Se evaluaron 12 generaciones mensuales sobre EURUSD H1:

- Training: seis meses inmediatamente anteriores al forward.
- Forward: mes natural siguiente, con límites `[inicio, fin)`.
- Generación: 100.000 estrategias GA únicas y 100.000 Random Search únicas.
- Selección: `training PF > 1.30 AND training trades > 250`, sin información forward.
- Riesgo: 0,5% por operación, máximo agregado 2,5%.
- Rollover: cierre al final del mes antes de sustituir la cartera.

La primera corrida con 100 iteraciones GA produjo 99.000 estrategias por generación debido a la reserva de élites del motor. Fue invalidada, no se usó en el informe y se conservó en `reports/p13_invalid_budget_run_99k/`. El protocolo se corrigió a 102 iteraciones para llenar exactamente el presupuesto; la corrida válida cumple `1.200.000 GA + 1.200.000 Random Search`.

## Censo completo

El censo contiene 2.400.000 filas: 12 generaciones × 2 generadores × 100.000 estrategias. Los resultados completos por generación, generador y población completa/elegible están en `census_summary.csv`.

El filtro histórico fue extremadamente restrictivo:

| Generador | Generaciones con ≥1 elegible | Generaciones con ≥5 elegibles | Elegibles totales en las 12 generaciones |
|---|---:|---:|---:|
| GA | 3/12 | 0/12 | 4 |
| Random Search | 2/12 | 0/12 | 2 |

Las generaciones elegibles fueron GA G03, G04 y G11; Random G03 y G04. Por tanto, ninguna generación pudo formar una cartera completa de cinco: se aplicó la política congelada de posiciones parciales y capital no asignado. Las otras generaciones permanecieron en efectivo.

En la población completa, el GA produjo una actividad media inferior a Random Search, pero no una mejora neta consistente. La media simple entre generaciones de la expectancy neta activa fue aproximadamente `-0,077R` para GA y `-0,066R` para Random Search baseline. Estas medias descriptivas no son observaciones independientes: comparten mercado, gramática y ventanas solapadas.

## Carteras seleccionadas

| Generador | Operaciones | Retorno bruto acumulado | Retorno neto baseline | Retorno neto costes ×2 | MaxDD baseline | Meses positivos |
|---|---:|---:|---:|---:|---:|---:|
| GA | 183 | -12,52% | -18,62% | -24,71% | 18,62% | 0/12 |
| Random Search | 93 | -6,63% | -10,38% | -14,04% | 10,38% | 0/12 |

Solo hubo actividad operativa en tres meses GA (G03, G04, G11) y dos meses Random (G03, G04). Todas las carteras activas fueron negativas baseline y con costes ×2. El filtro no convirtió la población en una cartera netamente rentable.

## Respuestas de falsación

1. **¿Hay suficientes elegibles?** No. El filtro produce menos de cinco elegibles en las 12 ventanas; la política parcial se activa en 5 casos y efectivo en 19.
2. **¿La población completa contiene estrategias forward rentables?** Sí, hay estrategias individuales positivas en ambos universos, pero la rentabilidad está distribuida entre poblaciones correlacionadas y no basta para la cartera histórica.
3. **¿El filtro enriquece la población?** No de forma útil en esta arquitectura. Los grupos elegibles son minúsculos y sus carteras tuvieron expectancy bruta negativa en los meses activos.
4. **¿GA supera a Random Search?** No. Random Search obtuvo una trayectoria menos negativa (`-10,38%` frente a `-18,62%` baseline), aunque con menos operaciones y solo dos meses activos. No es evidencia de superioridad de Random: ambas trayectorias comparten las limitaciones de muestra y mercado.
5. **¿Las carteras son rentables?** No, ni baseline ni costes ×2.
6. **¿Sobrevive la trayectoria a costes ×2?** No; GA termina en `-24,71%` y Random en `-14,04%`.
7. **¿Depende de pocos meses?** Sí. Toda la pérdida operativa procede de 3 meses GA y 2 Random; el resto es efectivo. Esto es concentración de actividad, no una validación de estabilidad.
8. **¿Hay concentración conductual?** Sí. Las firmas conductuales del censo son muy inferiores al número de estrategias en muchas generaciones y los seleccionados GA/Random incluso comparten hashes en G03/G04; el tamaño efectivo es menor que 2,4 millones.
9. **¿Reduce el deterioro de P12G?** No se observa una mejora operativa. La regeneración mensual evita mantener una misma cohorte, pero el filtro casi nunca asigna capital y los pocos meses activos son negativos.

## Costes y limitaciones

El bruto de cartera se reconstruyó desde ledgers ejecutados y la identidad de operaciones baseline/x2; `PnL bruto − costes agregados = PnL neto`. El simulador conserva `transaction_cost` agregado y no permite separar comisión, spread y slippage.

El censo individual conserva expectancy y retorno netos, expectancy bruta en R derivada de baseline/x2 y coste R por operación. No se inventó un retorno bruto capitalizado individual cuando el contrato agregado no lo preserva.

No se accedió al holdout ni a datos posteriores a junio de 2018. No se modificaron la gramática, los umbrales ni los resultados de P12F/P12G.

## Artefactos

- `forward_census_all.parquet`: SHA256 `a5f371d49db1dc7354182ea1d401aa8533936201c763d435b7930905794c8ec5`.
- `census_summary.csv`: SHA256 `13c81e77b2a1a7ea7702bbc02a3f5084c5c2262597793a53acd3492331362d7f`.
- `portfolio_results_all.csv`: SHA256 `c7c1b7de6c375e311bb658593e4a3fbddf22f4e310884cc859ca0467f1d961e5`.
- `rolling_trajectories.csv`: SHA256 `da3174ef37a815d033d993aecadb40a372276b99fb5fade9b7ce35f53e2d95b2`.
- Manifest: SHA256 `cd445e9f2ccbfdaa10246ef8c4153708fabcd1cbfdcd448b6ecfd405c795f8c2`.
