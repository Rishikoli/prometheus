# 90-second demo video

Spoken by you, about 220 words at a calm pace. Every number below is in `docs/RESULTS.md` or `results/`; say them as written.
The agent parts show results already recorded in the repo, so say "here is", not "watch it run".

## Before you record

```bash
cd prometheus && source .venv/bin/activate
prometheus serve data/prometheus.rl --weights-from results/backtest.json      # leave running
```

- Browser at 1440 × 900, zoom 100%, two tabs ready:
  - Tab 1: `http://127.0.0.1:8765/#year=2005`
  - Tab 2: `http://127.0.0.1:8765/landscape#year=2005`
- Terminal (large font) with these two commands typed but not run:

```bash
cat results/agent_ask/G06E_G06M.md | sed -n '/Short answer/,/After 2005/p'
relate --database results/ledger/ledger.rl "MATCH (f:Forecast)-[:BY]->(a:Agent), (f)-[:ABOUT]->(pr:Pair) RETURN a.name AS agent, count(f) AS picks, sum(CASE WHEN pr.outcome = 'combined' THEN 1 ELSE 0 END) AS came_true ORDER BY agent"
```

## Script

| Time | On screen | You say |
|---|---|---|
| 0:00–0:12 | Tab 1, the tree. Point at the red "Prediction check failed" sentence, top right. | "Prometheus is a graph of 123 technology fields, built from nine million US patents and kept in one Relate file. It predicts which fields combine next, and checks itself against history. The check we set in advance failed: it barely beats 'big fields combine with big fields'." |
| 0:12–0:30 | Tick **Newest only**, drag the slider from 1995 to 2010, untick it. Click the first dashed fire arc; the evidence appears on the right. | "Each arc is a pair of fields that combined, and the slider moves through time. Fire marks pairs that haven't combined yet. Click one, and Relate answers live: the fields already combined with both, and what both build on." |
| 0:30–0:45 | Tab 2, the landscape. Drag to rotate, then hover a hill so its row and column light up. | "Here every pair is a point on a landscape. Hills are where high-ranked gaps cluster. Away from the big fields, the graph does beat size, though we found that after the failed test, so we call it exploratory." |
| 0:45–1:02 | Terminal: run the first command. | "Agents can use it too. This agent got only Relate's read-only tools and asked why two fields might combine. It found ten bridge fields, and that the pair had been stalled since 1977. It never combined." |
| 1:02–1:20 | Terminal: run the second command. | "And three agents wrote their forecasts into one shared Relate file, through one server, each in a single transaction. The grader wrote back what really happened. Every pick, its reason and its outcome sits in this one file." |
| 1:20–1:30 | Back to Tab 1, the tree at rest. | "One file, clone and run. The repo has the store, the code, and every result, including the one that failed." |

218 words. If you run long, drop the second sentence of the 0:30 line first.

## Checks before you publish the video

- The tree shows "Prediction check failed" (not "unavailable"): the server must be started with `--weights-from results/backtest.json`.
- `relate` must be on your PATH for the last terminal command (`~/.local/bin`). Relate prints a telemetry notice the first time; it can be turned off with `relate telemetry off`.
- Do not show your home folder path or the `*.auth-token` file on screen.
