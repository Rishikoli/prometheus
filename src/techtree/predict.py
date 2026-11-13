"""Score pairs of fields that have not combined yet ("the adjacent possible").

Everything here is computed from a Snapshot: the graph as it stood in one year, built
from edges with firstYear <= that year. No total, count or later year ever enters a
feature, so a score for year Y cannot see anything after Y.

Signals (all existence-based)
  cn       common neighbours: number of fields already combined with both
  aa       Adamic-Adar: common neighbours, each weighted 1/log(its degree)
  prereq   shared prerequisites (both build on the same fields), +1 if one builds on the other
  pa       preferential attachment (degree product); used as a baseline
  genome   cosine similarity of the two fields' inheritance vectors (see genome.py)
Methods: random and pa are baselines; hybrid is a weighted mix of the percentile ranks
of cn, aa, prereq and genome.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from . import genome as genome_mod

SIGNALS = ("cn", "aa", "prereq", "pa", "genome")
MIX = ("cn", "aa", "prereq", "genome")  # signals that can enter the hybrid
DEFAULT_WEIGHTS = {"cn": 1.0, "aa": 1.0, "prereq": 1.0, "genome": 0.0}
TIE_SEED = 12345


class Snapshot:
    """The graph as of one year, in plain dictionaries."""

    def __init__(self, year, first_year, adj, pre):
        self.year = year
        self.first_year = first_year  # code -> year the field began to exist
        self.codes = sorted(first_year)
        self.adj = adj  # code -> set of combined partners
        self.pre = pre  # code -> set of fields it builds on

    @classmethod
    def from_graph(cls, g, year: int) -> "Snapshot":
        first_year = {f["code"]: f["firstYear"] for f in g.fields(year)}
        adj = {c: set() for c in first_year}
        pre = {c: set() for c in first_year}
        for a, b, _ in g.combined(year):
            if a in adj and b in adj:
                adj[a].add(b)
                adj[b].add(a)
        for s, d, _ in g.builds(year):
            if s in pre and d in pre:
                pre[s].add(d)
        return cls(year, first_year, adj, pre)

    def deg(self, c: str) -> int:
        return len(self.adj[c])

    def candidates(self) -> list[tuple[str, str]]:
        """Every pair of existing fields that has not combined yet (a < b)."""
        out = []
        for i, a in enumerate(self.codes):
            na = self.adj[a]
            for b in self.codes[i + 1:]:
                if b not in na:
                    out.append((a, b))
        return out

    def with_edge(self, a: str, b: str) -> "Snapshot":
        adj = {c: set(s) for c, s in self.adj.items()}
        adj[a].add(b)
        adj[b].add(a)
        return Snapshot(self.year, self.first_year, adj, self.pre)


# ---- signals -------------------------------------------------------------

def _cn_aa(snap: Snapshot) -> tuple[dict, dict]:
    cn: dict = defaultdict(int)
    aa: dict = defaultdict(float)
    for n, nb in snap.adj.items():
        d = len(nb)
        if d < 2:
            continue
        w = 1.0 / math.log(d)
        nbl = sorted(nb)
        for i in range(len(nbl)):
            a = nbl[i]
            na = snap.adj[a]
            for b in nbl[i + 1:]:
                if b in na:
                    continue
                cn[(a, b)] += 1
                aa[(a, b)] += w
    return cn, aa


def signal_table(snap: Snapshot, cands: list[tuple[str, str]], vectors: dict | None = None) -> dict[str, list[float]]:
    """One list per signal, aligned with `cands`."""
    cn, aa = _cn_aa(snap)
    table = {
        "cn": [float(cn.get(p, 0)) for p in cands],
        "aa": [aa.get(p, 0.0) for p in cands],
        "prereq": [
            float(len(snap.pre[a] & snap.pre[b]) + (1 if (b in snap.pre[a] or a in snap.pre[b]) else 0))
            for a, b in cands
        ],
        "pa": [float(snap.deg(a) * snap.deg(b)) for a, b in cands],
    }
    if vectors is not None:
        table["genome"] = [genome_mod.cosine(vectors.get(a), vectors.get(b)) for a, b in cands]
    return table


def average_ranks(values: list[float]) -> list[float]:
    """1-based ranks, ascending; tied values share the average of their ranks."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def percentile(values: list[float]) -> list[float]:
    n = len(values)
    return [r / n for r in average_ranks(values)] if n else []


def hybrid(table: dict[str, list[float]], weights: dict[str, float]) -> list[float]:
    n = len(next(iter(table.values())))
    out = [0.0] * n
    for name, w in weights.items():
        if w and name in table:
            p = percentile(table[name])
            for i in range(n):
                out[i] += w * p[i]
    return out


def random_scores(n: int, seed: int = 0) -> list[float]:
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]


def tie_breaker(n: int) -> list[float]:
    """Same pseudo-random tie-break for every method, so ties never favour one of them."""
    return random_scores(n, TIE_SEED)


def rank_order(scores: list[float], tie: list[float]) -> list[int]:
    """Indices from best to worst; equal scores are ordered by the shared tie-breaker."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], tie[i]))


def method_scores(table: dict[str, list[float]], weights: dict[str, float], seed: int = 0) -> dict[str, list[float]]:
    n = len(next(iter(table.values())))
    out = {"random": random_scores(n, seed), "pa": table["pa"], "cn": table["cn"], "aa": table["aa"],
           "prereq": table["prereq"], "hybrid": hybrid(table, weights)}
    if "genome" in table:
        out["genome"] = table["genome"]
    return out


def top_gaps(snap: Snapshot, weights: dict[str, float] | None = None, k: int = 20, use_genome: bool = False) -> list[dict]:
    """The k pairs the hybrid ranks highest as of the snapshot's year."""
    cands = snap.candidates()
    vectors = genome_mod.vectors(snap) if use_genome else None
    table = signal_table(snap, cands, vectors)
    w = dict(weights or DEFAULT_WEIGHTS)
    scores = hybrid(table, w)
    order = rank_order(scores, tie_breaker(len(cands)))
    return [
        {"rank": r + 1, "a": cands[i][0], "b": cands[i][1], "score": round(scores[i], 4),
         "cn": int(table["cn"][i]), "prereq": int(table["prereq"][i])}
        for r, i in enumerate(order[:k])
    ]


def breakthrough(snap: Snapshot, a: str, b: str, weights: dict[str, float] | None = None, k: int = 100,
                 use_genome: bool = False) -> dict:
    """What the model would score if the pair (a, b) combined now.

    Read-only: it adds the edge to an in-memory copy of the snapshot and re-scores. It shows
    which neighbouring pairs would climb into the top k. It describes the *model*, not
    the world, and is only worth showing if the backtest says the model has skill.
    """
    if b in snap.adj[a]:
        raise ValueError(f"{a} and {b} are already combined")
    w = dict(weights or DEFAULT_WEIGHTS)

    def run(s: Snapshot):
        cands = s.candidates()
        table = signal_table(s, cands, genome_mod.vectors(s) if use_genome else None)
        scores = hybrid(table, w)
        order = rank_order(scores, tie_breaker(len(cands)))
        rank = {cands[i]: r + 1 for r, i in enumerate(order)}
        score = {cands[i]: scores[i] for i in range(len(cands))}
        return rank, score

    pair = (min(a, b), max(a, b))
    rank0, score0 = run(snap)
    rank1, score1 = run(snap.with_edge(*pair))
    entered = sorted(
        (p for p, r in rank1.items() if r <= k and rank0.get(p, 10**9) > k),
        key=lambda p: rank1[p],
    )
    return {
        "added": pair,
        "rankBefore": rank0.get(pair),
        "enteredTop": [
            {"a": p[0], "b": p[1], "rankBefore": rank0.get(p), "rankAfter": rank1[p],
             "scoreBefore": round(score0[p], 4), "scoreAfter": round(score1[p], 4)}
            for p in entered
        ],
        "k": k,
    }
