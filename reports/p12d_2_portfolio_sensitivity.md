# P12D.2 — Selection Stability and Portfolio Sensitivity

## Scope and frozen rule

The exact P08 Q1 universe was restricted using only historical training fields: `training_profit_factor >= 1.05` and `training_n_trades >= 100`. This produced 7,517 of 100,000 strategies (7.517%). No additional eligibility filter was applied. Five-strategy portfolios were sampled uniformly without replacement with 1,000 deterministic seeds; the original P12D.1 portfolio was retained separately.

Protocol SHA256: `3fb814193f3827333d4a1b67350dcb1cb991d701881d313f165fdc50a2395f8b`. The 2018Q1–2019Q1 period was already inspected in P12A–P12D and is not independent validation.

## Eligible population

Historical distributions are in `eligible_describe.csv`; structural counts are in `eligible_structural_families.csv`. No forward result was used for eligibility.

```text
direction  complexity  size
     LONG           1     1
     LONG           2    48
     LONG           3   142
     LONG           4   172
    SHORT           1   152
    SHORT           2  1942
    SHORT           3  2920
    SHORT           4  2140
```

## Individual forward distribution

The eligible population has a more favorable individual distribution than the full population, but the effect is modest and does not imply portfolio profitability. Full comparison:

```text
      group       cost  mean_return  mean_expectancy_R  positive_return_pct  active_pct  mean_max_drawdown
   eligible    forward     0.000541          -0.006379             0.481815    0.989304           0.018063
   eligible forward_x2    -0.003288          -0.069882             0.430810    0.989304           0.019869
       full    forward    -0.006458          -0.007810             0.253588    0.611760           0.024656
       full forward_x2    -0.016316          -0.050597             0.190826    0.611760           0.030389
noneligible    forward    -0.007026          -0.007927             0.235038    0.581073           0.025192
noneligible forward_x2    -0.017375          -0.049029             0.171320    0.581073           0.031244
```

Forward behavior signatures are diagnostic only. Among eligible strategies, unique aggregate signatures and concentration were:

```text
quarter  eligible_rows  unique_signatures  largest_signature  duplicate_rows
 2018Q1           7517               4305                 81            3212
 2018Q2           7517               3833                253            3684
 2018Q3           7517               4145                 67            3372
 2018Q4           7517               4192                138            3325
 2019Q1           7517               4241                 45            3276
```
These signatures are not treated as independent observations. Exact operation-level similarity for every eligible pair was not archived; actual ledgers were used for all sampled portfolio components.

## 1,000 composition Monte Carlo

```text
    cost  n_controls  mean_return  median_return  p05_return  p95_return  positive_fraction  mean_max_drawdown  original_return  controls_beating_original_fraction  original_percentile_rank
baseline        1000     0.010967       0.005625   -0.172300    0.194136           0.522000           0.066828         0.151076                            0.107000                  0.893000
costs_x2        1000    -0.080289      -0.079132   -0.268812    0.092243           0.244000           0.107213         0.056598                            0.100000                  0.900000
```
The original portfolio is at the `original_percentile_rank` of the composition distribution; the percentile is descriptive, not confirmatory. It is above 89.3% of baseline controls and 90.0% of costs×2 controls, but this is one previously observed combination and not a new selection result.

## Operational overlap

Actual sampled ledgers were used to calculate maximum simultaneous positions; this is an execution diagnostic, not a selection variable.

```text
    cost  mean_max_concurrent  p95_max_concurrent  original_mean
baseline             3.143856            5.000000       2.200000
costs_x2             3.143856            5.000000       2.200000
```

## Original portfolio leave-one-out

```text
                                           removed_strategy_hash     cost  cumulative_return  max_drawdown  n_trades
235cd5a708fc720a197cd4589735667a523d568abedaf6d7e360a30f938f912d baseline           0.145291      0.001849       253
235cd5a708fc720a197cd4589735667a523d568abedaf6d7e360a30f938f912d costs_x2           0.065444      0.012102       253
261ba426e7299b34b053b93a8ed72f8db538b4ebc16a0c563a0868f1d3f48ad8 baseline           0.199474      0.000000       263
261ba426e7299b34b053b93a8ed72f8db538b4ebc16a0c563a0868f1d3f48ad8 costs_x2           0.107430      0.000000       263
84c498378a7b9639a4b585308852269dcea6587729525e63d4ef66e4075218ec baseline           0.115601      0.000000       189
84c498378a7b9639a4b585308852269dcea6587729525e63d4ef66e4075218ec costs_x2           0.041251      0.016356       189
ef0fa052721998be37d474e0b832243a459b07b10ce0850d3d251d88c85ef40d baseline           0.063541      0.010901       173
ef0fa052721998be37d474e0b832243a459b07b10ce0850d3d251d88c85ef40d costs_x2           0.012879      0.028868       173
fc1ce793e6530b29db17f62b3d49779bbbce4683ea2bbefc9866070fb74b24d4 baseline           0.080239      0.037356       242
fc1ce793e6530b29db17f62b3d49779bbbce4683ea2bbefc9866070fb74b24d4 costs_x2           0.004473      0.054901       242
```
Leave-one-out is diagnostic only. No replacement portfolio was constructed. The original outcome depends on composition, but removal of any single component does not turn this into an independent validation.

## Answers

A. Yes, the historical rule identifies a descriptively more favorable individual subpopulation: baseline mean return was approximately `+0.054%` per strategy-quarter versus `-0.646%` for the full population; costs×2 remained negative (`-0.329%`).

B. 52.2% of alternative five-strategy portfolios were baseline-positive; 24.4% remained positive with costs×2. The median baseline return was only about `+0.56%`, while the costs×2 median was `-7.91%`.

C. No. Profitability does not persist for most compositions when costs are doubled.

D. The original P12D.1 portfolio is favorable but not unique: it ranked around the 89th–90th percentile among the 1,000 alternatives, not at an isolated maximum.

E. There is material behavioral concentration: each quarter has thousands of distinct signatures but thousands of duplicate rows and a non-trivial largest signature. The original leave-one-out results show composition sensitivity, while shared market/GA construction lowers effective sample size.

F. The results justify, at most, a pre-registered test of the unchanged rule on genuinely later generations. They do not justify changing thresholds, creating Factory V2, or declaring edge.

## Limitations

The 1,000 portfolios reuse strategies and market data, so they are not independent draws from an external population. Forward data was used only for outcome and diagnostic calculations. No holdout data, GA rerun, real operation or retrospective threshold adjustment was used.
