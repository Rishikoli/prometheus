"""Sealed time capsules: one small read-only Relate file per year.

A capsule holds only what was known by year Y: fields and edges whose firstYear is Y or
earlier. Field codes and titles are replaced by opaque ids (F0001 ...), edge counts are
left out (they are totals through today and would leak the future), and there are no
PREDICTED edges. The id-to-code table is written NEXT to the capsule, never inside it.

Ids come from one seeded shuffle of every field in the full dataset, so the same field
has the same id in every capsule built with the same seed. That lets a forecast made on
the 1995 capsule be graded against the 2005 capsule.

Blinding reduces hindsight leakage; it does not prove it is zero (a language model might
still recognise the shape of the graph). Report agent results as an experiment.
"""
from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path

import relate

BRIEF = """# Forecaster brief

You are forecasting which pairs of technology fields will first be combined in a patent
family during the next {horizon} years (after {year}).

You may use ONLY the read-only database tools of the `{name}` MCP server. The database is
a snapshot of everything known up to {year}:

- `(:Field {{code, firstYear}})` - an anonymous technology field; `firstYear` is when it began.
- `(:Field)-[:COMBINED_WITH {{firstYear}}]-(:Field)` - two fields already combined, since that year.
- `(:Field)-[:BUILDS_ON {{firstYear}}]->(:Field)` - the first field cites the second as a prerequisite.

Field names are hidden on purpose. Do not try to guess what the fields are.

Task: return the 10 pairs of fields you think are most likely to combine for the first time
after {year}. Pairs must not already be connected by COMBINED_WITH. For each pair, include
the exact Cypher query that produced or supports it. Reply with JSON only:

{{"pairs": [{{"a": "F0001", "b": "F0002", "cypher": "MATCH ...", "why": "one sentence"}}]}}
"""


BRIEF_A4_RULE = """
Eligibility rule (this run only). Let deg(X) be the number of fields X is already combined with
(`COMBINED_WITH`, in either direction). A pair (a, b) is eligible ONLY if

    deg(a) * deg(b) <= {threshold}

Pairs above that value are the well-known big-field-meets-big-field pairs and are NOT eligible. All
10 of your pairs must be eligible and must not already be connected by COMBINED_WITH. Check each
pair's eligibility with a query before you include it.
"""


def pa_threshold(snap) -> int:
    """Lower median of deg(a) * deg(b) over every candidate (not yet combined) pair. Deterministic, no tie-breaking."""
    pa = sorted(snap.deg(a) * snap.deg(b) for a, b in snap.candidates())
    return pa[(len(pa) - 1) // 2]


def brief_a4(year: int, horizon: int, name: str, threshold: int) -> str:
    base = BRIEF.format(year=year, horizon=horizon, name=name)
    marker = "Task: return the 10 pairs"
    head, tail = base.split(marker, 1)
    return head + BRIEF_A4_RULE.format(threshold=threshold).lstrip("\n") + "\n" + marker + tail


def _read(path: Path):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def blind_ids(csv_dir, seed: int = 0) -> dict[str, str]:
    """code -> opaque id, stable across capsules built from the same data with the same seed."""
    codes = sorted(r["code"] for r in _read(Path(csv_dir) / "fields.csv"))
    rng = random.Random(seed)
    order = codes[:]
    rng.shuffle(order)
    return {c: f"F{i + 1:04d}" for i, c in enumerate(order)}


def build_capsule(csv_dir, as_of: int, out_path, seed: int = 0, horizon: int = 10, overwrite: bool = True) -> dict:
    csv_dir, out = Path(csv_dir), Path(out_path)
    ids = blind_ids(csv_dir, seed)
    fields = [r for r in _read(csv_dir / "fields.csv") if int(r["first_year"]) <= as_of]
    keep = {r["code"] for r in fields}
    if out.exists():
        if not overwrite:
            raise FileExistsError(out)
        shutil.rmtree(out) if out.is_dir() else out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = relate.connect(str(out))
    cur = conn.cursor()
    cur.execute("CREATE CONSTRAINT field_code_unique IF NOT EXISTS FOR (f:Field) REQUIRE f.code IS UNIQUE")
    rows = [{"code": ids[r["code"]], "firstYear": int(r["first_year"])} for r in fields]
    for i in range(0, len(rows), 5000):
        cur.execute("UNWIND $rows AS r CREATE (:Field {code: r.code, title: '', firstYear: r.firstYear})",
                    {"rows": rows[i:i + 5000]})

    def load(filename, a, b, rel):
        edges = [
            {"a": ids[r[a]], "b": ids[r[b]], "firstYear": int(r["first_year"])}
            for r in _read(csv_dir / filename)
            if int(r["first_year"]) <= as_of and r[a] in keep and r[b] in keep
        ]
        for i in range(0, len(edges), 5000):
            cur.execute(
                f"UNWIND $rows AS r MATCH (a:Field {{code: r.a}}), (b:Field {{code: r.b}}) "
                f"CREATE (a)-[:{rel} {{firstYear: r.firstYear}}]->(b)",
                {"rows": edges[i:i + 5000]},
            )
        return len(edges)

    n_b = load("builds_on.csv", "src", "dst", "BUILDS_ON")
    n_c = load("combined_with.csv", "a", "b", "COMBINED_WITH")
    cur.execute("CREATE (:Meta {source: 'capsule', blind: true, asOf: $y, dataEndYear: $y, slice: 'capsule'})",
                {"y": as_of})
    conn.flush()
    conn.close()

    # id-to-code table: next to the capsule, never inside it
    id_to_code = {ids[c]: c for c in keep}
    map_path = out.with_suffix(".map.json")
    map_path.write_text(json.dumps({"asOf": as_of, "seed": seed, "idToCode": id_to_code}, indent=1, sort_keys=True))
    name = f"capsule-{as_of}"
    brief_path = out.with_suffix(".brief.md")
    brief_path.write_text(BRIEF.format(year=as_of, horizon=horizon, name=name))
    mcp_path = out.with_suffix(".mcp.json")
    mcp_path.write_text(json.dumps(
        {"mcpServers": {name: {"command": "relate",
                               "args": ["serve", "--mcp", "stdio", "--database", str(out), "--read-only"]}}}, indent=2))
    return {"as_of": as_of, "fields": len(rows), "builds_on": n_b, "combined_with": n_c, "path": str(out),
            "map": str(map_path), "brief": str(brief_path), "mcp_config": str(mcp_path)}
