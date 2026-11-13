# Backtest report

Source: `patentsview` · slice: `all` · data ends 2025 · horizon 10 years · top K = 100

Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out cutoffs were looked at once the weights were frozen.

## Gate

**NO-GO**. Hybrid lift@100 on held-out cutoffs is 8.73, the better baseline is 8.43, ratio 1.04 (threshold 2.0, a judgment call).

## Tuned weights

`{"cn": 2.0, "aa": 2.0, "prereq": 1.0, "genome": 1.0}`

## Held-out cutoffs (these count)

### Cutoff 2005
630 fields, 164,336 candidate pairs, **9440 positives**, base rate 0.0574

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.502 | 8 | 0.080 | 1.39 |
| pa | 0.792 | 57 | 0.570 | 9.92 |
| cn | 0.849 | 61 | 0.610 | 10.62 |
| aa | 0.853 | 63 | 0.630 | 10.97 |
| prereq | 0.815 | 63 | 0.630 | 10.97 |
| hybrid | 0.856 | 58 | 0.580 | 10.10 |
| genome | 0.678 | 13 | 0.130 | 2.26 |

### Cutoff 2010
630 fields, 161,002 candidate pairs, **16482 positives**, base rate 0.1024

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.505 | 9 | 0.090 | 0.88 |
| pa | 0.801 | 82 | 0.820 | 8.01 |
| cn | 0.852 | 86 | 0.860 | 8.40 |
| aa | 0.856 | 88 | 0.880 | 8.60 |
| prereq | 0.817 | 74 | 0.740 | 7.23 |
| hybrid | 0.856 | 83 | 0.830 | 8.11 |
| genome | 0.715 | 64 | 0.640 | 6.25 |

### Cutoff 2014
630 fields, 156,759 candidate pairs, **17659 positives**, base rate 0.1127

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.500 | 12 | 0.120 | 1.07 |
| pa | 0.805 | 83 | 0.830 | 7.37 |
| cn | 0.851 | 88 | 0.880 | 7.81 |
| aa | 0.854 | 88 | 0.880 | 7.81 |
| prereq | 0.817 | 76 | 0.760 | 6.75 |
| hybrid | 0.854 | 90 | 0.900 | 7.99 |
| genome | 0.736 | 65 | 0.650 | 5.77 |

## Tuning cutoffs (weights were fitted here)

### Cutoff 1990
617 fields, 169,860 candidate pairs, **9496 positives**, base rate 0.0559

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.509 | 9 | 0.090 | 1.61 |
| pa | 0.783 | 55 | 0.550 | 9.84 |
| cn | 0.865 | 69 | 0.690 | 12.34 |
| aa | 0.869 | 69 | 0.690 | 12.34 |
| prereq | 0.838 | 66 | 0.660 | 11.81 |
| hybrid | 0.873 | 63 | 0.630 | 11.27 |
| genome | 0.488 | 10 | 0.100 | 1.79 |

### Cutoff 1995
624 fields, 169,410 candidate pairs, **8762 positives**, base rate 0.0517

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.494 | 8 | 0.080 | 1.55 |
| pa | 0.777 | 59 | 0.590 | 11.41 |
| cn | 0.851 | 67 | 0.670 | 12.95 |
| aa | 0.855 | 69 | 0.690 | 13.34 |
| prereq | 0.821 | 63 | 0.630 | 12.18 |
| hybrid | 0.861 | 65 | 0.650 | 12.57 |
| genome | 0.530 | 5 | 0.050 | 0.97 |

### Cutoff 2000
630 fields, 168,275 candidate pairs, **7273 positives**, base rate 0.0432

| Method | AUC | hits@100 | precision@100 | lift@100 |
|---|---|---|---|---|
| random | 0.508 | 3 | 0.030 | 0.69 |
| pa | 0.784 | 47 | 0.470 | 10.87 |
| cn | 0.849 | 54 | 0.540 | 12.49 |
| aa | 0.852 | 55 | 0.550 | 12.73 |
| prereq | 0.817 | 55 | 0.550 | 12.73 |
| hybrid | 0.856 | 55 | 0.550 | 12.73 |
| genome | 0.600 | 6 | 0.060 | 1.39 |

## Reading this

- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.
- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test cutoffs, which would inflate the result.
- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.
