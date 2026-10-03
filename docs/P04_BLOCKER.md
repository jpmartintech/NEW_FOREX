# P04 blocker: resolved by real EURUSD finalist export

Audit run: `p04-finalist-ledger-audit-20261002T211152Z`

The original blocker was that the checkout contained no real P03 finalist
artifact or operation ledger. It was resolved by the real EURUSD run
`p02-p04-eurusd-real-100k-clean-final`; the evidence is summarized in
`reports/p04_eurusd_real_100k.md` and retained under the ignored `runs/`
directory. The tracked
candidate-related inventory is limited to:

- `reports/p02_ga_100k.md` (capacity benchmark, explicitly not a selection run)
- `reports/p04_null_world.md` (null-world control)
- `reports/.gitkeep`

There is no P03 selection audit, finalist manifest, canonical strategy JSON,
or finalist trade ledger under tracked `reports/`, `runs/`, `trials/`, or
`data/` paths. The local `trials/*.jsonl` files are inherited evaluation
ledgers, not P03 strategy-operation ledgers, and are not used as a substitute.
No synthetic operations were created.

P03.1 now provides the export contract in
`src/new_forex/selection/export.py`. It calls `evaluate_rich` for each
selected `StrategyDefinition`, writes `finalist_manifest.json`,
`selection_audit.jsonl`, and one Parquet ledger per hash, and rejects holdout
ranges before evaluation. Its contract tests pass, but it has not emitted a
real finalist artifact because the required inputs are absent.

## Required P03 handoff

P03 must produce an immutable, pre-holdout finalist manifest containing at
least `canonical_hash`, strategy definition/parameters, pair, selection
metrics, source run ID, data partition, and config/code/data hashes. For each
finalist it must also provide the complete DEV/TRAIN operation series with:

`timestamp`, `symbol`, `direction`, `entry`, `exit`, `net_r`, `costs`, and
`canonical_hash`.

The existing backtest path is the intended source: `evaluate_rich(...).trades`
returns `entry_time`, `exit_bar_time`, `entry_price`, `exit_price`, `reason`,
`r`, and execution fields. Its `r` value already includes the evaluator's
cost/funding adjustment; P04 must not subtract costs a second time. The
adapter must preserve the finalist hash and symbol/direction metadata and
must reject any partition outside DEV/TRAIN before Monte Carlo execution.

## Required P04 execution after the handoff

Using only the handed-off ledgers, run the configured 5,000+ seeded iterations
per finalist with the versioned risk policy in `configs/mc.yaml`, then record
the configuration hash, seed, code SHA, split/data hashes, finalist hash, and
results for:

1. moving bootstrap;
2. stationary bootstrap;
3. complete temporal-period block bootstrap; and
4. matched null-world controls.

The required result fields are return/final-equity quantiles, drawdown
P50/P95/P99, longest-loss-streak distribution, and probability of breaching
the configured ruin floor. Until the manifest and real ledgers exist, running
these calculations would either fabricate trades or reuse unrelated ledgers,
so neither is permitted.

## P03.1 execution result

The deterministic regeneration check is now satisfied for EURUSD: the
100,000-row archive SHA256 is stable across repeated same-seed executions,
25 finalists have real backtester ledgers, and 3,438 operations pass the
export validations. The first real run is restricted to DEV/TRAIN and does
not imply validity for other symbols or later partitions.

## Holdout and gate decision

This audit did not unlock, read, or use final-holdout rows. P04 has passed for
the recorded EURUSD DEV/TRAIN run; P05 is not started until the final
regression and P04 commit/tag are complete.
