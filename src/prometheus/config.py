"""Settings that define what counts as a field, a combination and a dependency, and
how predictions are graded.

They are deliberately explicit: every result in this project depends on them, so
they are stated in one place and echoed in the README. Change them *before* looking
at results, not after.
"""

# ---- what the graph means --------------------------------------------------

# A technology field (CPC subclass) "exists" from the first year with this many
# patents classified in it.
MIN_FIELD_PATENTS_PER_YEAR = 5

# Two fields count as "combined" once this many patents carry both classifications.
MIN_PAIR_PATENTS = 3

# Field A "builds on" field B once this many citations link A's patents to B's.
MIN_BUILDS_CITATIONS = 5

# First grant year in PatentsView.
DEFAULT_MIN_YEAR = 1976

# ---- knock-out cascade -----------------------------------------------------

# How much of the exposure is passed on per hop, and how many rounds are run.
CASCADE_GAMMA = 0.85
CASCADE_ITERATIONS = 12

# ---- backtest --------------------------------------------------------------

# A pair is a "positive" if it first combines within this many years after the cutoff.
HORIZON = 10

# Method weights are tuned on the early cutoffs and reported on the later ones.
TUNE_CUTOFFS = (1990, 1995, 2000)
TEST_CUTOFFS = (2005, 2010, 2014)

# Precision/lift are measured on the top K ranked candidate pairs.
TOP_K = 100

# Go/no-go gate: the best method's lift@K on the held-out cutoffs must reach this
# multiple of the better of the two baselines (random, preferential attachment).
# 2.0 is a judgment call, not a number derived from data.
GATE_LIFT = 2.0

# A cutoff with fewer positives than this is labelled low-confidence.
LOW_POSITIVES = 30

# ---- genome ----------------------------------------------------------------

# A field's genome is its inheritance from this many "founder" fields (the most
# built-upon ones that exist at the chosen year).
GENOME_FOUNDERS = 64

# ---- display only ------------------------------------------------------------

# A pair is "stalled" in a year when at least one patent has carried both classes for this many years or more
# and the pair is still under the combination threshold. Shown as an overlay; it never enters a score.
STALLED_MIN_YEARS = 3
