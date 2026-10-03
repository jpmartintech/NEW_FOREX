NEW_FOREX — Master build loop
Source: https://github.com/jpmartintech/SQX_CLAUDE_FOREX
Mission
Build a Git-versioned, executable FOREX strategy factory. GA produces up to 100,000 unique candidates per run, no economic hypothesis required. Historical selection → Monte Carlo → operational stress → frozen strategy walk-forward → one-time final holdout → unchanged deployment. No claims of guaranteed future returns.
Time policy (inclusive start, exclusive end)
Data must be audited first: available symbols, source, timezone, M15 continuity, bid/ask or cost model, spread, rollover, DST, missing periods, outliers, and last available candle. Derive H1 causally from M15. Do not fabricate missing data. Record manifest + SHA256 per symbol and partition. Warm-up context before boundaries is allowed for indicators, never for scoring, optimization, labels, or trade P&L; purge trades crossing boundaries, or use an explicitly preregistered deterministic liquidation rule.
DEV/TRAIN: [2003-01-01, 2015-01-01): GA generation, initial ranking and exploratory stress/MC. Training-only decisions.
DEVELOPMENT WF: [2015-01-01, 2019-01-01): four 12-month frozen OOS tests. Each fold uses all preceding available history as train; re-run complete selection process at each fold, freeze strategies before next year. In addition, track strategies selected at 2014-12-31 without changes through 2015–2018. A fold's OOS results may be incorporated only into later chronological folds, never its own training.
PROCEDURE VALIDATION: [2019-01-01, 2023-01-01): four annual forward folds of fully frozen pipeline, selection criteria, risk model and execution settings. Do not tune using results in this block. If it fails, version the pipeline and designate new future unseen data for the final test; do not repeatedly mine the same years.
FINAL HOLDOUT: [2023-01-01, last_available_timestamp+1 candle): sealed until code, thresholds, strategy selection and portfolio weights are committed/tagged. 2026 is partial. Run once, report ALL results and failures. Do not use holdout to choose strategies, weights or thresholds. If revising after final holdout, new untouched future data is required.
Important distinction: the proposed development WF uses future data from 2015–2018 to choose the procedure, but never tunes an individual candidate on its own test fold. Procedure validation 2019–2022 and final 2023–2026 stay sealed until their gates.
Pipeline
GA: 100,000 unique canonical strategy evaluations per run; deterministic seed, archive, canonical hash, manifest; only TRAIN accessible.
Initial ranking: preregister minimum trades, net positive expectancy, PF, DD, trade frequency, concentration and deduplication. Retain top-K configurable (e.g. 50) as a provisional setting, not a magic threshold. Never rank using downstream holdouts.
Monte Carlo: trade bootstrap (conditional on dependence), moving/stationary block bootstrap, monthly/annual block resampling; 5k+ reproducible iterations; DD P50/P95/P99, longest loss streak, final equity, return quantiles, probability of breaching account constraints. Bootstrap of selected trades does not correct GA selection bias; separately run matched null-world end-to-end GA + selection to estimate false discovery.
Stress: costs x1/x1.5/x2, realistic variable spread, slippage, latency 1–2 bars, price perturbation, missed fills, symbol-specific swap/rollover and execution constraints. Perturbations must preserve causal order. Reject unexecutable candidates.
WF: selection on prior history only; freeze candidate canonical JSON, params, hash, risk, execution, then replay next chronological OOS year. Log complete candidate attrition and all OOS trades. No parameter reoptimization on its own OOS.
Procedure validation and final holdout: thresholds frozen beforehand, pass/fail per strategy and at portfolio level, multiple-comparison and selection accounting, realistic net costs and sufficient trades. Final holdout read gate requires approved frozen release manifest + explicit unlock command. Never silently unlock.
Deployment: deterministic export of ORIGINAL strategy rules, versioned executable, parity tests vs reference backtester, independent risk caps and kill switch; paper/forward before live. Strategy modifications produce new ID and restart validation.
Repo structure
NEW_FOREX/
README.md, pyproject.toml, .gitignore, .env.example, LICENSE (preserve original obligations)
AGENTS.md, CLAUDE.md, AUTONOMY.md, DECISIONS.md, CHANGELOG.md
configs/{data,splits,ga,selection,mc,stress,wf,validation,portfolio,deployment}.yaml
src/new_forex/{data,features,grammar,ga,backtest,selection,monte_carlo,stress,walk_forward,validation,portfolio,export,cli,ledger}/
tests/{unit,integration,parity,leakage,smoke}/
docs/{MASTER_PLAN,PROGRESS,PHASES,DATA_MANIFEST,VALIDATION_POLICY,DEPLOYMENT_POLICY}.md
reports/.gitkeep
scripts/{bootstrap,smoke,run_phase}.sh
data/{raw,canonical,derived,holdout}/ (gitignored; only manifests/checksums tracked)
runs/ (gitignored for heavy outputs; small summaries and run manifests tracked)
Git rules
New repository, not rename of the original. Record source URL and exact base commit in docs/PROVENANCE.md; retain notices and compatible license terms.
Do not commit datasets, API keys, .env, virtualenv, Parquet, trade ledgers or large models. Commit configs, seeds, code, lockfile, checksums, manifests, small reproducible reports.
main always green. Branch `phase/NN-name`, tests then PR/merge. Conventional commits `feat(pNN): ...`, `test(pNN): ...`, `docs(pNN): ...`; tag `v0.N-phase`. Record current commit, command, test count, artifacts, next task in docs/PROGRESS.md.
Every run has immutable run_id, git SHA, data hashes, split hash, config hash, code version, random seed, selection counts, time/cost metrics and errors. Append-only ledger.
Autonomous execution loop
Read MASTER_PLAN, AGENTS.md, PROGRESS.md, DECISIONS.md and latest git status. Choose the FIRST incomplete phase; do only that phase's smallest testable task. Write acceptance tests BEFORE implementation. Implement, run `ruff check .` and `pytest -q`, plus phase-specific integration/smoke. Verify chronological no-leakage and deterministic rerun when relevant. On fail: repair and rerun; never relax validation thresholds to get a PASS. Update docs/PROGRESS.md and DECISIONS.md (if a design change), commit, tag at phase gate, and output SHA, tests, evidence, runtime, blocker, next task. Repeat until all phase gates are complete or a genuine external blocker arises. Never access final holdout before explicit release gate. Never push or deploy real orders without explicit user authorization.
Phases and acceptance gates
P00 Bootstrap: create NEW_FOREX from original source, preserve provenance/license, imports renamed, clean env, CI, baseline tests green.
P01 Data: ingest user's 2003–2026 FX files, detect actual date range, timestamp consistency, duplicates/gaps, symbol specs, M15→H1 parity; immutable partitions and locked holdout. No raw data committed.
P02 GA: 100k unique candidate cap, seed reproducibility, no forbidden period access, canonical hash and archive; baseline benchmark.
P03 Selection: metrics net of costs, configurable predeclared top-K, trade minimum, duplicate filtering, selection audit.
P04 MC: 5k+ seeded iterations per finalist, block bootstrap, DD/streak/ruin distributions, calibration tests on synthetic data.
P05 Stress: x2 costs, variable spreads/slippage/delays/missed fills, parity and no lookahead.
P06 WF: 2015/16/17/18 annual frozen folds, full factory rerun and fixed 2014 cohort, year-by-year and aggregate reports; test that modifying OOS cannot alter prior selections.
P07 Procedure validation: lock pipeline and run 2019–2022 annual folds ONCE; explicit go/no-go based on precommitted objective metrics.
P08 Portfolio: dedup, correlation/overlap, weights using only allowed training/WF history; freeze risk and weights before final gate. If procedure validation has already been opened, do not retune using its results.
P09 Final holdout: tag release, unlock 2023–last available candle ONCE, immutable result with all candidates, portfolio and stress, no iterative retuning.
P10 Deployment: original canonical strategies, code/backtest parity, paper-forward, risk cap, kill switch, operator checklist; live execution separately authorized.
Critical guardrails
Do not equate Monte Carlo robustness with predictive validity.
Selection among 100k introduces winner's curse: preserve all trial counts and use end-to-end null controls.
Realistic FOREX costs and overnight financing vary by pair, date and broker; state assumptions if historical spread/swap unavailable.
Do not choose or revise pass thresholds after viewing the target partition.
Never use 2023–2026 data for feature selection, GA, model/threshold calibration, portfolio weights or debugging until final release.
Results may be negative. Preserve and report failures. No invented positive performance.
