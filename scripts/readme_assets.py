"""Build the README visuals from the real store and screenshots. Re-run after the data or the spark image changes.

    python scripts/readme_assets.py            # needs Google Chrome (to render SVG to PNG) and Pillow

Writes to assets/readme/:
  hero-layout.svg   editable SVG source of the hero (layout, type, the real graph fragment)
  hero.png          the published hero: the layout plus the spark composited at the predicted pair (2x resolution)
  hero.gif          the same scene: the shared links appear, the pair is picked, then combines (GitHub plays GIFs, not SVG animation)
  proof-board.webp  four real screenshots: tree, landscape, matrix, field profile
  result-card.svg   the honest result in three numbers (pure SVG, system fonts)
  architecture.svg  how the parts fit (pure SVG, system fonts)
  dataset.svg       what went in: the patent data in four numbers and a growth line
  headers/*.svg     a section card per heading in the README, the docs, the agent briefs and the challenge; each draws a
                    real predicted pair (the list is in src/header-pairs.json); headings are swapped for cards in place
The spark is a generated raster supplied by the author: assets/readme/src/spark.png. Without it a drawn placeholder is used.

The README palette (navy and cream cards, coral, teal and violet accents) is separate from the app's own design tokens.
Coral always means a prediction, teal a link that already exists, violet a prediction that came true.
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prometheus.server import Service  # noqa: E402

OUT = ROOT / "assets" / "readme"
SRC = OUT / "src"
FONTS = ROOT / "src" / "prometheus" / "web" / "fonts"
C = dict(navy="#121827", navy2="#1B2336", pill="#252F42", cream="#F5F1E9", ink="#172033", panel="#EEF0F4", white="#FFFFFF",
         line="#C9CED7", muted="#777E88", dim="#8A919D", soft="#AEB4BF", faint="#E6E1D6",
         coral="#FF7458", teal="#63D3BE", violet="#6A62D9", violet2="#8F88F0")
FACE = (f"@font-face{{font-family:'Instrument Sans';font-weight:400;src:url('file://{FONTS}/instrument-sans-latin-400-normal.woff2')}}"
        f"@font-face{{font-family:'Instrument Sans';font-weight:600;src:url('file://{FONTS}/instrument-sans-latin-600-normal.woff2')}}")
SYS_SANS = "system-ui, -apple-system, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
W, H = 1200, 540
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


def kicker(x, y, text, color, size=17, anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="600" letter-spacing="2" fill="{color}" '
            f'font-family="{{sans}}">{text}</text>')


def pill(x, y, text, fill, color, size=16):
    w = round(len(text) * size * 0.68 + 36)
    return (f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="18" fill="{fill}"/>'
            f'<text x="{x + w / 2}" y="{y + 24}" text-anchor="middle" font-size="{size}" font-weight="600" letter-spacing="1" '
            f'fill="{color}" font-family="{{sans}}">{text}</text>'), w


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


def hero_svg(d, year=YEAR, show_fire=True, reveal=False, show_spark_slot=False, published=True):
    """The pair, the fields both had already combined with (only arcs that touch the pair), and the predicted link.

    reveal: the static hero shows the 2005 picture and states what happened later in the pills."""
    a, b = d["a"], d["b"]
    pos = node_pos(d["nodes"], a, b)
    combined_now = year >= d["combined"]
    bridge_years = [fy for x, y, fy in d["arcs"] if {x, y} & {a, b} and {x, y} != {a, b}]
    n_bridges, by = len(d["nodes"]) - 2, max(bridge_years)
    sans = f"Instrument Sans, {SYS_SANS}" if published else SYS_SANS

    graph = []
    if not reveal:   # the year, faint, under the arcs (the GIF needs it; the static hero says it in the pills)
        graph.append(f'<text x="{CX}" y="{CY + 118}" text-anchor="middle" font-size="52" font-weight="600" fill="{C["pill"]}" '
                     f'font-family="{sans}">{year}</text>')
    for x, y, fy in sorted(d["arcs"], key=lambda t: -t[2]):
        if fy > year or not ({x, y} & {a, b}) or {x, y} == {a, b}:
            continue
        path, _ = arc_path(pos[x], pos[y], bend=0.25)
        age = year - fy
        op, sw = (1.0, 2.6) if age <= 3 else (0.75, 2.2) if age <= 10 else (0.45, 1.8)
        graph.append(f'<path d="{path}" fill="none" stroke="{C["teal"]}" stroke-width="{sw}" stroke-opacity="{op}" stroke-linecap="round"/>')
    pair_path, mid = arc_path(pos[a], pos[b], bend=0)
    if combined_now:
        graph.append(f'<path d="{pair_path}" fill="none" stroke="{C["violet2"]}" stroke-width="4.5" stroke-linecap="round"/>')
    elif show_fire:
        graph.append(f'<path d="{pair_path}" fill="none" stroke="{C["coral"]}" stroke-width="3.6" stroke-dasharray="11 7" stroke-linecap="round"/>')
    for n, (x, y, t) in pos.items():
        key = n in (a, b)
        graph.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 if key else 5.5}" fill="{C["cream"]}"/>')
        lx, ly = CX + (R + 20) * math.cos(t), CY + (R + 20) * math.sin(t)
        anchor = "start" if math.cos(t) > 0.2 else "end" if math.cos(t) < -0.2 else "middle"
        dy = 7 if abs(math.sin(t)) < 0.5 else (16 if math.sin(t) > 0 else 0)
        graph.append(f'<text x="{lx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" font-size="{22 if key else 18}" '
                     f'font-weight="{600 if key else 400}" fill="{C["cream"] if key else C["dim"]}" font-family="{sans}">{n}</text>')
    slot = (f'<circle cx="{mid[0]:.1f}" cy="{mid[1]:.1f}" r="30" fill="none" stroke="{C["soft"]}" stroke-dasharray="3 4"/>'
            if show_spark_slot else "")

    left = (f'<rect x="64" y="58" width="40" height="5" rx="2.5" fill="{C["coral"]}"/>'
            + kicker(64, 94, "PATENT GRAPH  ·  ONE RELATE FILE", C["dim"])
            + f'<text x="62" y="170" font-size="80" font-weight="600" fill="{C["cream"]}" font-family="{{sans}}">Prometheus</text>'
            f'<text x="64" y="216" font-size="28" font-weight="600" fill="{C["cream"]}" font-family="{{sans}}">Which technology fields will combine next?</text>'
            f'<text x="64" y="256" font-size="20" fill="{C["soft"]}" font-family="{{sans}}">A graph of 123 fields from 9.45 million US patents</text>'
            f'<text x="64" y="284" font-size="20" fill="{C["soft"]}" font-family="{{sans}}">that grades its own predictions against history.</text>')
    sub = "control systems × reading and recognising data" if (a, b) == ("G05D", "G06K") else ""
    panel = (f'<rect x="64" y="318" width="540" height="160" rx="16" fill="{C["navy2"]}"/>'
             + kicker(88, 352, f"THE GRAPH'S #{d['rank']} PICK IN {YEAR}", C["dim"], size=16)
             + f'<text x="88" y="392" font-size="32" font-weight="600" fill="{C["cream"]}" font-family="{{sans}}">{a} × {b}</text>'
             f'<text x="88" y="420" font-size="18" fill="{C["soft"]}" font-family="{{sans}}">{sub}</text>')
    if reveal or combined_now:
        pills = [(f"PICKED {YEAR}", C["coral"], C["navy"]), (f"COMBINED {d['combined']}", C["violet"], C["cream"])]
    elif show_fire:
        pills = [(f"PICKED {YEAR}", C["coral"], C["navy"]), ("NOT COMBINED YET", C["pill"], C["soft"])]
    else:
        pills = [(f"SHOWING {year}", C["pill"], C["soft"])]
    px = 88
    for text, fill, color in pills:
        s, w = pill(px, 432, text, fill, color)
        panel += s
        px += w + 12

    legend, lx = "", 64
    shared = f"{n_bridges} shared partners, all by {by}" if year >= by or reveal else f"links made by {year}"
    for kind, text in (("teal", shared), ("coral", "prediction"), ("violet2", "came true")):
        dash = ' stroke-dasharray="8 5"' if kind == "coral" else ""
        legend += (f'<line x1="{lx}" y1="{511}" x2="{lx + 26}" y2="511" stroke="{C[kind]}" stroke-width="3.5"{dash} stroke-linecap="round"/>'
                   f'<text x="{lx + 36}" y="517" font-size="18" fill="{C["dim"]}" font-family="{{sans}}">{text}</text>')
        lx += 36 + round(len(text) * 9.4) + 28

    style = f"<style>{FACE}</style>" if published else ""
    body = (left + panel + legend).replace("{sans}", sans)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Prometheus: a graph of technology fields that predicts which will combine next">{style}'
            f'<rect width="{W}" height="{H}" fill="{C["navy"]}"/>{body}{"".join(graph)}{slot}</svg>'), mid


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
        steps += [(YEAR, True, s, 90) for s in (0.25, 0.5, 0.75, 1.0)] + [(YEAR, True, 1.0, 1800), (d["combined"], True, 1.0, 3400)]
        for i, (yr, fire, spk, ms) in enumerate(steps):
            svg_i, mid_i = hero_svg(d, year=yr, show_fire=fire)
            f = Path(tmp) / f"f{i}.png"
            render_svg(svg_i, f, scale=1)
            frames.append(composite(f, mid_i, 1, spark, spk).convert("RGB"))
            durations.append(ms)
        # one palette for every frame, taken from the first and last frames together (bright new teal, then coral, violet
        # and the flame), so small accents keep their colour and nothing flickers between frames
        both = Image.new("RGB", (W, 2 * H))
        both.paste(frames[0], (0, 0))
        both.paste(frames[-1], (0, H))
        pal = both.quantize(colors=192, method=Image.MEDIANCUT)
        frames = [fr.quantize(palette=pal) for fr in frames]
        frames[0].save(OUT / "hero.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True, disposal=1)
    return real


# ---------------------------------------------------------------- proof board
def _font(bold, size):
    names = (("NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf") if bold else ("NotoSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"))
    dirs = ("/usr/share/fonts/truetype/noto/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", "C:/Windows/Fonts/")
    for n in names:
        for dd in dirs:
            try:
                return ImageFont.truetype(dd + n, size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_proof_board():
    shots = ROOT / "docs" / "screenshots"
    tiles = [("tree_2005_pair.png", (240, 15, 1425, 690), "TREE", "arcs are pairs that combined; dashed, a predicted pair"),
             ("landscape_2005.png", (20, 110, 1010, 672), "LANDSCAPE", "hills are where ranked gaps cluster"),
             ("matrix_2005.png", (100, 120, 1420, 870), "MATRIX", "every pair of fields is a cell"),
             ("field_G06N.png", (20, 110, 1360, 872), "FIELD", "one field over time")]
    tw, th, gap, cap, pad = 1120, 638, 64, 84, 48
    board = Image.new("RGB", (2 * tw + gap + 2 * pad, 2 * (th + cap) + gap + pad), C["navy"])
    dr = ImageDraw.Draw(board)
    f_num, f_kick, f_text = _font(True, 40), _font(True, 32), _font(False, 34)
    for k, (name, box, kick, label) in enumerate(tiles):
        im = Image.open(shots / name).convert("RGB").crop(box)
        k_ = min(tw / im.width, th / im.height)
        im = im.resize((round(im.width * k_), round(im.height * k_)), Image.LANCZOS)
        x0 = pad + (k % 2) * (tw + gap) + (tw - im.width) // 2
        y0 = pad + (k // 2) * (th + cap + gap)
        top = y0 + (th - im.height) // 2
        dr.rounded_rectangle([x0 - 10, top - 10, x0 + im.width + 9, top + im.height + 9], radius=18, fill=C["cream"])
        board.paste(im, (x0, top))
        tx, ty = pad + (k % 2) * (tw + gap), y0 + th + 24
        dr.text((tx, ty), f"0{k + 1}", fill=C["coral"], font=f_num)
        dr.text((tx + 70, ty + 5), kick, fill=C["cream"], font=f_kick)
        dr.text((tx + 70 + dr.textlength(kick, font=f_kick) + 20, ty + 3), label, fill=C["soft"], font=f_text)
    # WebP keeps the screenshots sharp at a quarter of the PNG size; GitHub renders it
    board.save(OUT / "proof-board.webp", quality=88, method=6)


# ---------------------------------------------------------------- result card and architecture (pure SVG, system fonts)
def build_result_card():
    def col(x, n, kick, big, line1, line2):
        return (f'<text x="{x + 330}" y="86" text-anchor="end" font-size="60" font-weight="700" fill="{C["faint"]}" font-family="{SYS_SANS}">0{n}</text>'
                f'<circle cx="{x + 330 - 92}" cy="76" r="6" fill="{C["teal"]}"/>'
                + kicker(x, 54, kick, C["muted"], size=16).replace("{sans}", SYS_SANS)
                + f'<rect x="{x}" y="68" width="36" height="5" rx="2.5" fill="{C["coral"]}"/>'
                f'<text x="{x}" y="134" font-size="48" font-weight="700" fill="{C["ink"]}" font-family="{SYS_SANS}">{big}</text>'
                f'<text x="{x}" y="174" font-size="20" fill="{C["ink"]}" font-family="{SYS_SANS}">{line1}</text>'
                f'<text x="{x}" y="202" font-size="18" fill="{C["muted"]}" font-family="{SYS_SANS}">{line2}</text>')
    body = (col(40, 1, "PRE-REGISTERED TEST", "Failed", "1.04x the size rule, 2x required", "top 100 pairs, 2005 to 2014")
            + f'<line x1="410" y1="40" x2="410" y2="206" stroke="{C["faint"]}" stroke-width="2"/>'
            + col(440, 2, "BEYOND SIZE", "+0.09 to 0.23", "AUC over the size rule", "exploratory: defined afterwards")
            + f'<line x1="810" y1="40" x2="810" y2="206" stroke="{C["faint"]}" stroke-width="2"/>'
            + col(840, 3, "AGENTS ON RELATE", "9 of 30", "came true; chance expects 1.5", "the graph alone: 10 of 30"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 240" width="100%" role="img" '
           f'aria-label="Results: the pre-registered test failed, 1.04 times the size rule against 2 times required. Beyond size, the graph adds 0.09 to 0.23 AUC (exploratory, defined afterwards). Agents reading the graph through Relate picked 9 of 30 pairs that came true, where chance expects 1.5 and the graph alone got 10.">'
           f'<rect x="1" y="1" width="1198" height="238" rx="18" fill="{C["cream"]}"/>{body}</svg>')
    (OUT / "result-card.svg").write_text(svg)


def build_architecture():
    def box(x, y, w, h, title, sub, kind="step"):
        """step: a white card; store: a navy card (a Relate file); agent: a white card with a violet edge."""
        if kind == "store":
            return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{C["navy"]}"/>'
                    f'<circle cx="{x + w - 22}" cy="{y + 24}" r="6" fill="{C["teal"]}"/>'
                    f'<text x="{x + 18}" y="{y + 38}" font-size="20" font-weight="700" fill="{C["cream"]}" font-family="{SYS_SANS}">{title}</text>'
                    f'<text x="{x + 18}" y="{y + 66}" font-size="18" fill="{C["soft"]}" font-family="{SYS_SANS}">{sub}</text>')
        edge = (f'<rect x="{x}" y="{y + 12}" width="5" height="{h - 24}" rx="2.5" fill="{C["violet"]}"/>' if kind == "agent" else "")
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{C["white"]}" stroke="{C["line"]}" stroke-width="1.5"/>{edge}'
                f'<text x="{x + 18}" y="{y + 32}" font-size="20" font-weight="700" fill="{C["ink"]}" font-family="{SYS_SANS}">{title}</text>'
                f'<text x="{x + 18}" y="{y + 58}" font-size="18" fill="{C["muted"]}" font-family="{SYS_SANS}">{sub}</text>')

    def arrow(x1, y1, x2, y2, label="", hot=False, at=None):
        """at = (x, y, anchor) places the label off a diagonal line; the default sits it above the middle."""
        col, mk = (C["coral"], "ahc") if hot else (C["dim"], "ah")
        lx, ly, anc = at or ((x1 + x2) / 2, (y1 + y2) / 2 - 10, "middle")
        lab = (f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="{anc}" font-size="18" fill="{C["muted"]}" '
               f'font-family="{SYS_SANS}">{label}</text>') if label else ""
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{2.5 if hot else 2}" marker-end="url(#{mk})"/>' + lab)

    heads = (kicker(20, 0, "SOURCE", C["muted"], size=16) + kicker(620, 0, "RELATE FILES", C["muted"], size=16)
             + kicker(990, 0, "WHO USES THEM", C["muted"], size=16)).replace("{sans}", SYS_SANS)
    body = (heads
            + box(20, 50, 230, 76, "PatentsView", "9.45M patents, 4 tables")
            + arrow(250, 88, 330, 88, "DuckDB")
            + box(330, 50, 210, 76, "Small CSVs", "fields, pairs, links")
            + arrow(540, 88, 620, 88, "build")
            + box(620, 40, 300, 96, "data/prometheus.rl", "the graph, one Relate file", "store")
            + box(620, 256, 300, 96, "capsules/YYYY.rl", "sealed, blinded, per year", "store")
            + arrow(435, 126, 620, 296, "capsule", at=(512, 236, "end"))
            + box(990, 14, 200, 70, "Web views", "Cypher, live")
            + box(990, 100, 200, 70, "Predictor", "backtest, scoring")
            + box(990, 186, 200, 70, "Your agent", "read-only MCP", "agent")
            + arrow(920, 62, 990, 49) + arrow(920, 88, 990, 135) + arrow(920, 116, 990, 215)
            + box(990, 286, 200, 70, "Forecasters", "read-only MCP", "agent")
            + arrow(920, 306, 990, 321)
            + box(620, 404, 300, 96, "results/ledger/ledger.rl", "shared: agents write in", "store")
            + arrow(1090, 356, 922, 446, "one transaction per forecast", hot=True, at=(1190, 492, "end"))
            + box(330, 414, 210, 76, "Grader", "writes outcomes back")
            + arrow(540, 452, 620, 452))
    marker = lambda mid, col: (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                               f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 580" width="100%" role="img" '
           f'aria-label="Architecture: PatentsView tables are reduced by DuckDB to small CSVs and built into one Relate file. Web views, the predictor and your own agent query it; sealed per-year capsules serve forecaster agents over read-only MCP; agents write forecasts into a shared ledger file, one transaction per forecast, and a grader writes the outcomes back.">'
           f'<defs>{marker("ah", C["dim"])}{marker("ahc", C["coral"])}</defs>'
           f'<rect x="1" y="1" width="1198" height="578" rx="18" fill="{C["panel"]}"/>'   # opaque: readable in dark mode
           f'<g transform="translate(0,52)">{body}</g></svg>')
    (OUT / "architecture.svg").write_text(svg)


# ---------------------------------------------------------------- section headers for the README and the docs
# (doc, the heading line as written in the Markdown, kicker, title on the card, a line kept under the card or None).
# A '# ' line is the document's title card; its kicker defaults to PROMETHEUS · DOCUMENTATION.
DOCS = {"readme": "README.md", "results": "docs/RESULTS.md", "guide": "docs/GUIDE.md", "architecture": "docs/ARCHITECTURE.md",
        "data": "docs/DATA.md", "prompt": "agent/PROMPT.md", "ledger": "agent/LEDGER.md", "challenge": "challenge/README.md"}
# each document's cards draw the graph's top picks from one year, so every card shows a different real pair
DOC_YEAR = {"readme": 2005, "results": 2010, "guide": 1995, "architecture": 2000, "data": 1990, "prompt": 2014, "ledger": 1985,
            "challenge": 2020}
HEADERS = [
    ("readme", "## Use case", "THE PROBLEM", "Use case", None),
    ("readme", "## How it uses Relate", "THE DATABASE", "How it uses Relate", None),
    ("readme", "## Setup and run", "GET STARTED", "Setup and run", None),
    ("readme", "## Dataset", "SOURCE", "Dataset", None),
    ("readme", "## Where the data lives", "FILES", "Where the data lives", None),
    ("readme", "## What we found", "RESULTS", "What we found", None),
    ("readme", "## The views", "INTERFACE", "The views", None),
    ("readme", "## Ask the graph with your own agent", "AGENTS", "Ask the graph with your own agent", None),
    ("readme", "## Beat the graph", "CHALLENGE", "Beat the graph", None),
    ("readme", "## Documentation", "READ MORE", "Documentation", None),
    ("readme", "## Credits and licence", "LICENCE", "Credits and licence", None),
    ("results", "# Results", None, "Results", None),
    ("results", "## The graph predicts", "THE BACKTEST", "The graph predicts", None),
    ("results", "## Where the graph adds most", "BEYOND SIZE", "Where the graph adds most", None),
    ("results", "## Agents reading Relate", "AGENTS", "Agents reading Relate", None),
    ("results", "## One shared ledger", "SHARED STATE", "One shared ledger", None),
    ("results", "## Limitations", "READ BEFORE CITING", "Limitations", None),
    ("results", "## Reproduce", "COMMANDS", "Reproduce", None),
    ("guide", "# Guide", None, "Guide", None),
    ("guide", "## Use case in more detail", "WHY", "Use case in more detail", None),
    ("guide", "## Run it on real patents", "REAL DATA", "Run it on real patents", None),
    ("guide", "## The commands", "CLI", "The commands", None),
    ("guide", "## Explore it (the tree of life)", "THE TREE OF LIFE", "Explore it", None),
    ("guide", "## How Relate is used, and why", "RELATE", "How Relate is used, and why", None),
    ("guide", "## The field slice", "SLICES", "The field slice", None),
    ("guide", "## Sealed capsules and the forecaster", "AGENTS", "Sealed capsules and the forecaster", None),
    ("guide", "## Layout", "FILES", "Layout", None),
    ("architecture", "# Architecture", None, "Architecture", None),
    ("architecture", "## 1. The whole picture", "OVERVIEW", "The whole picture", None),
    ("architecture", "## 2. What runs where", "RUNTIME", "What runs where", None),
    ("architecture", "## 3. The data model", "SCHEMA", "The data model", None),
    ("architecture", "## 4. Nothing from the future", "THE INVARIANT", "Nothing from the future",
     "The invariant everything else protects."),
    ("architecture", "## 5. The agent path", "AGENTS", "The agent path", None),
    ("architecture", "## 6. The web server", "WEB", "The web server", None),
    ("architecture", "## 7. Trade-offs", "LIMITS", "Trade-offs", None),
    ("data", "# Getting the data", None, "Getting the data", None),
    ("data", "## Where to download, and exactly what was used", "EXACTLY WHAT WAS USED", "Where to download", None),
    ("prompt", "# Ask the graph: a brief for an AI agent", "PROMETHEUS  ·  AGENT BRIEF", "Ask the graph", "A brief for an AI agent."),
    ("prompt", "## What the graph is", "THE SCHEMA", "What the graph is", None),
    ("prompt", "## Rules for answering", "AS OF A YEAR", "Rules for answering", None),
    ("prompt", "## Working queries", "CYPHER RECIPES", "Working queries", None),
    ("prompt", "## Connecting an agent", "MCP", "Connecting an agent", None),
    ("ledger", "# Forecast ledger: a brief for one of several forecaster agents", "PROMETHEUS  ·  AGENT BRIEF", "Forecast ledger",
     "A brief for one of several forecaster agents."),
    ("ledger", "## Your two connections", "READ AND WRITE", "Your two connections", None),
    ("ledger", "## Your task", "TEN PICKS", "Your task", None),
    ("ledger", "## Writing to the ledger", "ONE TRANSACTION", "Writing to the ledger", None),
    ("ledger", "## Running the ledger yourself", "SETUP", "Running the ledger yourself", None),
    ("challenge", "# Beat the graph", "PROMETHEUS  ·  CHALLENGE", "Beat the graph", None),
    ("challenge", "## Play", "THREE ROUNDS", "Play", None),
    ("challenge", "## Leaderboard", "SCORES", "Leaderboard", None),
    ("challenge", "## Fair play", "HONOUR SYSTEM", "Fair play", None),
]


def header_plan():
    """Number the cards per document; a '# ' line is the document's title card (no number). k is the card's place in its document."""
    out, n = [], {}
    for doc, line, kick, title, sub in HEADERS:
        if line.startswith("# "):
            out.append((doc, line, None, kick or "PROMETHEUS  ·  DOCUMENTATION", title, sub, f"{doc}-00.svg", 0))
        else:
            n[doc] = n.get(doc, 0) + 1
            out.append((doc, line, n[doc], f"{n[doc]:02d}  ·  {kick}", title, sub, f"{doc}-{n[doc]:02d}.svg", n[doc]))
    return out


def header_pairs(plan):
    """For card k of a document, the graph's #(k+1) pick in that document's year (or the next one not already drawn on
    another card), with up to six fields both had combined with."""
    svc = Service(str(ROOT / "data" / "prometheus.rl"), json.loads((ROOT / "results" / "backtest.json").read_text())["weights"])
    try:
        out, used = {}, set()
        for doc, _, _, _, _, _, name, k in plan:
            year = DOC_YEAR[doc]
            gaps = sorted(svc.state(year)["gaps"], key=lambda g: g["rank"])
            g = next(g for g in gaps[k:] if (g["a"], g["b"]) not in used)     # the next top pick not drawn on another card
            used.add((g["a"], g["b"]))
            bridges = [[x["code"], x["since"]] for x in svc.evidence(g["a"], g["b"], year)["bridgeFields"]][:6]
            out[name] = {"year": year, "rank": g["rank"], "a": g["a"], "b": g["b"], "bridges": bridges}
        return out
    finally:
        svc.g.close()


def pair_glyph(gx, gy, r, pair):
    """A tiny version of the hero: the pair across a circle, teal links to the fields both share, the coral predicted link."""
    br = pair["bridges"]
    age = {c: pair["year"] - since for c, since in br}
    top, bottom = br[0::2], br[1::2]
    ang = [math.radians(205 + 130 * (i + 0.5) / max(1, len(top))) for i in range(len(top))]
    ang += [math.radians(155 - 130 * (i + 0.5) / max(1, len(bottom))) for i in range(len(bottom))]
    pa, pb = (gx - r, gy), (gx + r, gy)
    pts = [(gx + r * math.cos(t), gy + r * math.sin(t)) for t in ang]
    s = f'<circle cx="{gx}" cy="{gy}" r="{r}" fill="none" stroke="{C["faint"]}" stroke-width="1.5"/>'
    for (code, _), (x, y) in zip(top + bottom, pts):     # newer shared links are brighter, as on the tree page
        op = 0.95 if age[code] <= 5 else 0.7 if age[code] <= 15 else 0.4
        for ex, ey in (pa, pb):
            s += f'<line x1="{ex:.1f}" y1="{ey:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{C["teal"]}" stroke-width="1.6" stroke-opacity="{op}"/>'
    s += f'<line x1="{pa[0]}" y1="{gy}" x2="{pb[0]}" y2="{gy}" stroke="{C["coral"]}" stroke-width="2.2" stroke-dasharray="5 4"/>'
    for x, y in pts:
        s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{C["ink"]}"/>'
    for x, y in (pa, pb):
        s += f'<circle cx="{x}" cy="{y}" r="4" fill="{C["ink"]}"/>'
    return s


def header_svg(num, kick, title, pair, big=False):
    """The cream section card: kicker, coral bar, bold title, a faded number, and a real predicted pair drawn small."""
    h = 128 if big else 104
    ty, size = (98, 44) if big else (80, 32)
    gx, gr = (842, 30) if num else (1000 - 28 - 40, 40)
    tag = (f'<text x="{gx - gr - 16}" y="{h / 2 - 2}" text-anchor="end" font-size="15" font-weight="700" fill="{C["muted"]}" '
           f'font-family="{SYS_SANS}">{pair["a"]} × {pair["b"]}</text>'
           f'<text x="{gx - gr - 16}" y="{h / 2 + 18}" text-anchor="end" font-size="14" fill="{C["muted"]}" '
           f'font-family="{SYS_SANS}">#{pair["rank"]} pick in {pair["year"]}</text>')
    if num:
        right = (tag + pair_glyph(gx, h / 2, gr, pair)
                 + f'<text x="{1000 - 28}" y="{h / 2 + 22}" text-anchor="end" font-size="60" font-weight="700" fill="{C["faint"]}" '
                 f'font-family="{SYS_SANS}">{num:02d}</text>')
    else:
        right = tag + pair_glyph(gx, h / 2, gr, pair)
    note = f'{pair["a"]} and {pair["b"]}, the graph\'s #{pair["rank"]} pick in {pair["year"]}'
    label = (f"{num:02d}. {title}" if num else title) + f" (drawn: {note})"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {h}" width="100%" role="img" aria-label="{label}">'
            f'<rect x="0" y="0" width="1000" height="{h}" rx="16" fill="{C["cream"]}"/>'
            + kicker(28, 32, kick, C["muted"], size=14).replace("{sans}", SYS_SANS)
            + f'<rect x="28" y="42" width="32" height="4" rx="2" fill="{C["coral"]}"/>'
            f'<text x="28" y="{ty}" font-size="{size}" font-weight="700" fill="{C["ink"]}" font-family="{SYS_SANS}">{title}</text>'
            f'{right}</svg>')


def build_headers():
    d = OUT / "headers"
    d.mkdir(exist_ok=True)
    for f in d.glob("*.svg"):
        f.unlink()
    plan = header_plan()
    pairs = header_pairs(plan)
    for doc, line, num, kick, title, sub, name, k in plan:
        (d / name).write_text(header_svg(num, kick, title, pairs[name], big=num is None))
    (SRC / "header-pairs.json").write_text(json.dumps(pairs, indent=1))


def apply_headers():
    """Swap any Markdown heading still listed in HEADERS for its card, with an anchor that keeps old links working. Idempotent."""
    import re
    slug = lambda t: re.sub(r"\s", "-", re.sub(r"[^\w\- ]", "", t.lower()))
    for doc, line, num, kick, title, sub, name, k in header_plan():
        f = ROOT / DOCS[doc]
        lines = f.read_text().split("\n")
        if line not in lines:
            continue
        i = lines.index(line)
        prefix = "../" * DOCS[doc].count("/")
        alt = title if num is None else f"{num:02d}. {title}"
        block = [f'<a id="{slug(line.lstrip("#").strip())}"></a>', f'<img src="{prefix}assets/readme/headers/{name}" width="100%" alt="{alt}">']
        lines[i:i + 1] = block + (["", sub] if sub else [])
        f.write_text("\n".join(lines))


# ---------------------------------------------------------------- the dataset card
def build_dataset_card():
    from prometheus.graph import TechGraph
    with TechGraph(ROOT / "data" / "prometheus.rl") as g:
        rows = g.q("MATCH (y:FieldYear) RETURN y.year AS year, sum(y.n) AS n ORDER BY year")
    years, ns = [r["year"] for r in rows], [r["n"] for r in rows]
    x0, x1, yb, hgt = 840, 1160, 196, 110        # the growth line, bottom right
    pts = " ".join(f"{x0 + (x1 - x0) * i / (len(ns) - 1):.1f},{yb - hgt * n / max(ns):.1f}" for i, n in enumerate(ns))
    area = f"{x0},{yb} {pts} {x1},{yb}"

    def stat(x, big, line1, line2):
        return (f'<text x="{x}" y="118" font-size="44" font-weight="700" fill="{C["cream"]}" font-family="{SYS_SANS}">{big}</text>'
                f'<text x="{x}" y="152" font-size="20" fill="{C["cream"]}" font-family="{SYS_SANS}">{line1}</text>'
                f'<text x="{x}" y="178" font-size="18" fill="{C["soft"]}" font-family="{SYS_SANS}">{line2}</text>')
    pills, px = "", 40
    for text, fill, color in (("CC BY 4.0", C["teal"], C["navy"]), ("USPTO  ·  PATENTSVIEW", C["pill"], C["soft"]),
                              ("NO INDIVIDUAL PATENT STORED", C["pill"], C["soft"])):
        s, w = pill(px, 214, text, fill, color)
        pills += s.replace("{sans}", SYS_SANS)
        px += w + 12
    body = (f'<rect x="40" y="34" width="36" height="5" rx="2.5" fill="{C["coral"]}"/>'
            + kicker(40, 64, "WHAT WENT IN", C["dim"], size=16).replace("{sans}", SYS_SANS)
            + stat(40, "9.45M", "US patents", f"granted {years[0]} to {years[-1]}")
            + stat(250, "4", "PatentsView tables", "dates, classes, citations, titles")
            + stat(560, "123", "deep-tech fields", "kept, as fields and pairs")
            + f'<polygon points="{area}" fill="{C["teal"]}" fill-opacity="0.18"/>'
            f'<polyline points="{pts}" fill="none" stroke="{C["teal"]}" stroke-width="2.5" stroke-linejoin="round"/>'
            + kicker(x1, 64, "15.5 GB  →  3.9 MB", C["dim"], size=16, anchor="end").replace("{sans}", SYS_SANS)
            + f'<text x="{x0}" y="{yb + 24}" font-size="16" fill="{C["dim"]}" font-family="{SYS_SANS}">{years[0]}</text>'
            f'<text x="{x1}" y="{yb + 24}" text-anchor="end" font-size="16" fill="{C["dim"]}" font-family="{SYS_SANS}">{years[-1]}</text>'
            + pills)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 280" width="100%" role="img" '
           f'aria-label="Dataset: 9.45 million US patents granted {years[0]} to {years[-1]}, four PatentsView tables, 123 deep-tech fields kept; '
           f'15.5 GB of raw tables reduced to a 3.9 MB Relate file. Licence CC BY 4.0. No individual patent is stored. The line shows '
           f'how patenting in these fields grew each year.">'
           f'<rect x="0" y="0" width="1200" height="280" rx="18" fill="{C["navy"]}"/>{body}</svg>')
    (OUT / "dataset.svg").write_text(svg)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    d = hero_data()
    (SRC / "hero-data.json").write_text(json.dumps({k: v for k, v in d.items() if k != "arcs"}, indent=1))
    real = build_hero(d)
    build_proof_board()
    build_result_card()
    build_architecture()
    build_headers()
    apply_headers()
    build_dataset_card()
    print(f"hero pair {d['a']} x {d['b']}: graph rank #{d['rank']} in {YEAR}, combined {d['combined']}; "
          f"spark: {'the generated image' if real else 'a drawn PLACEHOLDER (add assets/readme/src/spark.png)'}")
    for f in sorted(OUT.glob("*.*")):
        print(f"  {f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
