# Demo script (about 4 minutes)

Order matters: say the failed test first. Everything after it is labelled exploratory. All numbers are in the README and
were produced by the commands shown; read them from the page, do not improvise new ones.

## Before you start (once)

```bash
cd prometheus && source .venv/bin/activate
export PATH=$HOME/.local/bin:$PATH            # for the `relate` CLI
prometheus serve data/prometheus.rl --weights-from results/backtest.json --open   # http://127.0.0.1:8765/
```

The page needs no internet (D3 and the fonts are bundled). Have two terminal tabs ready: one for the server, one in
`~/prometheus-forecaster/2005` for the MCP step. If the browser tab misbehaves, these links open a specific view:

| View | Link |
|---|---|
| The tree at 2005 | `http://127.0.0.1:8765/#year=2005` |
| Top gap open, with evidence | `http://127.0.0.1:8765/#year=2005&gap=1` |
| The landscape, with a pair selected | `http://127.0.0.1:8765/landscape#year=2010&gap=3` |
| What breaks, H01L | `http://127.0.0.1:8765/#year=2005&mode=breaks&field=H01L` |
| Show what happened, details open | `http://127.0.0.1:8765/#year=2005&happened=1&gap=2&details=1` |

## 1. The claim, and the result that failed (30 s)

> "PROMETHEUS is a technology graph built from nine million US patents, kept in one Relate file. Before we looked at any
> result we wrote down a pass mark: our predictor has to beat the simple rule 'big fields combine with big fields' by 2 times.
> **It did not. 4.44 against 4.26, a ratio of 1.04.** The badge at the top of the page says NO-GO."

Point at the red badge. Do not soften it.

## 2. Why it failed, and the tree (60 s)

The page opens on 2005: 123 fields around a circle, grouped by shared foundations. Drag the slider (or press Play) and arcs build up:
blue is a pair that already combined, darker is newer; the dashed fire arcs are pairs the model ranks high that have not combined.

> "The graph does predict, AUC 0.84 against 0.5 for random. But by 2010 the size rule already reaches 91% of the best score
> that is even possible, so the headline test measured the one place where every method looks the same." Open **Details**
> (top right) to show the table.

## 3. Exploratory: what the graph adds beyond size (45 s)

Switch **Score** between **Size alone**, **Graph score** and **Beyond size**, and watch the dashed arcs and the Top gaps list
change. Click a dashed arc (or `#year=2005&gap=1`): the margin note gives the bridge fields and shared prerequisites, each one
a Cypher query on the store, and the ranks side by side. Turn on **Show what happened** at 2005 to see which gaps came true.

> "Size alone and the graph disagree on many pairs. On the pairs the size rule ranks in the bottom half, the graph beats it by
> 0.23, 0.17 and 0.09 AUC at 2005, 2010 and 2014, with intervals that exclude zero. We defined that test after seeing the
> failure, so it is exploratory, and the advantage shrinks over time."

**Optional (20 s):** click **Landscape** in the top bar and drag to rotate: "The same grid as terrain. Low blue ground is pairs that already combined; the orange hills are where the graph ranks many gaps among related fields. Switch Surface to Each pair to see every ranked pair as its own spike." Then **Matrix**. "The tree shows the top gaps. This is every pair: blue already combined, fire the ones the graph ranks highest. Same slider, same evidence."

## 4. Dependencies and what breaks (30 s)

Click a field, then **Dependencies**, then **What breaks**. Read the number of citing links in the note.

> "The tree shows no ages: 109 of our 123 fields were already around in 1976, the first year of data. The knock-out shows
> dependency along citations, not cause, and says how many links each number rests on."

## 5. Relate and an agent (60 s)

In the second terminal, from `~/prometheus-forecaster/2005` (a sealed 2005 capsule, field names replaced by ids, no counts):

```bash
python3 query.py "MATCH (f:Field) RETURN f LIMIT 1"        # an id, an empty title, no counts
python3 query.py "CREATE (:Hack {x:1})"                    # refused: Only MATCH queries are allowed
```

> "This is the sealed capsule an agent gets, served read-only over MCP. We gave fresh agents only Relate's two tools,
> `get_schema` and `read_cypher`. For 1995, 2005 and 2010 they forecast ten pairs each, each with its Cypher. Among the pairs
> the size rule does not rank as easy, they hit **9 of 30 where chance predicts 1.5**, about the same as our predictor
> (10 of 30). Against a control that just picks the biggest eligible pairs (4 of 30) it is roughly double, but that is
> suggestive, not established (p = 0.21)."

## 6. Close (15 s)

> "So: a pre-registered test that failed and why; an exploratory result that the graph adds something beyond size; and
> caveats we list ourselves: small samples, overlapping picks, the same model family in the experiment, and ages that start at
> 1976. Everything reproduces from four public files, with checksums, in `docs/DATA.md`."

## Questions to expect

- *"Did you move the goalposts?"* No: the gate, weights and slice were fixed first and the NO-GO stands; A2 and A4 are labelled
  exploratory and were declared in the README before they ran (A4's rule before any agent ran).
- *"Could the agent know the history?"* Possibly. Field names are hidden and the agents reasoned by counting shared partners,
  but blinding cannot prove it. The exact prompts are in `results/forecaster/` and `results/forecaster_a4/`.
- *"Is 9 of 30 better than your predictor?"* No, it matches it (9 vs 10, p = 1.0).
- *"Why is PA not just 'size'?"* It is one proxy (degree product). A different size proxy was not tested.
