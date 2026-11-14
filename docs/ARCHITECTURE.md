# Architecture

PROMETHEUS turns patent data into a small graph of technology fields, keeps it in one Relate file, and uses that graph three ways: to rank
which pairs of fields may combine next, to grade that ranking against history, and to let people and agents inspect the evidence.
About 2,500 lines of Python (`src/prometheus/`), three single-file web pages, nine `.cypher` queries, 63 unit tests and a 91-check browser script.

## 1. The whole picture

```mermaid
flowchart LR
  subgraph prep["Preparation (DuckDB, runs once)"]
    raw["PatentsView TSVs<br/>9.45M patents"] --> pipe["pipeline.py<br/>aggregate to fields and pairs"]
    pipe --> csv["small CSVs<br/>fields, combined_with, builds_on,<br/>co_assigned, field_year"]
  end
  csv --> build["build.py"]
  subgraph relate["Relate (single .rl files)"]
    store[("data/prometheus.rl<br/>the graph")]
    caps[("capsules/YYYY.rl<br/>sealed, blinded, one per year")]
  end
  build --> store
  csv --> capsule["capsule.py"] --> caps
  store --> graph["graph.py<br/>Cypher, read-only"]
  graph --> predict["predict.py / genome.py<br/>signals, scoring (Python)"]
  predict --> backtest["backtest.py / beyond.py<br/>grading"]
  graph --> server["server.py<br/>local read-only HTTP API"]
  predict --> server
  server --> pages["web pages<br/>tree, matrix, landscape"]
  caps --> mcp["relate serve --mcp<br/>read_cypher, get_schema"]
  mcp --> agent["forecaster agent"]
  agent --> grade["grade.py<br/>scores the 10 picks"]
  caps --> grade
```

## 2. What runs where

| Layer | Does | Does not do |
|---|---|---|
| **DuckDB** (`pipeline.py`) | the one heavy step: 9.45M patents, 6M classification rows and 10.9 GB of citations reduced to a few thousand rows | anything after the CSVs |
| **Relate** (`build.py`, `graph.py`, `capsule.py`, `genome.py`) | the single-file store, every query (as-of filters, evidence, ancestry, knock-out), the vector index for the genome, and the read-only MCP interface for agents | the heavy crunch, and the scoring math |
| **Python** (`predict.py`, `backtest.py`, `beyond.py`, `grade.py`) | pulls snapshots from Relate with Cypher, then scores in memory | writing to the store after the build |
| **Browser** | draws what the server returns; D3, Three.js and fonts are bundled, so it works offline | any computation that decides a result |

A test checks that the Cypher common-neighbours query (`queries/gaps_common_neighbours.cypher`) and the in-memory scorer agree on every pair, so the
scoring that happens in Python is not a different answer from the one Relate would give.

## 3. The data model

```
(:Field {code, title, firstYear, nPatents, genome})            a CPC subclass; genome is a vector with a vector index
(:Field)-[:COMBINED_WITH {firstYear, count}]->(:Field)          a < b, stored once, queried undirected
(:Field)-[:BUILDS_ON     {firstYear, count}]->(:Field)          the first field's patents cite the second's
(:Field)-[:CO_CLASSIFIED {firstYear}]->(:Field)                 some patent carries both classes (optional)
(:FieldYear {code, year, n})                                    patents of a field granted in one year (optional)
(:Meta {source, dataEndYear, slice, thresholds, asOf, blind})   provenance of this store
```

A field exists from the first year it has `MIN_FIELD_PATENTS_PER_YEAR` (5) patents. A pair is combined once `MIN_PAIR_PATENTS` (3) patents carry
both classes, and one field builds on another once `MIN_BUILDS_CITATIONS` (5) citations link them. All thresholds are in `config.py` and are written
into `Meta`, so a store says how it was made.

## 4. The invariant everything else protects: nothing from the future

A prediction made as of year Y must not be able to see anything after Y. The design enforces it in layers:

- **Time travel is a filter.** Every edge stores the year it first appeared, so "the graph as of Y" is `WHERE r.firstYear <= Y`, never a copy.
- **Totals never enter a feature.** `count` and `nPatents` are end-of-data totals and are display-only. Predictors, capsules and the knock-out use existence and `firstYear`.
  Where a size proxy needs counts (A2b), it sums per-year `FieldYear` rows up to the cutoff, never the total.
- **Capsules are blind.** A capsule holds only fields and edges with `firstYear` up to its year, opaque ids (`F0070`), empty titles and no counts.
  The id-to-code map is written next to it and never inside it, and ids are stable across capsules built with the same seed.
- **One tie-breaker for every method**, so ties never favour one of them (`predict.tie_breaker`).
- **Weights are tuned on 1990, 1995 and 2000 only** and frozen; results that count are on 2005, 2010 and 2014. The exploratory analyses (A2, A2b) load the frozen weights and never refit them.
- **Tests.** `test_predict_backtest.py` includes the no-peeking checks and a placebo (no planted structure, so the harness must say NO-GO). `test_beyond.py` runs the same harness on structured
  and placebo toy data. `test_capsule.py` checks sealing.

## 5. Modules

| File | Responsibility |
|---|---|
| `pipeline.py` | DuckDB: patents + classifications + citations to fields, combinations, dependencies, plus `co_assigned.csv` and `field_year.csv` |
| `slice.py`, `slices/*.json` | which CPC prefixes count as fields; `deeptech` (headline) and `deeptech_narrow` |
| `build.py` | CSVs to one `.rl` store (Cypher `UNWIND ... CREATE`, uniqueness constraint) |
| `graph.py` | `TechGraph`: read-only Cypher access, as-of views, ancestry, knock-out, bridge fields, stalled pairs |
| `predict.py` | `Snapshot` (the graph as of a year, in dictionaries), signals (common neighbours, Adamic-Adar, shared prerequisites, preferential attachment, genome), the hybrid, `top_gaps`, `breakthrough` |
| `genome.py` | a field's inheritance vector over founder fields, average-linkage clustering (the dendrogram), the vector index |
| `backtest.py` | cutoffs, positives, AUC, hits@K, lift, tuning, the gate |
| `beyond.py` | A2 and A2b: AUC on pairs a size proxy ranks in the bottom half, with a paired bootstrap |
| `capsule.py` | the sealed per-year store, the brief, the MCP config; the A4 eligibility brief |
| `grade.py` | scores a forecast against a later capsule, with optional `--pa-max` candidate restriction |
| `server.py` | the local read-only HTTP server and its API (section 7) |
| `cli.py` | `prometheus` commands: `toy pipeline build info gaps evidence knockout breakthrough backtest beyond genome relatives order serve capsule pa-threshold baseline-forecast grade` |
| `toy.py` | synthetic data with planted structure (and a placebo), only for tests and the demo; every number from it is labelled synthetic |
| `config.py` | every threshold and setting in one place; change them before looking at results, not after |

## 6. The agent path

```mermaid
sequenceDiagram
  participant C as capsule.py
  participant R as relate serve --mcp (read-only)
  participant A as forecaster agent
  participant G as grade.py
  C->>R: capsules/1995.rl (blind, sealed)
  A->>R: get_schema
  A->>R: read_cypher (MATCH ... only; writes refused)
  R-->>A: rows as JSON
  A->>G: forecast.json, 10 pairs, each with its Cypher
  G->>G: compare with the capsule ten years later, plus random, preferential attachment, graph predictor
```

The agent sees two tools and an anonymous graph. Every pair it submits must carry the Cypher that supports it, and the grader rejects pairs that are unknown or already combined.
Besides the sealed capsules, `prometheus agent-config` gives any MCP client read-only access to the full store, and `agent/PROMPT.md` briefs the agent
(schema, as-of rules, twelve checked Cypher recipes; example in `results/agent_ask/`). The six forecaster agents used a small helper that speaks the MCP protocol to `relate serve`, not Claude Desktop; exact prompts are in `results/forecaster*/`.

## 7. The web server and pages

`prometheus serve STORE` opens the store read-only on the main thread (a Relate connection is tied to the thread that opened it, so the server is deliberately single-threaded)
and serves static pages plus a JSON API. It binds to 127.0.0.1 and has no write route.

| Route | Returns |
|---|---|
| `/`, `/matrix`, `/landscape` | the tree (front page), the matrix and the 3D landscape; one HTML file each |
| `/api/meta` | fields, titles, domains, fixed genome order and merges, weights, backtest verdict |
| `/api/state?year=` | combined pairs as of the year and the top 1,500 candidate gaps with graph, size and beyond-size scores; cached per year |
| `/api/tree?year=` | the tree of shared foundations over the fields alive that year; cached |
| `/api/evidence?a=&b=&year=` | bridge fields, shared prerequisites, co-classified-since |
| `/api/knockout`, `/api/reach`, `/api/lineage`, `/api/stalled` | exposure with support counts, ancestors and descendants, the lineage forest, stalled pairs |
| `/api/check` | the backtest and A2 results, read from the two results files and nothing else |
| `/d3.min.js`, `/three.min.js`, `/OrbitControls.js`, `/fonts/*` | vendored libraries and fonts (a fixed whitelist, no path traversal) |

Rendering choices live in `docs/DESIGN.md`. Three decisions shape the code: arcs are drawn on a canvas under an SVG layer (4,000+ arcs stay smooth); the tree is re-laid-out per
year with each branch flipped to stay near last year's position; the landscape blurs its surface by default and says so, with a switch to the raw per-pair spikes.

## 8. Reproducibility and testing

- **From a clean clone:** `pip install -e ".[dev]"`, then `make demo` (synthetic data, a few seconds) and `make test`. The real-data store (`data/prometheus.rl`) and the capsules are committed, so `prometheus serve data/prometheus.rl` works without the raw data.
- **From the raw data:** `docs/DATA.md` gives the source, sizes, checksums and verified column names; the pipeline took about 30 seconds on the author's 12-core machine with a 3 GB memory limit (more on fewer cores).
- **Regression discipline:** after every pipeline change the three original CSVs were regenerated and compared byte for byte, and the main backtest and A2 were rerun and matched to the last digit.
- **Determinism:** results are identical across Python hash seeds (checked on the real data; one toy-data bug that depended on set order was found and fixed).
- **Browser checks:** `python scripts/ui_check.py` drives all three pages in a real browser (clicks, keyboard, Play, 3D picking, offline use, no console errors, the no-WebGL fallback). It is not part of `pytest` because it needs a browser.

## 9. Extending it

- **A new slice:** add `src/prometheus/slices/<name>.json` with CPC prefixes chosen from the titles, then `prometheus pipeline --slice <name>`. Declare it in the README before running.
- **A new size proxy for A2:** add it to `beyond.run` (as of the cutoff, never an end-of-data total) and declare it first.
- **A new view:** a new page reads `/api/state`, `/api/tree` and `/api/evidence`; keep fire colour for predicted pairs only and never put counts into a colour that implies a prediction.
- **A new store:** `prometheus build` accepts any CSV directory with the three required files; the optional two enable the stalled overlay and the patent-count proxy.

## 10. Known trade-offs

- Most fields are dated 1976, the first year of data, so ages are unreliable and the tree shows none.
- The server is single-threaded and local; it is a research tool, not a multi-user service.
- The heavy preparation is DuckDB and the scoring is Python, by design; Relate is the store, the query layer, the vector index and the agent interface.
- The pre-registered test failed. [RESULTS.md](RESULTS.md) lists what that does and does not mean.
