<a id="results"></a>
<img src="../assets/readme/headers/results-00.svg" width="100%" alt="Results">

Measured on real PatentsView data: 9.45 million US patents, 1976 to 2025, 123 deep-tech fields. Predictions are made as of a
year and graded on the ten years that followed; nothing after the cutoff is visible to the predictor. Full tables are in `results/`.

<a id="the-graph-predicts"></a>
<img src="../assets/readme/headers/results-01.svg" width="100%" alt="01. The graph predicts">

Weights were tuned on 1990 to 2000 and frozen, then tested on later years. On every held-out year the graph ranks the pairs that
went on to combine well above chance, and above the size rule ("big fields combine with big fields"):

| Held out | Pairs that combined within 10 years | Graph AUC | Size rule AUC | Random |
|---|---|---|---|---|
| 2005 | 660 | **0.843** | 0.777 | 0.50 |
| 2010 | 1,050 | **0.853** | 0.808 | 0.50 |
| 2014 | 1,046 | **0.864** | 0.829 | 0.50 |

The stricter test we set in advance, twice the size rule's hit rate in the top 100, was not met (1.04 times). At the very top
of the ranking the biggest fields combine almost regardless of method: by 2010 the size rule already reaches 91% of the best
possible score there, so that test leaves no room to show more. The graph's lead is below the top, as the next section shows.

<a id="where-the-graph-adds-most"></a>
<img src="../assets/readme/headers/results-02.svg" width="100%" alt="02. Where the graph adds most">

On the pairs the size rule ranks in its bottom half, the graph's AUC is 0.82 to 0.86, and it beats the size rule on the same
pairs at every cutoff. The 95% intervals exclude zero everywhere:

| Held out | Graph minus size rule | With patent counts as size | On a narrower set of 110 fields |
|---|---|---|---|
| 2005 | **+0.229** (+0.184 to +0.276) | **+0.224** (+0.186 to +0.264) | **+0.232** (+0.184 to +0.281) |
| 2010 | **+0.165** (+0.130 to +0.199) | **+0.172** (+0.142 to +0.203) | **+0.186** (+0.149 to +0.223) |
| 2014 | **+0.086** (+0.057 to +0.117) | **+0.139** (+0.105 to +0.171) | **+0.100** (+0.071 to +0.132) |

Common neighbours and Adamic-Adar carry most of it. On a placebo with no structure the same harness returns 0.5, so it does not
invent skill (`tests/test_beyond.py`).

<a id="agents-reading-relate"></a>
<img src="../assets/readme/headers/results-03.svg" width="100%" alt="03. Agents reading Relate">

Fresh agents got only Relate's read-only MCP tools (`get_schema`, `read_cypher`) on a sealed, blinded capsule of the graph, with
fields renamed so they could not recall history. Each picked ten pairs, outside the easy big-field pairs, with a Cypher query as
evidence for every pick. Graded on the capsule ten years later:

| Round | Came true | Graph alone | Size-only control | Chance |
|---|---|---|---|---|
| 1995 | 3 / 10 | 2 / 10 | 1 / 10 | 0.3 |
| 2005 | 3 / 10 | 4 / 10 | 2 / 10 | 0.5 |
| 2010 | 3 / 10 | 4 / 10 | 1 / 10 | 0.7 |
| **Total** | **9 / 30** | **10 / 30** | **4 / 30** | **1.5** |

About six times chance, level with the graph predictor, and every one of the 30 picks came with a query the grader accepted.
Prompts, briefs and grades: `results/forecaster_a4/`. You can try the same rounds: [challenge/README.md](../challenge/README.md).

<a id="one-shared-ledger"></a>
<img src="../assets/readme/headers/results-04.svg" width="100%" alt="04. One shared ledger">

Three agents forecast at the same time and wrote into one Relate file through a single `relate serve --mcp` server, each in one
transaction: 30 forecasts about 17 distinct pairs, 5 picked by all three. The grader wrote the outcomes back into the same file.
A stress test of 100 concurrent writes lost none and created no duplicates. Details: [results/ledger/REPORT.md](../results/ledger/REPORT.md).

<a id="limitations"></a>
<img src="../assets/readme/headers/results-05.svg" width="100%" alt="05. Limitations">

- The beyond-size and agent results were defined after the main test, and after a first agent test at the top of the ranking
  could not separate methods (everything scored nearly 10 of 10 there). They are exploratory.
- Samples are small: 30 agent picks, and pairs share fields, so the intervals are narrower than the real uncertainty.
- 109 of 123 fields already exist in 1976, the first year of data, so field ages are unknown; old patents carry today's classes.
- The agents are one model family. Blinding reduces hindsight but cannot prove it is absent.

<a id="reproduce"></a>
<img src="../assets/readme/headers/results-06.svg" width="100%" alt="06. Reproduce">

```bash
prometheus backtest data/prometheus.rl --out results                                     # the main test
prometheus beyond data/prometheus.rl --weights-from results/backtest.json                # beyond size (add --proxy patents)
prometheus challenge score results/forecaster_a4/forecast_2005.json --round 2005         # an agent round, regraded
```
