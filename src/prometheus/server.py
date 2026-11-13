"""`prometheus serve STORE`: a local, read-only web page over one store.

Standard library only. The store is opened read-only; every number on the page comes from
a query on it (existence and first year only, so a year on the slider cannot see later years).
Each gap carries two scores: `size` (what field size alone predicts: preferential attachment)
and `beyond` (what the graph adds above that: hybrid percentile minus size percentile).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import genome as genome_mod
from . import slice as slicemod
from .graph import TechGraph
from .predict import DEFAULT_WEIGHTS, Snapshot, hybrid, percentile, rank_order, signal_table, tie_breaker

WEB = Path(__file__).parent / "web"
MAX_GAPS = 1500
# Display rule only (never enters a score): a knock-out exposure that rests on fewer BUILDS_ON links than this is drawn as weak.
MIN_SUPPORT = 3
CPC_SECTIONS = {"A": "Human necessities", "B": "Performing operations, transporting", "C": "Chemistry, metallurgy",
                "D": "Textiles, paper", "E": "Fixed constructions",
                "F": "Mechanical engineering, lighting, heating, weapons", "G": "Physics", "H": "Electricity"}
FONTS = {"newsreader-latin-400-normal.woff2", "newsreader-latin-600-normal.woff2",
         "instrument-sans-latin-400-normal.woff2", "instrument-sans-latin-600-normal.woff2"}


class Service:
    def __init__(self, store, weights=None, verdict=None, results_dir=None):
        self.g = TechGraph(store, read_only=True)
        self.lock = threading.Lock()
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.verdict = verdict
        self.results_dir = Path(results_dir) if results_dir else None
        self.cache: dict[int, dict] = {}
        self.end = self.g.data_end_year
        fields = self.g.fields()
        self.start = min(f["firstYear"] for f in fields)
        snap = Snapshot.from_graph(self.g, self.end)
        self.has_genome = True
        try:
            order, merges = genome_mod.cluster(genome_mod.vectors(snap))
        except ValueError:  # too many fields to cluster
            order, merges = sorted(snap.codes), []
        self.order, self.merges = order, merges

    def domains(self, codes):
        """Domain label per field: from the slice file if the store names one, else the CPC section letter."""
        try:
            rule = slicemod.load(self.g.meta().get("slice"))
        except slicemod.SliceError:
            rule = None
        if rule is not None:
            return {c: (rule.domain_of(c) or CPC_SECTIONS.get(c[:1], c[:1])) for c in codes}, "slice"
        return {c: CPC_SECTIONS.get(c[:1], c[:1]) for c in codes}, "cpc-section"

    def reach(self, code: str, year: int):
        """What `code` builds on (ancestors) and what builds on it (descendants), with hop counts, as of the year."""
        year = max(self.start, min(self.end, year))
        return {"code": code, "year": year, "ancestors": self.g.ancestors(code, year),
                "descendants": self.g.descendants(code, year)}

    def meta(self):
        m = self.g.meta()
        fields = self.g.fields()
        doms, dkind = self.domains([f["code"] for f in fields])
        return {"meta": m, "synthetic": self.g.is_synthetic, "start": self.start, "end": self.end,
                "fields": [{"code": f["code"], "title": (f["title"] or "").strip(), "firstYear": f["firstYear"],
                            "nPatents": f["nPatents"]} for f in fields],
                "order": self.order, "merges": self.merges, "weights": self.weights, "verdict": self.verdict,
                "domains": doms, "domainKind": dkind}

    def state(self, year: int):
        year = max(self.start, min(self.end, year))
        if year in self.cache:
            return self.cache[year]
        snap = Snapshot.from_graph(self.g, year)
        cands = snap.candidates()
        table = signal_table(snap, cands, genome_mod.vectors(snap))
        hy = hybrid(table, self.weights)
        hp, pp = percentile(hy), percentile(table["pa"])
        top = rank_order(hy, tie_breaker(len(cands)))[:MAX_GAPS]
        gaps = [{"a": cands[i][0], "b": cands[i][1], "rank": r + 1, "hybrid": round(hp[i], 4),
                 "size": round(pp[i], 4), "beyond": round(hp[i] - pp[i], 4),
                 "cn": int(table["cn"][i]), "prereq": int(table["prereq"][i])} for r, i in enumerate(top)]
        out = {"year": year, "fields": len(snap.codes), "candidates": len(cands), "gaps": gaps,
               "combined": [[a, b, y] for a, b, y in self.g.combined(year)]}
        self.cache[year] = out
        return out

    def lineage(self):
        if not hasattr(self, "_lineage"):
            self._lineage = self.g.lineage()
        return self._lineage

    def knockout(self, code: str, year: int):
        """Dependency exposure if `code` were removed as of the year (not a causal claim).

        `support[c]` is how many BUILDS_ON links field c has as of the year, which is what its exposure is an
        average over. It is a count of links that exist, so it uses no totals and cannot leak the future.
        """
        year = max(self.start, min(self.end, year))
        res = self.g.knockout(code, year, weighted=False)  # link counts, never later totals
        rows = self.g.q("MATCH (f:Field)-[r:BUILDS_ON]->(:Field) WHERE r.firstYear <= $y RETURN f.code AS c, count(r) AS n",
                        {"y": year})
        n = {r["c"]: r["n"] for r in rows}
        return {"code": code, "year": year, "minSupport": MIN_SUPPORT,
                "exposure": {c: round(v, 4) for c, v in res.items()},
                "support": {c: n.get(c, 0) for c in res}}

    def check(self):
        """The prediction check, read from the two results files and nothing else. Never hides a failure."""
        if not self.results_dir:
            return {"available": False, "reason": "start the server with --weights-from results/backtest.json"}
        out = {"available": True, "backtest": None, "beyond": None}
        bt = self.results_dir / "backtest.json"
        if bt.exists():
            d = json.loads(bt.read_text())
            held = {}
            for y, c in d.get("heldout_cutoffs_result", {}).items():
                held[y] = {"candidates": c["candidates"], "positives": c["positives"], "base_rate": c["base_rate"],
                           "maxLift": (1 / c["base_rate"]) if c["base_rate"] else None,
                           "methods": {m: {"auc": v["auc"], "lift": v["lift_at_k"]} for m, v in c["methods"].items()
                                       if m in ("hybrid", "pa", "random")}}
            out["backtest"] = {"gate": d.get("gate"), "weights": d.get("weights"), "k": d.get("settings", {}).get("k"),
                               "tuneCutoffs": d.get("settings", {}).get("tune_cutoffs"), "heldout": held}
        bs = self.results_dir / "beyond_size" / "beyond_size.json"
        if bs.exists():
            d = json.loads(bs.read_text())
            out["beyond"] = {"definition": d.get("definition"), "nBoot": d.get("n_boot"),
                             "cutoffs": {y: {"positives": c["positives_subset"], "candidates": c["candidates_subset"],
                                             "methods": {m: c["methods"][m] for m in ("hybrid", "pa", "random") if m in c["methods"]},
                                             "diffVsPa": c["diff_vs_pa"].get("hybrid")}
                                         for y, c in d.get("cutoffs", {}).items()}}
        g = (out["backtest"] or {}).get("gate") or {}
        out["verdict"] = g.get("verdict")
        return out

    def evidence(self, a: str, b: str, year: int):
        ev = self.g.evidence(a, b, year)
        t = {f["code"]: (f["title"] or "").strip() for f in self.g.fields()}
        ev["titles"] = {a: t.get(a, ""), b: t.get(b, "")}
        return ev


def make_handler(svc: Service):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body: bytes, ctype: str, code: int = 200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(json.dumps(obj).encode(), "application/json", code)

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path in ("/", "/index.html"):
                    return self._send((WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
                if u.path.startswith("/fonts/") and u.path[7:] in FONTS:  # whitelist: no path traversal
                    return self._send((WEB / "fonts" / u.path[7:]).read_bytes(), "font/woff2")
                if u.path == "/d3.min.js":  # vendored (ISC licence), so the page works offline
                    return self._send((WEB / "d3.min.js").read_bytes(), "application/javascript; charset=utf-8")
                with svc.lock:
                    if u.path == "/api/meta":
                        return self._json(svc.meta())
                    if u.path == "/api/state":
                        return self._json(svc.state(int(q["year"])))
                    if u.path == "/api/check":
                        return self._json(svc.check())
                    if u.path == "/api/reach":
                        return self._json(svc.reach(q["code"], int(q["year"])))
                    if u.path == "/api/lineage":
                        return self._json(svc.lineage())
                    if u.path == "/api/knockout":
                        return self._json(svc.knockout(q["code"], int(q["year"])))
                    if u.path == "/api/evidence":
                        return self._json(svc.evidence(q["a"], q["b"], int(q["year"])))
                self._json({"error": "not found"}, 404)
            except (KeyError, ValueError) as e:
                self._json({"error": f"bad request: {e}"}, 400)
    return H


def serve(store, port=8765, weights_from=None, open_browser=False):
    weights, verdict = None, None
    if weights_from:
        d = json.loads(Path(weights_from).read_text())
        weights = d.get("weights")
        gate = d.get("gate") or {}
        verdict = {k: gate.get(k) for k in ("verdict", "ratio", "hybrid_lift", "better_baseline_lift", "threshold")}
    svc = Service(store, weights, verdict, Path(weights_from).parent if weights_from else None)
    srv = HTTPServer(("127.0.0.1", port), make_handler(svc))
    url = f"http://127.0.0.1:{port}/"
    print(f"PROMETHEUS serving {store} (read-only) at {url}   Ctrl+C to stop")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        svc.g.close()
