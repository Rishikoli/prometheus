"""Load the three CSVs into a single Relate file (a .rl store).

Graph model
  (:Field {code, title, firstYear, nPatents})
  (:Field)-[:BUILDS_ON     {count, firstYear}]->(:Field)   src builds on dst
  (:Field)-[:COMBINED_WITH {count, firstYear}]->(:Field)   stored once, a < b; query undirected
  (:Meta {source, dataEndYear, slice, thresholds...})      provenance of this store

`firstYear` on every edge is what makes time travel work: a snapshot "as of year Y" is
simply `WHERE r.firstYear <= Y`. `count` is a total through the end of the data, so it
is for display only; predictors and capsules never use it.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import relate

from . import config

CHUNK = 20_000


def _read(path: Path):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def _chunks(it, n=CHUNK):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def build(csv_dir, out_path, source: str | None = None, overwrite: bool = True) -> dict:
    csv_dir, out = Path(csv_dir), Path(out_path)
    meta_file = csv_dir / "meta.json"
    meta_in = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    source = source or meta_in.get("source", "patentsview")
    for name in ("fields.csv", "builds_on.csv", "combined_with.csv"):
        if not (csv_dir / name).exists():
            raise FileNotFoundError(f"{csv_dir / name} is missing; run `prometheus pipeline` or `prometheus toy` first")
    if out.exists():
        if not overwrite:
            raise FileExistsError(out)
        shutil.rmtree(out) if out.is_dir() else out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = relate.connect(str(out))
    cur = conn.cursor()
    cur.execute("CREATE CONSTRAINT field_code_unique IF NOT EXISTS FOR (f:Field) REQUIRE f.code IS UNIQUE")

    n_fields = 0
    for rows in _chunks(
        {"code": r["code"], "title": r["title"], "firstYear": int(r["first_year"]), "nPatents": int(float(r["n_patents"]))}
        for r in _read(csv_dir / "fields.csv")
    ):
        cur.execute(
            "UNWIND $rows AS r CREATE (:Field {code: r.code, title: r.title, firstYear: r.firstYear, nPatents: r.nPatents})",
            {"rows": rows},
        )
        n_fields += len(rows)

    def load_edges(filename, a, b, rel):
        n = 0
        for rows in _chunks(
            {"a": r[a], "b": r[b], "count": int(float(r["count"])), "firstYear": int(r["first_year"])}
            for r in _read(csv_dir / filename)
        ):
            cur.execute(
                f"UNWIND $rows AS r MATCH (a:Field {{code: r.a}}), (b:Field {{code: r.b}}) "
                f"CREATE (a)-[:{rel} {{count: r.count, firstYear: r.firstYear}}]->(b)",
                {"rows": rows},
            )
            n += len(rows)
        return n

    n_builds = load_edges("builds_on.csv", "src", "dst", "BUILDS_ON")
    n_comb = load_edges("combined_with.csv", "a", "b", "COMBINED_WITH")

    last_edge_year = max([int(r["first_year"]) for r in _read(csv_dir / "combined_with.csv")] or [0])
    cur.execute(
        "CREATE (:Meta {source: $source, dataEndYear: $end, slice: $slice, "
        "minFieldPatentsPerYear: $a, minPairPatents: $b, minBuildsCitations: $c, cascadeGamma: $g})",
        {
            "source": source,
            "end": int(meta_in.get("data_end_year", last_edge_year)),
            "slice": meta_in.get("slice", "all"),
            "a": int(meta_in.get("min_field_patents_per_year", config.MIN_FIELD_PATENTS_PER_YEAR)),
            "b": int(meta_in.get("min_pair_patents", config.MIN_PAIR_PATENTS)),
            "c": int(meta_in.get("min_builds_citations", config.MIN_BUILDS_CITATIONS)),
            "g": config.CASCADE_GAMMA,
        },
    )
    conn.flush()
    conn.close()
    return {"fields": n_fields, "builds_on": n_builds, "combined_with": n_comb, "path": str(out)}
