from prometheus import backtest, beyond
from prometheus.graph import TechGraph

CUTS = (1995, 2000, 2005)


def _weights(g):
    prep, _ = backtest.prepare(g, (1985, 1990), 10)
    return backtest.tune(prep, (1985, 1990))[0]


def test_subset_is_pa_bottom_half():
    pa = [5.0, 1.0, 9.0, 1.0, 3.0, 7.0, 0.0, 2.0, 8.0, 4.0, 6.0]
    sub = beyond.pa_bottom_half(pa)
    assert len(sub) == len(pa) // 2
    assert max(pa[i] for i in sub) <= min(pa[i] for i in range(len(pa)) if i not in sub)


def test_placebo_has_no_beyond_size_signal(placebo_store):
    with TechGraph(placebo_store) as g:
        r = beyond.run(g, _weights(g), cutoffs=CUTS, n_boot=200, log=lambda *a: None)
    assert r["cutoffs"]
    for c in r["cutoffs"].values():
        lo, hi = c["methods"]["hybrid"]["ci95"]
        assert lo <= 0.5 <= hi  # a harness that found skill here would be inventing it
        assert c["candidates_subset"] == c["candidates_all"] // 2


def test_structured_toy_beats_placebo(toy_store, placebo_store):
    def hyb(store):
        with TechGraph(store) as g:
            r = beyond.run(g, _weights(g), cutoffs=CUTS, n_boot=50, log=lambda *a: None)
        return sum(c["methods"]["hybrid"]["auc"] for c in r["cutoffs"].values()) / len(r["cutoffs"])
    structured, placebo = hyb(toy_store), hyb(placebo_store)
    # The planted effect in the PA-bottom-half subset is modest on 15 to 40 positives (about 0.60), and tuning can
    # fit a little noise even on the placebo (about 0.56), so the check is direction and a floor, not a large margin.
    assert structured > placebo and structured > 0.55


def test_a4_threshold_brief_and_restricted_grading(toy_csv, tmp_path):
    import json

    from prometheus import capsule, grade
    from prometheus.predict import Snapshot

    capsule.build_capsule(toy_csv, 1995, tmp_path / "c95.rl", seed=0)
    capsule.build_capsule(toy_csv, 2005, tmp_path / "c05.rl", seed=0)
    with TechGraph(tmp_path / "c95.rl") as g:
        snap = Snapshot.from_graph(g, 1995)
    t = capsule.pa_threshold(snap)
    pa = [snap.deg(a) * snap.deg(b) for a, b in snap.candidates()]
    assert sum(1 for x in pa if x <= t) >= len(pa) / 2  # at least half the candidates are eligible
    brief = capsule.brief_a4(1995, 10, "capsule-1995", t)
    assert f"<= {t}" in brief and "Task: return the 10 pairs" in brief and "{threshold}" not in brief

    elig = [p for p, v in zip(snap.candidates(), pa) if v <= t]
    inelig = [p for p, v in zip(snap.candidates(), pa) if v > t]
    pairs = [{"a": a, "b": b, "cypher": "x", "why": "y"} for a, b in elig[:3] + inelig[:2]]
    (tmp_path / "f.json").write_text(json.dumps({"pairs": pairs}))
    r = grade.grade(tmp_path / "f.json", tmp_path / "c05.rl", 1995, pa_max=t)
    assert r["pairs_valid"] == 3 and len(r["rejected"]) == len(inelig[:2])
    assert r["candidates"] == len(elig)
    full = grade.grade(tmp_path / "f.json", tmp_path / "c05.rl", 1995)
    assert full["pairs_valid"] == 5 and full["candidates"] == len(snap.candidates())
