# Decisions

## 2026-10-02 — independent bootstrap

- NEW_FOREX is a new Git repository on `main`; the source repository is not modified.
- The source snapshot is imported at commit `40820a9e1c631b8cd3e894a89d39fb66c63ddf68`.
- The Python package is renamed from `sqxf` to `new_forex` so future changes are independently attributable.
- Data and holdout access remain outside P00. The existing sealed loader is retained and will be hardened under P01's explicit access-policy tests.
- The source snapshot contained no license or notice file; this absence is recorded in `docs/PROVENANCE.md` for review.

## 2026-10-02 — P01 access policy

- Split boundaries are configured as local, half-open intervals: DEV/TRAIN through 2014-12-31, development WF 2015–2018, procedure validation 2019–2022, and final holdout from 2023-01-01.
- A normal read must stay within one partition and final holdout remains sealed even when an ordinary `release_unlocked` boolean is passed. The explicit release manifest and unlock command belong to P09.
- P01 audits may record file metadata and checksums, but no implementation task may materialize or inspect 2023–2026 rows before the final release gate.
- The first real audit used streaming reads and stopped before the first holdout payload. Seven direct CSV series were found; `XAUUSD` is recorded but excluded from the configured FX universe. Partition hashes cover accessible raw lines only.
- Gap counts are diagnostics, not an implicit data-repair rule. The observed maximum 4335-minute FX gap is consistent with session/weekend boundaries but must be classified against the broker calendar before continuity is accepted.
- H1 derivation is causal: each bar contains only M15 rows in its own UTC hour, incomplete hours are retained as incomplete, empty hours are omitted, and closed-bar prefixes are invariant to future price changes.
- Gap diagnostics classify only the simple Friday-to-Monday transition as a weekend gap. The remaining gaps are retained as an explicit unresolved data-quality item; P01 cannot be declared complete until a broker session/holiday calendar explains them or they are documented as unavailable.
- P01 gate is accepted with those gaps documented as unavailable calendar semantics; no rows are repaired or silently discarded. Any later execution/stress gate must use the explicit gap diagnostics and cost assumptions.

## 2026-10-02 — P02 GA contract

- GA configuration is declarative in `configs/ga.yaml` with a hard maximum of 100,000 unique canonical-hash evaluations per run.
- Exceeding the cap is a configuration error. The archive remains keyed by canonical hash and deterministic for a fixed seed and fitness input.
- The 100,000-candidate benchmark is synthetic until P02's train-only run manifest is implemented; no holdout or procedure-validation data is used.
- The synthetic benchmark reached exactly 100,000 unique candidates in 23.313 seconds and reproduced the same archive-order SHA256 on an independent same-seed run. This proves capacity only, not strategy validity.
- P02 gate accepted after verifying train-window perturbation invariance in the existing GA tests, deterministic archive persistence, and the 100,000-candidate synthetic capacity run.

## 2026-10-02 — P03 selection contract

- Historical ranking is configured in `configs/selection.yaml`; top-K is provisional/configurable, not a magic constant.
- Candidate metrics are computed after a declared per-trade cost, then gated by minimum trades, positive net mean, and minimum profit factor before deterministic ranking.
- Duplicate canonical hashes are collapsed and every selection result carries input, duplicate, eligible and selected counts. Holdout data is not an input to this contract.
- Selection supports a declared `max_pair_fraction` cap and records concentration rejections, preventing a top-K list from silently becoming a single-pair portfolio.
- P03 audit artifacts persist run ID, predeclared config, data hashes, split hash, attrition counts and selected hashes; no candidate ledger is committed to Git.

## 2026-10-02 — P04 bootstrap contract

- Monte Carlo defaults to at least 5,000 seeded iterations and supports moving and stationary circular block bootstrap.
- Every run returns final equity, max drawdown, longest loss streak, ruin probability and DD/equity/streak quantiles. Monte Carlo robustness is not treated as predictive validity.
- The current implementation is a trade-series risk simulator; monthly/annual resampling and end-to-end GA null controls remain P04 work.
- Complete-period resampling is now available for monthly/annual labels; it samples whole observed groups and never shuffles within a period.
- The null-world control runs the same bounded GA and selection interfaces on zero-mean random scores, records the fraction of positive selected winners, and is explicitly interpreted as selection bias rather than predictive evidence.
- The preregistered null benchmark used 100×1,000 candidates and selected 50 per world; its 1.0 positive-selected fraction is preserved as a failure/control result, not tuned away.
