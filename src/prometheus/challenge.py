"""Beat the graph: a forecast challenge on the sealed capsules.

A round is a capsule year. You pick 10 pairs of anonymous fields that have not combined yet AND are not the easy "big field meets
big field" pairs: deg(a) * deg(b) must be at most the round's threshold (the lower median of that product over all candidates, so
about half the candidates are eligible). That is the A4 setting, where the top of the ranking is not saturated: random guessing
expects well under one hit in ten. You are scored on how many of your pairs first combined in the next ten years, judged on the
capsule ten years later, against the graph predictor (weights frozen from the backtest), the size rule and chance, on exactly the
same eligible pairs.

Honour system: the later capsules and the id maps are in this repository, so a determined player could look up the answers. For a
sealed contest, keep the grading capsule private.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import capsule as capsule_mod
from . import grade as grade_mod
from .graph import TechGraph
from .predict import Snapshot

ROUNDS = {1995: 2005, 2005: 2015, 2010: 2020}   # forecast year -> the capsule that grades it


def paths(year: int, capsules_dir="capsules") -> tuple[Path, Path]:
    if year not in ROUNDS:
        raise ValueError(f"no round {year}; rounds are {sorted(ROUNDS)}")
    d = Path(capsules_dir)
    early, late = d / f"{year}.rl", d / f"{ROUNDS[year]}.rl"
    for p in (early, late):
        if not p.exists():
            raise FileNotFoundError(f"{p} is missing; build it with `prometheus capsule data/csv --as-of {p.stem} --out {p} --seed 0`")
    return early, late


def threshold(year: int, capsules_dir="capsules") -> int:
    early, _ = paths(year, capsules_dir)
    with TechGraph(early) as g:
        return capsule_mod.pa_threshold(Snapshot.from_graph(g, year))


def brief(year: int, capsules_dir="capsules") -> str:
    t = threshold(year, capsules_dir)
    head = (f"# Beat the graph: round {year}\n\nYour forecast is scored on the pairs that combine between {year + 1} and {year + 10}, judged on the "
            f"{ROUNDS[year]} capsule, against the graph predictor, the size rule and chance on the same eligible pairs. "
            "Connect your agent (or yourself) to the capsule read-only, for example `relate serve --mcp stdio --read-only --database "
            f"capsules/{year}.rl`, or query it with `python scripts/mcp_query.py capsules/{year}.rl \"MATCH ...\"`.\n\n"
            "Honour system: the later capsules and the id maps are in this repository. Do not open them while forecasting.\n\n---\n\n")
    return head + capsule_mod.brief_a4(year, 10, f"capsule-{year}", t)


def score(forecast, year: int, capsules_dir="capsules", weights: dict | None = None) -> dict:
    """Grade a forecast on the eligible pairs of a round, next to the graph predictor, the size rule and chance."""
    _, late = paths(year, capsules_dir)
    t = threshold(year, capsules_dir)
    res = grade_mod.grade(forecast, late, year, weights=weights, pa_max=t)
    res["round"] = year
    res["threshold"] = t
    you = res["forecaster"]["hits"]
    graph = res.get("graph_predictor", {}).get("hits")
    res["verdict"] = ("no valid pairs" if not res["pairs_valid"] else
                      "you beat the graph" if graph is not None and you > graph else
                      "you tied the graph" if you == graph else "the graph wins this round")
    return res


def leaderboard(capsules_dir="capsules", results_dir="results", weights: dict | None = None) -> str:
    """Baseline rows per round: chance, the size rule, the graph predictor, and the A4 agent if its forecast is in results/."""
    rows = []
    for year in sorted(ROUNDS):
        prior = Path(results_dir) / "forecaster_a4" / f"forecast_{year}.json"
        if not prior.exists():
            continue
        r = score(prior, year, capsules_dir, weights)
        rows.append((year, r["threshold"], r["candidates"], r["positives"], r["random_expected"]["hits"],
                     r["preferential_attachment"]["hits"], r["graph_predictor"]["hits"], r["forecaster"]["hits"]))
    lines = ["| Round | Eligible pairs | Combined within 10 years | Chance (expected) | Size rule | Graph predictor | A4 agent (Claude, 14 Nov 2026) |",
             "|---|---|---|---|---|---|---|"]
    for y, t, n, pos, rnd, pa, gp, ag in rows:
        lines.append(f"| {y} (deg product at most {t}) | {n:,} | {pos} | {rnd:.1f} | {pa} / 10 | **{gp} / 10** | {ag} / 10 |")
    return "\n".join(lines)


def load_weights(path):
    if not path:
        return None
    d = json.loads(Path(path).read_text())
    return d.get("weights", d)
