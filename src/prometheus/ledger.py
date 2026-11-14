"""A shared forecast ledger: several agents write their picks into one Relate file, and the grader writes the outcomes back.

Relate gives a store one writer lease, so the agents do not open the file themselves. One `relate serve --mcp PORT` process holds
it, and every agent writes through that server's `write_cypher` tool. Each agent records all of its picks in ONE statement
(`RECORD` below), which Relate runs as one transaction: a failing statement leaves nothing behind, and concurrent agents cannot
clobber each other. Pairs are shared nodes, so two agents that pick the same pair point at the same `Pair`.

    (:Agent {name})
    (:Forecast {asOf, capsule, rank, why, cypher, at})-[:BY]->(:Agent)
    (:Forecast)-[:ABOUT]->(:Pair {asOf, a, b})          a < b, opaque capsule ids such as F0012
    (:Pair {outcome, combinedIn, gradedAgainst})        written by `grade` after the agents finish
    (:Meta {kind: 'forecast-ledger'})
"""
from __future__ import annotations

from pathlib import Path

import relate

from . import config
from .graph import TechGraph
from .predict import Snapshot

RECORD = """MERGE (ag:Agent {name: $agent})
WITH ag
UNWIND $picks AS p
WITH ag, p, CASE WHEN p.a < p.b THEN p.a ELSE p.b END AS a, CASE WHEN p.a < p.b THEN p.b ELSE p.a END AS b
MERGE (pr:Pair {asOf: $asOf, a: a, b: b})
CREATE (f:Forecast {asOf: $asOf, capsule: $capsule, rank: p.rank, why: p.why, cypher: p.cypher, at: $at})
CREATE (f)-[:BY]->(ag)
CREATE (f)-[:ABOUT]->(pr)"""


def init(path) -> Path:
    """Create an empty ledger (refuses to overwrite one)."""
    p = Path(path)
    if p.exists():
        raise FileExistsError(f"{p} exists; a ledger is never overwritten")
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = relate.connect(str(p))
    cur = conn.cursor()
    cur.execute("CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE")
    cur.execute("CREATE (:Meta {kind: 'forecast-ledger', recordStatement: $s})", {"s": RECORD})
    conn.flush()
    conn.close()
    return p


def record(path, agent: str, as_of: int, capsule: str, picks: list[dict], at: str = "") -> None:
    """Write one agent's picks in one statement, the same statement an agent sends through MCP (used by tests and replays)."""
    conn = relate.connect(str(path))
    try:
        conn.cursor().execute(RECORD, {"agent": agent, "asOf": as_of, "capsule": capsule, "at": at, "picks": picks})
        conn.flush()
    finally:
        conn.close()


def grade(path, against, as_of: int, horizon: int | None = None) -> dict:
    """Write each pair's outcome, judged on a later capsule built with the same seed, and return per-agent hits.

    outcome is 'combined' (first combined in (as_of, as_of + horizon]), 'not combined', 'already combined' (not a valid
    forecast: it had combined by as_of) or 'unknown' (an id that is not a field alive at as_of).
    """
    with TechGraph(against) as g:
        end = g.data_end_year
        h = horizon if horizon is not None else min(config.HORIZON, end - as_of)
        if h <= 0:
            raise ValueError(f"{against} ends in {end}; it cannot grade forecasts made as of {as_of}")
        truth = {(min(a, b), max(a, b)): y for a, b, y in g.combined()}
        snap = Snapshot.from_graph(g, as_of)
    alive = set(snap.codes)
    cands = snap.candidates()
    positives = sum(1 for p in cands if as_of < truth.get(p, 10**9) <= as_of + h)
    base_rate = positives / len(cands) if cands else 0.0

    conn = relate.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute("MATCH (pr:Pair {asOf: $y}) RETURN pr.a AS a, pr.b AS b", {"y": as_of})
        rows = []
        for r in cur.fetchall():
            a, b = r["a"], r["b"]
            fy = truth.get((min(a, b), max(a, b)))
            if a not in alive or b not in alive:
                out = "unknown"
            elif fy is not None and fy <= as_of:
                out = "already combined"
            elif fy is not None and fy <= as_of + h:
                out = "combined"
            else:
                out = "not combined"
            rows.append({"a": a, "b": b, "outcome": out, "year": fy if out == "combined" else None})
        cur.execute("UNWIND $rows AS r MATCH (pr:Pair {asOf: $y, a: r.a, b: r.b}) "
                    "SET pr.outcome = r.outcome, pr.combinedIn = r.year, pr.gradedAgainst = $g, pr.horizon = $h",
                    {"rows": rows, "y": as_of, "g": Path(against).name, "h": h})
        conn.flush()
    finally:
        conn.close()
    rep = report(path, as_of)
    rep.update({"as_of": as_of, "horizon": h, "graded_against": Path(against).name, "candidates": len(cands),
                "positives": positives, "base_rate": base_rate})
    return rep


def report(path, as_of: int) -> dict:
    """Per-agent picks and hits, and the pairs several agents agreed on, read back from the ledger."""
    conn = relate.connect(str(path), read_only=True)
    try:
        cur = conn.cursor()
        cur.execute("MATCH (f:Forecast {asOf: $y})-[:BY]->(ag:Agent), (f)-[:ABOUT]->(pr:Pair) "
                    "RETURN ag.name AS agent, count(f) AS picks, "
                    "sum(CASE WHEN pr.outcome = 'combined' THEN 1 ELSE 0 END) AS hits, "
                    "sum(CASE WHEN pr.outcome IN ['combined', 'not combined'] THEN 1 ELSE 0 END) AS valid ORDER BY agent", {"y": as_of})
        agents = [dict(r) for r in cur.fetchall()]
        cur.execute("MATCH (pr:Pair {asOf: $y})<-[:ABOUT]-(f:Forecast)-[:BY]->(ag:Agent) "
                    "WITH pr, collect(DISTINCT ag.name) AS by WHERE size(by) >= 2 "
                    "RETURN pr.a AS a, pr.b AS b, by, pr.outcome AS outcome, pr.combinedIn AS combinedIn ORDER BY size(by) DESC, a, b", {"y": as_of})
        shared = [dict(r) for r in cur.fetchall()]
        cur.execute("MATCH (pr:Pair {asOf: $y}) RETURN count(pr) AS pairs, "
                    "sum(CASE WHEN pr.outcome = 'combined' THEN 1 ELSE 0 END) AS hits", {"y": as_of})
        tot = dict(cur.fetchall()[0])
    finally:
        conn.close()
    return {"agents": agents, "shared_pairs": shared, "distinct_pairs": tot["pairs"], "distinct_hits": tot["hits"]}
