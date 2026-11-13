"""A field's "genome": how strongly it inherits from the founder fields.

Founders are the most built-upon fields (most direct dependents) that exist in the
snapshot. For each field, the genome has one number per founder: gamma ** hops if the
founder is an ancestor through BUILDS_ON (1 for itself), else 0. Two fields with similar
genomes grew out of the same roots. The genome is stored as a Relate vector with a vector
index, so "nearest relatives" is one index query.
"""
from __future__ import annotations

import math

from . import config

GAMMA = 0.85
INDEX = "field_genome"


def founders(snap, n: int = config.GENOME_FOUNDERS) -> list[str]:
    deps: dict[str, int] = {c: 0 for c in snap.codes}
    for c, ps in snap.pre.items():
        for p in ps:
            deps[p] += 1
    ranked = sorted(snap.codes, key=lambda c: (-deps[c], c))
    return ranked[: min(n, len(ranked))]


def _hops_up(snap, code: str) -> dict[str, int]:
    seen = {code: 0}
    frontier = [code]
    depth = 0
    while frontier:
        depth += 1
        nxt = []
        for f in frontier:
            for p in snap.pre[f]:
                if p not in seen:
                    seen[p] = depth
                    nxt.append(p)
        frontier = nxt
    return seen


def vectors(snap, n: int = config.GENOME_FOUNDERS, gamma: float = GAMMA) -> dict[str, list[float]]:
    """code -> unit-length genome vector (all zeros if the field has no founder ancestry)."""
    fs = founders(snap, n)
    out = {}
    for c in snap.codes:
        hops = _hops_up(snap, c)
        v = [gamma ** hops[f] if f in hops else 0.0 for f in fs]
        norm = math.sqrt(sum(x * x for x in v))
        out[c] = [x / norm for x in v] if norm else v
    return out


def cosine(u, v) -> float:
    if not u or not v:
        return 0.0
    return sum(x * y for x, y in zip(u, v))  # vectors are unit length (or all zero)


def cluster(vecs: dict[str, list[float]]):
    """Average-linkage clustering on 1 - cosine. Returns (leaf order, merges).

    merges are (left, right, distance, size), where left/right are field codes or earlier
    merge indices written as "#<k>". This is the dendrogram drawn on the heatmap's edge.
    """
    codes = sorted(vecs)
    if len(codes) > 500:
        raise ValueError(f"clustering {len(codes)} fields is too slow (it is O(n^3)); use the slice or the top 500")
    clusters = {c: [c] for c in codes}
    name = {c: c for c in codes}
    dist = {}
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            dist[(a, b)] = 1.0 - cosine(vecs[a], vecs[b])
    merges = []
    nxt = 0
    active = set(codes)
    while len(active) > 1:
        (a, b), d = min(((k, v) for k, v in dist.items()), key=lambda kv: (kv[1], kv[0]))
        new = f"#{nxt}"
        nxt += 1
        merges.append((name[a], name[b], round(d, 6), len(clusters[a]) + len(clusters[b])))
        sa, sb = len(clusters[a]), len(clusters[b])
        clusters[new] = clusters[a] + clusters[b]
        name[new] = new
        for c in list(active):
            if c in (a, b):
                continue
            da = dist.get((a, c) if (a, c) in dist else (c, a))
            db = dist.get((b, c) if (b, c) in dist else (c, b))
            dist[(c, new) if c < new else (new, c)] = (da * sa + db * sb) / (sa + sb)
        for c in list(dist):
            if a in c or b in c:
                del dist[c]
        active -= {a, b}
        active.add(new)
        del clusters[a], clusters[b]
    order = clusters[next(iter(active))] if active else []
    return order, merges


# ---- Relate: store the vectors and search them --------------------------

def write_to_store(graph, snap) -> dict:
    """Write each genome as a vector property and create the vector index.

    `graph` must be opened read-write. Fields with an all-zero genome get no vector
    (cosine is undefined for them).
    """
    fs = founders(snap)
    vecs = vectors(snap)
    rows = [{"code": c, "v": v} for c, v in vecs.items() if any(v)]
    for i in range(0, len(rows), 500):
        graph.q("UNWIND $rows AS r MATCH (f:Field {code: r.code}) SET f.genome = r.v", {"rows": rows[i:i + 500]})
    dims = len(fs)
    graph.q(
        f"CREATE VECTOR INDEX {INDEX} IF NOT EXISTS FOR (f:Field) ON (f.genome) "
        f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, `vector.similarity_function`: 'cosine'}}}}"
    )
    graph.q("MATCH (m:Meta) SET m.genomeAsOf = $y, m.genomeFounders = $f", {"y": snap.year, "f": fs})
    return {"fields_with_genome": len(rows), "dimensions": dims, "founders": fs}


def nearest(graph, code: str, k: int = 10) -> list[dict]:
    """The k fields whose genome is most similar to `code`'s, by the vector index."""
    rows = graph.q("MATCH (f:Field {code: $c}) RETURN f.genome AS v", {"c": code})
    if not rows or not rows[0]["v"]:
        return []
    found = graph.q(
        f"CALL db.index.vector.queryNodes('{INDEX}', $k, $v) YIELD node, score "
        "RETURN node.code AS code, node.title AS title, score",
        {"k": k + 1, "v": rows[0]["v"]},
    )
    # Relate reports cosine scores as (1 + cosine) / 2; convert back to cosine.
    return [
        {"code": r["code"], "title": r["title"], "cosine": round(2 * r["score"] - 1, 4)}
        for r in found if r["code"] != code
    ][:k]
