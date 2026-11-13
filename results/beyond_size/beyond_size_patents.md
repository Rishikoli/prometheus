# A2b: beyond size, patent-count proxy (exploratory, no pass/fail threshold)

Source `patentsview`, slice `deeptech`. Subset: the candidate pairs in the bottom half by the product of the two fields' cumulative patent counts as of the cutoff. Weights are the ones tuned on 1990/1995/2000 and are not refitted: `{"cn": 2.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`. AUC with a 95% bootstrap interval over pairs (2000 resamples); pairs share fields, so the intervals are narrower than the real uncertainty.

## Cutoff 2005
2,443 of 4,887 candidate pairs, **143 positives** in the subset (base rate 0.059; 660 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.843 | 0.817 to 0.869 |
| cn | 0.784 | 0.755 to 0.813 |
| aa | 0.799 | 0.771 to 0.827 |
| prereq | 0.695 | 0.658 to 0.733 |
| genome | 0.659 | 0.617 to 0.701 |
| random | 0.522 | 0.475 to 0.572 |
| patents | 0.620 | 0.578 to 0.661 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.224 | +0.186 to +0.264 |
| cn | +0.164 | +0.126 to +0.202 |
| aa | +0.180 | +0.141 to +0.218 |
| prereq | +0.076 | +0.039 to +0.112 |
| genome | +0.040 | -0.021 to +0.104 |
| random | -0.097 | -0.163 to -0.033 |

## Cutoff 2010
2,325 of 4,650 candidate pairs, **223 positives** in the subset (base rate 0.096; 1050 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.837 | 0.811 to 0.860 |
| cn | 0.795 | 0.767 to 0.821 |
| aa | 0.807 | 0.780 to 0.831 |
| prereq | 0.754 | 0.724 to 0.781 |
| genome | 0.584 | 0.552 to 0.616 |
| random | 0.501 | 0.458 to 0.542 |
| patents | 0.665 | 0.628 to 0.699 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.172 | +0.142 to +0.203 |
| cn | +0.131 | +0.098 to +0.163 |
| aa | +0.142 | +0.109 to +0.176 |
| prereq | +0.090 | +0.060 to +0.118 |
| genome | -0.081 | -0.129 to -0.032 |
| random | -0.163 | -0.215 to -0.111 |

## Cutoff 2014
2,182 of 4,365 candidate pairs, **194 positives** in the subset (base rate 0.089; 1046 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.836 | 0.809 to 0.861 |
| cn | 0.812 | 0.785 to 0.838 |
| aa | 0.821 | 0.795 to 0.846 |
| prereq | 0.775 | 0.743 to 0.804 |
| genome | 0.584 | 0.556 to 0.613 |
| random | 0.498 | 0.456 to 0.541 |
| patents | 0.697 | 0.661 to 0.731 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.139 | +0.105 to +0.171 |
| cn | +0.115 | +0.081 to +0.148 |
| aa | +0.124 | +0.090 to +0.157 |
| prereq | +0.078 | +0.048 to +0.107 |
| genome | -0.113 | -0.157 to -0.071 |
| random | -0.199 | -0.259 to -0.144 |

## Reading this

- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.
- A reference's own AUC here is not a prediction target: it ranked these pairs in the bottom half.
- Exploratory: defined after seeing the NO-GO in the main backtest.
