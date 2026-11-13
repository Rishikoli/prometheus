"""Command line for PROMETHEUS: `prometheus --help`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config


def _g(path, rw=False):
    from .graph import TechGraph
    return TechGraph(path, read_only=not rw)


def _titles(g) -> dict:
    return {f["code"]: f["title"] for f in g.fields()}


def _weights(path):
    if not path:
        return None
    data = json.loads(Path(path).read_text())
    return data["weights"] if "weights" in data else data


def cmd_toy(a):
    from . import toy
    print(json.dumps(toy.generate(a.out, n_fields=a.fields, seed=a.seed, structure=a.structure)))


def cmd_pipeline(a):
    from . import pipeline, slice as slicemod
    rule = slicemod.load(a.slice)
    pipeline.aggregate(
        a.patent, a.cpc, a.cites, a.out, titles_tsv=a.titles, min_year=a.min_year, memory_limit=a.memory_limit,
        temp_dir=a.temp_dir, keep_work=a.keep_work, slice_rule=rule,
        min_field_patents=a.min_field_patents, min_pair_patents=a.min_pair_patents,
        min_builds_citations=a.min_builds_citations,
    )


def cmd_build(a):
    from . import build
    print(json.dumps(build.build(a.csv_dir, a.store)))


def cmd_info(a):
    with _g(a.store) as g:
        print(json.dumps({"meta": g.meta(), "fields": len(g.fields()), "combined": len(g.combined()),
                          "builds_on": len(g.builds())}, indent=2))


def cmd_gaps(a):
    from .predict import Snapshot, top_gaps
    with _g(a.store) as g:
        t = _titles(g)
        snap = Snapshot.from_graph(g, a.as_of)
        for r in top_gaps(snap, _weights(a.weights_from), k=a.top, use_genome=a.genome):
            print(f"{r['rank']:>3}  {r['a']} + {r['b']}  score {r['score']}  common {r['cn']}  prereq {r['prereq']}"
                  f"   {t.get(r['a'], '')[:30]} + {t.get(r['b'], '')[:30]}")


def cmd_evidence(a):
    with _g(a.store) as g:
        print(json.dumps(g.evidence(a.a, a.b, a.as_of), indent=2))


def cmd_reach(a):
    with _g(a.store) as g:
        t = _titles(g)
        fn = g.ancestors if a.direction == "ancestors" else g.descendants
        for c, d in sorted(fn(a.code, a.as_of).items(), key=lambda kv: (kv[1], kv[0])):
            print(f"hop {d}  {c}  {t.get(c, '')}")


def cmd_knockout(a):
    with _g(a.store) as g:
        t = _titles(g)
        res = g.knockout(a.code, a.as_of, weighted=False if g.meta().get("blind") else None)
        print(f"Exposure if {a.code} ({t.get(a.code, '')}) were removed; a dependency measure, not proof of cause:")
        for c, v in list(res.items())[: a.top]:
            print(f"  {v:.3f}  {c}  {t.get(c, '')}")


def cmd_breakthrough(a):
    from .predict import Snapshot, breakthrough
    with _g(a.store) as g:
        snap = Snapshot.from_graph(g, a.as_of)
    res = breakthrough(snap, a.a, a.b, _weights(a.weights_from), k=a.k)
    print(json.dumps(res, indent=2))


def cmd_backtest(a):
    from . import backtest
    with _g(a.store) as g:
        res = backtest.run(g, horizon=a.horizon, k=a.k, use_genome=not a.no_genome)
    md, js = backtest.write(res, a.out)
    print(backtest.render_markdown(res))
    print(f"\nwrote {md} and {js}")


def cmd_beyond(a):
    from . import beyond
    weights = _weights(a.weights_from)
    with _g(a.store) as g:
        res = beyond.run(g, weights, horizon=a.horizon, use_genome=not a.no_genome)
    md, js = beyond.write(res, a.out)
    print(beyond.render_markdown(res))
    print(f"wrote {md} and {js}")


def cmd_genome(a):
    from . import genome
    from .predict import Snapshot
    with _g(a.store, rw=True) as g:
        year = a.as_of or g.data_end_year
        info = genome.write_to_store(g, Snapshot.from_graph(g, year))
    print(json.dumps({k: v for k, v in info.items() if k != "founders"}))


def cmd_relatives(a):
    from . import genome
    with _g(a.store) as g:
        for r in genome.nearest(g, a.code, a.k):
            print(f"{r['cosine']:.3f}  {r['code']}  {r['title']}")


def cmd_order(a):
    from . import genome
    from .predict import Snapshot
    with _g(a.store) as g:
        snap = Snapshot.from_graph(g, a.as_of)
        order, merges = genome.cluster(genome.vectors(snap))
    print(json.dumps({"asOf": a.as_of, "order": order, "merges": merges}))


def cmd_serve(a):
    from . import server
    server.serve(a.store, port=a.port, weights_from=a.weights_from, open_browser=a.open)


def cmd_capsule(a):
    from . import capsule
    print(json.dumps(capsule.build_capsule(a.csv_dir, a.as_of, a.out, seed=a.seed, horizon=a.horizon), indent=2))


def cmd_pa_threshold(a):
    """A4: the eligibility threshold for a capsule, and optionally the A4 brief."""
    from . import capsule
    from .predict import Snapshot
    with _g(a.capsule) as g:
        year = g.meta().get("asOf") or g.data_end_year
        snap = Snapshot.from_graph(g, year)
        t = capsule.pa_threshold(snap)
        n = sum(1 for x, y in snap.candidates() if snap.deg(x) * snap.deg(y) <= t)
        total = len(snap.candidates())
    if a.write_brief:
        Path(a.write_brief).write_text(capsule.brief_a4(year, config.HORIZON, f"capsule-{year}", t))
    print(json.dumps({"as_of": year, "threshold": t, "eligible_pairs": n, "candidate_pairs": total}))


def cmd_baseline_forecast(a):
    """Write a forecast.json from the graph predictor, so the grading loop runs without a language model."""
    from .predict import Snapshot, top_gaps
    with _g(a.capsule) as g:
        year = g.meta().get("asOf") or g.data_end_year
        gaps = top_gaps(Snapshot.from_graph(g, year), k=a.top)
    pairs = [{"a": r["a"], "b": r["b"], "cypher": "(graph predictor, see queries/gaps_common_neighbours.cypher)",
              "why": f"{r['cn']} common neighbours, {r['prereq']} shared-prerequisite score"} for r in gaps]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"pairs": pairs}, indent=1))
    print(f"wrote {len(pairs)} pairs to {a.out}")


def cmd_grade(a):
    from . import grade
    res = grade.grade(a.forecast, a.against, a.as_of, map_path=a.map, horizon=a.horizon, weights=_weights(a.weights_from),
                      pa_max=a.pa_max)
    print(json.dumps(res, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="prometheus", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("toy", help="write SYNTHETIC toy CSVs (not patent data)")
    s.add_argument("out"); s.add_argument("--fields", type=int, default=150)
    s.add_argument("--seed", type=int, default=7); s.add_argument("--structure", choices=["strong", "none"], default="strong")
    s.set_defaults(fn=cmd_toy)

    s = sub.add_parser("pipeline", help="PatentsView TSVs -> three small CSVs")
    s.add_argument("--patent", required=True, help="g_patent.tsv"); s.add_argument("--cpc", required=True, help="g_cpc_current.tsv")
    s.add_argument("--cites", required=True, help="g_us_patent_citation.tsv"); s.add_argument("--titles", help="optional g_cpc_title.tsv")
    s.add_argument("--out", required=True); s.add_argument("--slice", default="deeptech", help="'deeptech', a JSON file, or 'all'")
    s.add_argument("--min-year", type=int, default=config.DEFAULT_MIN_YEAR)
    s.add_argument("--memory-limit", default="8GB"); s.add_argument("--temp-dir"); s.add_argument("--keep-work", action="store_true")
    s.add_argument("--min-field-patents", type=int, default=config.MIN_FIELD_PATENTS_PER_YEAR)
    s.add_argument("--min-pair-patents", type=int, default=config.MIN_PAIR_PATENTS)
    s.add_argument("--min-builds-citations", type=int, default=config.MIN_BUILDS_CITATIONS)
    s.set_defaults(fn=cmd_pipeline)

    s = sub.add_parser("build", help="CSVs -> one Relate file"); s.add_argument("csv_dir"); s.add_argument("store"); s.set_defaults(fn=cmd_build)
    s = sub.add_parser("info", help="what is in a store"); s.add_argument("store"); s.set_defaults(fn=cmd_info)

    s = sub.add_parser("gaps", help="top predicted combinations as of a year")
    s.add_argument("store"); s.add_argument("--as-of", type=int, required=True); s.add_argument("--top", type=int, default=20)
    s.add_argument("--weights-from", help="backtest.json to take tuned weights from"); s.add_argument("--genome", action="store_true")
    s.set_defaults(fn=cmd_gaps)

    s = sub.add_parser("evidence", help="bridge fields and shared prerequisites for a pair")
    s.add_argument("store"); s.add_argument("a"); s.add_argument("b"); s.add_argument("--as-of", type=int, required=True)
    s.set_defaults(fn=cmd_evidence)

    for name in ("ancestors", "descendants"):
        s = sub.add_parser(name, help=f"fields {'it builds on' if name == 'ancestors' else 'that build on it'}")
        s.add_argument("store"); s.add_argument("code"); s.add_argument("--as-of", type=int)
        s.set_defaults(fn=cmd_reach, direction=name)

    s = sub.add_parser("knockout", help="dependency exposure if a field were removed")
    s.add_argument("store"); s.add_argument("code"); s.add_argument("--as-of", type=int); s.add_argument("--top", type=int, default=15)
    s.set_defaults(fn=cmd_knockout)

    s = sub.add_parser("breakthrough", help="what the model would score if a pair combined now (read-only)")
    s.add_argument("store"); s.add_argument("a"); s.add_argument("b"); s.add_argument("--as-of", type=int, required=True)
    s.add_argument("--k", type=int, default=config.TOP_K); s.add_argument("--weights-from")
    s.set_defaults(fn=cmd_breakthrough)

    s = sub.add_parser("backtest", help="grade the predictor against history and write results/backtest.md")
    s.add_argument("store"); s.add_argument("--out", default="results"); s.add_argument("--horizon", type=int, default=config.HORIZON)
    s.add_argument("--k", type=int, default=config.TOP_K); s.add_argument("--no-genome", action="store_true")
    s.set_defaults(fn=cmd_backtest)

    s = sub.add_parser("beyond", help="A2: AUC on the pairs preferential attachment ranks in the bottom half")
    s.add_argument("store"); s.add_argument("--weights-from", required=True, help="backtest.json (frozen weights; never refitted)")
    s.add_argument("--out", default="results/beyond_size"); s.add_argument("--horizon", type=int, default=config.HORIZON)
    s.add_argument("--no-genome", action="store_true"); s.set_defaults(fn=cmd_beyond)

    s = sub.add_parser("genome", help="store genome vectors and a vector index in the store (writes to it)")
    s.add_argument("store"); s.add_argument("--as-of", type=int); s.set_defaults(fn=cmd_genome)
    s = sub.add_parser("relatives", help="nearest relatives by genome (vector index)")
    s.add_argument("store"); s.add_argument("code"); s.add_argument("--k", type=int, default=10); s.set_defaults(fn=cmd_relatives)
    s = sub.add_parser("order", help="dendrogram leaf order and merges for the heatmap (JSON)")
    s.add_argument("store"); s.add_argument("--as-of", type=int, required=True); s.set_defaults(fn=cmd_order)

    s = sub.add_parser("serve", help="local read-only web page: heatmap, year slider, evidence panel")
    s.add_argument("store"); s.add_argument("--port", type=int, default=8765); s.add_argument("--open", action="store_true")
    s.add_argument("--weights-from", help="backtest.json: tuned weights and the gate verdict shown on the page")
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("capsule", help="build a sealed, blinded time capsule file")
    s.add_argument("csv_dir"); s.add_argument("--as-of", type=int, required=True); s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=0); s.add_argument("--horizon", type=int, default=config.HORIZON)
    s.set_defaults(fn=cmd_capsule)

    s = sub.add_parser("pa-threshold", help="A4: the eligibility threshold for a capsule (and the A4 brief)")
    s.add_argument("capsule"); s.add_argument("--write-brief"); s.set_defaults(fn=cmd_pa_threshold)

    s = sub.add_parser("baseline-forecast", help="forecast.json from the graph predictor (no language model)")
    s.add_argument("capsule"); s.add_argument("--out", required=True); s.add_argument("--top", type=int, default=10)
    s.set_defaults(fn=cmd_baseline_forecast)

    s = sub.add_parser("grade", help="grade a forecast.json made on a capsule")
    s.add_argument("forecast"); s.add_argument("--against", required=True, help="later capsule, or the full store plus --map")
    s.add_argument("--as-of", type=int, required=True); s.add_argument("--map"); s.add_argument("--horizon", type=int)
    s.add_argument("--weights-from"); s.add_argument("--pa-max", type=int, help="A4: only pairs with deg(a)*deg(b) <= this are candidates")
    s.set_defaults(fn=cmd_grade)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
