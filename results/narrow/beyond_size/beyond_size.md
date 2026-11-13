# A2: beyond size (exploratory, no pass/fail threshold)

Source `patentsview`, slice `deeptech_narrow`. Subset: the candidate pairs that preferential attachment ranks in the bottom half. Weights are the ones tuned on 1990/1995/2000 and are not refitted: `{"cn": 1.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`. AUC with a 95% bootstrap interval over pairs (2000 resamples); pairs share fields, so the intervals are narrower than the real uncertainty.

## Cutoff 2005
1,794 of 3,589 candidate pairs, **128 positives** in the subset (base rate 0.071; 575 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.843 | 0.811 to 0.873 |
| cn | 0.761 | 0.725 to 0.795 |
| aa | 0.785 | 0.750 to 0.819 |
| prereq | 0.642 | 0.598 to 0.682 |
| genome | 0.670 | 0.627 to 0.712 |
| pa | 0.612 | 0.560 to 0.661 |
| random | 0.555 | 0.501 to 0.608 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.232 | +0.184 to +0.281 |
| cn | +0.150 | +0.111 to +0.187 |
| aa | +0.174 | +0.133 to +0.213 |
| prereq | +0.030 | -0.012 to +0.070 |
| genome | +0.058 | -0.009 to +0.133 |
| random | -0.057 | -0.129 to +0.019 |

## Cutoff 2010
1,692 of 3,384 candidate pairs, **177 positives** in the subset (base rate 0.105; 924 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.808 | 0.779 to 0.839 |
| cn | 0.721 | 0.685 to 0.757 |
| aa | 0.741 | 0.706 to 0.775 |
| prereq | 0.668 | 0.630 to 0.707 |
| genome | 0.653 | 0.615 to 0.688 |
| pa | 0.622 | 0.579 to 0.664 |
| random | 0.477 | 0.431 to 0.523 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.186 | +0.149 to +0.223 |
| cn | +0.099 | +0.071 to +0.128 |
| aa | +0.119 | +0.090 to +0.149 |
| prereq | +0.046 | +0.014 to +0.079 |
| genome | +0.031 | -0.030 to +0.091 |
| random | -0.145 | -0.208 to -0.083 |

## Cutoff 2014
1,568 of 3,136 candidate pairs, **166 positives** in the subset (base rate 0.106; 911 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.804 | 0.770 to 0.834 |
| cn | 0.759 | 0.727 to 0.789 |
| aa | 0.773 | 0.742 to 0.803 |
| prereq | 0.706 | 0.669 to 0.740 |
| genome | 0.628 | 0.594 to 0.660 |
| pa | 0.704 | 0.667 to 0.739 |
| random | 0.481 | 0.434 to 0.526 |

Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):

| Method | AUC minus PA AUC | 95% interval |
|---|---|---|
| hybrid | +0.100 | +0.071 to +0.132 |
| cn | +0.054 | +0.026 to +0.080 |
| aa | +0.069 | +0.040 to +0.096 |
| prereq | +0.001 | -0.038 to +0.038 |
| genome | -0.077 | -0.125 to -0.027 |
| random | -0.223 | -0.281 to -0.166 |

## Reading this

- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.
- `pa` is a reference: it ranked these pairs in the bottom half, so its AUC here is not a prediction target.
- Exploratory: defined after seeing the NO-GO in the main backtest.
