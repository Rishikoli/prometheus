# Backtest report

Source: `patentsview` · slice: `deeptech` · data ends 2025 · horizon 10 years · top K = 100

Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out cutoffs were looked at once the weights were frozen.

## Gate

**NO-GO**. Hybrid lift@100 on held-out cutoffs is 4.79, the better baseline is 4.44, ratio 1.08 (threshold 2.0, a judgment call).

## Tuned weights

`{"cn": 1.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`

## Held-out cutoffs (these count)

### Cutoff 2005
122 fields, 5,256 candidate pairs, **639 positives**, base rate 0.1216

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.505 | 15 | 0.150 | 1.23 |
| pa | 0.792 | 61 | 0.610 | 5.02 |
| cn | 0.826 | 68 | 0.680 | 5.59 |
| aa | 0.832 | 66 | 0.660 | 5.43 |
| prereq | 0.791 | 72 | 0.720 | 5.92 |
| hybrid | 0.859 | 72 | 0.720 | 5.92 |
| genome | 0.732 | 26 | 0.260 | 2.14 |

### Cutoff 2010
122 fields, 5,022 candidate pairs, **1014 positives**, base rate 0.2019

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.503 | 23 | 0.230 | 1.14 |
| pa | 0.815 | 87 | 0.870 | 4.31 |
| cn | 0.845 | 89 | 0.890 | 4.41 |
| aa | 0.850 | 89 | 0.890 | 4.41 |
| prereq | 0.815 | 93 | 0.930 | 4.61 |
| hybrid | 0.864 | 89 | 0.890 | 4.41 |
| genome | 0.737 | 47 | 0.470 | 2.33 |

### Cutoff 2014
122 fields, 4,744 candidate pairs, **1008 positives**, base rate 0.2125

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.490 | 16 | 0.160 | 0.75 |
| pa | 0.826 | 85 | 0.850 | 4.00 |
| cn | 0.848 | 87 | 0.870 | 4.09 |
| aa | 0.853 | 86 | 0.860 | 4.05 |
| prereq | 0.836 | 85 | 0.850 | 4.00 |
| hybrid | 0.863 | 86 | 0.860 | 4.05 |
| genome | 0.750 | 53 | 0.530 | 2.49 |

## Tuning cutoffs (weights were fitted here)

### Cutoff 1990
117 fields, 5,494 candidate pairs, **556 positives**, base rate 0.1012

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.502 | 12 | 0.120 | 1.19 |
| pa | 0.772 | 56 | 0.560 | 5.53 |
| cn | 0.819 | 65 | 0.650 | 6.42 |
| aa | 0.826 | 68 | 0.680 | 6.72 |
| prereq | 0.814 | 61 | 0.610 | 6.03 |
| hybrid | 0.858 | 69 | 0.690 | 6.82 |
| genome | 0.568 | 18 | 0.180 | 1.78 |

### Cutoff 1995
120 fields, 5,559 candidate pairs, **526 positives**, base rate 0.0946

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.482 | 9 | 0.090 | 0.95 |
| pa | 0.778 | 46 | 0.460 | 4.86 |
| cn | 0.812 | 60 | 0.600 | 6.34 |
| aa | 0.817 | 60 | 0.600 | 6.34 |
| prereq | 0.786 | 53 | 0.530 | 5.60 |
| hybrid | 0.837 | 58 | 0.580 | 6.13 |
| genome | 0.628 | 11 | 0.110 | 1.16 |

### Cutoff 2000
122 fields, 5,505 candidate pairs, **483 positives**, base rate 0.0877

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.500 | 13 | 0.130 | 1.48 |
| pa | 0.802 | 45 | 0.450 | 5.13 |
| cn | 0.838 | 58 | 0.580 | 6.61 |
| aa | 0.844 | 58 | 0.580 | 6.61 |
| prereq | 0.797 | 55 | 0.550 | 6.27 |
| hybrid | 0.864 | 57 | 0.570 | 6.50 |
| genome | 0.653 | 6 | 0.060 | 0.68 |

## Reading this

- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.
- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test cutoffs, which would inflate the result.
- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.
