import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

from prometheus import server


def _get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
        return r.status, r.read()


def test_server_api_and_no_peeking(toy_store):
    box, ready = {}, threading.Event()

    def run():  # a Relate connection must be used on the thread that opened it
        svc = server.Service(toy_store)
        srv = HTTPServer(("127.0.0.1", 0), server.make_handler(svc))
        box.update(svc=svc, srv=srv)
        ready.set()
        srv.serve_forever()
        srv.server_close()
        svc.g.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    assert ready.wait(60)
    srv = box["srv"]
    port = srv.server_address[1]
    try:
        status, body = _get(port, "/")
        assert status == 200 and b"Prometheus" in body and b"/d3.min.js" in body
        status, mx = _get(port, "/matrix")
        assert status == 200 and b"aria-current=\"page\">Matrix" in mx and b"/d3.min.js" in mx
        status, ls = _get(port, "/landscape")
        assert status == 200 and b"View as" not in ls and b"/three.min.js" in ls and b"/OrbitControls.js" in ls
        for path, marker in (("/three.min.js", b"three.js"), ("/OrbitControls.js", b"orbitcontrols")):
            status, body3 = _get(port, path)
            assert status == 200 and marker in body3[:3000].lower() + (body3 if marker == b"orbitcontrols" else b"").lower()
        status, js = _get(port, "/d3.min.js")
        assert status == 200 and b"d3js.org" in js[:400]

        meta = json.loads(_get(port, "/api/meta")[1])
        assert meta["synthetic"] is True
        assert sorted(meta["order"]) == sorted(f["code"] for f in meta["fields"])

        year = meta["start"] + (meta["end"] - meta["start"]) // 2
        st = json.loads(_get(port, f"/api/state?year={year}")[1])
        born = {f["code"] for f in meta["fields"] if f["firstYear"] <= year}
        # the page for a year may only mention fields and links that existed by then
        assert all(c[2] <= year and c[0] in born and c[1] in born for c in st["combined"])
        assert all(g["a"] in born and g["b"] in born for g in st["gaps"])
        combined = {frozenset(c[:2]) for c in st["combined"]}
        assert all(frozenset((g["a"], g["b"])) not in combined for g in st["gaps"])
        g = st["gaps"][0]
        assert abs(g["beyond"] - (g["hybrid"] - g["size"])) < 1e-3

        ev = json.loads(_get(port, f"/api/evidence?a={g['a']}&b={g['b']}&year={year}")[1])
        assert ev["a"] == g["a"] and "bridgeFields" in ev

        assert set(meta["domains"]) == set(first_codes := [f["code"] for f in meta["fields"]]) and meta["domainKind"] in ("slice", "cpc-section")
        status, font = _get(port, "/fonts/newsreader-latin-400-normal.woff2")
        assert status == 200 and font[:4] == b"wOF2"
        try:
            _get(port, "/fonts/../server.py")
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
        rc = json.loads(_get(port, f"/api/reach?code={first_codes[0]}&year={meta['end']}")[1])
        assert rc["code"] == first_codes[0] and isinstance(rc["ancestors"], dict) and isinstance(rc["descendants"], dict)
        code0 = meta["fields"][0]["code"]
        fp = json.loads(_get(port, f"/api/field?code={code0.lower()}&year={year}")[1])
        assert fp["code"] == code0 and fp["year"] == year and "partners" in fp and "buildsOn" in fp
        assert all(g["a"] == code0 or g["b"] == code0 for g in fp["gaps"])  # only this field's candidates
        try:
            _get(port, f"/api/field?code=NOPE&year={year}")
            raise AssertionError("expected a 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
        tr = json.loads(_get(port, f"/api/tree?year={year}")[1])
        alive = {f["code"] for f in meta["fields"] if f["firstYear"] <= year}
        assert set(tr["order"]) == alive and set(tr["dead"]) == {f["code"] for f in meta["fields"]} - alive  # the tree is over the fields alive that year
        assert len(tr["merges"]) == max(0, len(alive) - 1)
        stl = json.loads(_get(port, f"/api/stalled?year={year}")[1])
        assert stl["pairs"] == [] and stl["minYears"] >= 1  # the toy store has no CO_CLASSIFIED edges: the overlay is simply empty
        assert "coClassifiedSince" in ev and ev["coClassifiedSince"] is None
        lin = json.loads(_get(port, "/api/lineage")[1])
        first = {f["code"]: f["firstYear"] for f in meta["fields"]}
        assert all(first[p["parent"]] < first[c] for c, p in lin["parents"].items())  # parents are strictly older

        code = meta["fields"][0]["code"]
        ko = json.loads(_get(port, f"/api/knockout?code={code}&year={meta['end']}")[1])
        assert ko["code"] == code and code not in ko["exposure"]
        early = json.loads(_get(port, f"/api/knockout?code={code}&year={year}")[1])
        assert all(first[c] <= year for c in early["exposure"])  # nothing born later is exposed

        assert ko["minSupport"] >= 1 and set(ko["support"]) == set(ko["exposure"])
        assert all(isinstance(n, int) and n >= 0 for n in ko["support"].values())
        chk = json.loads(_get(port, "/api/check")[1])
        assert chk["available"] is False  # the toy service was started without a results directory

        try:
            _get(port, "/api/knockout?code=NOPE&year=2000")
            raise AssertionError("expected a 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
        try:
            _get(port, "/api/state?year=abc")
            raise AssertionError("expected a 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()
        t.join(10)


def test_check_reads_only_the_results_files(toy_store, tmp_path):
    import json as _json
    (tmp_path / "beyond_size").mkdir()
    (tmp_path / "backtest.json").write_text(_json.dumps({
        "gate": {"verdict": "NO-GO", "ratio": 1.04, "threshold": 2.0}, "weights": {"cn": 1}, "settings": {"k": 100},
        "heldout_cutoffs_result": {"2005": {"candidates": 10, "positives": 2, "base_rate": 0.2, "methods": {
            "hybrid": {"auc": 0.8, "lift_at_k": 4.0, "x": 1}, "pa": {"auc": 0.7, "lift_at_k": 3.9}, "random": {"auc": 0.5, "lift_at_k": 1.0},
            "cn": {"auc": 0.9, "lift_at_k": 9.0}}}}}))
    (tmp_path / "beyond_size" / "beyond_size.json").write_text(_json.dumps({
        "definition": "d", "n_boot": 5, "cutoffs": {"2005": {"positives_subset": 1, "candidates_subset": 5,
        "methods": {"hybrid": {"auc": 0.8, "ci95": [0.7, 0.9]}, "pa": {"auc": 0.6, "ci95": [0.5, 0.7]}},
        "diff_vs_pa": {"hybrid": {"diff": 0.2, "ci95": [0.1, 0.3]}}}}}))
    svc = server.Service(toy_store, results_dir=tmp_path)
    c = svc.check()
    svc.g.close()
    assert c["verdict"] == "NO-GO" and c["available"]
    h = c["backtest"]["heldout"]["2005"]
    assert set(h["methods"]) == {"hybrid", "pa", "random"} and abs(h["maxLift"] - 5.0) < 1e-9
    assert c["beyond"]["cutoffs"]["2005"]["diffVsPa"]["diff"] == 0.2
