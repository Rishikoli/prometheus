# A2b: beyond size, bottom half under both proxies (exploratory, no pass/fail threshold)

Source `patentsview`, slice `deeptech`. Subset: the candidate pairs in the bottom half under both the degree product and the patent-count product. Weights are the ones tuned on 1990/1995/2000 and are not refitted: `{"cn": 2.0, "aa": 2.0, "prereq": 1.0, "genome": 2.0}`. AUC with a 95% bootstrap interval over pairs (2000 resamples); pairs share fields, so the intervals are narrower than the real uncertainty.

## Cutoff 2005
1,964 of 4,887 candidate pairs, **85 positives** in the subset (base rate 0.043; 660 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.866 | 0.831 to 0.897 |
| cn | 0.818 | 0.782 to 0.852 |
| aa | 0.841 | 0.807 to 0.874 |
| prereq | 0.688 | 0.646 to 0.729 |
| genome | 0.691 | 0.640 to 0.745 |
| random | 0.555 | 0.492 to 0.615 |
| pa | 0.631 | 0.569 to 0.690 |
| patents | 0.584 | 0.527 to 0.639 |

Paired difference in AUC against the PA (degree product) on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.235 | +0.179 to +0.293 |
| cn | +0.187 | +0.140 to +0.235 |
| aa | +0.210 | +0.159 to +0.263 |
| prereq | +0.057 | +0.006 to +0.110 |
| genome | +0.060 | -0.020 to +0.142 |
| random | -0.076 | -0.166 to +0.013 |
| patents | -0.047 | -0.108 to +0.014 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.282 | +0.227 to +0.339 |
| cn | +0.234 | +0.175 to +0.294 |
| aa | +0.258 | +0.198 to +0.319 |
| prereq | +0.104 | +0.052 to +0.157 |
| genome | +0.107 | +0.039 to +0.179 |
| random | -0.029 | -0.106 to +0.048 |
| pa | +0.047 | -0.014 to +0.108 |

## Cutoff 2010
1,875 of 4,650 candidate pairs, **115 positives** in the subset (base rate 0.061; 1050 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.825 | 0.788 to 0.858 |
| cn | 0.766 | 0.729 to 0.800 |
| aa | 0.788 | 0.752 to 0.822 |
| prereq | 0.710 | 0.673 to 0.744 |
| genome | 0.617 | 0.570 to 0.661 |
| random | 0.504 | 0.444 to 0.561 |
| pa | 0.642 | 0.592 to 0.687 |
| patents | 0.604 | 0.554 to 0.654 |

Paired difference in AUC against the PA (degree product) on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.183 | +0.139 to +0.230 |
| cn | +0.124 | +0.087 to +0.163 |
| aa | +0.146 | +0.107 to +0.188 |
| prereq | +0.067 | +0.030 to +0.106 |
| genome | -0.025 | -0.093 to +0.046 |
| random | -0.138 | -0.212 to -0.062 |
| patents | -0.038 | -0.085 to +0.010 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.221 | +0.168 to +0.275 |
| cn | +0.162 | +0.106 to +0.219 |
| aa | +0.184 | +0.128 to +0.243 |
| prereq | +0.106 | +0.058 to +0.152 |
| genome | +0.013 | -0.051 to +0.078 |
| random | -0.100 | -0.175 to -0.026 |
| pa | +0.038 | -0.011 to +0.084 |

## Cutoff 2014
1,759 of 4,365 candidate pairs, **101 positives** in the subset (base rate 0.057; 1046 positives overall).

| Method | AUC | 95% interval |
|---|---|---|
| hybrid | 0.826 | 0.788 to 0.861 |
| cn | 0.805 | 0.768 to 0.839 |
| aa | 0.820 | 0.786 to 0.852 |
| prereq | 0.743 | 0.703 to 0.781 |
| genome | 0.581 | 0.543 to 0.616 |
| random | 0.497 | 0.439 to 0.555 |
| pa | 0.739 | 0.692 to 0.785 |
| patents | 0.666 | 0.619 to 0.715 |

Paired difference in AUC against the PA (degree product) on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.088 | +0.049 to +0.126 |
| cn | +0.066 | +0.030 to +0.100 |
| aa | +0.082 | +0.044 to +0.118 |
| prereq | +0.004 | -0.041 to +0.049 |
| genome | -0.158 | -0.217 to -0.099 |
| random | -0.241 | -0.323 to -0.162 |
| patents | -0.073 | -0.119 to -0.028 |

Paired difference in AUC against the patent-count product on the same pairs (same resamples, 95% interval):

| Method | AUC minus reference | 95% interval |
|---|---|---|
| hybrid | +0.161 | +0.110 to +0.211 |
| cn | +0.139 | +0.085 to +0.189 |
| aa | +0.155 | +0.100 to +0.206 |
| prereq | +0.077 | +0.030 to +0.121 |
| genome | -0.085 | -0.144 to -0.028 |
| random | -0.168 | -0.254 to -0.090 |
| pa | +0.073 | +0.028 to +0.119 |

## Reading this

- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.
- A reference's own AUC here is not a prediction target: it ranked these pairs in the bottom half.
- Exploratory: defined after seeing the NO-GO in the main backtest.
