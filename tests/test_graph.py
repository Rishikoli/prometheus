import json
from pathlib import Path

import pytest

from prometheus.graph import TechGraph
from prometheus.predict import Snapshot, _cn_aa

QUERIES = sorted((Path(__file__).parent.parent / "queries").glob("*.cypher"))


@pytest.fixture(scope="module")
def g(toy_store):
    with TechGraph(toy_store) as graph:
        yield graph


def test_store_basics(g):
    m = g.meta()
    assert m["source"] == "toy" and g.is_synthetic and m["dataEndYear"] == 2024
    assert len(g.fields()) == 150


def test_time_slices_only_grow(g):
    sizes = [(len(g.fields(y)), len(g.combined(y)), len(g.builds(y))) for y in (1980, 1990, 2000, 2010, 2024)]
    for a, b in zip(sizes, sizes[1:]):
        assert all(x <= y for x, y in zip(a, b))
    assert sizes[-1] == (150, len(g.combined()), len(g.builds()))
    assert all(y <= 1990 for _, _, y in g.combined(1990))


def test_ancestors_and_descendants_are_inverse(g):
    for code in ("TOY100", "TOY140"):
        anc = g.ancestors(code)
        assert anc, "toy fields past the first 30 build on earlier ones"
        for a, depth in list(anc.items())[:8]:
            assert depth >= 1
            assert code in g.descendants(a)


def test_ancestor_depth_matches_python_bfs(g):
    edges = g.builds()
    pre = {}
    for s, d, _ in edges:
        pre.setdefault(s, set()).add(d)
    seen, frontier, depth = {}, ["TOY120"], 0
    while frontier:
        depth += 1
        nxt = []
        for f in frontier:
            for p in pre.get(f, ()):
                if p not in seen:
                    seen[p] = depth
                    nxt.append(p)
        frontier = nxt
    assert g.ancestors("TOY120") == seen


def test_ancestors_respect_the_year(g):
    assert set(g.ancestors("TOY100", as_of=1990)) <= set(g.ancestors("TOY100"))
    assert g.ancestors("TOY149", as_of=1976) == {}


def test_lineage_is_a_forest_with_older_parents(g):
    lin = g.lineage()
    first = {f["code"]: f["firstYear"] for f in g.fields()}
    for child, p in lin["parents"].items():
        assert first[p["parent"]] < first[child]
        seen, cur = set(), child
        while cur in lin["parents"]:
            assert cur not in seen, "cycle"
            seen.add(cur)
            cur = lin["parents"][cur]["parent"]
        assert cur in lin["roots"]
    assert set(lin["roots"]).isdisjoint(lin["parents"])


def test_knockout_only_reaches_dependents(g):
    res = g.knockout("TOY001")
    assert res and all(0 < v <= 1 for v in res.values())
    assert set(res) <= set(g.descendants("TOY001"))
    early = g.knockout("TOY001", as_of=1990)
    assert set(early) <= set(g.descendants("TOY001", as_of=1990))
    assert g.knockout("TOY149") == {}  # nothing builds on the newest field


def test_knockout_exposure_fades_with_distance(g):
    res = g.knockout("TOY001")
    desc = g.descendants("TOY001")
    near = [v for c, v in res.items() if desc[c] == 1]
    far = [v for c, v in res.items() if desc[c] >= 4]
    assert near and far and sum(near) / len(near) > sum(far) / len(far)


def test_bridge_fields_match_python_common_neighbours(g):
    y = 2005
    snap = Snapshot.from_graph(g, y)
    checked = 0
    for a, b in snap.candidates():
        common = snap.adj[a] & snap.adj[b]
        if common:
            got = g.bridge_fields(a, b, y, top=1000)
            assert {r["code"] for r in got} == common
            ranks = [r["yearsEstablished"] for r in got]
            assert ranks == sorted(ranks, reverse=True)
            checked += 1
            if checked >= 5:
                break
    assert checked


def test_cypher_common_neighbours_equal_python(g):
    """The Cypher query file and the in-memory scorer must agree on every pair."""
    y = 2000
    rows = g.run_file(Path(__file__).parent.parent / "queries" / "gaps_common_neighbours.cypher", {"y": y})
    cypher = {(r["a"], r["b"]): r["commonNeighbours"] for r in rows}
    cn, _ = _cn_aa(Snapshot.from_graph(g, y))
    assert cypher == dict(cn)


@pytest.mark.parametrize("path", QUERIES, ids=[p.name for p in QUERIES])
def test_every_query_file_runs(g, path):
    first = path.read_text().splitlines()[0]
    assert first.startswith("// params:"), "each query file starts with example parameters"
    params = json.loads(first.removeprefix("// params:"))
    if params.get("loss") == "ZERO_MAP":
        params["loss"] = {f["code"]: 0.0 for f in g.fields()}
    rows = g.run_file(path, params)
    assert isinstance(rows, list)
