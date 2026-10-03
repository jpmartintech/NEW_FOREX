# P05 EURUSD stress test

Run ID: `p05-eurusd-stress-v1-clean`

## Frozen inputs

- Consumed the frozen P03.1 manifest and all 25 Parquet ledgers from
  `runs/p02-p04-eurusd-real-100k-clean-final/p03.1_export/`.
- Every ledger SHA256 was checked against `finalist_manifest.json`.
- Strategy hashes were reconstructed from the manifest strategy payloads and
  checked before evaluation; GA and selection were not rerun.
- Data: EURUSD canonical M15, SHA256
  `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4`.
- Partition: `dev_train`, `[2003-01-01, 2015-01-01)`; final holdout unused.
- Scenario contract: `configs/stress.yaml`, version `p05-stress-v1`.

The original P03.1 manifest records its dataset hash as `unknown` because the
Parquet cache metadata was not propagated into pandas attributes. P05 therefore
cross-checks the canonical-cache metadata against the independently registered
EURUSD hash above and records the resolved hash in `p05_report.json`.

## Scenarios and aggregate results

Every row in the machine-readable report contains per-strategy Profit Factor,
mean R, cumulative return, maximum drawdown, trade count and deltas against
that strategy's baseline. The table shows medians across 25 strategies, with
the maximum drawdown and trade-count range also reported.

| Scenario | Median PF | Median mean R | Median return | Max DD | Trades range | Technical |
|---|---:|---:|---:|---:|---:|---|
| Baseline costs x1 | 1.5804 | 0.3754 | 0.2903 | 0.0866 | 106–221 | PASS |
| Costs x1.5 | 1.5303 | 0.3480 | 0.2664 | 0.0936 | 106–221 | PASS |
| Costs x2 | 1.4793 | 0.3123 | 0.2429 | 0.1005 | 106–221 | PASS |
| Variable adverse slippage | 1.4398 | 0.3004 | 0.2273 | 0.1029 | 106–221 | PASS |
| M15 delay 1 bar | 1.4577 | 0.2970 | 0.2221 | 0.1224 | 107–218 | PASS |
| M15 delay 2 bars | 1.3966 | 0.2778 | 0.1956 | 0.1262 | 106–217 | PASS |
| Controlled price perturbation | 1.5239 | 0.3545 | 0.2639 | 0.1149 | 106–220 | PASS |
| Combined: x2 + slippage + delay 2 | 1.0691 | 0.0565 | 0.0333 | 0.2067 | 106–217 | PASS |

M15 delays were applied inside the next H1 bar using the original M15 candle
arrays. Signals and features remained those of the frozen original market;
incomplete delayed fills were treated as unexecutable, not fabricated.

## Null-world interpretation

The P04 `positive_fraction = 1.0` is not an out-of-sample success rate. In
`run_null_worlds`, each null candidate receives one random zero-mean score;
selection then keeps the top-K candidates within each world. The reported
fraction is the share of those selected, selection-conditioned null scores that
are positive. It measures winner's-curse/selection bias in the training-style
control and contains no OOS performance measurement.

## Gate decision

All 200 scenario rows pass technical identity, ordering and backtester checks.
Performance acceptance is `NOT_EVALUATED_NO_PREESTABLISHED_P05_GATE`: the
repository defines no committed P05 thresholds for PF, mean R, drawdown,
return degradation or trade-count loss. Inventing thresholds after seeing
these results would be retrospective criterion tuning. Therefore P05 remains
blocked, no P05 tag is created, and P06 is not started.

Machine-readable evidence: `runs/p05-eurusd-stress-v1-clean/p05_report.json`.

## P05.1 acceptance policy

Repository review found no earlier P05 acceptance thresholds. The policy is
therefore versioned as `configs/stress_acceptance.yaml` (`p05-acceptance-v1`)
after this first P05 execution. It cannot certify this already observed
cohort as an independent validation result; its application here is
exploratory only. The policy uses arithmetic mean `result_R` for
`expectancy_net_R`, requires at least 100 trades for formal classifications,
and requires finite PF before applying the `PF > 1` delay-1 rule. Infinite PF
is never an automatic pass.

Exploratory classification of the existing 200 rows:

| Scenario | Policy mode | Result |
|---|---|---|
| Baseline x1 | formal, expectancy > 0 | 25 PASS |
| Costs x1.5 | diagnostic-only | 25 DIAGNOSTIC_ONLY |
| Costs x2 | formal, expectancy > 0 | 25 PASS |
| Variable adverse slippage | formal, expectancy > 0 | 25 PASS |
| M15 delay 1 | formal, finite PF > 1 | 25 PASS |
| M15 delay 2 | diagnostic-only | 25 DIAGNOSTIC_ONLY |
| Price perturbation | diagnostic-only | 25 DIAGNOSTIC_ONLY |
| Combined adverse | diagnostic-only | 25 DIAGNOSTIC_ONLY |

Machine-readable exploratory output:
`runs/p05-eurusd-stress-v1-clean/p05_acceptance_exploratory.json`.

## Independent application procedure

The frozen strategy manifest is reused without GA or selection. After the
policy is registered, run the same stress runner on one allowed independent
half-open split at a time, for example:

```bash
PYTHONPATH=src python scripts/run_p05_stress.py \
  --manifest runs/p02-p04-eurusd-real-100k-clean-final/p03.1_export/finalist_manifest.json \
  --output runs/p05-eurusd-development-wf \
  --start 2015-01-01 --end 2019-01-01
```

Then repeat separately for `[2019-01-01, 2023-01-01)` as
`procedure_validation`. The runner rejects the final holdout, performs no
selection, and preserves the same frozen strategy hashes and scenario policy.
Those independent runs have not been executed in P05.1.
