import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

from techtree import server


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
        assert status == 200 and b"PROMETHEUS" in body and b"/d3.min.js" in body
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

        lin = json.loads(_get(port, "/api/lineage")[1])
        first = {f["code"]: f["firstYear"] for f in meta["fields"]}
        assert all(first[p["parent"]] < first[c] for c, p in lin["parents"].items())  # parents are strictly older

        code = meta["fields"][0]["code"]
        ko = json.loads(_get(port, f"/api/knockout?code={code}&year={meta['end']}")[1])
        assert ko["code"] == code and code not in ko["exposure"]
        early = json.loads(_get(port, f"/api/knockout?code={code}&year={year}")[1])
        assert all(first[c] <= year for c in early["exposure"])  # nothing born later is exposed

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
