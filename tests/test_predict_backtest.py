import json
import shutil

import pytest

from prometheus import backtest, build, genome, toy
from prometheus.graph import TechGraph
from prometheus.predict import (Snapshot, average_ranks, breakthrough, hybrid, percentile, rank_order,
                              signal_table, tie_breaker, top_gaps)


# ---- metrics ---------------------------------------------------------------

def test_average_ranks_share_ties():
    assert average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_auc_perfect_reversed_and_chance():
    assert backtest.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == 1.0
    assert backtest.auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == 0.0
    assert backtest.auc([1, 1, 1, 1], [0, 1, 0, 1]) == 0.5
    assert backtest.auc([1, 2, 3], [0, 0, 0]) is None


def test_rank_order_breaks_ties_the_same_way_for_everyone():
    tie = tie_breaker(5)
    assert rank_order([1, 1, 1, 1, 1], tie) == rank_order([2, 2, 2, 2, 2], tie)
    assert rank_order([0, 5, 0, 0, 0], tie)[0] == 1


def test_hybrid_is_a_weighted_mix_of_percentile_ranks():
    table = {"cn": [0.0, 1.0, 2.0], "aa": [2.0, 1.0, 0.0], "prereq": [0, 0, 0], "pa": [1, 1, 1]}
    only_cn = hybrid(table, {"cn": 1.0})
    assert only_cn == percentile(table["cn"])
    assert hybrid(table, {"cn": 1.0, "aa": 1.0}) == [a + b for a, b in zip(percentile(table["cn"]), percentile(table["aa"]))]


# ---- no peeking at the future ----------------------------------------------

def test_snapshot_does_not_depend_on_anything_after_the_cutoff(toy_csv, toy_store, tmp_path):
    """Build a store from data truncated at Y. Its snapshot at Y must equal the full store's snapshot at Y."""
    import csv
    y = 1998
    cut = tmp_path / "cut"
    cut.mkdir()
    for name, col in (("fields.csv", "first_year"), ("builds_on.csv", "first_year"), ("combined_with.csv", "first_year")):
        rows = list(csv.DictReader(open(toy_csv / name)))
        with open(cut / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(r for r in rows if int(r[col]) <= y)
    shutil.copy(toy_csv / "meta.json", cut / "meta.json")
    build.build(cut, tmp_path / "cut.rl")
    with TechGraph(toy_store) as full, TechGraph(tmp_path / "cut.rl") as trunc:
        a, b = Snapshot.from_graph(full, y), Snapshot.from_graph(trunc, y)
    assert a.codes == b.codes and a.adj == b.adj and a.pre == b.pre
    cands = a.candidates()
    assert signal_table(a, cands) == signal_table(b, cands)


# ---- the harness itself: it must find skill that is planted and none that is not ----

@pytest.fixture(scope="module")
def strong(toy_store):
    with TechGraph(toy_store) as g:
        return backtest.run(g, log=lambda *_: None)


@pytest.fixture(scope="module")
def placebo(placebo_store):
    with TechGraph(placebo_store) as g:
        return backtest.run(g, log=lambda *_: None)


def test_gate_says_go_when_structure_is_planted(strong):
    assert strong["gate"]["verdict"] == "GO"
    assert strong["gate"]["ratio"] >= 2.0
    for c in strong["heldout_cutoffs_result"].values():
        assert c["methods"]["hybrid"]["auc"] > 0.6
        assert c["methods"]["hybrid"]["auc"] > c["methods"]["random"]["auc"]


def test_gate_says_no_go_on_a_placebo_with_no_structure(placebo):
    """If this ever says GO, the harness is inventing skill."""
    assert placebo["gate"]["verdict"] == "NO-GO"
    for c in placebo["heldout_cutoffs_result"].values():
        assert abs(c["methods"]["hybrid"]["auc"] - 0.5) < 0.1


def test_every_cutoff_reports_its_positives(strong):
    for key in ("tuning_cutoffs_result", "heldout_cutoffs_result"):
        for c in strong[key].values():
            assert c["positives"] > 0 and c["candidates"] > c["positives"]
            assert c["low_confidence"] == (c["positives"] < 30)


def test_cutoffs_that_run_past_the_data_are_skipped(toy_store):
    with TechGraph(toy_store) as g:
        res = backtest.run(g, horizon=10, tune_cutoffs=(1995,), test_cutoffs=(2005, 2020), log=lambda *_: None)
    assert 2020 in res["skipped_cutoffs"] and 2005 in res["heldout_cutoffs_result"]


def test_weights_are_tuned_on_tuning_cutoffs_only(strong):
    assert set(strong["tuning"]["tuned_on"]) <= set(strong["settings"]["tune_cutoffs"])
    assert not set(strong["tuning"]["tuned_on"]) & set(strong["settings"]["test_cutoffs"])


def test_report_has_synthetic_banner_and_gate(strong, tmp_path):
    md, js = backtest.write(strong, tmp_path)
    text = md.read_text()
    assert "SYNTHETIC DATA" in text and "Gate" in text and "positives" in text
    assert json.loads(js.read_text())["gate"]["verdict"] == "GO"


# ---- predictions and the breakthrough what-if -------------------------------

def test_top_gaps_are_real_gaps(toy_store):
    with TechGraph(toy_store) as g:
        snap = Snapshot.from_graph(g, 2000)
        gaps = top_gaps(snap, k=15)
    assert len(gaps) == 15 and [r["rank"] for r in gaps] == list(range(1, 16))
    assert all(r["b"] not in snap.adj[r["a"]] for r in gaps)
    assert gaps[0]["score"] >= gaps[-1]["score"]


def test_breakthrough_is_read_only_and_lifts_neighbouring_pairs(toy_store):
    with TechGraph(toy_store) as g:
        snap = Snapshot.from_graph(g, 2000)
    before = {c: set(s) for c, s in snap.adj.items()}
    a, b = next((a, b) for a, b in snap.candidates() if snap.adj[a] and snap.adj[b])
    res = breakthrough(snap, a, b, k=100)
    assert snap.adj == before, "the snapshot must not be modified"
    assert res["added"] == (a, b)
    for item in res["enteredTop"]:
        assert item["rankAfter"] <= 100 < (item["rankBefore"] or 10**9)
        assert item["scoreAfter"] >= item["scoreBefore"] or item["rankAfter"] < item["rankBefore"]
    with pytest.raises(ValueError):
        breakthrough(snap, a, next(iter(snap.adj[a])))


# ---- genome ----------------------------------------------------------------

def test_genome_vectors_are_unit_length_and_self_similar(toy_store):
    with TechGraph(toy_store) as g:
        snap = Snapshot.from_graph(g, 2010)
    vecs = genome.vectors(snap)
    nonzero = [v for v in vecs.values() if any(v)]
    assert len(nonzero) > 100
    for v in nonzero:
        assert abs(sum(x * x for x in v) - 1) < 1e-9
        assert abs(genome.cosine(v, v) - 1) < 1e-9


def test_dendrogram_order_is_a_permutation(toy_store):
    with TechGraph(toy_store) as g:
        snap = Snapshot.from_graph(g, 1995)
    vecs = genome.vectors(snap)
    order, merges = genome.cluster(vecs)
    assert sorted(order) == sorted(vecs) and len(merges) == len(vecs) - 1
    assert merges[-1][3] == len(vecs)


def test_vector_index_agrees_with_python_cosine(toy_store, tmp_path):
    copy = tmp_path / "copy.rl"
    shutil.copy(toy_store, copy)
    with TechGraph(copy, read_only=False) as g:
        snap = Snapshot.from_graph(g, g.data_end_year)
        info = genome.write_to_store(g, snap)
        assert info["dimensions"] == 64
        near = genome.nearest(g, "TOY040", k=5)
        vecs = genome.vectors(snap)
    expected = sorted(((genome.cosine(vecs["TOY040"], v), c) for c, v in vecs.items() if c != "TOY040" and any(v)),
                      reverse=True)[:5]
    assert [r["code"] for r in near][:3] == [c for _, c in expected][:3]
    assert abs(near[0]["cosine"] - expected[0][0]) < 1e-3


def test_breakthrough_adds_exactly_one_common_neighbour_to_adjacent_pairs(toy_store):
    """If a and b combine, every field x already combined with b gains `a` ... i.e. pair (a, x) gains common neighbour b."""
    with TechGraph(toy_store) as g:
        snap = Snapshot.from_graph(g, 2000)
    a, b = next((a, b) for a, b in snap.candidates() if len(snap.adj[b] - snap.adj[a] - {a}) >= 2)
    after = snap.with_edge(a, b)
    xs = sorted(snap.adj[b] - snap.adj[a] - {a})
    pairs = [(min(a, x), max(a, x)) for x in xs]
    before_cn = dict(zip(pairs, signal_table(snap, pairs)["cn"]))
    after_cn = dict(zip(pairs, signal_table(after, pairs)["cn"]))
    assert all(after_cn[p] == before_cn[p] + 1 for p in pairs)
