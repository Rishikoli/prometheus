"""Read-side access to a prometheus store.

Every question is a Cypher query over the one small graph. "As of year Y" is always the
filter `r.firstYear <= Y` on the edges (and `f.firstYear <= Y` on the fields), so any
snapshot of history is a query, not a separate file.
"""
from __future__ import annotations

import relate

from . import config


class TechGraph:
    def __init__(self, path, read_only: bool = True):
        self.path = str(path)
        self.conn = relate.connect(self.path, read_only=read_only)
        self.cur = self.conn.cursor()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- plumbing -------------------------------------------------------
    def q(self, cypher: str, params: dict | None = None) -> list[dict]:
        if params is None:
            self.cur.execute(cypher)
        else:
            self.cur.execute(cypher, params)
        return [dict(r) for r in self.cur.fetchall()]

    # ---- store facts ----------------------------------------------------
    def meta(self) -> dict:
        rows = self.q(
            "MATCH (m:Meta) RETURN m.source AS source, m.dataEndYear AS dataEndYear, m.slice AS slice, "
            "m.minFieldPatentsPerYear AS minFieldPatentsPerYear, m.minPairPatents AS minPairPatents, "
            "m.minBuildsCitations AS minBuildsCitations, m.asOf AS asOf, m.blind AS blind"
        )
        return rows[0] if rows else {}

    @property
    def data_end_year(self) -> int:
        m = self.meta()
        if m.get("dataEndYear"):
            return int(m["dataEndYear"])
        r = self.q("MATCH ()-[r:COMBINED_WITH]->() RETURN max(r.firstYear) AS y")
        return int(r[0]["y"] or 0)

    @property
    def is_synthetic(self) -> bool:
        return self.meta().get("source") == "toy"

    # ---- time slices ----------------------------------------------------
    def fields(self, as_of: int | None = None) -> list[dict]:
        if as_of is None:
            return self.q(
                "MATCH (f:Field) RETURN f.code AS code, f.title AS title, f.firstYear AS firstYear, "
                "f.nPatents AS nPatents ORDER BY code"
            )
        return self.q(
            "MATCH (f:Field) WHERE f.firstYear <= $y RETURN f.code AS code, f.title AS title, "
            "f.firstYear AS firstYear, f.nPatents AS nPatents ORDER BY code",
            {"y": as_of},
        )

    def combined(self, as_of: int | None = None) -> list[tuple[str, str, int]]:
        """(a, b, firstYear) for every combination that exists as of the year (all years if None)."""
        if as_of is None:
            rows = self.q(
                "MATCH (a:Field)-[r:COMBINED_WITH]->(b:Field) RETURN a.code AS a, b.code AS b, r.firstYear AS y"
            )
        else:
            rows = self.q(
                "MATCH (a:Field)-[r:COMBINED_WITH]->(b:Field) WHERE r.firstYear <= $y "
                "RETURN a.code AS a, b.code AS b, r.firstYear AS y",
                {"y": as_of},
            )
        return [(r["a"], r["b"], r["y"]) for r in rows]

    def builds(self, as_of: int | None = None) -> list[tuple[str, str, int]]:
        """(src, dst, firstYear): src builds on dst."""
        if as_of is None:
            rows = self.q(
                "MATCH (s:Field)-[r:BUILDS_ON]->(d:Field) RETURN s.code AS s, d.code AS d, r.firstYear AS y"
            )
        else:
            rows = self.q(
                "MATCH (s:Field)-[r:BUILDS_ON]->(d:Field) WHERE r.firstYear <= $y "
                "RETURN s.code AS s, d.code AS d, r.firstYear AS y",
                {"y": as_of},
            )
        return [(r["s"], r["d"], r["y"]) for r in rows]

    # ---- optional tables (absent in older stores) ---------------------
    def patents_as_of(self, year: int) -> dict[str, int]:
        """Cumulative patents per field granted through `year` (an as-of count; the end-of-data total would leak the future)."""
        try:
            rows = self.q("MATCH (y:FieldYear) WHERE y.year <= $y RETURN y.code AS c, sum(y.n) AS n", {"y": year})
        except Exception:
            return {}
        return {r["c"]: int(r["n"]) for r in rows}

    def stalled(self, year: int, min_years: int = config.STALLED_MIN_YEARS) -> list[tuple[str, str, int]]:
        """(a, b, firstCoYear) for pairs co-classified for at least `min_years` years and still under the combination threshold in `year`."""
        try:
            rows = self.q(
                "MATCH (a:Field)-[r:CO_CLASSIFIED]->(b:Field) WHERE r.firstYear <= $y "
                "RETURN a.code AS a, b.code AS b, r.firstYear AS y", {"y": year - min_years})
        except Exception:
            return []
        done = {(min(a, b), max(a, b)) for a, b, _ in self.combined(year)}
        return [(r["a"], r["b"], r["y"]) for r in rows if (min(r["a"], r["b"]), max(r["a"], r["b"])) not in done]

    # ---- ancestry -------------------------------------------------------
    def _reach(self, code: str, as_of: int | None, up: bool, max_depth: int) -> dict[str, int]:
        """Breadth-first walk over BUILDS_ON, one 1-hop Cypher query per level.

        (A single variable-length path query enumerates every path and explodes on a dense
        graph; levelling it keeps the cost proportional to the number of edges.)
        """
        year_cond = "AND r.firstYear <= $y" if as_of is not None else ""
        if up:
            cypher = (
                f"MATCH (f:Field)-[r:BUILDS_ON]->(p:Field) WHERE f.code IN $fr {year_cond} "
                "RETURN DISTINCT p.code AS c"
            )
        else:
            cypher = (
                f"MATCH (f:Field)-[r:BUILDS_ON]->(p:Field) WHERE p.code IN $fr {year_cond} "
                "RETURN DISTINCT f.code AS c"
            )
        seen = {code: 0}
        frontier = [code]
        depth = 0
        while frontier and depth < max_depth:
            depth += 1
            params = {"fr": frontier}
            if as_of is not None:
                params["y"] = as_of
            nxt = []
            for r in self.q(cypher, params):
                if r["c"] not in seen:
                    seen[r["c"]] = depth
                    nxt.append(r["c"])
            frontier = nxt
        seen.pop(code)
        return seen

    def ancestors(self, code: str, as_of: int | None = None, max_depth: int = 50) -> dict[str, int]:
        """Fields `code` builds on, directly or through others, with the hop distance."""
        return self._reach(code, as_of, True, max_depth)

    def descendants(self, code: str, as_of: int | None = None, max_depth: int = 50) -> dict[str, int]:
        """Fields that build on `code`, directly or through others, with the hop distance."""
        return self._reach(code, as_of, False, max_depth)

    def lineage(self) -> dict:
        """Each field hangs from the older field it relies on most (its strongest prerequisite).

        Parents are strictly older than children, so this is a forest, never a cycle. A
        parent exists whenever its child does, so the tree as of year Y is simply this tree
        restricted to fields with firstYear <= Y. Weights are all-time totals: this view
        shows ancestry, not a forecast.
        """
        rows = self.q(
            "MATCH (f:Field)-[r:BUILDS_ON]->(p:Field) WHERE p.firstYear < f.firstYear "
            "RETURN f.code AS f, p.code AS p, r.count AS w, p.firstYear AS py"
        )
        best: dict[str, tuple] = {}
        for r in rows:
            w = r["w"] or 0  # capsules carry no counts
            key = (w, -r["py"], r["p"])  # strongest, then oldest, then by code
            if r["f"] not in best or key > best[r["f"]][0]:
                best[r["f"]] = (key, r["p"], w)
        parents = {child: {"parent": p, "weight": w} for child, (_, p, w) in best.items()}
        all_codes = [f["code"] for f in self.fields()]
        return {"parents": parents, "roots": [c for c in all_codes if c not in parents]}

    # ---- counterfactuals ------------------------------------------------
    def knockout(
        self,
        code: str,
        as_of: int | None = None,
        gamma: float = config.CASCADE_GAMMA,
        iterations: int = config.CASCADE_ITERATIONS,
        weighted: bool | None = None,
    ) -> dict[str, float]:
        """Dependency exposure if `code` were removed (not a causal claim).

        loss(code) is pinned at 1. Each round, every field takes gamma times the average
        loss of the fields it builds on, weighted by link strength. Fields that rely on
        `code` directly or through a chain pick up exposure that fades with each hop.

        Weights are citation totals when looking at the whole history, and plain link
        counts when `as_of` is given (a total through today would leak the future).
        """
        weighted = (as_of is None) if weighted is None else weighted
        year_cond = "WHERE r.firstYear <= $y" if as_of is not None else ""
        if weighted:
            agg = "sum(r.count * $loss[p.code]) AS s, sum(r.count) AS tot"
        else:
            agg = "sum($loss[p.code]) AS s, count(r) AS tot"
        cypher = f"MATCH (f:Field)-[r:BUILDS_ON]->(p:Field) {year_cond} RETURN f.code AS f, {agg}"
        codes = [f["code"] for f in self.fields()]
        if code not in codes:
            raise KeyError(f"unknown field {code}")
        loss = {c: 0.0 for c in codes}
        loss[code] = 1.0
        for _ in range(iterations):
            params = {"loss": loss}
            if as_of is not None:
                params["y"] = as_of
            nxt = {c: 0.0 for c in codes}
            for r in self.q(cypher, params):
                if r["tot"]:
                    nxt[r["f"]] = gamma * r["s"] / r["tot"]
            nxt[code] = 1.0
            loss = nxt
        loss.pop(code)
        return dict(sorted(((c, v) for c, v in loss.items() if v > 1e-9), key=lambda kv: -kv[1]))

    # ---- evidence for a pair of fields ---------------------------------
    def bridge_fields(self, a: str, b: str, as_of: int, top: int = 10) -> list[dict]:
        """Fields already combined with both `a` and `b` as of the year.

        Ranked by how long the *newer* of the two links has existed (the weaker link),
        so a bridge that is well established on both sides comes first. Uses existence and
        first year only, never totals, so the ranking is valid for any year.
        """
        rows = self.q(
            "MATCH (a:Field {code: $a})-[r1:COMBINED_WITH]-(c:Field)-[r2:COMBINED_WITH]-(b:Field {code: $b}) "
            "WHERE r1.firstYear <= $y AND r2.firstYear <= $y "
            "RETURN c.code AS code, c.title AS title, r1.firstYear AS y1, r2.firstYear AS y2",
            {"a": a, "b": b, "y": as_of},
        )
        out = [
            {"code": r["code"], "title": r["title"], "since": max(r["y1"], r["y2"]),
             "yearsEstablished": as_of - max(r["y1"], r["y2"])}
            for r in rows
        ]
        out.sort(key=lambda d: (-d["yearsEstablished"], d["code"]))
        return out[:top]

    def shared_prerequisites(self, a: str, b: str, as_of: int, top: int = 10) -> list[dict]:
        """Fields that both `a` and `b` build on, as of the year."""
        rows = self.q(
            "MATCH (a:Field {code: $a})-[r1:BUILDS_ON]->(c:Field)<-[r2:BUILDS_ON]-(b:Field {code: $b}) "
            "WHERE r1.firstYear <= $y AND r2.firstYear <= $y "
            "RETURN c.code AS code, c.title AS title, c.firstYear AS firstYear ORDER BY code",
            {"a": a, "b": b, "y": as_of},
        )
        return rows[:top]

    def evidence(self, a: str, b: str, as_of: int) -> dict:
        """Everything the evidence panel shows for a pair of fields."""
        return {
            "a": a,
            "b": b,
            "asOf": as_of,
            "bridgeFields": self.bridge_fields(a, b, as_of),
            "sharedPrerequisites": self.shared_prerequisites(a, b, as_of),
        }

    # ---- queries kept as files -----------------------------------------
    def run_file(self, path, params: dict | None = None) -> list[dict]:
        """Run one of the .cypher files in queries/ (the first non-comment text is the query)."""
        text = "\n".join(
            line for line in open(path).read().splitlines() if not line.lstrip().startswith("//")
        )
        return self.q(text, params or {})
