# Backtest report

Source: `patentsview` · slice: `deeptech` · data ends 2025 · horizon 10 years · top K = 100

Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out cutoffs were looked at once the weights were frozen.

## Gate

**NO-GO**. Hybrid lift@100 on held-out cutoffs is 4.27, the better baseline is 4.02, ratio 1.06 (threshold 2.0, a judgment call).

## Tuned weights

`{"cn": 1.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`

## Held-out cutoffs (these count)

### Cutoff 2005
122 fields, 4,569 candidate pairs, **674 positives**, base rate 0.1475

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.472 | 11 | 0.110 | 0.75 |
| pa | 0.785 | 75 | 0.750 | 5.08 |
| cn | 0.809 | 75 | 0.750 | 5.08 |
| aa | 0.814 | 76 | 0.760 | 5.15 |
| prereq | 0.787 | 81 | 0.810 | 5.49 |
| hybrid | 0.849 | 84 | 0.840 | 5.69 |
| genome | 0.694 | 16 | 0.160 | 1.08 |

### Cutoff 2010
122 fields, 4,325 candidate pairs, **1047 positives**, base rate 0.2421

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.519 | 34 | 0.340 | 1.40 |
| pa | 0.798 | 90 | 0.900 | 3.72 |
| cn | 0.814 | 87 | 0.870 | 3.59 |
| aa | 0.819 | 87 | 0.870 | 3.59 |
| prereq | 0.800 | 87 | 0.870 | 3.59 |
| hybrid | 0.842 | 92 | 0.920 | 3.80 |
| genome | 0.689 | 28 | 0.280 | 1.16 |

### Cutoff 2014
122 fields, 4,033 candidate pairs, **1032 positives**, base rate 0.2559

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.497 | 23 | 0.230 | 0.90 |
| pa | 0.802 | 83 | 0.830 | 3.24 |
| cn | 0.818 | 83 | 0.830 | 3.24 |
| aa | 0.822 | 83 | 0.830 | 3.24 |
| prereq | 0.806 | 88 | 0.880 | 3.44 |
| hybrid | 0.837 | 85 | 0.850 | 3.32 |
| genome | 0.703 | 35 | 0.350 | 1.37 |

## Tuning cutoffs (weights were fitted here)

### Cutoff 1990
117 fields, 4,852 candidate pairs, **583 positives**, base rate 0.1202

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.487 | 11 | 0.110 | 0.92 |
| pa | 0.757 | 56 | 0.560 | 4.66 |
| cn | 0.782 | 65 | 0.650 | 5.41 |
| aa | 0.787 | 65 | 0.650 | 5.41 |
| prereq | 0.788 | 63 | 0.630 | 5.24 |
| hybrid | 0.825 | 66 | 0.660 | 5.49 |
| genome | 0.537 | 19 | 0.190 | 1.58 |

### Cutoff 1995
120 fields, 4,882 candidate pairs, **533 positives**, base rate 0.1092

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.513 | 8 | 0.080 | 0.73 |
| pa | 0.751 | 45 | 0.450 | 4.12 |
| cn | 0.777 | 50 | 0.500 | 4.58 |
| aa | 0.783 | 49 | 0.490 | 4.49 |
| prereq | 0.761 | 42 | 0.420 | 3.85 |
| hybrid | 0.806 | 56 | 0.560 | 5.13 |
| genome | 0.582 | 17 | 0.170 | 1.56 |

### Cutoff 2000
122 fields, 4,814 candidate pairs, **489 positives**, base rate 0.1016

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.507 | 8 | 0.080 | 0.79 |
| pa | 0.770 | 53 | 0.530 | 5.22 |
| cn | 0.801 | 51 | 0.510 | 5.02 |
| aa | 0.807 | 51 | 0.510 | 5.02 |
| prereq | 0.783 | 54 | 0.540 | 5.32 |
| hybrid | 0.837 | 55 | 0.550 | 5.41 |
| genome | 0.603 | 15 | 0.150 | 1.48 |

## Reading this

- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.
- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test cutoffs, which would inflate the result.
- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.
