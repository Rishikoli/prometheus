# A2: beyond size (exploratory, no pass/fail threshold)

Source `patentsview`, slice `deeptech`. Subset: the candidate pairs that preferential attachment ranks in the bottom half. Weights are the ones tuned on 1990/1995/2000 and are not refitted: `{"cn": 2.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`. AUC with a 95% bootstrap interval over pairs (2000 resamples); pairs share fields, so the intervals are narrower than the real uncertainty.

## Cutoff 2005
2,443 of 4,887 candidate pairs, **113 positives** in the subset (base rate 0.046; 660 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.857 | 0.826 to 0.884 |
| cn | 0.802 | 0.768 to 0.834 |
| aa | 0.824 | 0.791 to 0.854 |
| prereq | 0.671 | 0.632 to 0.710 |
| genome | 0.691 | 0.645 to 0.734 |
| pa | 0.628 | 0.576 to 0.678 |
| random | 0.508 | 0.451 to 0.560 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.229 | +0.184 to +0.276 |
| cn | +0.174 | +0.132 to +0.219 |
| aa | +0.196 | +0.152 to +0.244 |
| prereq | +0.043 | -0.001 to +0.090 |
| genome | +0.063 | -0.004 to +0.127 |
| random | -0.120 | -0.201 to -0.037 |

## Cutoff 2010
2,325 of 4,650 candidate pairs, **171 positives** in the subset (base rate 0.074; 1050 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.821 | 0.791 to 0.851 |
| cn | 0.748 | 0.715 to 0.776 |
| aa | 0.770 | 0.738 to 0.800 |
| prereq | 0.694 | 0.660 to 0.726 |
| genome | 0.633 | 0.598 to 0.669 |
| pa | 0.657 | 0.617 to 0.696 |
| random | 0.518 | 0.470 to 0.564 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.165 | +0.130 to +0.199 |
| cn | +0.091 | +0.058 to +0.123 |
| aa | +0.113 | +0.080 to +0.148 |
| prereq | +0.037 | +0.001 to +0.072 |
| genome | -0.023 | -0.074 to +0.029 |
| random | -0.139 | -0.202 to -0.079 |

## Cutoff 2014
2,182 of 4,365 candidate pairs, **155 positives** in the subset (base rate 0.071; 1046 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.820 | 0.790 to 0.851 |
| cn | 0.780 | 0.747 to 0.811 |
| aa | 0.796 | 0.765 to 0.825 |
| prereq | 0.732 | 0.696 to 0.766 |
| genome | 0.611 | 0.582 to 0.643 |
| pa | 0.734 | 0.698 to 0.770 |
| random | 0.499 | 0.448 to 0.548 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.086 | +0.057 to +0.117 |
| cn | +0.046 | +0.018 to +0.075 |
| aa | +0.062 | +0.034 to +0.092 |
| prereq | -0.002 | -0.040 to +0.034 |
| genome | -0.123 | -0.167 to -0.074 |
| random | -0.235 | -0.298 to -0.171 |

## Reading this

- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.
- `pa` is a reference: it ranked these pairs in the bottom half, so its AUC here is not a prediction target.
- Exploratory: defined after seeing the NO-GO in the main backtest.
