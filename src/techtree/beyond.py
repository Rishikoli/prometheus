"""A2, "beyond size" (exploratory; defined after the main backtest returned NO-GO).

Question: among pairs that preferential attachment (PA) ranks in the bottom half, do the graph
signals still rank the pairs that later combine above the ones that do not? PA is what field
size alone predicts, so this removes the easy hub-meets-hub pairs by construction.

Definition, fixed in the README before it was run
  * cutoffs: the held-out ones (2005, 2010, 2014), horizon 10 years, positives as in the backtest;
  * subset: of the n candidate pairs at a cutoff, the n // 2 that PA ranks lowest (ties broken by
    the same shared tie-breaker every method uses);
  * hybrid weights: the ones already tuned on 1990/1995/2000 and stored in backtest.json. They are
    loaded, never refitted, and the hybrid's percentiles are taken over ALL candidates, so the model
    is exactly the main-run model; only the evaluation is restricted to the subset;
  * output: AUC on the subset for the hybrid and each single signal, with PA and random as
    references, and a 95% percentile bootstrap interval over pairs (2000 resamples, fixed seed).
    There is no pass/fail threshold.
Pairs share fields, so resampling pairs as independent understates the true uncertainty. The
intervals are a floor on it, not a guarantee.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from . import config
from .backtest import auc, prepare
from .predict import hybrid, method_scores, rank_order, tie_breaker

REPORTED = ("hybrid", "cn", "aa", "prereq", "genome", "pa", "random")
N_BOOT = 2000
BOOT_SEED = 20261113


def pa_bottom_half(pa: list[float]) -> list[int]:
    """Indices of the n // 2 candidates PA ranks lowest (shared tie-breaker, as everywhere else)."""
    n = len(pa)
    order = rank_order(pa, tie_breaker(n))  # best to worst
    return sorted(order[n - n // 2:])


def bootstrap_ci(scores: dict[str, list[float]], labels: list[int], n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    """95% percentile interval of each method's AUC; the same resamples are used for every method."""
    rng = random.Random(seed)
    n = len(labels)
    draws: dict[str, list[float]] = {m: [] for m in scores}
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        lab = [labels[i] for i in idx]
        if sum(lab) in (0, n):
            continue
        for m, sc in scores.items():
            a = auc([sc[i] for i in idx], lab)
            if a is not None:
                draws[m].append(a)
    out = {}
    for m, d in draws.items():
        d = sorted(d)
        out[m] = (d[int(0.025 * (len(d) - 1))], d[int(round(0.975 * (len(d) - 1)))]) if d else (None, None)
    return out


def bootstrap_diff(scores: dict[str, list[float]], labels: list[int], ref: str = "pa", n_boot: int = N_BOOT,
                   seed: int = BOOT_SEED):
    """Paired bootstrap of AUC(method) - AUC(ref): both are computed on the SAME resample each time, so the
    interval reflects the difference itself, not two separate intervals. Same seed as bootstrap_ci."""
    rng = random.Random(seed)
    n = len(labels)
    diffs: dict[str, list[float]] = {m: [] for m in scores if m != ref}
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        lab = [labels[i] for i in idx]
        if sum(lab) in (0, n):
            continue
        base = auc([scores[ref][i] for i in idx], lab)
        for m in diffs:
            a = auc([scores[m][i] for i in idx], lab)
            if a is not None and base is not None:
                diffs[m].append(a - base)
    out = {}
    for m, d in diffs.items():
        d.sort()
        out[m] = (d[int(0.025 * (len(d) - 1))], d[int(round(0.975 * (len(d) - 1)))]) if d else (None, None)
    return out


def run(g, weights: dict, cutoffs=config.TEST_CUTOFFS, horizon=config.HORIZON, use_genome=True,
        n_boot: int = N_BOOT, log=print) -> dict:
    prepared, skipped = prepare(g, cutoffs, horizon, use_genome)
    res = {}
    for y in cutoffs:
        if y not in prepared:
            continue
        p = prepared[y]
        n = len(p["labels"])
        sub = pa_bottom_half(p["table"]["pa"])
        labels = [p["labels"][i] for i in sub]
        full = method_scores(p["table"], weights, seed=y)  # scores over ALL candidates, weights frozen
        scores = {m: [full[m][i] for i in sub] for m in REPORTED if m in full}
        cis = bootstrap_ci(scores, labels, n_boot)
        dci = bootstrap_diff(scores, labels, "pa", n_boot)
        auc_pa = auc(scores["pa"], labels)
        log(f"cutoff {y}: {len(sub)} of {n} candidates in the PA bottom half, {sum(labels)} positives")
        res[y] = {"cutoff": y, "candidates_all": n, "candidates_subset": len(sub), "positives_all": sum(p["labels"]),
                  "positives_subset": sum(labels), "base_rate_subset": sum(labels) / len(sub),
                  "methods": {m: {"auc": auc(scores[m], labels), "ci95": list(cis[m])} for m in scores},
                  "diff_vs_pa": {m: {"diff": auc(scores[m], labels) - auc_pa, "ci95": list(dci[m])} for m in dci}}
    return {"definition": "A2 beyond size: pairs PA ranks in the bottom half; weights frozen from backtest.json",
            "weights": weights, "horizon": horizon, "n_boot": n_boot, "skipped_cutoffs": skipped,
            "meta": g.meta(), "cutoffs": res}


def _f(x):
    return "n/a" if x is None else f"{x:.3f}"


def render_markdown(r: dict) -> str:
    L = ["# A2: beyond size (exploratory, no pass/fail threshold)", "",
         f"Source `{r['meta'].get('source')}`, slice `{r['meta'].get('slice')}`. Subset: the candidate pairs that preferential "
         "attachment ranks in the bottom half. Weights are the ones tuned on 1990/1995/2000 and are not refitted: "
         f"`{json.dumps(r['weights'])}`. AUC with a 95% bootstrap interval over pairs ({r['n_boot']} resamples); pairs share "
         "fields, so the intervals are narrower than the real uncertainty.", ""]
    for y, c in r["cutoffs"].items():
        L += [f"## Cutoff {y}", f"{c['candidates_subset']:,} of {c['candidates_all']:,} candidate pairs, "
              f"**{c['positives_subset']} positives** in the subset (base rate {c['base_rate_subset']:.3f}; "
              f"{c['positives_all']} positives overall).", "", "| Method | AUC | 95% interval |", "|---|---|---|"]
        for m, v in c["methods"].items():
            L.append(f"| {m} | {_f(v['auc'])} | {_f(v['ci95'][0])} to {_f(v['ci95'][1])} |")
        L += ["", "Paired difference in AUC against PA on the same pairs (same resamples, 95% interval):", "",
              "| Method | AUC minus PA AUC | 95% interval |", "|---|---|---|"]
        for m, v in c["diff_vs_pa"].items():
            L.append(f"| {m} | {v['diff']:+.3f} | {v['ci95'][0]:+.3f} to {v['ci95'][1]:+.3f} |")
        L.append("")
    L += ["## Reading this", "",
          "- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.",
          "- `pa` is a reference: it ranked these pairs in the bottom half, so its AUC here is not a prediction target.",
          "- Exploratory: defined after seeing the NO-GO in the main backtest.", ""]
    return "\n".join(L)


def write(result: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md, js = out / "beyond_size.md", out / "beyond_size.json"
    md.write_text(render_markdown(result))
    js.write_text(json.dumps(result, indent=2, default=str))
    return md, js
