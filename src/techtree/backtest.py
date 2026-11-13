"""Grade the predictor against history, under rules fixed in advance.

For each cutoff year Y: take the graph as of Y, rank every pair of existing fields that has
not combined yet, and check which pairs really combined in (Y, Y + horizon]. Method weights
are tuned on the early cutoffs only; the numbers that count are on the later, untouched
ones. Every cutoff is reported, with how many positives it had.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from . import config
from . import genome as genome_mod
from .predict import (MIX, Snapshot, average_ranks, hybrid, method_scores, percentile, rank_order,
                      signal_table, tie_breaker)

BASELINES = ("random", "pa")


def auc(scores: list[float], labels: list[int]) -> float | None:
    """Probability that a random positive outranks a random negative (ties count half)."""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = average_ranks(scores)
    s = sum(r for r, y in zip(ranks, labels) if y)
    return (s - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def hits_at_k(order: list[int], labels: list[int], k: int) -> int:
    return sum(labels[i] for i in order[:k])


def prepare(g, cutoffs, horizon: int, use_genome: bool = True) -> tuple[dict, dict]:
    """Per cutoff: candidate pairs, labels, signal table. Returns (prepared, skipped)."""
    truth = {(min(a, b), max(a, b)): y for a, b, y in g.combined()}
    end = g.data_end_year
    prepared, skipped = {}, {}
    for y in cutoffs:
        if y + horizon > end:
            skipped[y] = f"needs data to {y + horizon}, store ends {end}"
            continue
        snap = Snapshot.from_graph(g, y)
        cands = snap.candidates()
        if not cands:
            skipped[y] = "no candidate pairs"
            continue
        labels = [1 if y < truth.get(p, 10**9) <= y + horizon else 0 for p in cands]
        vecs = genome_mod.vectors(snap) if use_genome else None
        prepared[y] = {"cands": cands, "labels": labels, "table": signal_table(snap, cands, vecs),
                       "fields": len(snap.codes)}
    return prepared, skipped


def tune(prepared: dict, cutoffs, values=(0, 1, 2)) -> tuple[dict, dict]:
    """Pick hybrid weights by mean AUC over the tuning cutoffs. Returns (weights, info)."""
    usable = [y for y in cutoffs if y in prepared and sum(prepared[y]["labels"]) > 0]
    signals = [s for s in MIX if usable and s in prepared[usable[0]]["table"]]
    if not usable or not signals:
        return dict(config_default_weights()), {"tuned_on": [], "note": "no usable tuning cutoff; default weights"}
    pct = {y: {s: percentile(prepared[y]["table"][s]) for s in signals} for y in usable}
    best, best_key = None, None
    for combo in itertools.product(values, repeat=len(signals)):
        if not any(combo):
            continue
        w = dict(zip(signals, combo))
        aucs = []
        for y in usable:
            n = len(prepared[y]["labels"])
            sc = [sum(w[s] * pct[y][s][i] for s in signals) for i in range(n)]
            aucs.append(auc(sc, prepared[y]["labels"]))
        mean_auc = sum(aucs) / len(aucs)
        key = (round(mean_auc, 6), -sum(combo), tuple(-c for c in combo))
        if best_key is None or key > best_key:
            best, best_key = w, key
    weights = {s: float(best.get(s, 0)) for s in MIX}
    return weights, {"tuned_on": usable, "mean_auc_on_tuning": best_key[0]}


def config_default_weights():
    from .predict import DEFAULT_WEIGHTS
    return DEFAULT_WEIGHTS


def evaluate(prepared: dict, cutoffs, weights: dict, k: int) -> dict:
    out = {}
    for y in cutoffs:
        if y not in prepared:
            continue
        p = prepared[y]
        labels, n = p["labels"], len(p["labels"])
        positives = sum(labels)
        kk = min(k, n)
        base_rate = positives / n
        tie = tie_breaker(n)
        methods = {}
        for name, sc in method_scores(p["table"], weights, seed=y).items():
            order = rank_order(sc, tie)
            h = hits_at_k(order, labels, kk)
            prec = h / kk
            methods[name] = {
                "auc": auc(sc, labels),
                "hits_at_k": h,
                "precision_at_k": prec,
                "lift_at_k": (prec / base_rate) if base_rate else None,
            }
        out[y] = {"cutoff": y, "fields": p["fields"], "candidates": n, "positives": positives,
                  "base_rate": base_rate, "k": kk, "low_confidence": positives < config.LOW_POSITIVES,
                  "methods": methods}
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def gate(results: dict) -> dict:
    """Go/no-go on the held-out cutoffs, using the pre-declared main predictor (hybrid).

    Random is 1.0 by definition of lift; preferential attachment is measured. The ratio is
    hybrid lift over the better of the two. Picking the best method on the test set would
    inflate the number, so the gate does not.
    """
    cuts = list(results.values())
    lift = {m: _mean([c["methods"][m]["lift_at_k"] for c in cuts]) for m in cuts[0]["methods"]} if cuts else {}
    if not cuts or lift.get("hybrid") is None:
        return {"verdict": "NO RESULT", "reason": "no held-out cutoff with positives"}
    baseline = max(1.0, lift.get("pa") or 0.0)
    ratio = lift["hybrid"] / baseline
    return {
        "verdict": "GO" if ratio >= config.GATE_LIFT else "NO-GO",
        "threshold": config.GATE_LIFT,
        "hybrid_lift": lift["hybrid"],
        "better_baseline_lift": baseline,
        "ratio": ratio,
        "mean_lift_by_method": lift,
        "best_single_method_on_test": max((m for m in lift if lift[m] is not None and m not in BASELINES + ("hybrid",)),
                                          key=lambda m: lift[m], default=None),
    }


def run(g, horizon=config.HORIZON, tune_cutoffs=config.TUNE_CUTOFFS, test_cutoffs=config.TEST_CUTOFFS,
        k=config.TOP_K, use_genome=True, log=print) -> dict:
    cutoffs = sorted(set(tune_cutoffs) | set(test_cutoffs))
    log(f"preparing {len(cutoffs)} cutoffs ...")
    prepared, skipped = prepare(g, cutoffs, horizon, use_genome)
    weights, tune_info = tune(prepared, tune_cutoffs)
    log(f"tuned weights {weights}")
    result = {
        "meta": g.meta(),
        "settings": {"horizon": horizon, "k": k, "tune_cutoffs": list(tune_cutoffs),
                     "test_cutoffs": list(test_cutoffs), "gate_lift": config.GATE_LIFT,
                     "low_positives": config.LOW_POSITIVES, "genome_signal": use_genome},
        "skipped_cutoffs": skipped,
        "weights": weights,
        "tuning": tune_info,
        "tuning_cutoffs_result": evaluate(prepared, tune_cutoffs, weights, k),
        "heldout_cutoffs_result": evaluate(prepared, test_cutoffs, weights, k),
    }
    result["gate"] = gate(result["heldout_cutoffs_result"])
    return result


def _fmt(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def render_markdown(r: dict) -> str:
    meta, st, gt = r["meta"], r["settings"], r["gate"]
    lines = []
    if meta.get("source") == "toy":
        lines += ["> **SYNTHETIC DATA.** These numbers come from a generated toy graph whose combinations were planted",
                  "> by a known rule. They show the machinery works. They say nothing about real technology history.", ""]
    lines += ["# Backtest report", "",
              f"Source: `{meta.get('source')}` · slice: `{meta.get('slice')}` · data ends {meta.get('dataEndYear')} · "
              f"horizon {st['horizon']} years · top K = {st['k']}", "",
              "Settings were fixed before any result. Weights were tuned on the tuning cutoffs only; the held-out "
              "cutoffs were looked at once the weights were frozen.", ""]
    lines += ["## Gate", ""]
    if gt.get("verdict") == "NO RESULT":
        lines += [f"**NO RESULT**: {gt['reason']}", ""]
    else:
        lines += [f"**{gt['verdict']}**. Hybrid lift@{st['k']} on held-out cutoffs is {_fmt(gt['hybrid_lift'], 2)}, "
                  f"the better baseline is {_fmt(gt['better_baseline_lift'], 2)}, ratio {_fmt(gt['ratio'], 2)} "
                  f"(threshold {gt['threshold']}, a judgment call).", ""]
    lines += ["## Tuned weights", "", "`" + json.dumps(r["weights"]) + "`", ""]
    if r["skipped_cutoffs"]:
        lines += ["## Skipped cutoffs", ""] + [f"- {y}: {why}" for y, why in r["skipped_cutoffs"].items()] + [""]
    for title, key in (("Held-out cutoffs (these count)", "heldout_cutoffs_result"),
                       ("Tuning cutoffs (weights were fitted here)", "tuning_cutoffs_result")):
        lines += [f"## {title}", ""]
        res = r[key]
        if not res:
            lines += ["No usable cutoff.", ""]
            continue
        for y, c in res.items():
            flag = "  (**low confidence: few positives**)" if c["low_confidence"] else ""
            lines += [f"### Cutoff {y}",
                      f"{c['fields']} fields, {c['candidates']:,} candidate pairs, **{c['positives']} positives**{flag}, "
                      f"base rate {c['base_rate']:.4f}", "",
                      f"| Method | AUC | hits@{c['k']} | precision@{c['k']} | lift@{c['k']} |", "|---|---|---|---|---|"]
            for m, v in c["methods"].items():
                lines.append(f"| {m} | {_fmt(v['auc'])} | {v['hits_at_k']} | {_fmt(v['precision_at_k'])} | "
                             f"{_fmt(v['lift_at_k'], 2)} |")
            lines.append("")
    lines += ["## Reading this", "",
              "- Lift is precision divided by the share of candidate pairs that turned out positive; random is 1.",
              "- The gate uses the hybrid (declared as the main predictor in advance), not the best method on the test "
              "cutoffs, which would inflate the result.",
              "- Counts and totals never enter a feature: everything is computed from existence and first year as of the cutoff.",
              ""]
    return "\n".join(lines)


def write(result: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md, js = out / "backtest.md", out / "backtest.json"
    md.write_text(render_markdown(result))
    js.write_text(json.dumps(result, indent=2, default=str))
    return md, js
