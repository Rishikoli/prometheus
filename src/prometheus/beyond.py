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
        n_boot: int = N_BOOT, proxy: str = "degree", log=print) -> dict:
    """proxy: 'degree' (A2: product of combination partners), 'patents' (A2b: product of cumulative patent counts as of the cutoff,
    never the end-of-data total) or 'both' (A2b: pairs in the bottom half under BOTH proxies; both are references)."""
    if proxy not in ("degree", "patents", "both"):
        raise ValueError(f"unknown size proxy {proxy!r}")
    prepared, skipped = prepare(g, cutoffs, horizon, use_genome)
    res = {}
    for y in cutoffs:
        if y not in prepared:
            continue
        p = prepared[y]
        n = len(p["labels"])
        refs: dict[str, list[float]] = {}
        if proxy in ("degree", "both"):
            refs["pa"] = p["table"]["pa"]
        if proxy in ("patents", "both"):
            cnt = g.patents_as_of(y)
            if not cnt:
                raise ValueError("this store has no per-year patent counts (FieldYear); rebuild it with a current `prometheus pipeline` and `build`")
            refs["patents"] = [float(cnt.get(a, 0)) * float(cnt.get(b, 0)) for a, b in p["cands"]]
        halves = [set(pa_bottom_half(v)) for v in refs.values()]
        sub = sorted(set.intersection(*halves))
        labels = [p["labels"][i] for i in sub]
        full = method_scores(p["table"], weights, seed=y)  # scores over ALL candidates, weights frozen
        scores = {m: [full[m][i] for i in sub] for m in REPORTED if m in full and m != "pa"}
        for name, v in refs.items():
            scores[name] = [v[i] for i in sub]
        cis = bootstrap_ci(scores, labels, n_boot)
        diffs = {name: bootstrap_diff(scores, labels, name, n_boot) for name in refs}
        aucs = {m: auc(sc, labels) for m, sc in scores.items()}
        log(f"cutoff {y}: {len(sub)} of {n} candidates in the bottom half ({proxy}), {sum(labels)} positives")
        res[y] = {"cutoff": y, "candidates_all": n, "candidates_subset": len(sub), "positives_all": sum(p["labels"]),
                  "positives_subset": sum(labels), "base_rate_subset": (sum(labels) / len(sub)) if sub else None,
                  "methods": {m: {"auc": aucs[m], "ci95": list(cis[m])} for m in scores},
                  **{f"diff_vs_{name}": {m: {"diff": aucs[m] - aucs[name], "ci95": list(ci)} for m, ci in diffs[name].items()}
                     for name in refs}}
    defs = {"degree": "A2 beyond size: pairs PA (degree product) ranks in the bottom half; weights frozen from backtest.json",
            "patents": "A2b: pairs in the bottom half by the product of cumulative patent counts as of the cutoff; weights frozen from backtest.json",
            "both": "A2b: pairs in the bottom half under BOTH degree product and patent-count product; weights frozen from backtest.json"}
    return {"definition": defs[proxy], "proxy": proxy, "weights": weights, "horizon": horizon, "n_boot": n_boot,
            "skipped_cutoffs": skipped, "meta": g.meta(), "cutoffs": res}


def _f(x):
    return "n/a" if x is None else f"{x:.3f}"


REF_NAMES = {"pa": "PA (degree product)", "patents": "patent-count product"}


def render_markdown(r: dict) -> str:
    proxy = r.get("proxy", "degree")
    title = {"degree": "A2: beyond size (exploratory, no pass/fail threshold)",
             "patents": "A2b: beyond size, patent-count proxy (exploratory, no pass/fail threshold)",
             "both": "A2b: beyond size, bottom half under both proxies (exploratory, no pass/fail threshold)"}[proxy]
    subset = {"degree": "the candidate pairs that preferential attachment (degree product) ranks in the bottom half",
              "patents": "the candidate pairs in the bottom half by the product of the two fields' cumulative patent counts as of the cutoff",
              "both": "the candidate pairs in the bottom half under both the degree product and the patent-count product"}[proxy]
    L = [f"# {title}", "",
         f"Source `{r['meta'].get('source')}`, slice `{r['meta'].get('slice')}`. Subset: {subset}. Weights are the ones tuned on "
         f"1990/1995/2000 and are not refitted: `{json.dumps(r['weights'])}`. AUC with a 95% bootstrap interval over pairs "
         f"({r['n_boot']} resamples); pairs share fields, so the intervals are narrower than the real uncertainty.", ""]
    for y, c in r["cutoffs"].items():
        L += [f"## Cutoff {y}", f"{c['candidates_subset']:,} of {c['candidates_all']:,} candidate pairs, "
              f"**{c['positives_subset']} positives** in the subset (base rate {_f(c['base_rate_subset'])}; "
              f"{c['positives_all']} positives overall).", "", "| Method | AUC | 95% interval |", "|---|---|---|"]
        for m, v in c["methods"].items():
            L.append(f"| {m} | {_f(v['auc'])} | {_f(v['ci95'][0])} to {_f(v['ci95'][1])} |")
        for name in (k[len("diff_vs_"):] for k in c if k.startswith("diff_vs_")):
            L += ["", f"Paired difference in AUC against the {REF_NAMES.get(name, name)} on the same pairs (same resamples, 95% interval):", "",
                  "| Method | AUC minus reference | 95% interval |", "|---|---|---|"]
            for m, v in c[f"diff_vs_{name}"].items():
                L.append(f"| {m} | {v['diff']:+.3f} | {v['ci95'][0]:+.3f} to {v['ci95'][1]:+.3f} |")
        L.append("")
    L += ["## Reading this", "",
          "- AUC 0.5 means no better than a coin flip at telling later-combining pairs from the rest within this subset.",
          "- A reference's own AUC here is not a prediction target: it ranked these pairs in the bottom half.",
          "- Exploratory: defined after seeing the NO-GO in the main backtest.", ""]
    return "\n".join(L)


def write(result: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if result.get("proxy", "degree") == "degree" else "_" + result["proxy"]
    md, js = out / f"beyond_size{suffix}.md", out / f"beyond_size{suffix}.json"
    md.write_text(render_markdown(result))
    js.write_text(json.dumps(result, indent=2, default=str))
    return md, js
