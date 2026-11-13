# Backtest report

Source: `patentsview` · slice: `deeptech_narrow` · data ends 2025 · horizon 10 years · top K = 100

Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out cutoffs were looked at once the weights were frozen.

## Gate

**NO-GO**. Hybrid lift@100 on held-out cutoffs is 3.74, the better baseline is 3.52, ratio 1.06 (threshold 2.0, a judgment call).

## Tuned weights

`{"cn": 1.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`

## Held-out cutoffs (these count)

### Cutoff 2005
109 fields, 3,589 candidate pairs, **575 positives**, base rate 0.1602

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.531 | 18 | 0.180 | 1.12 |
| pa | 0.746 | 69 | 0.690 | 4.31 |
| cn | 0.778 | 71 | 0.710 | 4.43 |
| aa | 0.784 | 72 | 0.720 | 4.49 |
| prereq | 0.752 | 79 | 0.790 | 4.93 |
| hybrid | 0.823 | 76 | 0.760 | 4.74 |
| genome | 0.710 | 29 | 0.290 | 1.81 |

### Cutoff 2010
109 fields, 3,384 candidate pairs, **924 positives**, base rate 0.2730

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.489 | 30 | 0.300 | 1.10 |
| pa | 0.788 | 91 | 0.910 | 3.33 |
| cn | 0.814 | 92 | 0.920 | 3.37 |
| aa | 0.819 | 92 | 0.920 | 3.37 |
| prereq | 0.793 | 93 | 0.930 | 3.41 |
| hybrid | 0.839 | 93 | 0.930 | 3.41 |
| genome | 0.730 | 51 | 0.510 | 1.87 |

### Cutoff 2014
109 fields, 3,136 candidate pairs, **911 positives**, base rate 0.2905

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.505 | 32 | 0.320 | 1.10 |
| pa | 0.814 | 85 | 0.850 | 2.93 |
| cn | 0.838 | 91 | 0.910 | 3.13 |
| aa | 0.841 | 89 | 0.890 | 3.06 |
| prereq | 0.823 | 90 | 0.900 | 3.10 |
| hybrid | 0.854 | 89 | 0.890 | 3.06 |
| genome | 0.747 | 62 | 0.620 | 2.13 |

## Tuning cutoffs (weights were fitted here)

### Cutoff 1990
104 fields, 3,852 candidate pairs, **534 positives**, base rate 0.1386

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.524 | 16 | 0.160 | 1.15 |
| pa | 0.755 | 52 | 0.520 | 3.75 |
| cn | 0.785 | 60 | 0.600 | 4.33 |
| aa | 0.790 | 61 | 0.610 | 4.40 |
| prereq | 0.765 | 60 | 0.600 | 4.33 |
| hybrid | 0.827 | 69 | 0.690 | 4.98 |
| genome | 0.542 | 19 | 0.190 | 1.37 |

### Cutoff 1995
107 fields, 3,884 candidate pairs, **491 positives**, base rate 0.1264

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.511 | 12 | 0.120 | 0.95 |
| pa | 0.760 | 52 | 0.520 | 4.11 |
| cn | 0.786 | 57 | 0.570 | 4.51 |
| aa | 0.792 | 59 | 0.590 | 4.67 |
| prereq | 0.762 | 57 | 0.570 | 4.51 |
| hybrid | 0.818 | 63 | 0.630 | 4.98 |
| genome | 0.630 | 15 | 0.150 | 1.19 |

### Cutoff 2000
109 fields, 3,810 candidate pairs, **426 positives**, base rate 0.1118

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.509 | 11 | 0.110 | 0.98 |
| pa | 0.758 | 45 | 0.450 | 4.02 |
| cn | 0.787 | 52 | 0.520 | 4.65 |
| aa | 0.792 | 52 | 0.520 | 4.65 |
| prereq | 0.770 | 54 | 0.540 | 4.83 |
| hybrid | 0.827 | 58 | 0.580 | 5.19 |
| genome | 0.634 | 13 | 0.130 | 1.16 |

## Reading this

- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.
- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test cutoffs, which would inflate the result.
- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.
