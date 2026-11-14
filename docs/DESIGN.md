# PROMETHEUS page: complete design (tree of life only)

Behaviour, data and the predictors do not change. Only the look, the layout, the words and how the data is drawn change. The
page has one representation: a circular tree of life of the technology fields, with combinations drawn as arcs through it. The
old heatmap is removed from the page (keep its code under a hidden `?view=matrix` route only if it helps make README
screenshots; delete it otherwise).

Trade-off the author accepted: the tree cannot show all candidate pairs at once (about 5,000 at 1998). It shows the top gaps, plus
every candidate partner of whichever field is selected. Do not try to recover the full matrix on this page.

## 1. The idea
A wall chart of technology. 123 fields sit around a circle, grouped by how similar their foundations are. Pairs of fields that
combined are bundled arcs through the middle, shaded by the year they first combined, so the picture builds up like layers as the
slider moves. Pairs that have not combined yet but are likely to are dashed fire-coloured arcs. Fire is used for nothing else
(Prometheus stole fire). Everything else stays quiet. The memorable thing is the tree and the fire; do not add a second one.

## 2. What the picture claims, and must not claim
- The tree comes from **similarity of foundations** (genome clustering on the "builds on" graph). It is not a tree of descent. Call
  it "the family tree of shared foundations" in the interface. Never say "evolved from" in labels.
- The data starts in 1976, and 109 of 123 fields already existed then. So the tree does not grow over time and no ages are shown.
  Combinations (arcs) change over time; branches do not.
- A dashed arc is a ranking, not a probability. The prediction check failed on the top 100 pairs, and that stays visible (section 8).
- If `Meta.source` is `toy`, show a permanent SYNTHETIC banner across the top.
- Counts are display-only (leaf size, tooltips). They never feed any score or any colour that implies a prediction.

## 3. Tokens

Colour (checked with the data-viz palette validator against the paper colour: the ramps pass, steps are distinguishable, the
lightest step of each has at least 2:1 contrast, and history vs fire stay separable under red-green colour blindness. The grey ramp
was validated separately on the paper colour; contrast on paper is 2.2, 3.9, 7.2 and 14.5:1):
```css
:root {
  --paper:   #EEF1EC;  /* page and plate: cool grey-green, not cream */
  --ink:     #16211C;  /* text, branches, selected state */
  --ink-2:   #4B5750;  /* secondary text */
  --hair:    #C9D0C8;  /* hairlines, only where two kinds of content meet */
  --wedge:   #E5E9E2;  /* every second domain wedge on the rim (no hue) */
  /* history of combinations: one hue, by AGE relative to the slider year; oldest lightest -> newest darkest */
  --hist-1: #80A3CF; --hist-2: #5589C2; --hist-3: #3470AF; --hist-4: #235791; --hist-5: #143E6B;
  /* gaps: one hue, three steps (terciles of the selected score). The lighter #EE8F6A was dropped: 2.1:1 on paper */
  --fire-2: #E4572E; --fire-3: #BF3A16; --fire-4: #8E2208;
  /* what breaks: its own ramp, grey, light -> dark exposure. Never fire: fire means "predicted pair" only */
  --grey-1: #9AA59E; --grey-2: #6E7A73; --grey-3: #46524B; --grey-4: #16211C;
}
```
- History shading is by **age relative to the slider year**, not by absolute year, so the newest arcs are always the darkest.
  Age 0 to 3 years: `--hist-5`; 4 to 6: `--hist-4`; 7 to 10: `--hist-3` (these three all have at least 4.5:1 on paper). Older than 10 years:
  `--hist-2` (11 to 20) and `--hist-1` (over 20), drawn at 25% opacity and 0.7 px so they read as faint texture where they
  overlap. The legend names the age bands ("combined in the last 3 years", and so on); the tooltip gives the exact year. A pair
  first combined in 1976 is labelled "already combined when the data starts (1976)", never as a 1976 event.
- Gap shading: terciles of the selected score among the gaps currently drawn, mapped to `--fire-2`, `--fire-3`, `--fire-4`.
- Fire is used **only** for predicted (not yet combined) pairs. "Show what happened" keeps that rule: an arc that came true was still a
  predicted pair. "What breaks" uses the grey ramp instead.
- No other hues. Domains are told apart by rim position and direct labels, never by colour. If domain colours are wanted later, use the
  first seven validated slots of the data-viz default palette except orange, and re-run the validator.
- Not alive yet in the selected year: leaf at 25% ink, label dimmed.

Type
- Serif with character for the wordmark, field names, the year numeral and the margin note title: Newsreader.
- Sans for controls, evidence text and numbers: Instrument Sans, with tabular figures. No monospace.
- Scale (px): 12, 14, 16, 20, 28, 96 (year numeral). Weights 400 and 600 only. Sentence case everywhere: no all-caps, no letter
  spacing, no eyebrow labels above panels.
- Bundle the fonts locally (woff2); the page must work offline for judges. Fallbacks: Georgia, system-ui.
- Wordmark: "Prometheus", serif, 28 px, no letter spacing.

Shape and stroke
- No cards, no shadows, no pill buttons. One radius (2 px) on inputs only. Hairlines only where they separate content.
- Arcs: combined 0.7 px; recent combined 1.4 px; gaps 1.6 px dashed (6 3); selected 2.4 px. Leaves: 3 to 7 px radius by log patents.

## 4. Layout (design at 1440 x 900, minimum 1280 wide)
```
+----------------------------------------------------------------------------------------------+
| Prometheus                                          Prediction check failed: on the top 100   |
| How 123 technology fields combined, 1976 to 2025,   pairs the graph does no better than field |
| from US patent data.                                size. Beyond size it does better.  Details|
|                                                                                              |
|          domain labels around the rim                                    | Margin note        |
|        .-"""""""""""""""""-.                                              | ------------------ |
|      /  leaves + field codes  \                                            | G02B x G01J        |
|     |   bundled arcs through    |      2005                                | Optical elements   |
|     |   the middle              |  (year, 96 px serif)                     | x measurement of.. |
|      \                         /                                           | Why they might     |
|        '-.................-'                                               | combine: bridge    |
|                                                                            | fields, shared     |
|   Combinations | Dependencies | What breaks                                | prerequisites      |
|   Score: Beyond size | Graph | Size alone                                  | Top gaps list      |
|   1976 |----------o--------|2005|2010|2014|-------------| 2025   Play  [ ] Show what happened |
+----------------------------------------------------------------------------------------------+
```
- The tree plate is centred in the left 2/3, diameter about 780 px. The margin note column is 340 px, left-aligned, no panel
  border, separated from the plate by whitespace only.
- Title and subtitle top left. The prediction-check sentence top right, right edge aligned to the note column.
- Everything is left-aligned. The only centred thing is the year numeral inside the tree.
- The timeline is full width at the bottom with the backtest cutoffs (2005, 2010, 2014) marked as small ticks with labels.
- Default year on load: 2005 (the first held-out cutoff, so "show what happened" works immediately).

## 5. How the data is drawn
| Data | Drawing |
|---|---|
| Field | A leaf on the circle: dot (size by log patents), code in the sans, 12 px, rotated radially. Full title on hover |
| Dendrogram | Radial branches in ink, 1 px. Built from the genome clustering (`genome.cluster` order and merges) |
| Domain | A wedge on the rim (alternate `--wedge` and paper) with the domain name set along the arc, from the slice file's domain names. With `--slice all` (no domains) fall back to the CPC sections with their official names: A Human necessities; B Performing operations, transporting; C Chemistry, metallurgy; D Textiles, paper; E Fixed constructions; F Mechanical engineering, lighting, heating, weapons, blasting; G Physics; H Electricity |
| Combined pair | A bundled arc between two leaves, d3 `curveBundle` beta 0.85. Colour = age at the slider year (history ramp, section 3) |
| Recent combinations | Arcs combined within 10 years before the slider year: full colour, 1.4 px. Older ones: 25% opacity, 0.7 px, so they read as bedrock |
| Gap | Dashed fire arc, three steps by tercile. Only the top 15 by the selected score, plus all candidates of the selected field (max 10) |
| Selected | Ink arcs and a ring on the leaves; everything else drops to 35% |

Do not draw all combined arcs at full strength: more than 4,000 arcs is a hairball. The two-level opacity above is part of the design.

Tree layout and time (decision for the build):
- Target: recompute the tree as of the slider year (`genome` as of that year, endpoint `/api/tree?year=`), and animate leaves to
  their new angular positions over 600 ms. Keep leaf order as close as possible to the previous year.
- Acceptable first version: one fixed tree computed from all data, plus a visible note under the plate: "Tree layout uses data
  through 2025. Arcs follow the slider." Replace it with the per-year tree if time allows.
- `genome.cluster` refuses more than 500 fields. That is fine for 123. Show a clear message if the store is larger.

## 6. Modes and interactions (one tree, three modes)
A segmented control under the plate. Switching modes changes only what is drawn on the same tree.

1. **Combinations** (default): arcs as above. Click a leaf or an arc to select it.
2. **Dependencies**: needs a selected field. Draws what it builds on (arcs toward older foundations, solid ink) and what builds on it
   (arcs outward, dotted ink), from `ancestors`, `descendants` and the BUILDS_ON graph. Direction is shown by a short arrowhead, and
   the margin note lists the first two steps in each direction.
3. **What breaks**: needs a selected field. Colours the leaves by how exposed they are if that field disappeared (`knockout`),
   on the **grey** ramp (`--grey-1` to `--grey-4`; never fire). Every exposure shows how many supporting links it rests on (the count of
   BUILDS_ON links as of the slider year, not citation totals). Fields with fewer than the minimum support are drawn in an outline-only
   style with a note, so small sparse fields do not look like findings.

Other controls
- **Year slider**: drag, arrow keys, and Play (one year per 400 ms; stops at the data end). Marks at 2005, 2010 and 2014.
- **Score**: Beyond size (default), Graph score, Size alone. Changes the ranking of the gaps drawn and listed. The margin note shows both
  ranks for a gap: size rank and graph rank.
- **Show what happened** (off by default; available only for slider years up to **2014**, the last backtest cutoff, which keeps the
  ten-year window inside 2024 and away from a partial 2025; disabled after that, with the tooltip "needs ten years of later data"):
  gap arcs become solid fire if the pair combined within 10 years, and hollow grey dashes if not. The margin note counts both. The
  breakthrough button stays hidden while the prediction check is a NO-GO.
- **Pair evidence** (click a gap arc or a row in Top gaps): the bridge fields and shared prerequisites light up on the tree as ink
  rings; the margin note names them (`bridge_fields`, `shared_prerequisites`).
- **Hover** a leaf: tooltip with code, full title, patents, first year. Hover an arc: the two codes and "combined in YEAR" or
  "has not combined". For pairs combined in 1976 say "already combined when the data starts (1976)".
- **Esc** clears the selection. Everything works with the keyboard: Tab moves through leaves in rim order, Enter selects.

States
- Empty margin note: "Click a field or a dashed arc to see why two fields might combine."
- Loading: the tree appears as ink branches first; arcs fade in once loaded. Never show a spinner over the plate.
- Error: say what failed and what to do ("The data file could not be read. Check that `prometheus serve` was started with a .rl file.").
- A field that is not alive in the selected year: leaf dimmed, tooltip "Not in the data yet (needs 5 patents a year)".

## 7. Margin note (right column)
In order: selected field or pair (serif, 20 px), full CPC titles (sans, 14 px), then evidence (bridge fields, shared prerequisites, up
to 5 each), then the two ranks, then the Top gaps list (10 rows: two codes, one short title, size rank and graph rank). Titles are cut at a
word boundary with an ellipsis and show in full on hover. Line length stays under 60 characters.

## 8. Prediction check (always visible, plain)
Top right, one sentence: "Prediction check failed: on the top 100 pairs the graph does no better than field size. Beyond size, it does
better." It links to a panel with the per-cutoff table and one small chart: graph versus size alone on all pairs and on the beyond-size
subset, each with its interval. The panel reads from `results/backtest.json` and the beyond-size analysis, and is collapsed by default.
If the check ever passes, the sentence changes and the breakthrough button appears. Never hide a failure.

## 9. Words
| Where | Text |
|---|---|
| Title | Prometheus |
| Subtitle | How 123 technology fields combined, 1976 to 2025, from US patent data. |
| Modes | Combinations, Dependencies, What breaks |
| Score | Beyond size, Graph score, Size alone |
| Toggle | Show what happened |
| Legend (history) | Combined in the last 3 years, 4 to 6 years ago, 7 to 10 years ago, over 10 years ago |
| Legend (gap) | Not combined yet, ranked by the selected score (top third, middle, lower) |
| Legend (what breaks) | Exposure if the selected field disappeared, light to dark |
| Tree note | The tree groups fields with similar foundations. It is not a family of descent. |
| Dependencies empty | Select a field to see what it builds on and what builds on it. |
| What-breaks empty | Select a field to see which others lose the most if it disappeared. |
| Support note | Based on N citing links. Few links means a weak signal. |
Use active, plain verbs and keep one name per action across the page. Never apologise in errors.

## 10. Motion
One moment: when the slider advances, arcs that newly combine pulse once (300 ms) in their history colour. Leaf movement when the tree is
recomputed is the only other animation, and it follows a user action. Nothing animates on load beyond the fade-in. Respect
`prefers-reduced-motion` (no pulse, no leaf tween; swap instantly).

## 11. Accessibility
- Text contrast against paper at least 4.5:1 (ink and ink-2 both pass; check any new colour).
- Colour is never the only carrier: gaps are dashed, history solid; domains are labelled; the legend names every colour.
- A visually hidden table lists the top gaps with the same columns as the visible list, for screen readers.
- Visible keyboard focus: a 2 px ink ring on leaves, buttons and the slider.

## 12. Build notes
- D3 v7 in a single static page, no build step. `d3.cluster` radial layout from the merge list; `d3.lineRadial` with `curveBundle`.
- Arcs on a canvas layer under an SVG layer for leaves, labels and focus rings, so 4,000+ arcs stay smooth.
- Reuse existing server endpoints and functions: `genome.cluster`, `TechGraph.lineage`, `knockout`, `bridge_fields`,
  `shared_prerequisites`, `top_gaps`, `Snapshot`. Add `/api/tree?year=` only if the per-year tree is built. Server stays read-only.
- Do not change predictors, weights, thresholds or the gate. Do not fetch anything from the network at runtime.

## 12b. Decisions for v1 (author, 13 Nov 2026)
- Fixed tree only (one tree from all data, with the visible note under the plate). The per-year tree and `/api/tree` are v2.
- Minimum support for the knock-out display rule is 3 BUILDS_ON links (`MIN_SUPPORT` in `server.py`); it only changes how a field is drawn, never a score.
- Server additions for v1: `/api/check` (reads only `results/backtest.json` and `results/beyond_size/beyond_size.json`, nothing else) and a
  supporting-link count in the knock-out output (the number of BUILDS_ON links as of the year; no totals).
- Rename the package, command and store file to `prometheus` before building the page, in one commit, so the page is not edited twice.
- Build order: rename and tests; server additions; tree page v1 (arcs, slider, three modes); margin note, evidence and the
  prediction-check panel; states, keyboard use and reduced motion; screenshots at 1985, 1998 and 2010.

## 12c. As built (v1), and where it differs from the design above

Built and checked on the real store on 13 Nov 2026. `python scripts/ui_check.py` passes 25 checks in a real browser (keyboard,
click and hover on arcs, Play, slider, modes, happened range, offline, console errors, reduced motion, resize).

Differences, with the reason:
- **Tree radii use merge rank, not distance.** Genome distances cluster near the top of the tree, which drew one long spoke per
  leaf. Rank spreads the branches evenly. The tree still shows the same grouping; its radial lengths do not mean distance.
- **Domain wedges are runs of consecutive leaves.** The leaf order comes from genome similarity, not from domain, so fields of one
  domain are not contiguous. A domain can therefore appear on several wedges (for example "AI, computing" twice). Only runs wide
  enough for their label are named.
- **Plate size scales with the window** (520 to 780 px) so the slider stays on screen at 1440 x 900 (about 650 px there); the
  design's 780 px needs a taller window. Leaf dots scale with spacing (about 2 to 5 px here) because 123 leaves on a smaller
  circle would otherwise merge into a ring.
- **Arc opacity by age band is 0.12, 0.16, 0.45, 0.75 and 1** from oldest to newest (the design's "full colour" for all recent arcs
  hid the age layers once thousands overlapped). Old arcs are 0.6 px, recent ones 1.4 px.
- **Dependencies draws at most the first two steps, and only the first step, thin and light, when a field has more than 25**
  in a direction (a hub can have 100); the margin note lists everything.
- **Show what happened** gets the ten-year outcome from the server's state at year + 10, so no extra endpoint was needed.
- **Added `scripts/ui_check.py`** and URL deep links (`#year=`, `#mode=`, `#score=`, `#field=`, `#gap=`, `#happened=1`, `#details=1`).
- **The matrix was kept as a secondary view** at `/matrix` (decided 13 Nov 2026), reachable from "View as matrix" under the tree's
  controls. It shares the tokens, fonts, slider, score toggle, evidence panel and prediction-check sentence, uses the age ramp for
  combined cells and fire only for predicted pairs, and is a separate page (`matrix.html`) with no new server logic beyond the route.
  It colours the server's top 1,500 pairs by the hybrid, so a pair size ranks high but the graph does not is not shown there.
- **A 3D landscape was added as a third view** at `/landscape` (decided 13 Nov 2026, after a concept mockup showed a terrain view).
  Mapping, fixed so every vertex is a real pair: x and z are the 123 fields in genome order; combined pairs are low ground shaded by age
  (newer slightly higher); not-yet-combined ranked pairs rise by their rank under the selected score; fire is only for those. The first
  version drew each ranked pair as a needle and read as a porcupine, not terrain, so the default surface is blurred (two passes of a
  5-tap kernel, about two fields) and the toggle "Each pair" keeps the raw spikes. Smooth heights and the fire/blue mix are relative to the
  tallest hill that year, so they say where ranked gaps cluster, not how large a score is. The cross-section and history panels use true
  values, never the blur. Pointer picking snaps to the ranked pair nearest the ray's hit point on the surface, because row spacing is a
  pixel or two on the far side. Not taken from the mockup: its numbers (they do not match the data), a "combination count" palette
  (it would use totals through 2025 in an as-of view), and a "Flow" view (undefined).
- **Per-year tree: built** (13/14 Nov 2026), `/api/tree?year=`. The genome clustering takes about 0.07 s a year, so it is computed on request and cached. Alive fields get that
  year's tree; each branch is flipped to sit near where its leaves were last year, with a mirror image only if it moves fewer leaves (consecutive years move a leaf 6 of 123
  positions on average, measured in `scripts/ui_check.py`). Fields not yet in the data wait in a gap at the end of the circle and move in when they appear. Leaves tween over
  600 ms; branches and arcs are hidden during the move and redrawn after (the arcs are bundled through the tree, so they cannot follow a moving tree). No tween while Play runs
  or under reduced motion, or when nothing moved. `#tree=fixed` keeps the single all-data tree. A rotation of the whole order is not allowed because the gap breaks the circle.
- **Stalled-pair overlay: built.** Grey dotted arcs (never fire) for pairs whose first co-classified patent is at least 3 years old and that are still under the combination
  threshold; derived from two first-years in the store (`CO_CLASSIFIED`, `COMBINED_WITH`), so no totals. Off by default (about 800 arcs make a grey haze in the middle).
  Pair evidence on all three pages says when a pair has been co-classified without reaching the threshold. It is a display, not a score.
- **Landscape readability pass (14 Nov 2026).** The first 3D version had no way to say which fields a point was. Added: field codes on the near edges and domain names on the far edges
  (greedy de-cluttering in screen space, longest domain runs first); clickable labels on the top ten hills (one per hill, nearest copy of the symmetric surface); a crosshair (row and column
  strips on the terrain) and edge markers for the hovered pair, the selected pair or a focused field; **Find a field** with cross-section and candidates for a field on its own; a gentle
  camera move to the selection (pan, and come closer only if farther than a set distance); Oblique, Low angle, Top down and Reset; fog and a hemisphere light for depth; a corner scale for
  height. Labels never take the pointer; clicks are matched to label boxes in the canvas handler. Edge labels go to the near edges (codes) and far edges (names) so they stay clear of the tree
  and the empty backdrop, because perspective squeezes far-edge text and near-edge text collides with the tree lines.
- **Second readability pass (all views, 14 Nov 2026).** Matrix: field codes every fourth field, domain bands and names in right and bottom gutters (the tree stays on top and left);
  a crosshair and both field names in the gutters on hover; Find a field; stalled pairs in grey (never fire). Tree: Find a field, and **Newest only** (pairs combined in the last
  three years) because hiding only arcs older than ten years changed almost nothing: those arcs were already nearly transparent, and the dense mass is the recent decade.
  All views: a focused or selected field carries over through the top bar links, and a footer credits PatentsView.
- **The landscape's cross-section is a smoothed stacked area chart** (decided 14 Nov 2026), not bars: along the bottom the other fields in order; stacked heights are the share of
  nearby fields combined with the selected field (by age) and ranked as candidates (by rank third). Smoothing follows the Surface toggle; Each pair draws steps.
- **Not built:** the breakthrough button (hidden while the check is a NO-GO, as designed).

Observed limit: the bundled-tree layout puts every year's arcs in the same corridors, so 1985, 1998 and 2010 look alike at a
glance. The build-up shows as density and colour, and in the central fan, not as new shapes. At 1998 there are 691 arcs from
the last ten years against 1,444 older ones; at 2010, 533 against 2,198.

## 13. Done when
1. Screenshots at 1985, 1998 and 2010 show the tree, a visible build-up of arcs, fire only on gaps, and the NO-GO sentence.
2. For each element ask: would it look the same on a page about something else? If yes, change it.
3. Remove one decoration before calling it done.
4. Check: tab order works, reduced motion works, the page works with the network off.
5. Crop browser chrome and tabs from any screenshot used for Devpost.

---

## Reviewer notes (added when this file was created; points 1, 2, 3, 4 and 5 were settled by the author on 13 Nov 2026 and are now in the sections above)

Checked against the repository on 13 Nov 2026. These are points to settle before building, not changes to the design.

1. **Fire is used twice.** Section 1 says fire is used for nothing else, but the "What breaks" mode (section 6) colours leaves on the
   fire ramp, and "Show what happened" uses solid fire for hits. A knock-out exposure is a dependency measure, not a gap. Either
   give "What breaks" its own ramp (for example the history blue, reversed) or accept that fire means "attention" and say so in the
   legend. Decide before building the legend.
2. **Contrast numbers (computed, not assumed).** Against `--paper`: `--ink` 14.5:1, `--ink-2` 6.6:1 (both pass 4.5:1 for text).
   History ramp 2.3, 3.2, 4.5, 6.5, 9.5. Fire ramp 2.1, 3.2, 4.8, 7.7. The lightest steps (`--hist-1`, `--fire-1`) are about 2:1,
   below the 3:1 usually wanted for lines that carry meaning; dashing and the legend carry the meaning there, so keep gap arcs at
   1.6 px or wider and do not use `--fire-1` for the selected gap. `--hair` is 1.4:1, fine for separators only. The colour-blind
   separation claim and the "validator" pass were not re-run here.
3. **Server work this implies.** The current server returns `order` and `merges` once (fixed tree). It has no endpoint for the
   backtest or beyond-size tables (section 8 needs one that reads `results/backtest.json` and `results/beyond_size/beyond_size.json`),
   no per-year tree, and no "how many supporting links" count for knock-out (section 6.3 needs it from the BUILDS_ON counts).
   Gaps today are returned as the top 1,500; the design needs top 15 plus all candidates for a selected field, which the
   existing `/api/state` can already supply client-side.
4. **Domain wedges need a slice file.** Domain names come from `slices/deeptech.json`. With `--slice all` there are none, so the rim
   needs a fallback (for example CPC section letters).
5. **"Show what happened" and held-out data.** It needs the data end to be at least 10 years after the slider year. On the real store
   (ends 2025) it is available through 2015.
6. **CLI name.** The error text in section 6 uses `prometheus serve` (the command that exists), not `prometheus serve`.
7. **The 1976 caveat appears in two places** (section 2 and the tooltip rule for 1976 pairs). Keep both: the tree shows no ages, and
   any pair first combined in 1976 means "already combined when the data starts", not "combined in 1976".
