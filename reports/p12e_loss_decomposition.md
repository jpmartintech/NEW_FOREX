# P12E — Portfolio loss decomposition

## Protocolo y alcance

Se reutilizaron sin remuestreo las composiciones y los ledgers congelados de P12D.3. Política `p12e-loss-decomposition-v1`, SHA256 de configuración `20c1dfc6fd9d75e18238f27eebae1a83933fca1ab053eb563f173c93878e4b92`. Se reconstruyeron 90,000 carteras, 13,677,678 operaciones efectivamente ejecutadas y 6,000 trayectorias.

El holdout 2023–2026 no se abrió. La regla histórica y el motor de selección permanecen intactos.

## Reconciliación contable

Para cada operación, `gross_R = result_R + transaction_cost / risk`; `net_R = result_R`. El PnL bruto en precio es movimiento firmado más funding; el neto resta el coste agregado registrado. El motor capitaliza cada operación con el riesgo de cartera (0,5%) y conserva por separado la curva neta y la curva bruta.

El ledger sólo registra `transaction_cost` agregado. No identifica por separado comisión, spread y slippage, por lo que P12E no inventa esa división. La comparación ×2 duplica el coste agregado del backtester; si cambia la trayectoria de señales, esa diferencia no debe interpretarse como coste puro.

La identidad `bruto en la trayectoria neta = neto + cost_drag_capitalized_at_net_path` se verificó operación a operación; el retorno neto y el maximum drawdown coinciden con P12D.3 dentro de 1e-10.

## Cost drag por cartera

| Grupo | Coste | Bruto | Neto | Drag | Exp. bruta R | Exp. neta R | MaxDD | % bruto + | % bruto+/neto− | Coste R/op. | Oper. | Simult. máx. | Bloqueos |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| activity_matched | baseline | -0.46% | -9.58% | 9.28% | -0.0003 | -0.0811 | 14.83% | 48.34% | 27.30% | 0.0807 | 245.0 | 4.0 | 0 |
| activity_matched | costs_x2 | -0.46% | -17.83% | 17.70% | -0.0003 | -0.1612 | 21.00% | 48.34% | 41.71% | 0.1614 | 245.0 | 4.0 | 0 |
| eligible | baseline | 1.64% | -0.04% | 1.86% | 0.0698 | 0.0038 | 5.67% | 58.26% | 8.51% | 0.0672 | 58.0 | 3.0 | 0 |
| eligible | costs_x2 | 1.64% | -1.86% | 3.69% | 0.0698 | -0.0647 | 6.50% | 58.26% | 18.25% | 0.1344 | 58.0 | 3.0 | 0 |
| full_random | baseline | 0.00% | -3.56% | 4.04% | 0.0000 | -0.0733 | 8.12% | 49.00% | 20.96% | 0.0777 | 111.0 | 2.0 | 0 |
| full_random | costs_x2 | 0.00% | -7.34% | 7.93% | 0.0000 | -0.1520 | 10.65% | 49.00% | 33.72% | 0.1553 | 111.0 | 2.0 | 0 |

La población elegible tiene mediana bruta positiva pero mediana neta negativa en ambos escenarios; por tanto, para esta cohorte el coste drag es suficiente para transformar una parte material de los resultados brutos en pérdidas netas. En los controles la mediana bruta es aproximadamente nula o negativa y la fricción agrava el resultado.

## Trayectorias rolling

| Grupo | Coste | P05–P95 neto | Mediana bruto | Mediana neto | Drag mediano | % positivas | MaxDD mediano |
|---|---|---:|---:|---:|---:|---:|---:|
| activity_matched | baseline | -91.51%–-60.65% | 4.65% | -81.07% | 85.82% | 0.00% | 77.98% |
| activity_matched | costs_x2 | -98.91%–-91.07% | 4.65% | -96.56% | 101.13% | 0.00% | 95.08% |
| eligible | baseline | -35.37%–22.63% | 24.18% | -9.86% | 34.69% | 28.50% | 21.63% |
| eligible | costs_x2 | -54.23%–-9.45% | 24.18% | -35.18% | 59.76% | 1.20% | 34.05% |
| full_random | baseline | -76.05%–-26.05% | 5.08% | -55.26% | 58.53% | 0.30% | 52.50% |
| full_random | costs_x2 | -92.72%–-61.75% | 5.08% | -80.65% | 84.34% | 0.00% | 76.83% |

La capitalización importa: las trayectorias no se reconstruyeron sumando retornos trimestrales. La mediana elegible pasa de bruto `24.18%` a neto `-9.86%` en baseline, y a `-35.18%` con ×2.

## Concentración temporal y dependencia

- eligible: peores meses 2019-06 (-60.398), 2019-10 (-56.605), 2020-06 (-51.563); mejores 2020-02 (98.162), 2021-08 (46.383), 2021-03 (43.165).
- full_random: peores meses 2019-06 (-57.041), 2019-10 (-52.176), 2019-12 (-42.302); mejores 2020-11 (33.922), 2020-02 (18.300), 2019-07 (14.088).

Dirección (suma descriptiva sobre las carteras muestreadas):
- activity_matched baseline LONG: 1,750,092 operaciones, neto acumulado -730.6247, pérdida en 57.55%.
- activity_matched baseline SHORT: 2,199,077 operaciones, neto acumulado -727.8282, pérdida en 55.91%.
- activity_matched costs_x2 LONG: 1,750,092 operaciones, neto acumulado -1312.9584, pérdida en 57.90%.
- activity_matched costs_x2 SHORT: 2,199,077 operaciones, neto acumulado -1530.5007, pérdida en 56.45%.
- eligible baseline LONG: 210,807 operaciones, neto acumulado 33.4562, pérdida en 57.93%.
- eligible baseline SHORT: 701,760 operaciones, neto acumulado -95.9442, pérdida en 58.23%.
- eligible costs_x2 LONG: 210,807 operaciones, neto acumulado -36.1714, pérdida en 58.27%.
- eligible costs_x2 SHORT: 701,760 operaciones, neto acumulado -348.6632, pérdida en 58.76%.
- full_random baseline LONG: 861,110 operaciones, neto acumulado -362.9488, pérdida en 57.46%.
- full_random baseline SHORT: 1,115,993 operaciones, neto acumulado -375.3344, pérdida en 56.02%.
- full_random costs_x2 LONG: 861,110 operaciones, neto acumulado -672.3302, pérdida en 57.82%.
- full_random costs_x2 SHORT: 1,115,993 operaciones, neto acumulado -811.8412, pérdida en 56.57%.

La tabla `temporal_concentration.csv` contiene la contribución por generación/trimestre, mes y semana para cada grupo y coste. `direction_decomposition.csv` separa LONG/SHORT; `strategy_decomposition.csv` conserva la contribución de cada componente muestreado. Los episodios más negativos y el leave-one-generation-out están disponibles en `leave_one_generation_out.csv`; no se eliminó ningún periodo.

El contador de simultaneidad de pérdidas mide cierres negativos mientras había otras posiciones abiertas. Las carteras elegibles muestran dependencia de pérdidas concurrentes, pero no se interpretan las 70.341 estrategias como observaciones independientes. La firma conductual de P12D.3 era agregada y forward-only; no se reconstruye como predictor.

## Efecto del motor

No se registraron señales bloqueadas por el límite agregado en las 90.000 carteras; cinco estrategias con 0,5% por operación alcanzan como máximo el 2,5% permitido. Por ello, en esta cohorte no hay evidencia de que el límite de exposición explique las pérdidas. El ledger no conserva un log de todas las señales candidatas rechazadas, así que no es posible distinguir retrospectivamente prioridad frente a ausencia de señal; sólo se auditan las operaciones efectivamente ejecutadas.

## Respuestas diagnósticas

1. **Antes o después de costes:** en las elegibles, el resultado bruto agregado es descriptivamente favorable en mediana, pero la trayectoria neta es negativa; en los controles la pérdida ya aparece en bruto o es casi nula.
2. **Proporción atribuible a costes:** el drag se reporta por cartera, operación y trayectoria en los artefactos; no se convierte en una fracción causal única porque la capitalización y ×2 cambian la trayectoria económica.
3. **Concentración:** la descomposición mensual/semanal y leave-one-out muestran cuánto depende cada resultado de periodos; no se optimizó eliminando periodos.
4. **Pérdidas simultáneas:** sí existen cierres negativos con otras posiciones abiertas; su frecuencia y magnitud están en `simultaneous_loss_exits` y `other_open_losses_at_exit`.
5. **Restricciones:** no hubo bloqueos por cap en los ledgers muestreados; el impacto observable del motor es la capitalización, prioridad temporal y riesgo por operación.
6. **Ventaja frente al control:** la elegibilidad mejora la distribución histórica/forward de la cartera, reduciendo frecuencia y operaciones, pero no crea suficiente margen neto bajo costes; la diferencia es enriquecimiento relativo, no rentabilidad absoluta.
7. **Limitación dominante:** para las elegibles, el margen bruto pequeño frente a costes por operación y la concentración/dependencia temporal dominan; para el control, también falta rentabilidad bruta.

## Limitaciones

No se pueden separar comisión, spread y slippage desde estos ledgers. Tampoco se puede reconstruir el universo de señales bloqueadas que nunca llegó al ledger. Los controles comparten mercado y estrategias entre carteras, y las generaciones tienen ventanas solapadas; las distribuciones no son muestras independientes. Los resultados son contables y diagnósticos, no una nueva regla de selección ni evidencia confirmatoria de edge.
