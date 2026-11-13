"""Grade a forecast made on a capsule against what happened afterwards.

The forecast is a JSON file {"pairs": [{"a": "F0001", "b": "F0002", "cypher": "...", "why": "..."}, ...]}.
It is graded against a LATER store (a later capsule built with the same seed, or the full
store with codes plus the capsule's map file). The same candidate pairs are used to score
two baselines (random, preferential attachment) and the graph predictor, so the forecaster
is compared like for like.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config
from . import genome as genome_mod
from .backtest import auc, hits_at_k
from .graph import TechGraph
from .predict import (DEFAULT_WEIGHTS, Snapshot, hybrid, rank_order, signal_table, tie_breaker)


def _load_pairs(path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    pairs = data["pairs"] if isinstance(data, dict) else data
    if not isinstance(pairs, list):
        raise ValueError("forecast must hold a list of pairs")
    return pairs


def grade(forecast_path, against_path, as_of: int, map_path=None, horizon: int | None = None,
          weights: dict | None = None, pa_max: int | None = None) -> dict:
    """`against_path`: a later capsule (same seed, blind ids) or a full store (needs `map_path`)."""
    pairs = _load_pairs(forecast_path)
    with TechGraph(against_path) as g:
        meta = g.meta()
        blind_store = bool(meta.get("blind"))
        end = g.data_end_year
        h = horizon if horizon is not None else min(config.HORIZON, end - as_of)
        if h <= 0 or as_of + h > end:
            raise ValueError(f"cannot grade {as_of} + {h} years: the store ends in {end}")
        id_to_code = None
        if not blind_store:
            if not map_path:
                raise ValueError("a full store uses real codes: pass the capsule's .map.json (map_path)")
            id_to_code = json.loads(Path(map_path).read_text())["idToCode"]
        truth = {(min(a, b), max(a, b)): y for a, b, y in g.combined()}
        snap = Snapshot.from_graph(g, as_of)

    def code_of(x):
        return id_to_code.get(x) if id_to_code is not None else x

    all_cands = snap.candidates()
    w = dict(weights or DEFAULT_WEIGHTS)
    vecs = genome_mod.vectors(snap) if w.get("genome") else None
    table = signal_table(snap, all_cands, vecs)
    scores = hybrid(table, w)  # computed over ALL candidates, so the model is the same with or without a restriction
    keep = [i for i in range(len(all_cands)) if pa_max is None or table["pa"][i] <= pa_max]
    cands = [all_cands[i] for i in keep]
    table = {m: [v[i] for i in keep] for m, v in table.items()}
    scores = [scores[i] for i in keep]
    labels = [1 if as_of < truth.get(p, 10**9) <= as_of + h else 0 for p in cands]
    positives = sum(labels)
    base_rate = positives / len(cands) if cands else 0.0
    cand_set = set(cands)

    valid, rejected, seen = [], [], set()
    for item in pairs:
        a, b = code_of(item.get("a")), code_of(item.get("b"))
        if a is None or b is None or a == b:
            rejected.append({"pair": [item.get("a"), item.get("b")], "reason": "unknown field id"})
            continue
        p = (min(a, b), max(a, b))
        if p in seen:
            rejected.append({"pair": [item.get("a"), item.get("b")], "reason": "duplicate"})
        elif p not in cand_set:
            rejected.append({"pair": [item.get("a"), item.get("b")],
                             "reason": "not a candidate (unknown field, not yet existing, already combined"
                                       + (f", or deg(a)*deg(b) above {pa_max}" if pa_max is not None else "") + ")"})
        else:
            seen.add(p)
            valid.append((p, item))
    k = len(valid)
    hits = sum(1 for p, _ in valid if as_of < truth.get(p, 10**9) <= as_of + h)

    out = {"as_of": as_of, "horizon": h, "graded_against": str(against_path), "candidates": len(cands),
           "positives": positives, "base_rate": base_rate, "pairs_submitted": len(pairs),
           "pairs_valid": k, "rejected": rejected,
           "with_cypher": sum(1 for _, it in valid if str(it.get("cypher", "")).strip()),
           "forecaster": {"hits": hits, "precision": hits / k if k else None,
                          "lift": (hits / k / base_rate) if k and base_rate else None}}
    if pa_max is not None:
        out["pa_max"] = pa_max
        out["restricted_to"] = "pairs with deg(a)*deg(b) <= pa_max"
    if k:
        tie = tie_breaker(len(cands))
        for name, sc in (("preferential_attachment", table["pa"]), ("graph_predictor", scores)):
            order = rank_order(sc, tie)
            hh = hits_at_k(order, labels, k)
            out[name] = {"hits": hh, "precision": hh / k, "lift": (hh / k / base_rate) if base_rate else None,
                         "auc": auc(sc, labels)}
        out["random_expected"] = {"hits": round(k * base_rate, 2), "lift": 1.0}
    out["note"] = ("With only a few forecasts the hit count is noisy. Blinding reduces, but does not remove, the "
                   "chance that a language model recognises the history; treat this as an experiment.")
    return out
