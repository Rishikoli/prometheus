# How AI was used

Updated 14 Nov 2026. Lines in [square brackets] are things only the author can confirm; edit or delete them before submitting.

## Summary

Most of the code, tests, documentation and analysis scripts in this repository were written by Claude (Anthropic's AI model), working with
the author. The author set the idea, the rules for judging the result, and every decision below marked "author". The numbers in the README come
from real runs on the real data; nothing in them was typed in by hand.

## Which AI, doing what

| Part | Who | Notes |
|---|---|---|
| Idea and scope | author, with Claude in conversation | A patent-derived technology graph that grades its own predictions. [Say what you decided yourself.] |
| First version of the pipeline, store builder, queries, predictor, backtest, genome vectors, capsules, grader, command line, 53 tests | Claude (an earlier chat session) | Written with no access to real data, tested on synthetic toy data and a hand-made fixture only |
| Real-data run, backtest, sensitivity runs, A2, A2b, narrowed slice | Claude, run on the author's machine | Claude ran the pipeline and read the results; every number is read from files in `results/` |
| Three web pages (tree, matrix, 3D landscape), the server, the browser check script, 63 unit tests | Claude (Claude Code, model Sonnet 5.5, 13 to 14 Nov 2026) | Built to a design the author supplied and revised (`docs/DESIGN.md`) |
| Forecaster experiments A3 and A4 | six fresh Claude subagents | See below |
| Data download | author | The four PatentsView tables were downloaded by the author (a browser agent was used; Claude wrote its instructions) |
| Pass mark, choice of slice, which analyses to run and in what order, what to publish | author | The author wrote the gate rule before any result existed, and asked for each exploratory analysis |
| Demo video, Devpost text | [author to confirm] | |

## What the author decided (as it appears in the work)

- The pre-registered gate (hybrid must reach about twice the better baseline) and that a failure stays visible on every page.
- To run the sensitivity runs and the forecaster experiments, and in what order.
- That analyses defined after the NO-GO (A2, A2b, A4, the narrowed slice) are labelled exploratory, with the definition written into the README before the run.
- The design of the pages, including that fire colour means a predicted pair only, and which views to keep (tree as the front page, matrix and landscape as secondary).
- That Claude is not listed as a contributor in the git history; this document is the disclosure instead.

The author also supplied planning and review notes during the work (for example the A2/A3/A4 definitions and a Fisher exact check of the A4 hit counts).
Claude recomputed the Fisher p-values (0.209, 0.125, 1.0) and they matched. [Say which of these notes came from the author and which from another tool.]

## The forecaster experiments used AI too

In A3 and A4 the "forecaster" is a language model. Each of six agents was a fresh Claude subagent (the same model family that wrote the code), given only a sealed,
blinded capsule through a read-only Relate query tool. They were told to stay in their own folder; Claude audited their tool calls afterwards and none left it.
The exact prompts, briefs and helper are in `results/forecaster/` and `results/forecaster_a4/`. Because the forecasters and the author of the code are
the same model family, and a language model might recognise the shape of the graph, `docs/RESULTS.md` treats these as experiments, not as evidence of foresight.

## How the output was checked

- 63 unit tests, including a placebo (no planted structure, so the analyses must find nothing) and checks that nothing from a later year leaks into an earlier one.
- Regression checks after every pipeline change: the three original CSVs were regenerated from the real files and compared byte for byte; the main backtest and the original A2 were rerun and matched to the last digit.
- A browser script (`scripts/ui_check.py`, 91 checks) drives all three pages: clicks, keyboard, Play, picking in 3D, offline use, no console errors, the no-WebGL fallback.
- Counts shown on the pages were compared with the API; the as-of patent counts were compared with the end-of-data totals to confirm they differ.
- The author's own review. [Say what you read, ran and changed yourself.]

## Where AI output was wrong, and how it was caught

- A test for the new analysis failed only on some runs. Cause: toy data was built by looping over a set of strings, whose order changes between Python processes. Fixed; the real-data results were never affected (checked across hash seeds).
- The 3D view first drew every ranked gap as a needle and looked like a porcupine, not terrain. It now blurs by default and says so, with a switch back to the raw spikes.
- The 3D controls were swallowing the slider's arrow keys, and clicking a thin peak often missed it. Both were found by driving the page in a real browser and fixed.
- A first reading of a forecaster result ("lost to the size rule") was too strong; the test was saturated and could not separate the methods. The README now says so.
- An early draft said an analysis was declared before it was run when part of it had already been run. Corrected to say exactly that.

## AI-made material that is not code

- A concept image of a terrain-style page was shown to Claude by the author. It was used as an idea only. It is not in the repository, and its numbers did not match the real data, so none were used.
- Screenshots in `docs/screenshots/` are renders of the real pages on the real data.
- Writing in the README and docs was drafted by Claude and edited at the author's direction. [Confirm you have read it.]

## Data and third-party material

- Patent data: PatentsView (USPTO), downloaded 13 Nov 2026; see `docs/DATA.md` for the source and checksums. Real-data numbers are from the author's own run; toy-data numbers are labelled synthetic wherever they appear.
- Bundled, with licences kept next to them: D3 (ISC), Three.js (MIT), Newsreader and Instrument Sans fonts (SIL OFL). The database is Relate.
