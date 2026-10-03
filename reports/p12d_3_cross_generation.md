# P12D.3 — Cross-generation rule replication

## Alcance y protocolo

Se replicó exploratoriamente, sin repetir el GA, la regla congelada `training Profit Factor >= 1.05` y `training trades >= 100` sobre las 15 generaciones P09 (2019 Q2–2022 Q4). La elegibilidad usa exclusivamente las métricas del entrenamiento específico de cada generación. Cada generación tiene 1.000 carteras elegibles de cinco estrategias y 1.000 controles uniformes del universo completo; además se conservaron controles emparejados por actividad histórica y el benchmark descriptivo de los cinco finalistas P09.

- Política: `p12d-3-cross-generation-rule-replication-v1`; SHA256 de configuración: `55b95145481e6d9fda50c3b09113f9176b6b2aa20a447c30552dcf7314cea044`.
- Generaciones: 15; registros de población elegible: 70,341.
- Filas de carteras: 90,030; trayectorias: 6,000.
- Costes: baseline y multiplicador ×2. Riesgo: 0.5% por operación y límite agregado 2.5%, con el motor de cartera congelado.
- Holdout: no utilizado; el acceso se limitó a procedure_validation (2019–2022). No hubo operaciones reales.

La unidad de replicación interpretativa es la generación/trimestre. Las 1.000 carteras dentro de una generación no son experimentos independientes: comparten mercado, población y estrategias. Las trayectorias también comparten componentes entre réplicas.

## Elegibilidad por generación

| Generación | Población | Elegibles | % | Universo actividad (n≥100) | Insuficiente |
|---|---:|---:|---:|---:|---:|
| 2019Q2 | 100,000 | 7,136 | 7.14% | 57,115 | no |
| 2019Q3 | 100,000 | 8,350 | 8.35% | 57,305 | no |
| 2019Q4 | 100,000 | 5,849 | 5.85% | 46,894 | no |
| 2020Q1 | 100,000 | 6,449 | 6.45% | 48,164 | no |
| 2020Q2 | 100,000 | 6,499 | 6.50% | 50,850 | no |
| 2020Q3 | 100,000 | 3,688 | 3.69% | 50,383 | no |
| 2020Q4 | 100,000 | 2,929 | 2.93% | 49,665 | no |
| 2021Q1 | 100,000 | 4,627 | 4.63% | 47,703 | no |
| 2021Q2 | 100,000 | 5,425 | 5.42% | 52,012 | no |
| 2021Q3 | 100,000 | 5,581 | 5.58% | 49,614 | no |
| 2021Q4 | 100,000 | 3,117 | 3.12% | 50,348 | no |
| 2022Q1 | 100,000 | 1,789 | 1.79% | 47,971 | no |
| 2022Q2 | 100,000 | 4,161 | 4.16% | 48,451 | no |
| 2022Q3 | 100,000 | 2,723 | 2.72% | 50,158 | no |
| 2022Q4 | 100,000 | 2,018 | 2.02% | 47,184 | no |

## Ventanas exactas y hashes de entrada

| Generación | Training | Development | Forward | Hash P12C combinado |
|---|---|---|---|---|
| 2019Q2 | 2009-04-01 ≤ t < 2017-04-01 | 2017-04-01 ≤ t < 2019-04-01 | 2019-04-01 ≤ t < 2019-07-01 | `51feedc3993bcf53b6d14ec751dbad3f9fce96eb68a328dea7f6c6728a87386d` |
| 2019Q3 | 2009-07-01 ≤ t < 2017-07-01 | 2017-07-01 ≤ t < 2019-07-01 | 2019-07-01 ≤ t < 2019-10-01 | `da6cbfd265a691f63d84441a9dfec30194acfe9458a7739f2abfd39381a86c1e` |
| 2019Q4 | 2009-10-01 ≤ t < 2017-10-01 | 2017-10-01 ≤ t < 2019-10-01 | 2019-10-01 ≤ t < 2020-01-01 | `d13223c07a58b3d45a3468ca736ea457d47ab302750583bd252800b1f1e364ad` |
| 2020Q1 | 2010-01-01 ≤ t < 2018-01-01 | 2018-01-01 ≤ t < 2020-01-01 | 2020-01-01 ≤ t < 2020-04-01 | `5bf63129bd09f5f18451688e44c085124e9d485f9948492e149f86cd405b1aff` |
| 2020Q2 | 2010-04-01 ≤ t < 2018-04-01 | 2018-04-01 ≤ t < 2020-04-01 | 2020-04-01 ≤ t < 2020-07-01 | `19cc6ec266b56402170592543784b035b01c86518eade579fdafb099e1952726` |
| 2020Q3 | 2010-07-01 ≤ t < 2018-07-01 | 2018-07-01 ≤ t < 2020-07-01 | 2020-07-01 ≤ t < 2020-10-01 | `53d533a6971d5cb986d8bbd1d307aee9dc111856c1bbe2ef2b074b17524b864e` |
| 2020Q4 | 2010-10-01 ≤ t < 2018-10-01 | 2018-10-01 ≤ t < 2020-10-01 | 2020-10-01 ≤ t < 2021-01-01 | `04319b0773cfcd39b79944490e4be5302211081eb42c6296017c4b2667b6fb74` |
| 2021Q1 | 2011-01-01 ≤ t < 2019-01-01 | 2019-01-01 ≤ t < 2021-01-01 | 2021-01-01 ≤ t < 2021-04-01 | `838b7fc887892c25f7a8467d8cb1727f5ec998a820d8544fb7c4bcb4d1fe6ff4` |
| 2021Q2 | 2011-04-01 ≤ t < 2019-04-01 | 2019-04-01 ≤ t < 2021-04-01 | 2021-04-01 ≤ t < 2021-07-01 | `eac6f89c50394a473af9dfb006eaa8a06aba05abf6dcabf3c40c77ffa1ea1dd9` |
| 2021Q3 | 2011-07-01 ≤ t < 2019-07-01 | 2019-07-01 ≤ t < 2021-07-01 | 2021-07-01 ≤ t < 2021-10-01 | `67ca309d1227b65485401235edd452e73d0b4344c4c81f72a4a5db765beaf1bd` |
| 2021Q4 | 2011-10-01 ≤ t < 2019-10-01 | 2019-10-01 ≤ t < 2021-10-01 | 2021-10-01 ≤ t < 2022-01-01 | `bb63249e6aa92bd4b960020c868363797982da872225bf70b194d7c679f38b8d` |
| 2022Q1 | 2012-01-01 ≤ t < 2020-01-01 | 2020-01-01 ≤ t < 2022-01-01 | 2022-01-01 ≤ t < 2022-04-01 | `613a4113e1b9832c85ad419a12f3549904212f47e208d64b929456bf06ea96e3` |
| 2022Q2 | 2012-04-01 ≤ t < 2020-04-01 | 2020-04-01 ≤ t < 2022-04-01 | 2022-04-01 ≤ t < 2022-07-01 | `c7fc88f4f44c109dece2279f6b503706cd4cbceb6c240173f6f860e3e95fb041` |
| 2022Q3 | 2012-07-01 ≤ t < 2020-07-01 | 2020-07-01 ≤ t < 2022-07-01 | 2022-07-01 ≤ t < 2022-10-01 | `3458b4e344df1aedbcc6833472ee2f7d8bc0ede215a1ec5954ea00a7c0a1d2a9` |
| 2022Q4 | 2012-10-01 ≤ t < 2020-10-01 | 2020-10-01 ≤ t < 2022-10-01 | 2022-10-01 ≤ t < 2023-01-01 | `f3710ace0cb451b7eaaacbf9c78d7c986e14f9e589200035f2922deded1fc3c3` |
Cada generación conserva 20 partes P12C; los hashes se calculan sobre nombre y bytes de todas sus partes ordenadas. Los hashes canónicos de los 15 archivos GA están en `manifest.json`.

Todas las generaciones que entraron en el muestreo tenían al menos cinco elegibles; no se completó ninguna cartera artificialmente.

## Resumen de carteras por generación

| Generación | Grupo | Coste | Mediana retorno | P05–P95 | % positivas | Exp. R media | MaxDD medio | Operaciones medias |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 2019Q2 | activity_matched | baseline | -18.88% | -35.70%–-6.09% | 0.40% | -0.1706 | 21.84% | 262.5 |
| 2019Q2 | eligible | baseline | -8.57% | -18.22%–-0.70% | 4.10% | -0.2674 | 10.95% | 69.6 |
| 2019Q2 | full_random | baseline | -10.02% | -27.82%–0.00% | 4.50% | -0.1755 | 13.41% | 147.1 |
| 2019Q2 | activity_matched | costs_x2 | -28.68% | -52.60%–-11.16% | 0.00% | -0.2826 | 31.43% | 262.5 |
| 2019Q2 | eligible | costs_x2 | -11.21% | -22.02%–-2.90% | 1.70% | -0.3569 | 13.15% | 69.6 |
| 2019Q2 | full_random | costs_x2 | -16.02% | -40.85%–-0.94% | 1.60% | -0.2833 | 19.12% | 147.1 |
| 2019Q3 | activity_matched | baseline | -1.38% | -22.83%–17.29% | 44.80% | -0.0060 | 14.01% | 270.8 |
| 2019Q3 | eligible | baseline | 2.84% | -5.54%–14.23% | 69.10% | 0.0904 | 5.20% | 61.7 |
| 2019Q3 | full_random | baseline | -0.20% | -18.05%–12.24% | 47.70% | 0.0017 | 9.31% | 153.1 |
| 2019Q3 | activity_matched | costs_x2 | -13.21% | -43.72%–5.21% | 12.50% | -0.1177 | 21.92% | 270.8 |
| 2019Q3 | eligible | costs_x2 | 0.38% | -8.46%–10.41% | 52.60% | 0.0048 | 6.11% | 61.7 |
| 2019Q3 | full_random | costs_x2 | -6.40% | -31.89%–5.29% | 21.60% | -0.1078 | 13.92% | 153.1 |
| 2019Q4 | activity_matched | baseline | -19.15% | -38.09%–-5.99% | 0.40% | -0.1883 | 21.84% | 248.7 |
| 2019Q4 | eligible | baseline | -7.96% | -15.04%–-2.31% | 1.10% | -0.2658 | 8.91% | 64.1 |
| 2019Q4 | full_random | baseline | -8.54% | -27.53%–0.15% | 5.50% | -0.1999 | 11.69% | 116.9 |
| 2019Q4 | activity_matched | costs_x2 | -29.59% | -54.15%–-12.56% | 0.00% | -0.3138 | 32.02% | 248.7 |
| 2019Q4 | eligible | costs_x2 | -11.10% | -18.62%–-5.05% | 0.10% | -0.3745 | 11.42% | 64.1 |
| 2019Q4 | full_random | costs_x2 | -13.56% | -40.40%–-0.02% | 2.50% | -0.3208 | 16.80% | 116.9 |
| 2020Q1 | activity_matched | baseline | 0.34% | -21.10%–17.49% | 51.60% | 0.0047 | 13.09% | 257.5 |
| 2020Q1 | eligible | baseline | 7.95% | -2.26%–18.83% | 89.50% | 0.1667 | 4.74% | 98.9 |
| 2020Q1 | full_random | baseline | 0.39% | -16.56%–12.14% | 53.10% | 0.0192 | 7.93% | 119.7 |
| 2020Q1 | activity_matched | costs_x2 | -9.06% | -35.80%–8.01% | 19.00% | -0.0833 | 18.07% | 257.5 |
| 2020Q1 | eligible | costs_x2 | 3.47% | -6.27%–13.20% | 72.90% | 0.0805 | 5.62% | 98.9 |
| 2020Q1 | full_random | costs_x2 | -3.07% | -26.75%–6.78% | 30.10% | -0.0660 | 10.19% | 119.7 |
| 2020Q2 | activity_matched | baseline | -12.62% | -26.67%–-0.20% | 4.70% | -0.1185 | 16.69% | 242.5 |
| 2020Q2 | eligible | baseline | -13.41% | -21.12%–-3.22% | 1.60% | -0.4311 | 15.37% | 64.4 |
| 2020Q2 | full_random | baseline | -6.36% | -19.10%–1.98% | 11.70% | -0.1359 | 10.20% | 128.7 |
| 2020Q2 | activity_matched | costs_x2 | -18.47% | -36.49%–-4.87% | 1.60% | -0.1840 | 21.92% | 242.5 |
| 2020Q2 | eligible | costs_x2 | -15.02% | -22.91%–-4.29% | 0.70% | -0.4872 | 16.72% | 64.4 |
| 2020Q2 | full_random | costs_x2 | -9.50% | -27.21%–0.12% | 5.40% | -0.1987 | 13.05% | 128.7 |
| 2020Q3 | activity_matched | baseline | -10.20% | -28.87%–5.54% | 15.50% | -0.0877 | 16.59% | 263.0 |
| 2020Q3 | eligible | baseline | -3.31% | -10.20%–4.65% | 22.20% | -0.1426 | 6.63% | 48.8 |
| 2020Q3 | full_random | baseline | -3.52% | -22.36%–5.18% | 25.20% | -0.0941 | 9.96% | 130.9 |
| 2020Q3 | activity_matched | costs_x2 | -17.40% | -40.22%–-1.26% | 4.00% | -0.1575 | 21.95% | 263.0 |
| 2020Q3 | eligible | costs_x2 | -4.56% | -11.68%–3.07% | 16.50% | -0.1984 | 7.38% | 48.8 |
| 2020Q3 | full_random | costs_x2 | -6.78% | -30.60%–2.61% | 13.00% | -0.1611 | 12.58% | 130.9 |
| 2020Q4 | activity_matched | baseline | 0.86% | -17.43%–16.75% | 53.30% | 0.0169 | 12.89% | 258.9 |
| 2020Q4 | eligible | baseline | 4.74% | -3.78%–14.31% | 81.90% | 0.1792 | 4.55% | 58.6 |
| 2020Q4 | full_random | baseline | 0.43% | -12.86%–11.48% | 53.10% | 0.0411 | 7.78% | 128.8 |
| 2020Q4 | activity_matched | costs_x2 | -8.93% | -31.89%–7.61% | 19.40% | -0.0685 | 17.50% | 258.9 |
| 2020Q4 | eligible | costs_x2 | 2.77% | -5.83%–11.76% | 70.50% | 0.1113 | 5.17% | 58.6 |
| 2020Q4 | full_random | costs_x2 | -2.85% | -22.76%–6.42% | 31.70% | -0.0410 | 10.20% | 128.8 |
| 2021Q1 | activity_matched | baseline | -5.09% | -22.43%–10.22% | 29.40% | -0.0349 | 12.99% | 262.0 |
| 2021Q1 | eligible | baseline | 4.05% | -3.30%–11.79% | 82.80% | 0.1163 | 4.69% | 69.4 |
| 2021Q1 | full_random | baseline | -1.09% | -15.36%–8.04% | 39.80% | -0.0168 | 7.43% | 122.8 |
| 2021Q1 | activity_matched | costs_x2 | -13.47% | -36.03%–2.51% | 9.90% | -0.1128 | 18.91% | 262.0 |
| 2021Q1 | eligible | costs_x2 | 1.80% | -5.35%–8.61% | 66.40% | 0.0497 | 5.36% | 69.4 |
| 2021Q1 | full_random | costs_x2 | -4.32% | -24.63%–4.66% | 22.00% | -0.0915 | 10.20% | 122.8 |
| 2021Q2 | activity_matched | baseline | -12.96% | -27.16%–-1.61% | 2.90% | -0.1193 | 18.43% | 241.1 |
| 2021Q2 | eligible | baseline | -3.31% | -9.57%–3.78% | 22.10% | -0.1395 | 7.30% | 49.6 |
| 2021Q2 | full_random | baseline | -5.72% | -20.15%–1.41% | 11.30% | -0.1136 | 10.94% | 126.5 |
| 2021Q2 | activity_matched | costs_x2 | -20.64% | -41.15%–-7.04% | 0.70% | -0.2096 | 25.16% | 241.1 |
| 2021Q2 | eligible | costs_x2 | -4.94% | -11.61%–1.94% | 11.50% | -0.2160 | 8.33% | 49.6 |
| 2021Q2 | full_random | costs_x2 | -10.06% | -32.08%–0.00% | 5.00% | -0.2020 | 14.67% | 126.5 |
| 2021Q3 | activity_matched | baseline | -10.52% | -34.16%–3.78% | 12.10% | -0.0937 | 17.49% | 261.6 |
| 2021Q3 | eligible | baseline | 3.73% | -3.17%–12.06% | 81.10% | 0.1056 | 6.50% | 79.3 |
| 2021Q3 | full_random | baseline | -4.23% | -23.44%–4.28% | 25.10% | -0.0840 | 10.51% | 135.9 |
| 2021Q3 | activity_matched | costs_x2 | -20.73% | -50.04%–-4.33% | 1.50% | -0.1978 | 26.08% | 261.6 |
| 2021Q3 | eligible | costs_x2 | 0.43% | -6.23%–8.11% | 55.40% | 0.0208 | 7.71% | 79.3 |
| 2021Q3 | full_random | costs_x2 | -9.40% | -36.84%–1.02% | 9.90% | -0.1863 | 15.18% | 135.9 |
| 2021Q4 | activity_matched | baseline | -12.25% | -31.02%–2.48% | 9.10% | -0.1052 | 18.04% | 274.3 |
| 2021Q4 | eligible | baseline | -0.46% | -7.05%–6.48% | 45.30% | 0.0004 | 5.12% | 47.8 |
| 2021Q4 | full_random | baseline | -5.34% | -20.90%–3.57% | 17.50% | -0.1101 | 10.48% | 137.4 |
| 2021Q4 | activity_matched | costs_x2 | -22.17% | -46.16%–-5.17% | 0.80% | -0.2030 | 26.25% | 274.3 |
| 2021Q4 | eligible | costs_x2 | -1.95% | -8.78%–4.81% | 31.80% | -0.0679 | 5.75% | 47.8 |
| 2021Q4 | full_random | costs_x2 | -9.98% | -32.99%–0.38% | 6.20% | -0.2016 | 14.63% | 137.4 |
| 2022Q1 | activity_matched | baseline | -19.30% | -39.23%–0.40% | 5.40% | -0.1550 | 22.67% | 276.5 |
| 2022Q1 | eligible | baseline | -3.02% | -10.27%–3.83% | 22.50% | -0.1386 | 6.20% | 44.0 |
| 2022Q1 | full_random | baseline | -7.35% | -27.27%–2.79% | 15.00% | -0.1380 | 12.13% | 130.9 |
| 2022Q1 | activity_matched | costs_x2 | -26.80% | -49.93%–-5.74% | 1.40% | -0.2313 | 28.76% | 276.5 |
| 2022Q1 | eligible | costs_x2 | -4.41% | -12.08%–2.69% | 15.40% | -0.2036 | 6.92% | 44.0 |
| 2022Q1 | full_random | costs_x2 | -10.62% | -35.82%–0.91% | 8.70% | -0.2105 | 15.22% | 130.9 |
| 2022Q2 | activity_matched | baseline | -7.65% | -25.22%–5.33% | 16.30% | -0.0640 | 14.42% | 277.7 |
| 2022Q2 | eligible | baseline | 4.18% | -2.20%–10.91% | 87.20% | 0.1207 | 5.76% | 68.2 |
| 2022Q2 | full_random | baseline | -3.11% | -18.03%–6.01% | 27.30% | -0.0540 | 8.69% | 135.6 |
| 2022Q2 | activity_matched | costs_x2 | -14.17% | -35.89%–-0.39% | 4.40% | -0.1239 | 19.59% | 277.7 |
| 2022Q2 | eligible | costs_x2 | 2.49% | -3.42%–8.88% | 76.80% | 0.0747 | 6.21% | 68.2 |
| 2022Q2 | full_random | costs_x2 | -5.99% | -25.80%–2.93% | 17.40% | -0.1108 | 11.16% | 135.6 |
| 2022Q3 | activity_matched | baseline | -3.78% | -21.92%–12.61% | 35.80% | -0.0237 | 13.61% | 275.0 |
| 2022Q3 | eligible | baseline | 4.17% | -4.01%–13.59% | 80.10% | 0.1839 | 4.41% | 46.1 |
| 2022Q3 | full_random | baseline | -0.59% | -15.35%–10.03% | 44.50% | 0.0105 | 8.23% | 134.1 |
| 2022Q3 | activity_matched | costs_x2 | -10.23% | -31.59%–5.99% | 15.60% | -0.0823 | 18.15% | 275.0 |
| 2022Q3 | eligible | costs_x2 | 3.20% | -4.98%–12.33% | 73.80% | 0.1388 | 4.77% | 46.1 |
| 2022Q3 | full_random | costs_x2 | -3.03% | -23.82%–6.55% | 31.00% | -0.0450 | 10.43% | 134.1 |
| 2022Q4 | activity_matched | baseline | -3.58% | -24.04%–15.65% | 37.50% | -0.0245 | 13.45% | 277.0 |
| 2022Q4 | eligible | baseline | 0.65% | -8.71%–9.14% | 55.20% | 0.0418 | 4.94% | 42.1 |
| 2022Q4 | full_random | baseline | -0.68% | -15.72%–11.10% | 44.60% | -0.0273 | 7.95% | 128.8 |
| 2022Q4 | activity_matched | costs_x2 | -10.14% | -33.58%–8.67% | 21.20% | -0.0774 | 17.37% | 277.0 |
| 2022Q4 | eligible | costs_x2 | -0.17% | -9.88%–7.88% | 48.10% | -0.0067 | 5.43% | 42.1 |
| 2022Q4 | full_random | costs_x2 | -3.26% | -22.75%–7.37% | 30.90% | -0.0795 | 9.81% | 128.8 |

## Comparación consolidada

### baseline

- Generaciones con al menos cinco elegibles: **15/15**.
- Mediana elegible positiva: **8/15**.
- Mediana elegible superior al control completo: **14/15**.
- Mediana de las medianas por generación: elegible **0.0065**, control completo **-0.0352**.
- Mediana de carteras rentables: elegible **55.20%**; control completo **25.20%**.

### costs_x2

- Generaciones con al menos cinco elegibles: **15/15**.
- Mediana elegible positiva: **7/15**.
- Mediana elegible superior al control completo: **14/15**.
- Mediana de las medianas por generación: elegible **-0.0017**, control completo **-0.0678**.
- Mediana de carteras rentables: elegible **48.10%**; control completo **13.00%**.

## Trayectorias rolling

| Grupo | Coste | Mediana retorno acumulado | P05–P95 | % positivas | Mediana MaxDD |
|---|---|---:|---:|---:|---:|
| activity_matched | baseline | -81.07% | -91.51%–-60.65% | 0.00% | 77.98% |
| activity_matched | costs_x2 | -96.56% | -98.91%–-91.07% | 0.00% | 95.08% |
| eligible | baseline | -9.86% | -35.37%–22.63% | 28.50% | 21.63% |
| eligible | costs_x2 | -35.18% | -54.23%–-9.45% | 1.20% | 34.05% |
| full_random | baseline | -55.26% | -76.05%–-26.05% | 0.30% | 52.50% |
| full_random | costs_x2 | -80.65% | -92.72%–-61.75% | 0.00% | 76.83% |

## Actividad y dependencia

Las tablas individuales en `individual_by_generation.csv` separan población completa, elegible y no elegible, y conservan actividad, retorno y expectancy con ambos costes. Las firmas conductuales se usan sólo como diagnóstico: `dependence_by_generation.csv` muestra el número de firmas sobre el forward agregado de las elegibles y la concentración de la firma dominante; no se usaron para seleccionar componentes.

| Generación | Elegibles | Firmas | Duplicados | Mayor firma |
|---|---:|---:|---:|---:|
| 2019Q2 | 7,136 | 4,105 | 3,031 | 193 |
| 2019Q3 | 8,350 | 4,022 | 4,328 | 93 |
| 2019Q4 | 5,849 | 3,742 | 2,107 | 46 |
| 2020Q1 | 6,449 | 4,083 | 2,366 | 52 |
| 2020Q2 | 6,499 | 3,965 | 2,534 | 106 |
| 2020Q3 | 3,688 | 2,897 | 791 | 68 |
| 2020Q4 | 2,929 | 2,566 | 363 | 46 |
| 2021Q1 | 4,627 | 3,055 | 1,572 | 102 |
| 2021Q2 | 5,425 | 3,621 | 1,804 | 74 |
| 2021Q3 | 5,581 | 3,390 | 2,191 | 102 |
| 2021Q4 | 3,117 | 1,992 | 1,125 | 44 |
| 2022Q1 | 1,789 | 1,516 | 273 | 25 |
| 2022Q2 | 4,161 | 2,566 | 1,595 | 104 |
| 2022Q3 | 2,723 | 1,950 | 773 | 34 |
| 2022Q4 | 2,018 | 1,660 | 358 | 31 |

## Respuestas operativas

1. **Existencia:** la regla identifica al menos cinco estrategias en 15/15 generaciones; esto no implica que sean rentables.
2. **Enriquecimiento:** debe juzgarse comparando las medianas y fracciones positivas elegibles frente a `full_random` en la tabla y CSV; una ventaja en una sola métrica no se interpreta como edge.
3. **Carteras y costes:** la comparación baseline frente a ×2 y las trayectorias muestran si cualquier diferencia sobrevive a costes; ×2 es el análisis económico más exigente.
4. **Consistencia:** se reporta el recuento de generaciones donde la mediana elegible supera al control; no se promedian percentiles trimestrales para sustituir trayectorias.
5. **Dependencia:** la reutilización de estrategias, mercado y ventanas solapadas reduce el número efectivo de observaciones; los resultados son exploratorios.
6. **Interpretación:** la existencia de ganadoras individuales, el enriquecimiento de la población, la rentabilidad de carteras elegibles y la rentabilidad de trayectorias son afirmaciones distintas y se mantienen separadas.

## Trazabilidad y limitaciones

Los ledgers ricos se generaron causalmente con las definiciones archivadas y se guardaron por generación/coste para los componentes muestreados. Las estadísticas individuales de toda la población se reutilizan de P12C; no se presentan como nuevos backtests completos fuera de sus artefactos de origen. PF infinito por ausencia de pérdidas se conserva en los ledgers y se excluye de medias de PF cuando corresponde. La exposición y la prioridad de señales se calculan mediante el motor de cartera; no se suman retornos individuales.

Los artefactos incluyen composiciones, ledgers, resultados individuales, resultados de cartera, trayectorias, resúmenes, firmas, hashes de archivos GA y manifiesto. Cualquier diferencia material entre archivos de entrada y sus hashes debe invalidar la reproducción.
