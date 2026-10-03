# P08 — Rolling Factory V1

## Estado

La primera generación trimestral se ejecutó de forma reproducible. El diseño
queda preparado para desplazar las tres ventanas cada trimestre, pero no se
ejecutaron generaciones posteriores.

- Nacimiento: `2019-01-01`.
- Training: `[2009-01-01, 2017-01-01)`.
- Development WF: `[2017-01-01, 2019-01-01)`.
- Forward operativo: `[2019-01-01, 2019-04-01)`.
- GA: 100.000 evaluaciones únicas, semilla `20261003`.
- Selección: 2.489 candidatas elegibles, 5 activas, cap de riesgo agregado
  `5 × 0.005 = 0.025`.
- Holdout: no utilizado; datos cargados hasta antes de `2019-04-01`.
- Operaciones reales: ninguna.

El run aceptado es `runs/p08-rolling-2019-q1-v3/generation.json` y conserva el
archivo GA, auditoría de selección, finalistas, ledgers development/forward,
Monte Carlo, stress y forward. Los runs v1/v2 no certifican resultados: v1
terminó con 99.000 evaluaciones por una configuración insuficiente de
generaciones y v2 usó el runner aún no commitido. v3 repitió el run tras el
commit del runner; su archive SHA coincide con v2:

`0dd44f144ce30751df5956ce94db2d04944e99dce8c106bc5c46177f0e87b6cb`

## Política congelada

`configs/rolling_factory.yaml`, `p08-rolling-factory-v1`, SHA256:

`73f7bb0649c814a0ec076fff9d9e3413ba480fb31eca765ed18b860f6e1c72ed`

Los criterios se fijaron antes del forward: mínimo 20 operaciones en WF,
expectancy estrictamente positiva, PF finito mayor que 1.05, al menos uno de
dos años positivo, expectancy positiva con costes ×2, máximo 5 activas y
desempate determinista por expectancy, PF, drawdown, operaciones y hash
ascendente. Con cero supervivientes se registra un forward vacío; no se
fabrican estrategias ni operaciones. El riesgo por operación es `0.005` y el
riesgo agregado máximo `0.025`.

## Selección y forward

| Hash | WF N | WF E R | WF PF | WF E×2 R | Forward N | Forward E R | Forward PF | Forward retorno |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `66626ccd60aa` | 24 | 1.1658 | 2.9176 | 1.0400 | 3 | 0.5182 | 1.6733 | 0.0076 |
| `d3acb202769e` | 32 | 0.9599 | 2.4652 | 0.8554 | 5 | -0.3374 | 0.6292 | -0.0086 |
| `db66b5b1d15d` | 22 | 0.9285 | 2.4057 | 0.8114 | 3 | -1.1197 | 0.0000 | -0.0167 |
| `d8a55f2a2910` | 36 | 0.7774 | 2.5538 | 0.7149 | 5 | 0.3800 | 1.5848 | 0.0093 |
| `d19322abcaed` | 33 | 0.7026 | 1.9149 | 0.6048 | 3 | -1.1732 | 0.0000 | -0.0175 |

El forward trimestral es un resultado operativo inicial, no una nueva selección:
2 de 5 estrategias terminaron positivas y 3 negativas. No se modificaron los
criterios ni se sustituyeron estrategias después de observarlo.

## Monte Carlo y stress

Monte Carlo se ejecutó sobre los ledgers de development de las 5 estrategias,
con 5.000 iteraciones por método, semillas derivadas de `20261003`, bloque 20 y
riesgo fraccional `0.005`. Se conservaron moving, stationary y period-block en
`generation.json`.

Stress técnico se ejecutó sobre development con baseline y costes ×2 usando el
backtester; se conservaron las métricas por estrategia en `generation.json`.
El forward se ejecutó después de congelar hashes, ledgers y configuración.

## Proveniencia

- Dataset EURUSD: `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Splits: `e1f8bef238126ad130d0bca19768087fc9aa7ead392e55484515b18549c19ba4`.
- Config data: `1bb8bffaac03c7d3af6a4b8017017f723db12be35850e57a84da8e33222260c9`.
- Config GA base: `b5efc9957e9802e6ead3c8371c30a290ff7136864c09bfe38eba7129f2302490`.
- Runner commit: `acc8d49` (`0.1.0+acc8d4990cbf`).

## Gate técnico

La prueba reducida `runs/p08-smoke-2019-q1` generó todos los artefactos con
cero supervivientes explícito y sin forward sintético. La ejecución completa
v3 alcanzó exactamente 100.000 evaluaciones, verificó los hashes de estrategia
y ledgers, y no cruzó el holdout. El resultado forward no se usa para cambiar
la política.
