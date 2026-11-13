"""`techtree serve STORE`: a local, read-only web page over one store.

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
from .graph import TechGraph
from .predict import DEFAULT_WEIGHTS, Snapshot, hybrid, percentile, rank_order, signal_table, tie_breaker

WEB = Path(__file__).parent / "web"
MAX_GAPS = 1500


class Service:
    def __init__(self, store, weights=None, verdict=None):
        self.g = TechGraph(store, read_only=True)
        self.lock = threading.Lock()
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.verdict = verdict
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

    def meta(self):
        m = self.g.meta()
        fields = self.g.fields()
        return {"meta": m, "synthetic": self.g.is_synthetic, "start": self.start, "end": self.end,
                "fields": [{"code": f["code"], "title": (f["title"] or "").strip(), "firstYear": f["firstYear"],
                            "nPatents": f["nPatents"]} for f in fields],
                "order": self.order, "merges": self.merges, "weights": self.weights, "verdict": self.verdict}

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
        """Dependency exposure if `code` were removed as of the year (not a causal claim)."""
        year = max(self.start, min(self.end, year))
        res = self.g.knockout(code, year, weighted=False)  # link counts, never later totals
        return {"code": code, "year": year, "exposure": {c: round(v, 4) for c, v in res.items()}}

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
                if u.path == "/d3.min.js":  # vendored (ISC licence), so the page works offline
                    return self._send((WEB / "d3.min.js").read_bytes(), "application/javascript; charset=utf-8")
                with svc.lock:
                    if u.path == "/api/meta":
                        return self._json(svc.meta())
                    if u.path == "/api/state":
                        return self._json(svc.state(int(q["year"])))
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
    svc = Service(store, weights, verdict)
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
