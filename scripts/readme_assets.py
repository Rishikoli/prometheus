"""Build the README visuals from the real store and screenshots. Re-run after the data or the spark image changes.

    python scripts/readme_assets.py            # needs Google Chrome (to render SVG to PNG) and Pillow

Writes to assets/readme/:
  hero-layout.svg   editable SVG source of the hero (layout, type, the real tree fragment)
  hero.png          the published hero: the layout plus the spark composited at the predicted pair (2x resolution)
  hero.gif          the same scene building up decade by decade (GitHub plays GIFs; it does not animate SVG)
  proof-board.webp  four real screenshots: tree, landscape, matrix, field profile
  result-card.svg   the honest result in three numbers (pure SVG, system fonts)
  architecture.svg  how the parts fit (pure SVG, system fonts)
The spark is a generated raster supplied by the author: assets/readme/src/spark.png. Without it a drawn placeholder is used.
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prometheus.server import Service  # noqa: E402

OUT = ROOT / "assets" / "readme"
SRC = OUT / "src"
FONTS = ROOT / "src" / "prometheus" / "web" / "fonts"
C = dict(paper="#EEF1EC", ink="#16211C", ink2="#4B5750", hair="#C9D0C8", wedge="#E5E9E2",
         h1="#80A3CF", h2="#5589C2", h3="#3470AF", h4="#235791", h5="#143E6B", f2="#E4572E", f3="#BF3A16", f4="#8E2208")
SERIF_FACE = (f"@font-face{{font-family:Newsreader;font-weight:600;src:url('file://{FONTS}/newsreader-latin-600-normal.woff2')}}"
              f"@font-face{{font-family:Newsreader;font-weight:400;src:url('file://{FONTS}/newsreader-latin-400-normal.woff2')}}"
              f"@font-face{{font-family:'Instrument Sans';font-weight:400;src:url('file://{FONTS}/instrument-sans-latin-400-normal.woff2')}}"
              f"@font-face{{font-family:'Instrument Sans';font-weight:600;src:url('file://{FONTS}/instrument-sans-latin-600-normal.woff2')}}")
SYS_SANS = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
SYS_SERIF = "Georgia, 'Times New Roman', serif"
W, H = 1200, 520
YEAR, PAIR_RANK = 2005, 1


def chrome():
    for exe in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(exe):
            return exe
    sys.exit("needs Google Chrome or Chromium to render SVG")


def render_svg(svg_text, out_png, w=W, h=H, scale=2):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "a.svg"
        f.write_text(svg_text)
        subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--hide-scrollbars", f"--window-size={w},{h}",
                        f"--force-device-scale-factor={scale}", "--virtual-time-budget=3000", f"--screenshot={out_png}", f.as_uri()],
                       check=True, capture_output=True)


# ---------------------------------------------------------------- data
def hero_data():
    svc = Service(str(ROOT / "data" / "prometheus.rl"), json.loads((ROOT / "results" / "backtest.json").read_text())["weights"])
    try:
        later = {(min(a, b), max(a, b)): y for a, b, y in svc.g.combined()}
        gaps = sorted(svc.state(YEAR)["gaps"], key=lambda g: g["rank"])
        g = next(g for g in gaps if g["rank"] >= PAIR_RANK and later.get((min(g["a"], g["b"]), max(g["a"], g["b"]))))
        a, b = g["a"], g["b"]
        ev = svc.evidence(a, b, YEAR)
        nodes = [a] + [x["code"] for x in ev["bridgeFields"]][:10] + [b]
        nodes = list(dict.fromkeys(nodes))
        arcs = [(x, y, fy) for x, y, fy in svc.g.combined() if x in nodes and y in nodes]
        return {"a": a, "b": b, "rank": g["rank"], "combined": later[(min(a, b), max(a, b))], "nodes": nodes, "arcs": arcs,
                "candidates": svc.state(YEAR)["candidates"]}
    finally:
        svc.g.close()


# ---------------------------------------------------------------- hero
CX, CY, R = 925, 262, 172


def node_pos(nodes, a, b):
    """The predicted pair on opposite sides of the circle; the fields both have combined with spread over the top and bottom."""
    others = [n for n in nodes if n not in (a, b)]
    top, bottom = others[0::2], others[1::2]
    pos = {a: math.pi, b: 0.0}
    for i, n in enumerate(top):
        pos[n] = math.radians(212 + 116 * (i + 0.5) / len(top))
    for i, n in enumerate(bottom):
        pos[n] = math.radians(148 - 116 * (i + 0.5) / len(bottom))
    return {n: (CX + R * math.cos(t), CY + R * math.sin(t), t) for n, t in pos.items()}


def arc_path(p, q, bend=0.42):
    (x1, y1, _), (x2, y2, _) = p, q
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    cx, cy = mx + (CX - mx) * bend, my + (CY - my) * bend
    return f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}", (0.25 * x1 + 0.5 * cx + 0.25 * x2, 0.25 * y1 + 0.5 * cy + 0.25 * y2)


def age_color(fy, year):
    age = year - fy
    return C["h5"] if age <= 3 else C["h4"] if age <= 6 else C["h3"] if age <= 10 else C["h2"] if age <= 20 else C["h1"]


def hero_svg(d, year=YEAR, show_fire=True, reveal=False, show_spark_slot=False, published=True):
    """The pair, the fields both had already combined with (only arcs that touch the pair), and the predicted link.

    reveal: the static hero shows the 2005 state and says in words what happened later."""
    a, b = d["a"], d["b"]
    pos = node_pos(d["nodes"], a, b)
    combined_now = year >= d["combined"]
    parts = []
    for x, y, fy in sorted(d["arcs"], key=lambda t: -t[2]):
        if fy > year or not ({x, y} & {a, b}) or {x, y} == {a, b}:
            continue
        path, _ = arc_path(pos[x], pos[y], bend=0.25)
        old = year - fy > 10
        parts.append(f'<path d="{path}" fill="none" stroke="{age_color(fy, year)}" stroke-width="{1.8 if old else 2.6}" '
                     f'stroke-opacity="{0.55 if old else 0.95}" stroke-linecap="round"/>')
    fire_path, mid = arc_path(pos[a], pos[b], bend=0)
    if combined_now:
        parts.append(f'<path d="{fire_path}" fill="none" stroke="{C["h5"]}" stroke-width="4" stroke-linecap="round"/>')
    elif show_fire:
        parts.append(f'<path d="{fire_path}" fill="none" stroke="{C["f3"]}" stroke-width="3.6" stroke-dasharray="11 7" stroke-linecap="round"/>')
    for n, (x, y, t) in pos.items():
        key = n in (a, b)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 if key else 6}" fill="{C["ink"]}"/>')
        lx, ly = CX + (R + 20) * math.cos(t), CY + (R + 20) * math.sin(t)
        anchor = "start" if math.cos(t) > 0.2 else "end" if math.cos(t) < -0.2 else "middle"
        dy = 7 if abs(math.sin(t)) < 0.5 else (16 if math.sin(t) > 0 else 0)
        parts.append(f'<text x="{lx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" font-size="{22 if key else 18}" '
                     f'font-weight="{600 if key else 400}" fill="{C["ink"] if key else C["ink2"]}" font-family="Instrument Sans, {SYS_SANS}">{n}</text>')
    yr = (f'<text x="{CX}" y="{CY + 112}" text-anchor="middle" font-size="40" fill="{C["ink"]}" fill-opacity="0.22" '
          f'font-family="Newsreader, {SYS_SERIF}">{year}</text>')
    slot = (f'<circle cx="{mid[0]:.1f}" cy="{mid[1]:.1f}" r="30" fill="none" stroke="{C["ink2"]}" stroke-dasharray="3 4"/>'
            if show_spark_slot else "")
    serif, sans = f"Newsreader, {SYS_SERIF}", f"Instrument Sans, {SYS_SANS}"
    left = (f'<text x="64" y="138" font-size="88" font-weight="600" fill="{C["ink"]}" font-family="{serif}">Prometheus</text>'
            f'<text x="66" y="194" font-size="28" fill="{C["ink"]}" font-family="{serif}">Which technology fields will combine next?</text>'
            f'<text x="66" y="238" font-size="20" fill="{C["ink2"]}" font-family="{sans}">A graph of 123 fields from 9.45 million US patents,</text>'
            f'<text x="66" y="266" font-size="20" fill="{C["ink2"]}" font-family="{sans}">kept in one Relate file, that grades its own</text>'
            f'<text x="66" y="294" font-size="20" fill="{C["ink2"]}" font-family="{sans}">predictions against history.</text>')
    cap = f'<line x1="66" y1="330" x2="560" y2="330" stroke="{C["hair"]}"/>'
    if show_fire or combined_now:
        outcome = (f"They combined {d['combined'] - YEAR} years later, in {d['combined']}." if reveal else
                   f"They combined in {d['combined']}." if combined_now else "Not combined yet.")
        sub = "control systems × reading and recognising data" if (a, b) == ("G05D", "G06K") else ""
        cap += (f'<line x1="66" y1="364" x2="104" y2="364" stroke="{C["f3"]}" stroke-width="3.6" stroke-dasharray="11 7"/>'
                f'<text x="116" y="371" font-size="20" fill="{C["ink"]}" font-family="{sans}">The graph\'s #{d["rank"]} pick in {YEAR}: '
                f'<tspan font-weight="600">{a} × {b}</tspan></text>'
                f'<text x="116" y="399" font-size="18" fill="{C["ink2"]}" font-family="{sans}">{sub}</text>'
                f'<text x="66" y="440" font-size="20" font-weight="600" fill="{C["ink"]}" font-family="{sans}">{outcome}</text>')
    bridge_years = [fy for x, y, fy in d["arcs"] if {x, y} & {a, b} and {x, y} != {a, b}]
    n_bridges, by = len(d["nodes"]) - 2, max(bridge_years)
    legend = (f"Blue: the {n_bridges} fields both had combined with, all by {by}." if year >= by else
              f"Blue: pairs combined by {year}, darker if newer.")
    cap += f'<text x="66" y="484" font-size="18" fill="{C["ink2"]}" font-family="{sans}">{legend}</text>'
    style = f"<style>{SERIF_FACE}</style>" if published else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Prometheus: a graph of technology fields that predicts which will combine next">{style}'
            f'<rect width="{W}" height="{H}" fill="{C["paper"]}"/>{left}{cap}{"" if reveal else yr}{"".join(parts)}{slot}</svg>'), mid


def spark_image():
    """The author's generated spark with its white background removed; a drawn placeholder if it is missing."""
    f = SRC / "spark.png"
    if f.exists():
        src = Image.open(f).convert("RGBA")
        # colour-to-alpha against white: how far the pixel is from white is how opaque it is. The generated "white" is
        # noisy (values 245 to 255), so anything that close to white becomes fully transparent, and the flame body
        # (well away from white) becomes fully opaque instead of slightly see-through.
        def matte(p):
            r, g, b, a0 = p
            a = max(255 - r, 255 - g, 255 - b) / 255
            alpha = min(1.0, max(0.0, (a - 0.08) / 0.45)) * a0 / 255
            if alpha >= 0.999 or a <= 0:
                return (r, g, b, round(alpha * 255))
            unmix = lambda c: max(0, min(255, round(255 - (255 - c) / a)))   # remove the white mixed into edge pixels
            return (unmix(r), unmix(g), unmix(b), round(alpha * 255))
        im = Image.new("RGBA", src.size)
        im.putdata([matte(p) for p in src.getdata()])
        bbox = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        im = im.crop(bbox) if bbox else im
        im.save(SRC / "spark-cutout.png")    # the transparent layer, kept as an editable source
        return im, True
    im = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.polygon([(100, 10), (150, 120), (140, 190), (100, 250), (60, 190), (50, 120)], fill=(228, 87, 46, 255))
    dr.polygon([(100, 90), (125, 160), (100, 240), (75, 160)], fill=(142, 34, 8, 255))
    return im, False


def composite(base_png, mid, scale, spark, size_frac=1.0):
    base = Image.open(base_png).convert("RGBA")
    if size_frac <= 0:
        return base
    target_h = int(168 * scale * size_frac)
    sp = spark.resize((max(1, int(spark.width * target_h / spark.height)), target_h), Image.LANCZOS)
    x = int(mid[0] * scale - sp.width / 2)
    y = int(mid[1] * scale - sp.height * 0.90)
    base.alpha_composite(sp, (x, y))
    return base


def build_hero(d):
    spark, real = spark_image()
    svg, mid = hero_svg(d, reveal=True, published=False, show_spark_slot=True)
    (OUT / "hero-layout.svg").write_text(svg)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "h.png"
        pub, mid = hero_svg(d, reveal=True)
        render_svg(pub, p, scale=2)
        composite(p, mid, 2, spark).convert("RGB").save(OUT / "hero.png", optimize=True)
        # GIF: the shared links appear year by year, then the predicted pair, then the spark grows, then the pair combines
        frames, durations = [], []
        first = min(fy for x, y, fy in d["arcs"])
        last = max(fy for x, y, fy in d["arcs"] if {x, y} & {d["a"], d["b"]} and {x, y} != {d["a"], d["b"]})
        steps = [(y, False, 0, 650) for y in range(first, last)] + [(last, False, 0, 1500), (YEAR, True, 0, 900)]
        steps += [(2005, True, s, 90) for s in (0.25, 0.5, 0.75, 1.0)] + [(2005, True, 1.0, 1800), (d["combined"], True, 1.0, 3400)]
        for i, (yr, fire, spk, ms) in enumerate(steps):
            svg_i, mid_i = hero_svg(d, year=yr, show_fire=fire)
            f = Path(tmp) / f"f{i}.png"
            render_svg(svg_i, f, scale=1)
            frames.append(composite(f, mid_i, 1, spark, spk).convert("RGB").quantize(colors=128, method=Image.MEDIANCUT))
            durations.append(ms)
        frames[0].save(OUT / "hero.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True, disposal=1)
    return real


# ---------------------------------------------------------------- proof board
def build_proof_board():
    shots = ROOT / "docs" / "screenshots"
    tiles = [("tree_2005_pair.png", (240, 15, 1425, 690), "Tree: arcs are pairs that combined; fire is a predicted pair"),
             ("landscape_2005.png", (20, 110, 1010, 672), "Landscape: hills are where ranked gaps cluster"),
             ("matrix_2005.png", (100, 120, 1420, 870), "Matrix: every pair of fields is a cell"),
             ("field_G06N.png", (20, 110, 1360, 872), "Field profile: one field over time")]
    tw, th, gap, cap, pad = 1120, 638, 64, 72, 40
    board = Image.new("RGB", (2 * tw + gap + 2 * pad, 2 * (th + cap) + gap + pad), C["paper"])
    dr = ImageDraw.Draw(board)
    from PIL import ImageFont
    font = None
    for f in ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arial.ttf"):
        try:
            font = ImageFont.truetype(f, 38)
            break
        except OSError:
            continue
    for k, (name, box, label) in enumerate(tiles):
        im = Image.open(shots / name).convert("RGB").crop(box)
        k_ = min(tw / im.width, th / im.height)
        im = im.resize((round(im.width * k_), round(im.height * k_)), Image.LANCZOS)
        x0 = pad + (k % 2) * (tw + gap) + (tw - im.width) // 2
        y0 = pad + (k // 2) * (th + cap + gap)
        board.paste(im, (x0, y0 + (th - im.height) // 2))
        dr.rectangle([x0 - 2, y0 + (th - im.height) // 2 - 2, x0 + im.width + 1, y0 + (th - im.height) // 2 + im.height + 1],
                     outline=C["hair"], width=2)
        dr.text((pad + (k % 2) * (tw + gap), y0 + th + 16), label, fill=C["ink2"], font=font)
    # WebP keeps the screenshots sharp at a quarter of the PNG size; GitHub renders it
    board.save(OUT / "proof-board.webp", quality=88, method=6)


# ---------------------------------------------------------------- result card and architecture (pure SVG, system fonts)
def build_result_card():
    def col(x, kicker, big, line1, line2):
        return (f'<text x="{x}" y="58" font-size="18" font-weight="600" fill="{C["ink2"]}" font-family="{SYS_SANS}">{kicker}</text>'
                f'<text x="{x}" y="118" font-size="50" fill="{C["ink"]}" font-family="{SYS_SERIF}">{big}</text>'
                f'<text x="{x}" y="160" font-size="20" fill="{C["ink"]}" font-family="{SYS_SANS}">{line1}</text>'
                f'<text x="{x}" y="188" font-size="18" fill="{C["ink2"]}" font-family="{SYS_SANS}">{line2}</text>')
    body = (col(40, "PRE-REGISTERED TEST", "Failed", "1.04x the size rule, 2x required", "on the top 100 pairs, 2005 to 2014")
            + f'<line x1="410" y1="40" x2="410" y2="200" stroke="{C["hair"]}"/>'
            + col(440, "BEYOND SIZE (EXPLORATORY)", "+0.09 to +0.23", "AUC over the size rule", "on pairs it ranks low; defined afterwards")
            + f'<line x1="810" y1="40" x2="810" y2="200" stroke="{C["hair"]}"/>'
            + col(840, "AGENTS THROUGH RELATE", "9 of 30", "came true; chance expects 1.5", "the graph alone: 10 of 30"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 230" width="100%" role="img" '
           f'aria-label="Results: the pre-registered test failed (1.04 times the size rule, 2 times required); beyond size the graph adds 0.09 to 0.23 AUC (exploratory); agents reading the graph through Relate picked 9 of 30 pairs that came true, where chance expects 1.5 and the graph alone got 10.">'
           f'<rect x="1" y="1" width="1198" height="228" rx="10" fill="{C["paper"]}" stroke="{C["hair"]}"/>{body}</svg>')
    (OUT / "result-card.svg").write_text(svg)


def build_architecture():
    def box(x, y, w, h, title, sub, store=False):
        shape = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{18 if store else 8}" fill="{C["wedge"] if store else C["paper"]}" '
                 f'stroke="{C["ink"] if store else C["hair"]}" stroke-width="{2 if store else 1.5}"/>')
        return (shape + f'<text x="{x + 16}" y="{y + 34}" font-size="20" font-weight="600" fill="{C["ink"]}" font-family="{SYS_SANS}">{title}</text>'
                + f'<text x="{x + 16}" y="{y + 62}" font-size="18" fill="{C["ink2"]}" font-family="{SYS_SANS}">{sub}</text>')

    def arrow(x1, y1, x2, y2, label="", dash=False, color=None, at=None):
        """at = (x, y, anchor) places the label off a diagonal line; the default sits it above the middle."""
        col = color or C["ink2"]
        lx, ly, anc = at or ((x1 + x2) / 2, (y1 + y2) / 2 - 8, "middle")
        lab = (f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="{anc}" font-size="18" fill="{C["ink2"]}" '
               f'font-family="{SYS_SANS}">{label}</text>') if label else ""
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="2" {"stroke-dasharray=\"7 5\"" if dash else ""} '
                f'marker-end="url(#ah)"/>' + lab)
    body = (box(20, 40, 230, 80, "PatentsView", "9.45M patents, 4 tables")
            + arrow(250, 80, 330, 80, "DuckDB")
            + box(330, 40, 210, 80, "Small CSVs", "fields, pairs, links")
            + arrow(540, 80, 620, 80, "build")
            + box(620, 30, 300, 100, "data/prometheus.rl", "the graph, one Relate file", store=True)
            + box(620, 250, 300, 100, "capsules/YYYY.rl", "sealed, blinded, per year", store=True)
            + arrow(435, 120, 620, 290, "capsule", at=(512, 228, "end"))
            + box(990, 0, 200, 70, "Web views", "Cypher, live")
            + box(990, 90, 200, 70, "Predictor", "backtest, scoring")
            + box(990, 180, 200, 70, "Your agent", "read-only MCP")
            + arrow(920, 50, 990, 36) + arrow(920, 80, 990, 125) + arrow(920, 110, 990, 210)
            + box(990, 280, 200, 70, "Forecasters", "read-only MCP")
            + arrow(920, 300, 990, 315)
            + box(620, 400, 300, 90, "results/ledger/ledger.rl", "shared: agents write in", store=True)
            + arrow(1090, 350, 920, 440, "one transaction per forecast", at=(1190, 484, "end"))
            + box(330, 410, 210, 70, "Grader", "writes outcomes back")
            + arrow(540, 445, 620, 445))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 530" width="100%" role="img" '
           f'aria-label="Architecture: PatentsView tables are reduced by DuckDB to small CSVs and built into one Relate file. Web views, the predictor and your own agent query it; sealed per-year capsules serve forecaster agents over read-only MCP; agents write forecasts into a shared ledger file in one transaction each and a grader writes the outcomes back.">'
           f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{C["ink2"]}"/></marker></defs>'
           f'<rect x="1" y="1" width="1198" height="528" rx="10" fill="{C["paper"]}" stroke="{C["hair"]}"/>'   # opaque: readable in dark mode
           f'<g transform="translate(0,20)">{body}</g></svg>')
    (OUT / "architecture.svg").write_text(svg)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    d = hero_data()
    (SRC / "hero-data.json").write_text(json.dumps({k: v for k, v in d.items() if k != "arcs"}, indent=1))
    real = build_hero(d)
    build_proof_board()
    build_result_card()
    build_architecture()
    print(f"hero pair {d['a']} x {d['b']}: graph rank #{d['rank']} in {YEAR}, combined {d['combined']}; "
          f"spark: {'the generated image' if real else 'a drawn PLACEHOLDER (add assets/readme/src/spark.png)'}")
    for f in sorted(OUT.glob("*.*")):
        print(f"  {f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
