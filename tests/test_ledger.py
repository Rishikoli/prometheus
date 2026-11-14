from pathlib import Path

import pytest

from prometheus import capsule, ledger
from prometheus.graph import TechGraph
from prometheus.predict import Snapshot


@pytest.fixture()
def capsules(toy_csv, tmp_path):
    capsule.build_capsule(toy_csv, 1995, tmp_path / "1995.rl", seed=0)
    capsule.build_capsule(toy_csv, 2005, tmp_path / "2005.rl", seed=0)
    return tmp_path / "1995.rl", tmp_path / "2005.rl"


def test_several_agents_share_pairs_and_the_grader_writes_outcomes(capsules, tmp_path):
    early, late = capsules
    with TechGraph(early) as g:
        snap = Snapshot.from_graph(g, 1995)
    with TechGraph(late) as g:
        truth = {(min(a, b), max(a, b)): y for a, b, y in g.combined()}
    cands = snap.candidates()
    hit = next(p for p in cands if 1995 < truth.get(p, 10**9) <= 2005)
    miss = next(p for p in cands if p not in truth)
    alive = set(snap.codes)
    already = next(p for p, y in truth.items() if y <= 1995 and p[0] in alive and p[1] in alive)  # combined before the forecast
    path = ledger.init(tmp_path / "ledger.rl")
    with pytest.raises(FileExistsError):
        ledger.init(path)  # never overwritten
    # agent 1 writes the pair in reverse order: the ledger normalises it, so both agents point at one Pair
    ledger.record(path, "agent-1", 1995, "1995.rl", [{"a": hit[1], "b": hit[0], "rank": 1, "why": "w", "cypher": "MATCH ..."},
                                                      {"a": miss[0], "b": miss[1], "rank": 2, "why": "w", "cypher": "MATCH ..."}])
    ledger.record(path, "agent-2", 1995, "1995.rl", [{"a": hit[0], "b": hit[1], "rank": 1, "why": "w", "cypher": "MATCH ..."},
                                                      {"a": already[0], "b": already[1], "rank": 2, "why": "w", "cypher": "MATCH ..."},
                                                      {"a": "F9999", "b": hit[0], "rank": 3, "why": "w", "cypher": "MATCH ..."}])
    res = ledger.grade(path, late, 1995)
    by = {r["agent"]: r for r in res["agents"]}
    assert by["agent-1"] == {"agent": "agent-1", "picks": 2, "hits": 1, "valid": 2}
    assert by["agent-2"] == {"agent": "agent-2", "picks": 3, "hits": 1, "valid": 1}  # already-combined and unknown ids are not valid
    assert res["distinct_pairs"] == 4 and res["distinct_hits"] == 1
    assert [(s["a"], s["b"]) for s in res["shared_pairs"]] == [hit] and sorted(res["shared_pairs"][0]["by"]) == ["agent-1", "agent-2"]
    assert res["shared_pairs"][0]["outcome"] == "combined" and 1995 < res["shared_pairs"][0]["combinedIn"] <= 2005
    assert 0 < res["base_rate"] < 1 and res["horizon"] == 10


def test_the_agent_brief_uses_the_exact_record_statement():
    brief = (Path(__file__).resolve().parents[1] / "agent" / "LEDGER.md").read_text()
    assert ledger.RECORD in brief  # agents send exactly what the tests exercise
