# P04 EURUSD real run

Run ID: `p02-p04-eurusd-real-100k-clean-final`

## Input and provenance

- Partition: `dev_train` only, `[2003-01-01, 2015-01-01)`, local EET.
- Input: `data/raw/EURUSD_15M.csv`, SHA256
  `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Code version: `0.1.0+cec14f5a22bb`.
- GA seed: `20261002`; archive SHA256:
  `8cdbd0b42f03588919b70489477369da30b850505804fdc7671de39f6cd89aa5`.
- P02: 100,000 unique evaluations; 100,000 unique archive rows.
- P03: 12,963 eligible candidates; 25 selected after the unchanged
  concentration rule (`max_pair_fraction=0.5`).
- P03.1: 25 finalist Parquet ledgers, 3,438 operations in total.

The smoke run also completed end to end before the full run: 125 evaluated,
14 selected, 14 ledgers exported, and all P04 methods executed.

## Monte Carlo policy and results

Risk policy: `p04-fixed-fractional-r-v1`; each input return is
`result_R * 0.005`; ruin floor is `0.5`; block length is `20`; each finalist
has 5,000 iterations.

The following are worst-case summaries across the 25 real finalists:

| Method | DD P95 max | DD P99 max | Loss streak P95 max | Final equity P05 min | Ruin probability max |
|---|---:|---:|---:|---:|---:|
| Moving bootstrap | 0.13654 | 0.16631 | 18 | 0.91228 | 0.0 |
| Stationary bootstrap | 0.08657 | 0.11440 | 15 | 1.13897 | 0.0 |
| Temporal-period blocks | 0.19669 | 0.23865 | 19 | 0.84990 | 0.0 |

Null-world control: 100 worlds x 1,000 candidates, 5,000 selected, positive
selected fraction `1.0`. This is recorded as a selection-bias warning, not as
evidence of predictive validity.

The complete machine-readable evidence is in the ignored run directory
`runs/p02-p04-eurusd-real-100k-clean-final/`, including the finalist manifest,
selection audit, 25 ledgers and `p04_report.json`. Repeating the same GA seed
and configuration produced a byte-identical archive.

No procedure-validation or final-holdout rows were loaded, and no real orders
were placed. P05 is not started.
