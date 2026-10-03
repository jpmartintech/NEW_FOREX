# P06 — Bloqueo de criterios de aceptación

## Estado

El bloqueo previo a resultados queda resuelto por la política congelada
`p06-frozen-wf-v1` en `configs/wf_acceptance.yaml` (commit `6c52227`). La
evaluación técnica ya se ejecutó con esa política y sus resultados están en
`reports/p06_eurusd_wf.md`. La certificación de cada estrategia se aplicó sin
compensaciones: 1 PASS y 24 FAIL.

Auditoría de criterios: `p06-criteria-audit-20261002T224744Z`.

## Evidencia revisada

- `configs/funnel.yaml` contiene criterios históricos del funnel de descubrimiento
  (incluidos años walk-forward), pero describe una fase de selección completa y
  no el gate de evaluación de las 25 estrategias congeladas.
- `configs/wf_procedure.yaml` describe una evaluación de la *procedura* con
  reoptimización GA por ventana y controles aleatorios. No es una evaluación
  sin recalibración de los finalistas de `finalist_manifest.json`.
- `configs/wf/README.md` identifica los folds anuales como entregable, pero no
  define umbrales de aceptación.
- `docs/VALIDATION_POLICY.md` permanece como documento no operativo/pendiente y
  no establece el gate P06 para esta cohorte.

La manifest congelada de P03.1 contiene 25 hashes únicos y sus ledgers
correspondientes. P06 cargó únicamente `development_wf` hasta 2019-01-01; el
run registró cero filas posteriores a ese límite. No se abrió
`procedure_validation` ni el holdout.

## Consecuencia

No se modifican criterios por el resultado. La estrategia con hash completo
`237d10ee505b9bf528a2033d30babb26db137e9de3852a8bb116f73799798ebd` es la única
que supera todos los criterios; cero supervivientes también habría sido un
resultado válido. El tag P06 queda condicionado a la validación final,
commit separado de resultados y trazabilidad completa.
