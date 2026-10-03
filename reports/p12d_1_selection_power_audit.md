# P12D.1 — Historical Selection Power Audit

## Scope and causal boundary

This is an exploratory audit of the exact 100,000-strategy P08 Q1 population using the 900,000 P12D rows. Rule discovery used 2017Q1–2017Q4 only. Formal evaluation used fixed rules over 2018Q1–2019Q1. This is not an independent validation: 2018–2019 was already inspected in P12A–P12D.

The protocol was frozen before formal evaluation. PASS is retained only as a retrospective benchmark because its original decision used later development information; it is not a causal candidate rule.

## Historical variables audit

Available before forward evaluation: training number of trades, expectancy R, profit factor, return, MaxDD, maximum loss streak, direction, predicate count/complexity, and original PASS/FAIL decision. Per-year training regularity and an independent exposure series were not archived. Forward behavior signatures, forward activity and all forward metrics were excluded as predictors.

## Rules tested during discovery

All 11 definitions and their 2017 results are in `rule_trials_2017.csv`. No identifier-based rule or forward signature was tested.

```text
                        rule_id      n  mean_return  mean_expectancy_R  positive_return_pct  mean_R_per_trade
                full_population 400000    -0.017764          -0.081946             0.159438         -0.132851
                full_population 400000    -0.028222          -0.126283             0.110890         -0.204730
        original_pass_benchmark   9956     0.003837           0.103405             0.579148          0.104190
        original_pass_benchmark   9956     0.000586           0.044697             0.525512          0.045036
              train_pf_100_n100  56860    -0.017845          -0.133823             0.311027         -0.133971
              train_pf_100_n100  56860    -0.025735          -0.199806             0.237355         -0.200027
              train_pf_105_n100  30068    -0.010832          -0.133833             0.350040         -0.134034
              train_pf_105_n100  30068    -0.015666          -0.199222             0.283225         -0.199521
              train_pf_110_n100  16988    -0.006473          -0.133146             0.374794         -0.133421
              train_pf_110_n100  16988    -0.009615          -0.199927             0.320697         -0.200340
        train_exp_positive_n100  56860    -0.017845          -0.133823             0.311027         -0.133971
        train_exp_positive_n100  56860    -0.025735          -0.199806             0.237355         -0.200027
  train_exp_positive_pf105_n100  30068    -0.010832          -0.133833             0.350040         -0.134034
  train_exp_positive_pf105_n100  30068    -0.015666          -0.199222             0.283225         -0.199521
train_return_positive_dd20_n100  42332    -0.012894          -0.125396             0.330766         -0.125580
train_return_positive_dd20_n100  42332    -0.018408          -0.187261             0.259898         -0.187535
train_pf105_n100_complexity_le2   8572    -0.014341          -0.139610             0.324545         -0.139675
train_pf105_n100_complexity_le2   8572    -0.020035          -0.200996             0.254900         -0.201090
          train_pf105_n100_long   1452     0.001967           0.032007             0.516529          0.032118
          train_pf105_n100_long   1452    -0.001647          -0.032470             0.448347         -0.032582
         train_pf105_n100_short  28616    -0.011482          -0.142248             0.341592         -0.142447
         train_pf105_n100_short  28616    -0.016377          -0.207683             0.274846         -0.207974
```

## Formal individual results

The complete table is in `formal_individual_by_rule.csv`; percentages are population fractions, not economic portfolio returns.

```text
                rule_id scenario  observations  mean_return  mean_expectancy_R  positive_return_pct_mean  median_finite_PF_mean  mean_max_drawdown
        full_population baseline        500000    -0.006458          -0.007810                  0.253588               0.608278           0.024656
        full_population costs_x2        500000    -0.016316          -0.050597                  0.190826               0.530428           0.030389
original_pass_benchmark baseline         12445     0.004962           0.153317                  0.618642               1.169472           0.014014
original_pass_benchmark costs_x2         12445     0.002102           0.097576                  0.570430               1.056021           0.015236
      train_pf_105_n100 baseline         37585     0.000541          -0.006379                  0.481815               0.975139           0.018063
      train_pf_105_n100 costs_x2         37585    -0.003288          -0.069882                  0.430810               0.874636           0.019869
  train_pf105_n100_long baseline          1815    -0.005321          -0.081546                  0.399449               0.820021           0.019652
  train_pf105_n100_long costs_x2          1815    -0.008740          -0.142746                  0.341047               0.726259           0.021524
 train_pf105_n100_short baseline         35770     0.000839          -0.002565                  0.485994               0.986760           0.017983
 train_pf105_n100_short costs_x2         35770    -0.003012          -0.066184                  0.435365               0.883878           0.019785
```

## Formal portfolios and controls

Each frozen group used one deterministic five-strategy portfolio. Each formal rule also has 100 uniform, without-replacement controls of five strategies from the same historical-activity base (`training_n_trades >= 100`). The original execution engine, 0.5% risk per trade and 2.5% aggregate risk cap were used; portfolios were built from actual rich ledgers, not aggregate statistics.

```text
               rule_id  actual_baseline_cumulative_return  control_baseline_mean  control_baseline_fraction_beating_actual  actual_costs_x2_cumulative_return  control_costs_x2_mean  control_costs_x2_fraction_beating_actual
     train_pf_105_n100                           0.151076              -0.205703                                  0.030000                           0.056598              -0.452431                                  0.010000
 train_pf105_n100_long                          -0.091327              -0.231870                                  0.230000                          -0.133845              -0.486853                                  0.040000
train_pf105_n100_short                          -0.016121              -0.212925                                  0.130000                          -0.103929              -0.454368                                  0.050000
```

Cumulative returns compound the five chronological quarterly portfolio returns. They are not sums of individual strategy returns. Full portfolio details are in `portfolio_results.csv` and cumulative controls in the accompanying CSV files.

## Answers

1. Retrospectively favorable subpopulations exist descriptively: the original PASS group and some 2017 rule groups show higher positive fractions, but this does not establish a usable rule.
2. Historical training variables identify differences in population distributions, but the formal rules do not produce a robust positive portfolio. The PF/activity/direction rules were not sufficient.
3. No formal rule maintained favorable results across all five quarters. The aggregate `train_pf_105_n100` portfolio was positive baseline, but costs ×2 were positive only weakly and its quarter-to-quarter behavior was not stable.
4. The rule portfolios outperformed the matched random controls in the recorded comparison, but controls remained negative on average and this does not demonstrate edge; the comparison is conditional on one frozen five-strategy sample and shared market data.
5. No new-rule portfolio provides evidence of stable positive net profitability after costs. The original PASS benchmark also had negative cumulative portfolio performance under this fixed sample.

## Dependence and limitations

Strategies share the same GA, market, indicators and execution process. Positive percentages are not independent evidence, and the five-strategy portfolios are sensitive to overlap and path dependence. The experiment does not estimate an unbiased discovery-to-validation performance because the 2018–2019 period has already been inspected in prior phases. No thresholds were changed after formal results.

## Conclusion

Historical statistics can describe subpopulation differences, but this experiment does not justify a new acceptance policy or Factory V2. No strategies were modified, no GA was rerun, no holdout data was opened, and no real operations were performed.
