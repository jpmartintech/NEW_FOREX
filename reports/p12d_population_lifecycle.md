# P12D — Full Population Forward Lifecycle

## Scope

The exact 100,000-strategy P08 Q1 archive was evaluated over 2017 Q1 through 2019 Q1. No GA, selection, forward ranking, or holdout access was used.

Dataset: 900,000 strategy-quarter rows; unique strategies: 100,000; quarters: 9.

## Quarterly population statistics

See `p12d_artifacts/quarterly_population_summary.csv` for activity, expectancy, return, Profit Factor distributions, drawdown, efficiency, R/trade and costs ×2. The dataset preserves individual strategy results; it is not a portfolio simulation and rows are not independent observations.

```text
quarter       cost      n  active_pct  zero_trade_n  mean_n_trades  median_n_trades  p95_n_trades  mean_expectancy_R  median_expectancy_R  p05_expectancy_R  p95_expectancy_R  mean_return  median_return  p05_return  p95_return  positive_expectancy_pct  positive_return_pct  finite_pf_pct  pf_gt_1_pct  median_finite_pf  p95_finite_pf  mean_max_drawdown  median_max_drawdown  mean_efficiency_return_dd  mean_R_per_trade
 2017Q1    forward 100000    0.599830         40017      29.174690         7.000000    120.000000          -0.014244             0.000000         -0.342784          0.296480    -0.005591       0.000000   -0.053494    0.028140                 0.250990             0.245890       0.983690     0.250990          0.673049       1.526160           0.024659             0.011061                   0.059461         -0.023747
 2017Q1 forward_x2 100000    0.599830         40017      29.174690         7.000000    120.000000          -0.053192             0.000000         -0.417826          0.238943    -0.015340       0.000000   -0.088985    0.016878                 0.174960             0.171150       0.983750     0.174960          0.589977       1.371740           0.030694             0.012160                  -0.111681         -0.088679
 2017Q2    forward 100000    0.619040         38096      30.672470         9.000000    121.000000          -0.111022             0.000000         -0.595877          0.243353    -0.028034       0.000000   -0.132701    0.013760                 0.124640             0.123070       0.982060     0.124640          0.471008       1.359666           0.039295             0.016335                  -0.234016         -0.179345
 2017Q2 forward_x2 100000    0.619040         38096      30.672470         9.000000    121.000000          -0.160131            -0.061246         -0.686635          0.169371    -0.039571      -0.005050   -0.173860    0.007250                 0.091640             0.090250       0.982350     0.091640          0.408669       1.182658           0.048198             0.018099                  -0.336605         -0.258676
 2017Q3    forward 100000    0.645410         35459      30.563770         8.000000    122.000000          -0.107821            -0.003329         -1.040161          0.177900    -0.016794      -0.000720   -0.087240    0.012706                 0.142590             0.139160       0.986060     0.142590          0.575459       1.274141           0.031328             0.015775                  -0.164202         -0.167058
 2017Q3 forward_x2 100000    0.645410         35459      30.563770         8.000000    122.000000          -0.151461            -0.060212         -1.080321          0.113690    -0.026807      -0.005602   -0.124621    0.006423                 0.094670             0.092840       0.986100     0.094670          0.506343       1.149180           0.038505             0.016871                  -0.311918         -0.234675
 2017Q4    forward 100000    0.603020         39698      28.686000         8.000000    117.000000          -0.094697             0.000000         -0.566755          0.192664    -0.020639       0.000000   -0.109754    0.014550                 0.131620             0.129630       0.987900     0.131620          0.483653       1.307013           0.033136             0.014059                  -0.184720         -0.157038
 2017Q4 forward_x2 100000    0.603020         39698      28.686000         8.000000    117.000000          -0.140346            -0.022006         -0.657319          0.121289    -0.031169      -0.002162   -0.148871    0.006975                 0.090950             0.089320       0.988180     0.090950          0.420024       1.153922           0.040822             0.015887                  -0.298710         -0.232739
 2018Q1    forward 100000    0.611160         38884      29.000580         9.000000    116.000000          -0.028411             0.000000         -0.389240          0.297955    -0.009326       0.000000   -0.068462    0.025821                 0.214550             0.210880       0.983670     0.214550          0.632708       1.502354           0.026723             0.013367                  -0.020105         -0.046487
 2018Q1 forward_x2 100000    0.611160         38884      29.000580         9.000000    116.000000          -0.062946             0.000000         -0.453227          0.242953    -0.017633       0.000000   -0.096972    0.016471                 0.160120             0.157370       0.983720     0.160120          0.566091       1.364319           0.031580             0.014677                  -0.150015         -0.102994
 2018Q2    forward 100000    0.593300         40670      27.193110         6.000000    120.000000           0.007710             0.000000         -0.468852          0.417503     0.000330       0.000000   -0.047773    0.047356                 0.327850             0.323540       0.981050     0.327850          0.595248       1.857257           0.019803             0.010361                   0.308424          0.012996
 2018Q2 forward_x2 100000    0.593300         40670      27.193110         6.000000    120.000000          -0.032262             0.000000         -0.541011          0.344304    -0.008907       0.000000   -0.078070    0.031344                 0.253920             0.250190       0.981120     0.253920          0.525404       1.660770           0.024241             0.010820                   0.075408         -0.054377
 2018Q3    forward 100000    0.613450         38655      29.893590         8.000000    123.000000          -0.065761             0.000000         -0.571056          0.200159    -0.011299       0.000000   -0.065632    0.015967                 0.172430             0.167840       0.983660     0.172430          0.593114       1.320106           0.027431             0.011916                  -0.112987         -0.107199
 2018Q3 forward_x2 100000    0.613450         38655      29.893590         8.000000    123.000000          -0.108966            -0.007226         -0.654690          0.136455    -0.021925      -0.001131   -0.104999    0.007610                 0.108410             0.106100       0.983750     0.108410          0.516070       1.178328           0.034030             0.013431                  -0.250815         -0.177629
 2018Q4    forward 100000    0.599060         40094      28.283560         6.000000    120.000000           0.011868             0.000000         -0.400604          0.597282    -0.007716       0.000000   -0.075691    0.040879                 0.247320             0.243310       0.981280     0.247320          0.616110       2.670712           0.025023             0.007329                   0.314232          0.019810
 2018Q4 forward_x2 100000    0.599060         40094      28.283560         6.000000    120.000000          -0.029063             0.000000         -0.485746          0.539923    -0.017301       0.000000   -0.113591    0.032064                 0.195410             0.192970       0.981670     0.195410          0.536410       2.387849           0.030956             0.008302                   0.117506         -0.048514
 2019Q1    forward 100000    0.641830         35817      26.324190         6.000000    112.000000           0.035542             0.000000         -0.555014          0.683168    -0.004277       0.000000   -0.069906    0.040675                 0.325350             0.322370       0.955230     0.325350          0.604208       2.355870           0.024299             0.010359                   0.303174          0.055376
 2019Q1 forward_x2 100000    0.641830         35817      26.324190         6.000000    112.000000          -0.019746             0.000000         -0.652946          0.597635    -0.015815       0.000000   -0.110037    0.025709                 0.250750             0.247500       0.955790     0.250750          0.508165       2.043948           0.031136             0.010920                   0.065126         -0.030765
```

## Favorable groups

Groups are descriptive and are never used to select the next quarter. See `favorable_groups.csv`.

```text
quarter                      group     n  mean_forward_expectancy_R  mean_forward_return  mean_training_expectancy_R  mean_training_n_trades  costs_x2_positive_expectancy_pct
 2017Q1 active_positive_expectancy 25099                   0.219402             0.017289                   -0.003060             1110.158453                          0.697080
 2017Q1     active_positive_return 24589                   0.223904             0.017665                   -0.002322             1092.213795                          0.711538
 2017Q1       active_positive_both 24589                   0.223904             0.017665                   -0.002322             1092.213795                          0.711538
 2017Q1                       rest 75411                  -0.091897            -0.013173                    4.769500              826.021880                          0.000000
 2017Q2 active_positive_expectancy 12464                   0.343454             0.019751                    0.059082              862.761954                          0.735237
 2017Q2     active_positive_return 12307                   0.347805             0.020009                    0.060154              855.979443                          0.744617
 2017Q2       active_positive_both 12307                   0.347805             0.020009                    0.060154              855.979443                          0.744617
 2017Q2                       rest 87693                  -0.175414            -0.034776                    4.092406              896.457437                          0.000000
 2017Q3 active_positive_expectancy 14259                   0.243053             0.012410                    0.014492              795.515394                          0.663932
 2017Q3     active_positive_return 13916                   0.248988             0.012731                    0.015451              781.889767                          0.680296
 2017Q3       active_positive_both 13916                   0.248988             0.012731                    0.015451              781.889767                          0.680296
 2017Q3                       rest 86084                  -0.165501            -0.021567                    4.175000              909.191058                          0.000000
 2017Q4 active_positive_expectancy 13162                   0.276372             0.016439                   -0.017004              989.144887                          0.691004
 2017Q4     active_positive_return 12963                   0.280576             0.016702                   -0.016607              974.493327                          0.701612
 2017Q4       active_positive_both 12963                   0.280576             0.016702                   -0.016607              974.493327                          0.701612
 2017Q4                       rest 87037                  -0.150589            -0.026200                    4.134230              879.111458                          0.000000
 2018Q1 active_positive_expectancy 21455                   0.261888             0.017400                    0.043456             1067.587695                          0.746306
 2018Q1     active_positive_return 21088                   0.266398             0.017715                    0.044907             1051.442527                          0.759294
 2018Q1       active_positive_both 21088                   0.266398             0.017715                    0.044907             1051.442527                          0.759294
 2018Q1                       rest 78912                  -0.107194            -0.016552                    4.545173              848.727202                          0.000000
 2018Q2 active_positive_expectancy 32785                   0.253416             0.025298                   -0.012333             1394.292847                          0.774501
 2018Q2     active_positive_return 32354                   0.256753             0.025647                   -0.012120             1383.474254                          0.784818
 2018Q2       active_positive_both 32354                   0.256753             0.025647                   -0.012120             1383.474254                          0.784818
 2018Q2                       rest 67646                  -0.111402            -0.011779                    5.321938              656.160823                          0.000000
 2018Q3 active_positive_expectancy 17243                   0.233856             0.013283                   -0.004373              972.019602                          0.628719
 2018Q3     active_positive_return 16784                   0.240181             0.013668                   -0.003628              947.987905                          0.645913
 2018Q3       active_positive_both 16784                   0.240181             0.013668                   -0.003628              947.987905                          0.645913
 2018Q3                       rest 83216                  -0.127467            -0.016335                    4.322204              880.077774                          0.000000
 2018Q4 active_positive_expectancy 24732                   0.374778             0.023754                   -0.005397              965.031942                          0.790110
 2018Q4     active_positive_return 24331                   0.380916             0.024158                   -0.004966              947.754675                          0.803132
 2018Q4       active_positive_both 24331                   0.380916             0.024158                   -0.004966              947.754675                          0.803132
 2018Q4                       rest 75669                  -0.106798            -0.017965                    4.754080              873.379614                          0.000000
 2019Q1 active_positive_expectancy 32535                   0.399386             0.022251                    0.426195             1190.892915                          0.770708
 2019Q1     active_positive_return 32237                   0.403060             0.022464                    0.430474             1182.820672                          0.777833
 2019Q1       active_positive_both 32237                   0.403060             0.022464                    0.430474             1182.820672                          0.777833
 2019Q1                       rest 67763                  -0.139298            -0.016998                    5.102172              752.873854                          0.000000
```

## Lifecycle and dependence

Activity and distribution changes are reported by quarter. Behavioral signatures are computed separately per quarter; repeated signatures and shared market data mean the 900,000 rows cannot be treated as independent. `dependence_by_quarter.csv` records concentration:

```text
quarter   rows  unique_strategies  unique_signatures  duplicate_rows
 2017Q1 100000             100000              47377           52623
 2017Q2 100000             100000              49730           50270
 2017Q3 100000             100000              48196           51804
 2017Q4 100000             100000              47284           52716
 2018Q1 100000             100000              47988           52012
 2018Q2 100000             100000              45378           54622
 2018Q3 100000             100000              47211           52789
 2018Q4 100000             100000              47139           52861
 2019Q1 100000             100000              48090           51910
```

Exposure-based profit per unit could not be computed because the preserved aggregate contract contains no independent exposure series; R/trade and return/drawdown are reported instead.

## P12A equivalence

The 2019 Q1 rows match P12A on trade count, expectancy, return, drawdown and costs ×2 fields. See `equivalence_p12a.json`.

## Candidate regularities for later research

1. Activity and forward distributions vary materially by quarter; this is descriptive and may reflect market regime changes.
2. Costs ×2 reduce both expectancy and the positive-return fraction; cost sensitivity should remain a measured property.
3. Positive-expectancy and positive-return groups are sparse relative to the full population and unstable across quarters.
4. Return/drawdown efficiency has unstable denominators when no drawdown is recorded and must not be used as an automatic filter.
5. Repeated behavioral signatures imply substantial dependence; effective sample size is lower than 900,000.

## Limitations

The period ends at 2019-04-01 exclusive. No 2019 Q2 onward or holdout data was accessed. This exploratory census cannot establish edge, causal relationships, or a new acceptance policy.
