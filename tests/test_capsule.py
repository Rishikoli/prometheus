import json
import re

import pytest

from prometheus import capsule, grade
from prometheus.graph import TechGraph
from prometheus.predict import Snapshot


@pytest.fixture(scope="module")
def caps(toy_csv, tmp_path_factory):
    d = tmp_path_factory.mktemp("caps")
    a = capsule.build_capsule(toy_csv, 1995, d / "1995.rl", seed=3)
    b = capsule.build_capsule(toy_csv, 2005, d / "2005.rl", seed=3)
    return d, a, b


def test_capsule_holds_nothing_after_its_year(caps):
    d, a, _ = caps
    with TechGraph(d / "1995.rl") as g:
        assert all(f["firstYear"] <= 1995 for f in g.fields())
        assert all(y <= 1995 for _, _, y in g.combined()) and all(y <= 1995 for _, _, y in g.builds())
        assert g.meta()["asOf"] == 1995 and g.meta()["blind"] is True and g.data_end_year == 1995


def test_capsule_hides_codes_titles_and_counts(caps, toy_csv):
    d, _, _ = caps
    import csv
    real = {r["code"] for r in csv.DictReader(open(toy_csv / "fields.csv"))}
    with TechGraph(d / "1995.rl") as g:
        fields = g.fields()
        assert all(re.fullmatch(r"F\d{4}", f["code"]) for f in fields)
        assert not {f["code"] for f in fields} & real
        assert all(not f["title"] and f["nPatents"] is None for f in fields)
        assert g.q("MATCH ()-[r]->() WHERE r.count IS NOT NULL RETURN count(r) AS n")[0]["n"] == 0
        assert g.q("MATCH ()-[r:PREDICTED]->() RETURN count(r) AS n")[0]["n"] == 0
        assert g.meta()["source"] == "capsule"


def test_ids_are_stable_across_capsules_and_the_map_is_outside(caps):
    d, a, b = caps
    m1 = json.loads(open(a["map"]).read())["idToCode"]
    m2 = json.loads(open(b["map"]).read())["idToCode"]
    assert all(m2[k] == v for k, v in m1.items())  # same id, same field
    assert len(m2) > len(m1)
    assert a["map"].endswith(".map.json") and a["path"].endswith("1995.rl")
    with TechGraph(d / "1995.rl") as g:  # the map is not inside the capsule
        text = json.dumps(g.q("MATCH (n) RETURN properties(n) AS p"))
    assert not any(code in text for code in list(m1.values())[:20])


def test_brief_and_mcp_config(caps):
    _, a, _ = caps
    cfg = json.loads(open(a["mcp_config"]).read())["mcpServers"]["capsule-1995"]
    assert cfg["command"] == "relate" and "--read-only" in cfg["args"] and "--mcp" in cfg["args"]
    brief = open(a["brief"]).read()
    assert "1995" in brief and "Cypher" in brief and "{" in brief


def _positives(d, y0, y1):
    with TechGraph(d / f"{y1}.rl") as late, TechGraph(d / f"{y0}.rl") as early:
        before = {(min(a, b), max(a, b)) for a, b, _ in early.combined()}
        snap = Snapshot.from_graph(early, y0)
        return [(a, b) for a, b, y in late.combined() if y0 < y <= y1 and (a, b) in {c for c in snap.candidates()}], before


def test_perfect_forecast_scores_full_marks(caps, tmp_path):
    d, _, _ = caps
    pos, _ = _positives(d, 1995, 2005)
    assert len(pos) >= 10
    fc = tmp_path / "f.json"
    fc.write_text(json.dumps({"pairs": [{"a": a, "b": b, "cypher": "MATCH (n) RETURN n"} for a, b in pos[:10]]}))
    res = grade.grade(fc, d / "2005.rl", as_of=1995)
    assert res["horizon"] == 10 and res["pairs_valid"] == 10 and res["with_cypher"] == 10
    assert res["forecaster"]["hits"] == 10 and res["forecaster"]["precision"] == 1.0
    assert res["graph_predictor"]["hits"] <= 10 and res["random_expected"]["lift"] == 1.0


def test_bad_pairs_are_rejected_not_counted(caps, tmp_path):
    d, _, _ = caps
    with TechGraph(d / "1995.rl") as g:
        already = g.combined()[0]
    fc = tmp_path / "f.json"
    fc.write_text(json.dumps({"pairs": [{"a": already[0], "b": already[1]}, {"a": "F9999", "b": "F0001"},
                                        {"a": "F0001", "b": "F0001"}]}))
    res = grade.grade(fc, d / "2005.rl", as_of=1995)
    assert res["pairs_valid"] == 0 and len(res["rejected"]) == 3 and res["forecaster"]["hits"] == 0


def test_grading_against_full_store_with_map_matches(caps, toy_store, tmp_path):
    d, a, _ = caps
    pos, _ = _positives(d, 1995, 2005)
    fc = tmp_path / "f.json"
    fc.write_text(json.dumps({"pairs": [{"a": x, "b": y, "cypher": "q"} for x, y in pos[:6]]}))
    r1 = grade.grade(fc, d / "2005.rl", as_of=1995)
    r2 = grade.grade(fc, toy_store, as_of=1995, map_path=a["map"], horizon=10)
    assert r1["forecaster"] == r2["forecaster"] and r1["positives"] == r2["positives"]
    with pytest.raises(ValueError):
        grade.grade(fc, toy_store, as_of=1995)  # a full store needs the map
    with pytest.raises(ValueError):
        grade.grade(fc, d / "2005.rl", as_of=1995, horizon=20)  # beyond what the store knows
