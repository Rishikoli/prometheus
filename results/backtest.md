# Backtest report

Source: `patentsview` · slice: `deeptech` · data ends 2025 · horizon 10 years · top K = 100

Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out cutoffs were looked at once the weights were frozen.

## Gate

**NO-GO**. Hybrid lift@100 on held-out cutoffs is 4.44, the better baseline is 4.26, ratio 1.04 (threshold 2.0, a judgment call).

## Tuned weights

`{"cn": 2.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`

## Held-out cutoffs (these count)

### Cutoff 2005
122 fields, 4,887 candidate pairs, **660 positives**, base rate 0.1351

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.502 | 12 | 0.120 | 0.89 |
| pa | 0.777 | 68 | 0.680 | 5.04 |
| cn | 0.808 | 70 | 0.700 | 5.18 |
| aa | 0.814 | 73 | 0.730 | 5.41 |
| prereq | 0.778 | 79 | 0.790 | 5.85 |
| hybrid | 0.843 | 76 | 0.760 | 5.63 |
| genome | 0.700 | 22 | 0.220 | 1.63 |

### Cutoff 2010
122 fields, 4,650 candidate pairs, **1050 positives**, base rate 0.2258

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.505 | 22 | 0.220 | 0.97 |
| pa | 0.808 | 91 | 0.910 | 4.03 |
| cn | 0.830 | 91 | 0.910 | 4.03 |
| aa | 0.836 | 91 | 0.910 | 4.03 |
| prereq | 0.809 | 93 | 0.930 | 4.12 |
| hybrid | 0.853 | 93 | 0.930 | 4.12 |
| genome | 0.704 | 35 | 0.350 | 1.55 |

### Cutoff 2014
122 fields, 4,365 candidate pairs, **1046 positives**, base rate 0.2396

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.490 | 22 | 0.220 | 0.92 |
| pa | 0.829 | 89 | 0.890 | 3.71 |
| cn | 0.847 | 93 | 0.930 | 3.88 |
| aa | 0.851 | 91 | 0.910 | 3.80 |
| prereq | 0.835 | 89 | 0.890 | 3.71 |
| hybrid | 0.864 | 86 | 0.860 | 3.59 |
| genome | 0.730 | 46 | 0.460 | 1.92 |

## Tuning cutoffs (weights were fitted here)

### Cutoff 1990
117 fields, 5,159 candidate pairs, **592 positives**, base rate 0.1148

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.510 | 14 | 0.140 | 1.22 |
| pa | 0.775 | 52 | 0.520 | 4.53 |
| cn | 0.811 | 59 | 0.590 | 5.14 |
| aa | 0.815 | 63 | 0.630 | 5.49 |
| prereq | 0.796 | 61 | 0.610 | 5.32 |
| hybrid | 0.844 | 73 | 0.730 | 6.36 |
| genome | 0.537 | 16 | 0.160 | 1.39 |

### Cutoff 1995
120 fields, 5,201 candidate pairs, **536 positives**, base rate 0.1031

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.498 | 14 | 0.140 | 1.36 |
| pa | 0.779 | 49 | 0.490 | 4.75 |
| cn | 0.812 | 60 | 0.600 | 5.82 |
| aa | 0.818 | 62 | 0.620 | 6.02 |
| prereq | 0.788 | 58 | 0.580 | 5.63 |
| hybrid | 0.840 | 67 | 0.670 | 6.50 |
| genome | 0.606 | 12 | 0.120 | 1.16 |

### Cutoff 2000
122 fields, 5,124 candidate pairs, **474 positives**, base rate 0.0925

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.494 | 6 | 0.060 | 0.65 |
| pa | 0.780 | 46 | 0.460 | 4.97 |
| cn | 0.813 | 53 | 0.530 | 5.73 |
| aa | 0.818 | 54 | 0.540 | 5.84 |
| prereq | 0.791 | 53 | 0.530 | 5.73 |
| hybrid | 0.845 | 54 | 0.540 | 5.84 |
| genome | 0.625 | 9 | 0.090 | 0.97 |

## Reading this

- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.
- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test cutoffs, which would inflate the result.
- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.
