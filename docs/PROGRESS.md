# Progress

## Current gate

- Phase: P12F high historical quality and immediate forward efficiency
- Status: complete; protocol frozen before evaluation, 100,000 individuals and 4,000 five-strategy portfolios evaluated on 2017Q1 only, holdout sealed
- Final holdout: sealed; no unlock command has been used
- Real operations: not configured or authorized

## Evidence

- Source baseline: `ruff check .` passed; `178 passed in 328.23s` on the source snapshot.
- Source commit: `40820a9e1c631b8cd3e894a89d39fb66c63ddf68`
- NEW_FOREX run ID: `p00-bootstrap-20261002T162128Z-40820a9`
- P01 slice run ID: `p01-access-policy-20261002T162128Z-40820a9`
- P01 audit run ID: `p01-data-audit-20261002T162128Z-40820a9`
- P01 H1 run ID: `p01-h1-causality-20261002T162128Z-40820a9`
- P01 continuity run ID: `p01-continuity-20261002T162128Z-40820a9`
- P01 cache run ID: `p01-cache-20261002T162128Z-40820a9`
- P02 contract run ID: `p02-ga-contract-20261002T162128Z-40820a9`
- P02 benchmark run ID: `p02-ga-100k-20261002T162128Z`
- P03 contract run ID: `p03-selection-contract-20261002T162128Z`
- P03 concentration run ID: `p03-selection-concentration-20261002T162128Z`
- P03 audit run ID: `p03-selection-audit-20261002T162128Z`
- P04 bootstrap run ID: `p04-bootstrap-contract-20261002T162128Z`
- P04 period-block run ID: `p04-period-block-20261002T162128Z`
- P04 null-world run ID: `p04-null-world-20261002T162128Z`
- P04 null-world benchmark: 100 worlds × 1,000 candidates, 5,000 selected, positive-selected fraction `1.0`.
- P00 acceptance: `ruff check .` passed; `173 passed, 8 skipped in 178.78s`.
- P01 slice acceptance: `ruff check .` passed; `177 passed, 8 skipped in 177.75s`.
- P01 audit slice acceptance: `ruff check .` passed; `181 passed, 8 skipped in 175.57s`.
- P01 H1 slice acceptance: `ruff check .` passed; `183 passed, 8 skipped in 179.65s`.
- P01 continuity acceptance: `ruff check .` passed; `183 passed, 8 skipped in 178.47s`.
- P01 cache acceptance: `ruff check .` passed; `184 passed, 8 skipped in 178.32s`.
- P02 contract acceptance: `ruff check .` passed; `187 passed, 8 skipped in 178.98s`.
- P02 benchmark evidence: `reports/p02_ga_100k.md`; 100,000 unique evaluations in 23.313 s with identical same-seed archive SHA256.
- P03 contract acceptance: `ruff check .` passed; `191 passed, 8 skipped in 180.68s`.
- P03 concentration acceptance: `ruff check .` passed; `192 passed, 8 skipped in 180.57s`.
- P03 audit acceptance: `ruff check .` passed; `193 passed, 8 skipped in 176.64s`.
- P04 bootstrap acceptance: `ruff check .` passed; `196 passed, 8 skipped in 179.24s`.
- P04 period-block acceptance: `ruff check .` passed; `198 passed, 8 skipped in 183.58s`.
- P04 null-world acceptance: `ruff check .` passed; `199 passed, 8 skipped in 181.14s`.
- P04 null-world final regression: `ruff check .` passed; `199 passed, 8 skipped in 184.34s`.
- P04 finalist-ledger audit: `p04-finalist-ledger-audit-20261002T211152Z`; no tracked P03 selection audit, finalist manifest, or real finalist operation ledger exists. See `docs/P04_BLOCKER.md`.
- P03.1 export attempt: contract implemented and tested, but zero finalists exported: no `data/raw` bars, P02 GA archive, or P03 selection audit/candidate archive is present. Deterministic regeneration is impossible from `configs/ga.yaml` alone; see `docs/P04_BLOCKER.md`.
- P03.1/P04 real smoke: `runs/p03.1-smoke-eurusd`; 125 evaluated, 14 selected, 14 real ledgers, 5,000 iterations per finalist, null-world smoke passed.
- P02–P04 real EURUSD: `runs/p02-p04-eurusd-real-100k-clean-final`; 100,000 evaluated, 25 selected, 25 real ledgers, 3,438 operations, 5,000 iterations per finalist for moving/stationary/period-block methods, and 100 x 1,000 null-world control. See `reports/p04_eurusd_real_100k.md`.
- P04 real reproducibility: archive SHA256 `8cdbd0b42f03588919b70489477369da30b850505804fdc7671de39f6cd89aa5`; repeated same-seed archive was byte-identical.
- P05 stress run: `runs/p05-eurusd-stress-v1-clean`; 25 frozen finalists × 8 scenarios = 200 rows, all technical checks passed. See `reports/p05_eurusd_stress.md`.
- P05 scenario contract: `configs/stress.yaml`, version `p05-stress-v1`, committed before evaluation. Performance acceptance is blocked because no prior P05 thresholds exist; no retrospective threshold was invented.
- P05.1 acceptance policy: `configs/stress_acceptance.yaml`, version `p05-acceptance-v1`, committed after the first P05 run and explicitly prohibited from certifying that cohort retrospectively. Exploratory output: `runs/p05-eurusd-stress-v1-clean/p05_acceptance_exploratory.json`; 25 PASS for baseline, cost x2, variable slippage and delay-1, with the remaining scenarios diagnostic-only.
- P05.1 independent procedure prepared for `development_wf` and `procedure_validation` using the frozen manifest, no selection and no holdout access; those runs are not yet executed.
- P06 criteria audit: `p06-criteria-audit-20261002T224744Z`; the pre-run audit found no applicable gate and blocked OOS until policy freeze. See `docs/P06_BLOCKER.md` and `reports/p06_eurusd_wf.md`.
- P06 policy freeze: `6c52227`; `configs/wf_acceptance.yaml`, SHA256 `c62cf8368dcdf40fb183f6b8158ac5ade1b3c77e9941bfceb05d5405636f412c`.
- P06 frozen walk-forward: `runs/p06-eurusd-frozen-wf-v1`; 25 strategies, WF1–WF4 2015–2018, zero rows `>=2019-01-01`, 1 survivor, 24 rejected. See `reports/p06_eurusd_wf.md`.
- P07 policy freeze: `a23ced5`; `configs/procedure_validation.yaml`, SHA256 `7c6545eb453f69cf3de61456abad3fe00a373eef05a42ee46cf918f7d8a0c807`.
- P07 procedure validation: `runs/p07-eurusd-procedure-validation-v1`; 57 trades over 2019–2022, zero rows `>=2023-01-01`, decision `FAIL` for expectancy, PF, positive years and costs ×2. See `reports/p07_eurusd_validation.md`.
- P07A lifetime analysis: `reports/p07a_eurusd_lifetime.md` and `reports/p07a_artifacts/`; 57 chronological operations, first cumulative expectancy crossing on `2019-05-02`, descriptive recovery in 2022, formal P07 `FAIL` unchanged.
- P08 rolling policy: `4c89b3c`; `configs/rolling_factory.yaml`, SHA256 `73f7bb0649c814a0ec076fff9d9e3413ba480fb31eca765ed18b860f6e1c72ed`.
- P08 first generation: `runs/p08-rolling-2019-q1-v3`; exact 100,000 GA evaluations, 2,489 eligible, 5 selected, 5 forward ledgers, no holdout. See `reports/p08_rolling_factory.md`.
- P09 rolling historical: `a4ea022`, `539dfa9`, `ce15de7`; 15 chronological generations Q2-2019–Q4-2022, each 100,000 evaluations, 293 portfolio operations, no holdout. See `reports/p09_rolling_historical.md` and `reports/p09_artifacts/`.
- P10 integrity: baseline `-16.9897586%`, DD `29.1497340%`, costs x2 `-28.7591429%`, DD x2 `38.9005187%`, 293 operations; 0 duplicates and 0 holdout rows. See `reports/p10_factory_diagnostics.md` and `reports/p10_artifacts/integrity.json`.
- P10 null procedure: commit `e7c4562`, `configs/p10_null_control.yaml`, SHA256 `d443e5a7aa7933c8f52a9acc00e7ee39b4edfdda9f9e4984d7e404537e55e6ca`; control A not run because candidate forward ledgers were not preserved, control B proposed with 1.5M minimum additional evaluations.
- P10.1 decision audit: `reports/p10_1_decision_audit.md`; 30/60/90-day aggregates are -13.8970%/-3.0574%/-15.4749% over 93/180/283 operations; baseline loss precedes costs; recommended next experiment is frozen control A with 100 paired random replicates per generation and 8,000 forward backtests, not yet executed.
- P11 availability audit: all 16 generations retained 100,000 GA archive rows, executable eligible strategy definitions, hashes and five selected hashes; no GA rerun was needed. See `reports/p11_artifacts/availability_audit.json`.
- P11 protocol freeze: `cbc7732`; `configs/random_selection_control.yaml`, SHA256 `11db3cdca55d5e33fdcb6d7ef65dfe382a30d58b88f93cbdf0ae057c895aab9f`.
- P11 implementation: `3879eda`, with resume fixes `333d4dd` and `8e23d77`; empty forward ledgers and frozen candidate universes are handled idempotently.
- P11 results: 1,600 quarterly random portfolios, 100 rolling trajectories, 8,000 sampled strategy slots and 7,168 unique deterministic backtests. Quarterly baseline controls beat NEW_FOREX in 98.625% of cases; rolling controls beat it in 62%. See `reports/p11_random_selection_control.md` and `reports/p11_artifacts/`.
- P12A full census: P08 Q1 archive `ga_archive.jsonl`, 100,000/100,000 executable strategies evaluated on 2019 Q1 forward in 50 resumable chunks; 35,817 had zero trades, 32,535 had positive forward expectancy, and mean return was -0.4277%. See `reports/p12a_full_ga_forward_census.md` and `reports/p12a_artifacts/`.
- P12B reverse-forward: 100,000-row joined dataset, 32,237 strategies in the descriptive active-positive-return group, 31,108 of them historical FAIL; historical win rate was unavailable and not reconstructed. See `reports/p12b_reverse_forward_analysis.md` and `reports/p12b_artifacts/`.
- P12C availability audit: all 15 later generations retain 100,000 archived executable strategies, complete historical variables required by the protocol, and verifiable canonical hashes; no holdout access. See `reports/p12c_artifacts/availability_audit.json`.
- P12C protocol freeze: commit `600e50c`; `configs/p12c_temporal_validation.yaml`, SHA256 `3ac952bfbfdd057b3b012a78ac413e52dbe388132ad9afdfe1c146af0c6d32e4`.
- P12C implementation: commits `89ae655` and `d0811a2`; 15/15 generations evaluated in chronological order, 1,500,000 full-universe strategy evaluations at baseline and costs ×2, plus 1,500 comparable random five-strategy portfolios. See `reports/p12c_temporal_validation.md` and `reports/p12c_artifacts/`.
- P12D protocol and implementation: commit `c8f59a6`; `configs/p12d_population_lifecycle.yaml`, SHA256 `d7c6bd2a484a6a4814eae354acbbe888beeba2e2d056e5569e400f60c683f7a5`; no GA rerun, selection or forward ranking.
- P12D results: 900,000 strategy-quarter observations from the exact 100,000-strategy P08 Q1 archive across 2017Q1–2019Q1, baseline and costs ×2, with P12A 2019Q1 equivalence verified. Dataset SHA256 `614d38565fbc7ecc3347c33b515c2444e97432d6ec97f4025d96a0733f565e11`; no holdout access. See `reports/p12d_population_lifecycle.md` and `reports/p12d_artifacts/`.
- P12D.1 protocol freeze: commits `95f9d75` and `b49b500`; `configs/p12d_1_selection_power.yaml`, SHA256 `f667964d4d7d56ba02072e7edf07e493713b2da9560dbf9bd7ef5941ce49bfc2`. Discovery used only 2017; formal rules, five-strategy portfolios, risk and seeds were frozen before formal evaluation.
- P12D.1 results: 11 rules tested descriptively, 3 formal rules, 300 random controls, and 1,525 portfolio-quarter rows built from actual rich ledgers. `train_pf_105_n100` returned `+15.11%` baseline and `+5.66%` with costs ×2 for its frozen portfolio; direction variants were negative. No rule established stable post-cost profitability. See `reports/p12d_1_selection_power_audit.md` and `reports/p12d_1_artifacts/`.
- P12D.2 protocol freeze: commit `87ba9a3`; `configs/p12d_2_portfolio_sensitivity.yaml`, SHA256 `3fb814193f3827333d4a1b67350dcb1cb991d701881d313f165fdc50a2395f8b`.
- P12D.2 results: the unchanged historical rule yielded 7,517 eligible strategies (7.517%); 1,000 uniform portfolios of five were evaluated across 2018Q1–2019Q1 with actual ledgers, baseline and costs ×2, plus original leave-one-out diagnostics. Baseline-positive controls: 52.2%; costs ×2: 24.4%. The original portfolio ranked at the 89.3%/90.0% descriptive percentiles. See `reports/p12d_2_portfolio_sensitivity.md` and `reports/p12d_2_artifacts/`.
- P12D.3 protocol freeze: commits `03e237d`, `44d45b3`, `8bcde6b`, `4605120` and `eb7549f`; `configs/p12d_3_cross_generation.yaml`, SHA256 `55b95145481e6d9fda50c3b09113f9176b6b2aa20a447c30552dcf7314cea044`. The rule, 15 generation windows, 1,000 five-strategy portfolios per group/generation, seeds, risk, costs and no-forward-selection safeguards were frozen before evaluation.
- P12D.3 results: all 15 P09 generations (2019 Q2–2022 Q4) completed without GA reruns or holdout access. The frozen rule produced 70,341 eligible population records; 15/15 generations had at least five eligible strategies. Artifacts contain 45,000 deterministic compositions, 90,030 portfolio/cost rows, causal sampled ledgers for every generation and cost, and 6,000 rolling trajectories. Eligible portfolio medians exceeded the full-universe control in 14/15 generations at both baseline and costs ×2, but rolling median return remained `-9.86%` baseline and `-35.18%` at costs ×2; this is exploratory enrichment, not demonstrated edge. See `reports/p12d_3_cross_generation.md` and `reports/p12d_3_artifacts/`.
- P12E protocol freeze: commit `dd6e851`; `configs/p12e_loss_decomposition.yaml`, SHA256 `20c1dfc6fd9d75e18238f27eebae1a83933fca1ab053eb563f173c93878e4b92`. It freezes the P12D.3 artifact hashes, accounting identities, risk/capitalization policy, no-resampling rule, and the explicit limitation that commission/spread/slippage are not separately identifiable.
- P12E results: 90,000 frozen portfolios and 13,677,678 executed operations were reconciled exactly to P12D.3 within `1e-10`; 1,504,796 temporal rows and 6,000 rolling decompositions were produced. Eligible portfolios had median gross capitalized return `+1.64%` versus median net `-0.04%` baseline, and rolling eligible median `+24.18%` gross versus `-9.86%` net; costs ×2 reduced rolling median net to `-35.18%`. No aggregate-risk blocks were observed. The dominant observable limitation is small gross margin relative to aggregate transaction costs plus temporal/dependent losses; no new filter or optimization was introduced. See `reports/p12e_loss_decomposition.md` and `reports/p12e_artifacts/`.
- P12F protocol freeze: commit `a8f8c47`; `configs/p12f_high_quality.yaml`, SHA256 `ac64ba99f586d8b1af042a1b13b1d71ae07d717e11c75726d6a1bf41d24f4926`. The frozen rule is `training PF > 1.30 AND training trades > 250`, with 2017Q1-only forward, 1,000 portfolios per group/control, fixed seeds, 0.5% risk per trade and 2.5% aggregate cap.
- P12F implementation: commits `52b4b42` and `4b7f72c`; 100,000 individual strategies, 47 high-quality eligible strategies, 7,517 prior-filter strategies, 4,000 five-strategy portfolios and 10,000 baseline/x2 portfolio rows. Baseline/x2 trade identity and gross-R reconciliation passed; no later quarter or holdout was read. See `reports/p12f_high_quality.md` and `reports/p12f_artifacts/`.
- P12F result: the 47-strategy population had median active gross expectancy `0.1728R`, net `0.1198R`, x2 `0.0522R`; its portfolio medians were `+2.72%` baseline and `+1.37%` x2, versus `-0.28%`/`-2.00%` for the prior filter and `-1.85%`/`-5.41%` for the full universe. This is one-quarter exploratory evidence, not demonstrated edge; individual gross capitalized return was unavailable in P12D and was not invented.
- P12G protocol freeze: commit `126f46db`; `configs/p12g_fixed_cohort.yaml`, SHA256 `c19797497c16271d8afed24b843ed9ee52cb84274de29ea83e2273381c03b5a1`. It freezes the 47 P12F hashes, 1,000 exact P12F compositions, nine quarters 2017Q1–2019Q1, risk/costs and no-reselection safeguards.
- P12G results: 423 individual quarter rows, 18,000 portfolio-quarter-cost rows and 2,000 capitalized trajectories. The cohort remained active, but individual gross expectancy turned negative in 2017Q3; portfolio median turned negative in 2017Q3 baseline and 2017Q2 x2. Final trajectory medians were `-27.79%` baseline and `-40.11%` x2, with median final drawdowns `32.56%` and `41.63%`. No holdout access. See `reports/p12g_fixed_cohort.md` and `reports/p12g_artifacts/`.
- P13 protocol freeze: initial commit `1cf1c9c1` was technically corrected before valid results; corrected protocol commit `7977c162`, `configs/p13_six_month_rolling.yaml`, SHA256 `d0758174ff0a4bcf89517cf708982c40a76bee247800e7dc058a43825cd1562f`. The correction sets GA to 102 generations so the existing elite-preserving engine reaches exactly 100,000 unique evaluations; the invalid 99,000-evaluation run is retained separately under `reports/p13_invalid_budget_run_99k/`.
- P13 valid execution: 12 monthly generations, 1,200,000 GA evaluations and 1,200,000 Random Search evaluations, 2,400,000 census rows, no holdout. The fixed filter produced fewer than five eligible strategies in every generation; GA had eligible strategies in 3/12 generations and Random Search in 2/12. Selected partial portfolios were negative in all active months; rolling returns were `-18.62%` GA baseline / `-24.71%` x2 and `-10.38%` Random baseline / `-14.04%` x2. See `reports/p13_six_month_rolling.md` and `reports/p13_artifacts/`.
- P13A protocol freeze: commit `f80c1e43`; `configs/p13a_census_anatomy.yaml`, SHA256 `f05af029b785d16b3e9358d98a8f041933e567876f4a26ec1eb4dbb397b0aad9`. It freezes the valid P13 census, excludes `reports/p13_invalid_budget_run_99k/`, defines mutually exclusive A–E economic classes with exact zero non-positive, and forbids forward selection.
- P13A results: 2,400,000 valid strategy-forward rows classified and reconciled; classes A/B/C/D/E contain `575,249/957,464/154,332/123,524/589,431` rows. GA active rate was `72.64%`, with `28.91%` baseline-positive and `24.86%` positive at costs x2; Random was `79.42%`, `30.50%` and `24.26%`. Active mean gross expectancy was `0.0083R` GA and `0.0006R` Random versus net baseline `-0.0715R` and `-0.0660R`; the source censo SHA256 is `a5f371d49db1dc7354182ea1d401aa8533936201c763d435b7930905794c8ec5`. No holdout was read. See `reports/p13a_census_anatomy.md` and `reports/p13a_artifacts/`.
- P13B protocol freeze: commits `e496f6de` and hash pin fix `55d2f3ba`; `configs/p13b_predictability_mapping.yaml`, final SHA256 `df417d2ffe1c664046de9c748a05a20033f77937c8ea080ed16a31ddd2a9c681`. Historical X/Y separation, fixed PF/trade bins, activity conditions, no forward selection and no fabricated portfolio sums were frozen before mapping.
- P13B results: 2,400,000 rows and 12 generations mapped univariately and through four small historical interactions. Some PF and trade intervals show descriptive E-lift across months, including PF `1.30–<1.50`, but net expectancy remains negative and no complete per-strategy ledgers exist for arbitrary stratum portfolios. Conclusion: descriptive enrichment only; `NO HISTORICAL PREDICTABILITY EVIDENCE` as an economically validated policy. No holdout access. See `reports/p13b_predictability_mapping.md` and `reports/p13b_artifacts/`.
- P13C protocol freeze: commit `f070e6c6`; `configs/p13c_rolling_6m_1m.yaml`, SHA256 `216ba43c800e68b6d53aa6eb32193ba82388130d59456828e421fe41c442d7c2`. Implementation commits `5c999462`, `e536df3b`, `8d14df91`, `17c78262` and `3313f5ac` freeze the 54-month calendar, exact 100,000-evaluation GA, PF > 1.30/trades > 30 filter, controls and ledger engine.
- P13C execution blocker: G001–G003 completed with exact GA archives, training metrics, 3,000 compositions per generation and baseline/x2 ledgers; G004 was in progress when the interactive compute/storage projection reached several hours and multiple GB. The run was stopped without interpreting partial results as P13C. See `docs/P13C_BLOCKER.md` and `reports/p13c_artifacts/checkpoint.json`.
- Pre-holdout audit evidence: `docs/DATA_MANIFEST.md`; seven local series audited through 2022-12-30 23:45, final holdout sealed.
- Skips are data-dependent tests; no local datasets were copied and no holdout unlock was used.

## Next task

Do not start Factory V2 from these exploratory results. Do not open the final
holdout or execute operations in the real world.
