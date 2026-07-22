"""OnScript static-site generator (§8).

Reads the committed derived JSON in ``data/derived/`` and writes a plain,
fast, newspaper-style static site to ``site/public/``. Pure Python stdlib:
no Node, no build step, no client JS framework, zero external requests.
Every page is self-contained HTML with one inline stylesheet and inline SVG.
Vercel serves ``site/public/`` as static files.

Design tenets honored here (gameplan §8 / design tenets):
  * newspaper-plain, muted palette, system fonts, no CDNs/web-fonts/analytics.
  * the "receipts strip" (member count + verbatim quote + topic) under every
    composite claim is the visual signature.
  * neutrality is armor: the Methodology page shows the nightly symmetry audit
    and the live prompt text verbatim.
  * honesty: dry-run / degraded / quiet / fallback output is labeled as such,
    never dressed up as production.

Run:  python pipeline/site.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make ``from pipeline import config`` work when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import boilerplate, build, config, distill, nomenclature, privacy, util, verify  # noqa: E402
from pipeline.phrase_window import public_phrase_window  # noqa: E402

# Windows console: emit UTF-8 (member text contains curly quotes, accents).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DERIVED = config.DERIVED
OUT = config.REPO_ROOT / "site" / "public"
FAVICON_SOURCE = config.REPO_ROOT / "site" / "brand" / "avatar-brand.png"
PROMPTS_DIR = config.REPO_ROOT / "pipeline" / "prompts"
ROSTER_FILE = config.REFERENCE / "roster.json"
TAXONOMY_FILE = config.TAXONOMY_FILE
CORRECTIONS_FILE = config.REFERENCE / "corrections.json"  # operator-appended; corrections are public posts

PARTY_NAME = {"D": "Democrats", "R": "Republicans", "I": "Independents"}
PARTY_LONG = {
    "D": "Democratic members of Congress",
    "R": "Republican members of Congress",
    "I": "Independent members of Congress",
}


# ---------------------------------------------------------------------------
# Small robust IO helpers
# ---------------------------------------------------------------------------
def _load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def esc(value) -> str:
    """HTML-escape any value (never inject raw member/JSON text)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _num(value, default=0):
    try:
        if value is None:
            return default
        return value
    except Exception:
        return default


def _pct(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# Reference data (loaded once)
# ---------------------------------------------------------------------------
ROSTER = _load_json(ROSTER_FILE) or {}
TAXONOMY = _load_json(TAXONOMY_FILE) or {}
CORRECTIONS = _load_json(CORRECTIONS_FILE) or []
PHRASE_EVIDENCE = _load_json(DERIVED / "phrase-evidence.json") or {"phrases": {}}
TOPIC_LABEL = {t.get("id"): t.get("label", t.get("id")) for t in TAXONOMY.get("topics", [])}


def member_name(bioguide, fallback_name=None, *, include_suffix: bool = True) -> str:
    """Resolve a bioguide id to a display name without ever presenting an id as a name."""
    entry = ROSTER.get(bioguide) if isinstance(ROSTER, dict) else None
    name = None
    state = party = None
    if isinstance(entry, dict):
        name = entry.get("name")
        state, party = entry.get("state"), entry.get("party")
    if not name and fallback_name and not re.fullmatch(r"[A-Z]\d{6}", str(fallback_name)):
        name = fallback_name
    if name:
        suffix = ""
        if include_suffix and party and state:
            suffix = f" ({esc(party)}-{esc(state)})"
        elif include_suffix and state:
            suffix = f" ({esc(state)})"
        return f"{esc(name)}{suffix}"
    if not bioguide:
        return "—"
    return "member name unavailable"


def topic_label(topic_id) -> str:
    return esc(TOPIC_LABEL.get(topic_id, topic_id))


# ---------------------------------------------------------------------------
# Shared stylesheet + page shell
# ---------------------------------------------------------------------------
CSS = """
:root{
  --ink:#1a1a1a; --muted:#5a5a5a; --faint:#8a8a8a; --line:#e2e2e2;
  --bg:#fbfbf9; --panel:#ffffff; --accent:#333;
  --blue:#2b4c7e; --blue-bg:#eef2f8; --blue-line:#c7d6ea;
  --red:#8a2f2f; --red-bg:#f8eeee; --red-line:#e6cccc;
  --warn-bg:#fff6e0; --warn-line:#e8cf8a; --warn-ink:#6b4e00;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
.skip-link{position:absolute; left:12px; top:8px; z-index:10; padding:8px 12px; background:var(--panel);
  color:var(--ink); border:2px solid var(--ink); transform:translateY(-150%)}
.skip-link:focus{transform:translateY(0)}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6; font-size:17px;
}
.wrap{max-width:1000px; margin:0 auto; padding:0 20px 80px}
a{color:var(--blue); text-decoration:none}
a:hover{text-decoration:underline}
header.site{border-bottom:2px solid var(--ink); margin-bottom:8px; padding:22px 0 12px}
header.site .brand{font-size:30px; font-weight:800; letter-spacing:-0.02em; color:var(--ink)}
header.site .brand a{color:var(--ink)}
header.site .tag{color:var(--muted); font-size:15px; margin-top:2px; font-style:italic}
nav.top{display:flex; flex-wrap:wrap; gap:16px; padding:10px 0; border-bottom:1px solid var(--line);
  margin-bottom:26px; font-size:15px}
nav.top a{color:var(--muted)}
nav.top a:hover{color:var(--ink)}
h1{font-size:26px; line-height:1.25; margin:26px 0 6px; letter-spacing:-0.01em}
h2{font-size:20px; margin:34px 0 10px; padding-bottom:5px; border-bottom:1px solid var(--line)}
h3{font-size:17px; margin:22px 0 8px}
p{margin:10px 0}
.subhead{color:var(--muted); font-size:15px; margin-top:0}
.mono,code,.sha{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
.sha{font-size:12px; color:var(--faint); word-break:break-all}
.muted{color:var(--muted)}
.faint{color:var(--faint)}
small{font-size:13px}

.banner{border:1px solid var(--warn-line); background:var(--warn-bg); color:var(--warn-ink);
  border-radius:6px; padding:10px 14px; margin:16px 0; font-size:14.5px}
.banner strong{color:var(--warn-ink)}

.lines{display:grid; grid-template-columns:1fr 1fr; gap:18px; margin:18px 0 8px}
@media(max-width:720px){.lines{grid-template-columns:1fr}}
.line{border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:16px 18px}
.line.D{border-top:4px solid var(--blue)}
.line.R{border-top:4px solid var(--red)}
.line .who{font-weight:700; font-size:15px; text-transform:uppercase; letter-spacing:.04em}
.line.D .who{color:var(--blue)}
.line.R .who{color:var(--red)}
.line .composite{margin:8px 0 0; font-size:17px; line-height:1.55}
.line .cnote{margin:8px 0 0; font-size:12.5px; color:var(--faint); font-style:italic}
.line .nocite{margin:12px 0 0; font-size:13px; color:var(--faint)}
.line .metaflags{margin-top:8px; font-size:12.5px; color:var(--faint)}

.duet{margin:18px 0 26px; padding:14px; border:1px solid var(--line); border-radius:8px}
.duet-head{margin-bottom:10px; padding-bottom:8px; border-bottom:1px dashed var(--line)}
/* The phrase is code-computed, so it is set in the UI's own voice (mono, unquoted) and never in
   quotation marks — typographic quotes here would read as "a member said this". */
.duet-phrase{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:700; color:var(--ink)}
.duet .line{padding:0}
.duet .rlabel{margin-bottom:8px}
.receipts{margin-top:14px; padding-top:12px; border-top:1px dashed var(--line)}
.receipts .rlabel{font-size:11.5px; text-transform:uppercase; letter-spacing:.08em; color:var(--faint); margin-bottom:8px}
.receipt{margin:0 0 12px; padding-left:12px; border-left:3px solid var(--line)}
.line.D .receipt{border-left-color:var(--blue-line)}
.line.R .receipt{border-left-color:var(--red-line)}
.receipt .rhead{font-size:13px; color:var(--muted); margin-bottom:2px}
.receipt .rcount{font-weight:700; color:var(--ink)}
.receipt .quote{font-size:14.5px; color:var(--ink)}
.receipt .quote:before{content:"\\201C"} .receipt .quote:after{content:"\\201D"}
.receipt .rtopics{font-size:12px; color:var(--faint); margin-top:2px}
.receipt ul.cites{list-style:none; margin:6px 0 0; padding:0; font-size:12.5px}
.receipt ul.cites li{margin:8px 0 0; color:var(--ink)}
.receipt ul.cites li:first-child{margin-top:4px}
.receipt .citemeta{font-size:12px; color:var(--muted); margin-top:2px}
.receipt .rmore{font-size:11.5px; color:var(--faint); margin-top:6px}
.receipt ul.cites a{color:var(--blue)}
.receipt .quote mark.keyspan{background:#fff2ab; color:inherit; padding:0 1px; border-radius:2px}
.receipt .rtests{margin:5px 0 2px; display:flex; flex-wrap:wrap; gap:5px}
.tchip{display:inline-block; font-size:10.5px; font-weight:600; padding:0 6px; border-radius:9px;
       border:1px solid var(--line); white-space:nowrap; line-height:1.7}
.tchip.ok{color:#1a7f37; border-color:#b7e0c0}
.tchip.no{color:var(--red); border-color:#e6b8b8}
.tchip.info{color:var(--muted)}

.scroll{overflow-x:auto; -webkit-overflow-scrolling:touch}
table{border-collapse:collapse; width:100%; font-size:14.5px}
th,td{text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:middle}
th{font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--faint); font-weight:600; white-space:nowrap}
td.num,th.num{text-align:right; font-variant-numeric:tabular-nums}
tr:hover td{background:#faf9f6}
.pill{display:inline-block; font-size:11px; font-weight:700; padding:1px 7px; border-radius:10px; line-height:1.5}
.pill.D{background:var(--blue-bg); color:var(--blue)}
.pill.R{background:var(--red-bg); color:var(--red)}
.pill.I{background:#eee; color:#555}
.nomtag{display:inline-block; font-size:10.5px; font-weight:600; padding:0 6px; margin-left:6px;
        border:1px solid var(--line); border-radius:9px; color:var(--muted); background:var(--panel);
        white-space:nowrap; vertical-align:1px; cursor:help}
.spark{display:block}
.pcols{display:flex; gap:20px; flex-wrap:wrap}
.pcol{flex:1 1 300px; min-width:0}
.pcol h3{font-size:14px; margin:0 0 6px; font-weight:600}
ol.pcol-list{list-style:none; margin:0; padding:0; font-size:14px}
ol.pcol-list li{padding:6px 0; border-bottom:1px solid var(--line); display:flex; flex-wrap:wrap; align-items:baseline; gap:6px}
.pcount{display:inline-block; min-width:24px; font-weight:700; font-variant-numeric:tabular-nums}

.nav-pn{display:flex; justify-content:space-between; gap:12px; margin:26px 0; font-size:15px}
ul.daylist{list-style:none; margin:0 0 22px; padding:0; display:grid;
  grid-template-columns:repeat(auto-fill, minmax(190px, 1fr)); gap:2px 16px; font-size:14.5px}
ul.daylist li{padding:5px 0; border-bottom:1px solid var(--line)}
.chartbox{border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:12px; margin:16px 0}
.legend{font-size:13px; color:var(--muted); margin:6px 0 0}
.legend .sw{display:inline-block; width:22px; height:0; border-top:3px solid; vertical-align:middle; margin-right:5px}

.kv{display:grid; grid-template-columns:auto 1fr; gap:4px 16px; font-size:14.5px; margin:10px 0}
.kv dt{color:var(--faint)}
.kv dd{margin:0}
@media(max-width:520px){.kv{grid-template-columns:1fr; gap:0}.kv dd{margin-bottom:8px}}

pre.prompt{white-space:pre-wrap; word-wrap:break-word; background:#f6f5f1; border:1px solid var(--line);
  border-radius:6px; padding:12px 14px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:13px; line-height:1.5; color:#2a2a2a; overflow-x:auto}
.promptmeta{font-size:12.5px; color:var(--faint); margin:4px 0 2px}

ul.tight{margin:8px 0; padding-left:22px}
ul.tight li{margin:3px 0}

footer.site{border-top:1px solid var(--line); margin-top:50px; padding-top:16px; color:var(--faint); font-size:13px}
footer.site a{color:var(--muted)}
""".strip()


def page(title: str, body: str, depth: int = 0, description: str = "", path: str = "") -> str:
    """Wrap page ``body`` in the shared shell. ``depth`` = subdir levels below
    the site root (0 for /index.html, 1 for /day/*.html and /phrases/*.html).
    ``path`` = this page's path relative to the site root (e.g. "day/2026-07-18.html"), used to build
    the absolute og:url / canonical. It matches the value the caller appends to ``written``."""
    root = "../" * depth
    # Dark features (docs/11-BUILD-PROGRAM.md) link into the nav only once their FEATURES flag
    # flips True in a commit (the release act). Built-but-unreleased => no public link.
    dark_nav = ""
    if config.feature_on("archive"):
        dark_nav += f'<a href="{root}archive/index.html">Archive</a>'
    if config.feature_on("concordance"):
        dark_nav += f'<a href="{root}concordance.html">Concordance</a>'
    if config.feature_on("awards"):
        dark_nav += f'<a href="{root}awards.html">Awards</a>'
    if config.feature_on("phrase_search"):
        dark_nav += f'<a href="{root}phrases/search.html">Search</a>'
    # The signed post log links into the nav only once the accounts have actually posted (§Session-8);
    # pre-launch it exists at /posts.html but isn't advertised as an empty page.
    if HAS_POSTS:
        dark_nav += f'<a href="{root}posts.html">Posts</a>'
    nav = (
        f'<a href="{root}index.html">Today</a>'
        # The date archive is NAVIGATION to already-public pages, not a feature: the day pages have
        # always been written and permanent, but nothing linked to them (index.html pointed at zero
        # of them and the prev/next chain had no entry point). So it is ungated — a FEATURES flag
        # here would be gating the table of contents of a book that is already on the shelf.
        f'<a href="{root}day/index.html">Days</a>'
        f'<a href="{root}phrases/index.html">Phrases</a>'
        f'{dark_nav}'
        f'<a href="{root}methodology.html">Methodology</a>'
        f'<a href="{root}about.html">About</a>'
    )
    desc = esc(description) if description else "OnScript — what each party said today, compressed to one voice, with receipts."
    # LINK CARDS (docs/23 §7.5 amendment 2). Every share of this site — the launch announce, the
    # receipts link in every composite thread, every reader's repost — is unfurled by a crawler that
    # sees only these tags. Without them the card is a bare imageless URL.
    #
    # THE RULE, and it is a privacy rule, not a style one: og values are built HERE, from this
    # function's own `title`/`description` arguments, and from nothing else. They must never be
    # assembled at a call site and never sourced from composite prose
    # (`day_json["daily_lines"][p]["composite"]`). Composites pass through `privacy_correct_line()`
    # at render time, which can return `withheld` or `recomposed` under Article XIII — meta tags are
    # a surface no audit scans and no reader sees, so sourcing them from raw prose would republish
    # exactly the text the page body deliberately withheld. Both values below are already escaped
    # (`esc(..., quote=True)`), which also closes attribute injection: real composites contain
    # literal double quotes.
    canonical = f"{config.SITE_URL}/" if path in ("", "index.html") else f"{config.SITE_URL}/{path}"
    og_image = f"{config.SITE_URL}/{config.OG_IMAGE}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{esc(title)}</title>
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" type="application/atom+xml" title="OnScript daily feed" href="{esc(config.SITE_URL)}/feed.xml">
<link rel="icon" type="image/png" href="{root}favicon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="OnScript">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og_image)}">
<meta property="og:image:width" content="{config.OG_IMAGE_W}">
<meta property="og:image:height" content="{config.OG_IMAGE_H}">
<meta property="og:image:alt" content="OnScript — what each party said today, compressed to one voice, with receipts.">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site">
  <div class="brand"><a href="{root}index.html">OnScript</a></div>
  <div class="tag">This is what each party said today, compressed to one voice, with receipts.</div>
</header>
<nav class="top" aria-label="Primary">{nav}</nav>
<main id="main-content">
{body}
</main>
<footer class="site">
  <p>OnScript is a symmetric measurement instrument: identical pipeline, prompts, and thresholds for both
  parties, audited nightly in public. See the <a href="{root}methodology.html">Methodology</a>.
  Every distilled talking point links to at least three real source statements. No tracking, no external requests.</p>
</footer>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Inline SVG charts (no external libs)
# ---------------------------------------------------------------------------
_SPARK_COLOR = {"D": "#2b4c7e", "R": "#8a2f2f"}


def sparkline_svg(values, width: int = 120, height: int = 28, party: str | None = None) -> str:
    """Tiny inline SVG sparkline for a list of numeric values (max(D,R) per day). Colored by the
    phrase's leading party so a red-dominant phrase's trend isn't drawn in Democratic blue (§S7 D)."""
    color = _SPARK_COLOR.get(party or "", "#2b4c7e")
    vals = [max(0, int(v)) for v in values if v is not None]
    if len(vals) < 2:
        # Not enough points: draw a flat baseline so the cell isn't empty.
        return (
            f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img"><title>Phrase trend</title><desc>No trend series is available.</desc>'
            f'<line x1="1" y1="{height-3}" x2="{width-1}" y2="{height-3}" stroke="#ccc" stroke-width="1"/></svg>'
        )
    vmax = max(vals) or 1
    n = len(vals)
    pad = 2
    innerw = width - 2 * pad
    innerh = height - 2 * pad
    pts = []
    for i, v in enumerate(vals):
        x = pad + (innerw * i / (n - 1))
        y = pad + innerh - (innerh * v / vmax)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    lastx, lasty = pts[-1].split(",")
    return (
        f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img"><title>Phrase trend</title><desc>{n} observations; peak {vmax} members.</desc>'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>'
        f'<circle cx="{lastx}" cy="{lasty}" r="1.8" fill="{color}"/></svg>'
    )


def curve_svg(series, width: int = 900, height: int = 260) -> str:
    """Larger adoption-curve line chart: D and R series over time with axes,
    gridlines, a peak marker, and sampled date labels on the x-axis.

    ``series`` is the chronological list of {"day":..,"D":..,"R":..,"I":..}.
    """
    rows = [r for r in (series or []) if isinstance(r, dict) and r.get("day")]
    if len(rows) < 2:
        return '<p class="faint">Not enough data points to plot an adoption curve.</p>'

    left, right, top, bottom = 44, 14, 14, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(rows)

    d_vals = [max(0, int(r.get("D") or 0)) for r in rows]
    r_vals = [max(0, int(r.get("R") or 0)) for r in rows]
    vmax = max(d_vals + r_vals + [1])

    def x_of(i):
        return left + (plot_w * i / (n - 1))

    def y_of(v):
        return top + plot_h - (plot_h * v / vmax)

    def poly_for(vals):
        return " ".join(f"{x_of(i):.1f},{y_of(v):.1f}" for i, v in enumerate(vals))

    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" preserveAspectRatio="xMinYMin meet" style="min-width:{width}px">'
        '<title>Phrase adoption curve</title>'
        f'<desc>Democrats peak at {max(d_vals or [0])} member'
        f'{"" if max(d_vals or [0]) == 1 else "s"}; Republicans peak at '
        f'{max(r_vals or [0])} member{"" if max(r_vals or [0]) == 1 else "s"}, from '
        f'{esc(rows[0].get("day"))} through '
        f'{esc(rows[-1].get("day"))}.</desc>'
    ]
    # y gridlines + labels (0, mid, max)
    for frac in (0.0, 0.5, 1.0):
        yv = vmax * frac
        yy = y_of(yv)
        parts.append(
            f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left-6}" y="{yy+4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#8a8a8a">{int(round(yv))}</text>'
        )
    # axes
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#ccc" stroke-width="1"/>')
    parts.append(
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#ccc" stroke-width="1"/>'
    )
    # R then D so D (usually the mover) sits on top
    parts.append(
        f'<polyline fill="none" stroke="#8a2f2f" stroke-width="1.8" '
        f'stroke-linejoin="round" points="{poly_for(r_vals)}"/>'
    )
    parts.append(
        f'<polyline fill="none" stroke="#2b4c7e" stroke-width="2" '
        f'stroke-linejoin="round" points="{poly_for(d_vals)}"/>'
    )
    # peak marker on the higher-of-the-two series
    combined = [max(a, b) for a, b in zip(d_vals, r_vals)]
    peak_i = combined.index(max(combined))
    peak_v = combined[peak_i]
    px, py = x_of(peak_i), y_of(peak_v)
    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="#1a1a1a"/>')
    label = f"peak {peak_v} · {esc(rows[peak_i].get('day'))}"
    anchor = "end" if px > width * 0.7 else "start"
    dx = -6 if anchor == "end" else 6
    parts.append(
        f'<text x="{px+dx:.1f}" y="{py-6:.1f}" text-anchor="{anchor}" '
        f'font-size="11" fill="#1a1a1a">{label}</text>'
    )
    # sampled x-axis date labels (~5 across)
    n_labels = min(5, n)
    seen = set()
    for k in range(n_labels):
        i = round((n - 1) * k / (n_labels - 1)) if n_labels > 1 else 0
        if i in seen:
            continue
        seen.add(i)
        xx = x_of(i)
        anchor = "start" if k == 0 else ("end" if k == n_labels - 1 else "middle")
        parts.append(
            f'<text x="{xx:.1f}" y="{top+plot_h+16:.1f}" text-anchor="{anchor}" '
            f'font-size="11" fill="#8a8a8a">{esc(rows[i].get("day"))}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Data discovery
# ---------------------------------------------------------------------------
def all_day_files():
    """Return sorted list of (day_str, dict) for every days/*.json file."""
    ddir = DERIVED / "days"
    out = []
    if not ddir.exists():
        return out
    for p in sorted(ddir.glob("*.json")):
        data = _load_json(p)
        if isinstance(data, dict) and data.get("day"):
            out.append((data["day"], data))
    out.sort(key=lambda t: t[0])
    return out


def phrase_page_slugs():
    """Set of slugs that have a phrases/<slug>.json page (so we only link real pages)."""
    pdir = DERIVED / "phrases"
    slugs = set()
    if pdir.exists():
        for p in pdir.glob("*.json"):
            if p.stem != "top":
                slugs.add(p.stem)
    return slugs


def has_daily_lines(day_data) -> bool:
    dl = day_data.get("daily_lines")
    return isinstance(dl, dict) and any(isinstance(dl.get(p), dict) for p in ("D", "R"))


def _atom_timestamp(day_data: dict) -> str:
    """A stable Atom timestamp sourced only from the day artifact's code-computed date."""
    day = str((day_data or {}).get("day") or "")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return "1970-01-01T00:00:00Z"
    return f"{day}T00:00:00Z"


def atom_feed(rendered: list[tuple[str, dict]], limit: int = 30) -> str:
    """Deterministic Atom feed: dates and aggregate phrase counts only, never authored prose."""
    entries = []
    selected = list(reversed(rendered[-limit:]))
    for day, data in selected:
        rows, _ = privacy.filter_rows(data.get("top_synchronized") or [])
        counts = {p: sum(1 for row in rows if (row or {}).get("party") == p)
                  for p in config.COMPOSITE_PARTIES}
        url = f"{config.SITE_URL}/day/{day}.html"
        summary = (f"Democrats: {counts.get('D', 0)} synchronized phrases; "
                   f"Republicans: {counts.get('R', 0)} synchronized phrases.")
        entries.append(
            "<entry>"
            f"<title>OnScript — {esc(day)}</title><id>{esc(url)}</id>"
            f'<link href="{esc(url)}"/><updated>{_atom_timestamp(data)}</updated>'
            f"<summary>{esc(summary)}</summary></entry>"
        )
    updated = _atom_timestamp(selected[0][1]) if selected else "1970-01-01T00:00:00Z"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>OnScript daily readings</title>'
        f"<id>{esc(config.SITE_URL)}/feed.xml</id>"
        f'<link href="{esc(config.SITE_URL)}/feed.xml" rel="self"/>'
        f'<link href="{esc(config.SITE_URL)}/"/>'
        f"<updated>{updated}</updated>{''.join(entries)}</feed>\n"
    )


def sitemap(page_paths: list[str]) -> str:
    """Every and only the HTML paths emitted by this build, in deterministic order."""
    urls = []
    for path in sorted(set(page_paths)):
        url = f"{config.SITE_URL}/" if path == "index.html" else f"{config.SITE_URL}/{path}"
        urls.append(f"<url><loc>{esc(url)}</loc></url>")
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{''.join(urls)}</urlset>\n"
    )


# ---------------------------------------------------------------------------
# Honesty banner
# ---------------------------------------------------------------------------
# Genuine LLM-voice generators — the ONLY values that mean the composite came from the language
# model. Any other generator (dry_run, deterministic, or a legacy 'sonnet_batch' label) is a
# template stub: the honesty banner discloses it as "not a language model". The real Sonnet voice
# is not yet wired (§Session-5 HIGH-2) — until it is, no day carries one of these, so every day is
# honestly flagged as a stub. When the live voice IS wired, its generator label is added here in the
# SAME commit that wires it.
PRODUCTION_GENERATORS = {"llm", "production", "sonnet_direct"}
_STUB_VOICE_MSG = {
    "dry_run": "dry-run stub",
    "deterministic": "deterministic template (not the language model)",
}


def privacy_correct_line(party: str, day_data) -> tuple[dict | None, list, str]:
    """RENDER-TIME Article XIII correction for one party-day. Returns (line, talking_points, state)
    where state is "clean" | "recomposed" | "withheld".

    Why render-time and not a one-time JSON rewrite: a rewrite is undone by the next cloud run that
    rebuilds the day, and protects no future day. Render-time is idempotent and re-applies forever —
    the same argument _voice_flags already makes for correcting historical pages without re-assembly.
    It is also the ONLY option here: local state ends 2026-07-09, so the affected days cannot be
    rebuilt locally, and a cloud re-assemble would call the paid voice.

    The re-composition is honest rather than cosmetic because distill._compose_dry(stats) takes STATS
    AND NOTHING ELSE — no ledger, no network, $0 — so "generator: deterministic" is LITERALLY TRUE:
    it is the same function the pipeline itself uses, and this system's established trusted
    degradation path (distill.py already falls Sonnet -> deterministic on verify failure).

    The rejected alternative — regex-excising the offending clause — would yield text Sonnet never
    wrote, still badged sonnet_direct/claude-sonnet-5: fabrication-by-editing."""
    dl = day_data.get("daily_lines") or {}
    line = dl.get(party) if isinstance(dl, dict) else None
    tps_all = (day_data.get("talking_points") or {}).get(party, []) \
        if isinstance(day_data.get("talking_points"), dict) else []
    tps, tps_dropped = privacy.filter_talking_points(tps_all)
    # docs/19 §4b — the render-time ADMISSION floor rides HERE (alongside privacy) so the composite is
    # re-derived from the SAME surviving set: drop connective/attribution scaffold talking points, so an
    # already-published day's PROSE never narrates a phrase whose receipt was removed (the 07-17 D line
    # narrated three scaffold keys that the receipts now drop). New days are gated at generation
    # (run_assemble); this is the retroactive half, on the same trusted deterministic degradation path.
    _n_tp = len(tps)
    tps = [t for t in tps if not boilerplate.is_scaffold_key((t or {}).get("label", ""))]
    adm_dropped = len(tps) < _n_tp
    if not isinstance(line, dict):
        return line, tps, "clean"

    composite = line.get("composite") or ""
    stats_raw = line.get("stats")
    stats, stats_dropped = privacy.filter_stats(stats_raw)
    if isinstance(stats, dict):
        _s_all = stats.get("talking_points") or []
        _s_kept = [t for t in _s_all if not boilerplate.is_scaffold_key((t or {}).get("label", ""))]
        if len(_s_kept) < len(_s_all):
            stats = {**stats, "talking_points": _s_kept}
            adm_dropped = True
    priv_dropped = tps_dropped or stats_dropped or privacy.is_suppressed(composite)
    if not (priv_dropped or adm_dropped):
        return line, tps, "clean"

    # Something in this line must not publish — it names a private individual (privacy) and/or a
    # talking point was bound by connective/attribution scaffolding (docs/19 §4b). Either way, re-derive
    # the composite from the FILTERED stats so the prose matches the surviving receipts.
    if not isinstance(stats, dict):
        return None, tps, "withheld"           # no stats to recompose from -> withhold, never guess
    has_quote = any((t or {}).get("quote") for t in (stats.get("talking_points") or []))
    top = stats.get("top_phrase")
    if not has_quote and not (isinstance(top, dict) and top.get("text")):
        # Everything measurable was suppressed. Withholding is RIGHT here: _compose_dry would emit
        # "No phrase was shared by 3 or more of us today" — a fabricated silence FINDING manufactured
        # by our own privacy fix (Art. II). allow_absence_claim=False stops that line; withholding
        # stops the empty shell it would leave.
        return None, tps, "withheld"

    text = distill._quiet_dry(stats) if line.get("quiet") \
        else distill._compose_dry(stats, allow_absence_claim=False)

    # The STORED verifier block describes the SONNET text; rendering "verifier: passed" over a
    # swapped composite would attest text that is no longer published. Re-verify what we publish.
    groundable = [f.get("text") for t in tps for f in (t.get("fragments") or [])
                  if isinstance(f, dict) and f.get("text")]
    ok, _reasons = verify.verify_daily_line({"composite": text}, json.dumps(stats, ensure_ascii=False),
                                            groundable, stats=stats)
    if not ok:
        return None, tps, "withheld"
    out = dict(line)
    out["composite"] = text
    out["generator"] = "deterministic"      # literally true: distill's own composer produced this
    out.pop("model", None)                  # a stale 'claude-sonnet-5' would falsely claim authorship
    out["verifier"] = {"checked": True, "passed": True, "reasons": []}
    out["_privacy_corrected"] = priv_dropped
    out["_admission_corrected"] = adm_dropped
    # A privacy drop is the stronger disclosure and owns the banner; an ADMISSION-only correction is a
    # distinct reason ("readmitted") so the banner never claims a private name was removed when it was a
    # scaffold key. Both relabel generator="deterministic", so the honest "deterministic template" note
    # fires either way.
    return out, tps, ("recomposed" if priv_dropped else "readmitted")


def privacy_states(day_data) -> dict:
    """{party: "clean"|"recomposed"|"withheld"|"readmitted"} for the day — shared by the banner and the
    panels so a corrected composite can never render under an uncorrected banner. "recomposed"/"withheld"
    are Art. XIII privacy; "readmitted" is a docs/19 §4b scaffold-key correction (deterministic re-compose)."""
    return {p: privacy_correct_line(p, day_data)[2] for p in ("D", "R")}


def honesty_state(day_data, symmetry):
    """Return (needs_banner, message, has_stub_voice). has_stub_voice is True when EITHER party's
    Daily Line was composed by a non-LLM template (dry_run / deterministic / any legacy non-production
    generator) — so the banner discloses "not a language model". It is False for a genuine LLM day
    that merely carries a transparency flag (quiet / fallback / degraded)."""
    flags = []
    has_stub_voice = False
    dl = day_data.get("daily_lines")
    if isinstance(dl, dict):
        for p in ("D", "R"):
            party = dl.get(p)
            if not isinstance(party, dict):
                continue
            gen = party.get("generator")
            if gen and gen not in PRODUCTION_GENERATORS:
                has_stub_voice = True
                label = _STUB_VOICE_MSG.get(gen, f"template stub (generator={esc(gen)})")
                flags.append(f"{PARTY_NAME[p]}' Daily Line is a <strong>{label}</strong>")
            if party.get("quiet"):
                flags.append(f"{PARTY_NAME[p]}' line is a <strong>quiet-day</strong> line (low volume)")
            if party.get("fallback"):
                flags.append(f"{PARTY_NAME[p]}' line used a <strong>fallback</strong>")
            ver = party.get("verifier") or {}
            if ver.get("checked") and ver.get("passed") is False:
                flags.append(f"{PARTY_NAME[p]}' line <strong>failed the citation verifier</strong>")
    if isinstance(symmetry, dict) and symmetry.get("degraded"):
        flags.append("today's run is <strong>degraded</strong> (see the symmetry audit)")
    if not flags:
        return False, "", has_stub_voice
    seen = []
    for f in flags:
        if f not in seen:
            seen.append(f)
    return True, "; ".join(seen), has_stub_voice


def banner_html(day_data, symmetry, depth: int = 1) -> str:
    need, msg, has_stub_voice = honesty_state(day_data, symmetry)
    # Art. XIII: a suppression-corrected day gets its OWN branch and its own reason. The
    # has_stub_voice tail below says the phrasing is "a placeholder until the live model voice is
    # wired in" — that copy is stale (the voice went live in Session 6b) and on a corrected day it
    # would state a FALSE REASON (voice not built) for what is actually privacy protection.
    pstates = privacy_states(day_data)
    corrected = [p for p, s in pstates.items() if s == "recomposed"]
    withheld = [p for p, s in pstates.items() if s == "withheld"]
    readmitted = [p for p, s in pstates.items() if s == "readmitted"]   # docs/19 §4b scaffold correction
    if corrected or withheld or readmitted:
        bits = []
        if corrected:
            bits.append(
                f"{' and '.join(PARTY_NAME[p] for p in sorted(corrected))}' Daily Line was "
                f"<strong>re-composed by the deterministic composer</strong> because the model&rsquo;s "
                f"version named a private individual")
        if readmitted:
            # Its OWN honest reason — never the stale "voice not wired" tail, and never the privacy claim.
            bits.append(
                f"{' and '.join(PARTY_NAME[p] for p in sorted(readmitted))}' Daily Line was "
                f"<strong>re-composed by the deterministic composer</strong> because a talking point was "
                f"bound by connective or attribution phrasing rather than a shared message")
        if withheld:
            bits.append(
                f"{' and '.join(PARTY_NAME[p] for p in sorted(withheld))}' Daily Line is "
                f"<strong>withheld under the privacy floor</strong>")
        # depth-correct: this banner also renders on index.html (depth 0), where "../" would 404.
        tail = (" Every number is the day&rsquo;s real measurement; nothing about the instrument or its "
                "thresholds changed, and the same rule is applied identically to both parties. "
                f'See the <a href="{"../" * depth}methodology.html">privacy floor</a> and the '
                "corrections log.")
        extra = f"{msg}; " if need else ""
        return f'<div class="banner">Honesty note: {extra}{"; ".join(bits)}.{tail}</div>'
    if not need:
        return ""
    if has_stub_voice:
        tail = (" The composite voice for any line above marked a stub/template is <strong>not a "
                "language model</strong> — it is composed deterministically from the day's measured "
                "statistics. The numbers, quotes, and receipts are real and verified; the phrasing is "
                "a placeholder until the live model voice is wired in.")
    else:
        # Genuine LLM voice, just a transparency flag (quiet / fallback / degraded).
        tail = " Numbers, quotes, and receipts are real and verified; the note above is a transparency flag."
    return f'<div class="banner">Honesty note: {msg}.{tail}</div>'


def _voice_flags(line: dict) -> list[str]:
    """Honest per-line voice provenance for the metaflags line, at RENDER time (so it corrects EVERY
    day page — including historical ones written before Session 5 — without re-assembly). A
    non-production generator (dry_run, deterministic, or the legacy 'sonnet_batch' mislabel) is
    deterministic TEMPLATE output; render it uniformly as such and SUPPRESS the stored model id — a
    stale 'claude-sonnet-5' would falsely claim language-model authorship and contradict the honesty
    banner. Only a genuine production generator (§PRODUCTION_GENERATORS) shows its real model."""
    gen = line.get("generator")
    if not gen:
        return []
    if gen in PRODUCTION_GENERATORS:
        out = [f"generator: {esc(gen)}"]
        model = line.get("model")
        if model:
            out.append(f"model: {esc(model)}")
        return out
    return ["voice: deterministic template (not a language model)"]


# ---------------------------------------------------------------------------
# Receipts strip + Daily Line panels
# ---------------------------------------------------------------------------
def _safe_http_url(url) -> str:
    """Return url only if it is an http(s) URL, else "". The corpus is external/mirrorable and thus
    poisonable — a citation with a javascript:/data: scheme would become a clickable XSS sink on a
    site that advertises zero JS. Whitelist the scheme before ever emitting an href. §Session-5."""
    u = str(url or "").strip()
    lo = u.lower()
    return u if (lo.startswith("http://") or lo.startswith("https://")) else ""


def _wayback_url(url: str, date: str | None) -> str:
    """A Wayback Machine capture link for a cited release. Member sites migrate CMSs and delete
    releases, so the live .gov link rots; the Wayback capture (nearest to the ingest date) survives.
    The full text is ALSO preserved in our immutable data release — this is the reader-facing fallback.
    §Session-8 (link rot)."""
    ts = "".join(ch for ch in str(date or "") if ch.isdigit())[:8] or "2"
    return f"https://web.archive.org/web/{ts}/{url}"


def _key_pattern(key: str) -> str:
    """A whitespace/apostrophe/punctuation-tolerant, case-insensitive regex for a cluster key's token
    sequence, so it matches the key however a source rendered it ('Trump administration's' vs the token
    key, or 'National Security, Department' where the tokenizer dropped the comma). Punctuation-tolerant
    between tokens so the highlight agrees with boilerplate.contains_gram (§4b P3)."""
    parts = []
    for t in (key or "").split():
        t = re.sub(r"['’]", "\x00", t)                 # protect apostrophes from re.escape
        parts.append(re.escape(t).replace("\x00", "['’]"))
    return r"[\s,;:.–—-]+".join(parts)        # space OR a token separator the tokenizer dropped


def _mark_key(quote: str, key: str) -> tuple[str, bool]:
    """Escape a receipt quote and wrap the cluster key where it appears, so a reader sees exactly the
    span that licensed the row (docs/19 §4b req 3). Returns (html, key_present). Matched on the RAW
    quote (then escaped per fragment) so the highlight survives casing/whitespace differences; if the
    key does not appear in this quote nothing is marked — an honest 'no false highlight'."""
    q = quote or ""
    if not key:
        return esc(q), False
    m = re.search(_key_pattern(key), q, flags=re.IGNORECASE)
    if not m:
        return esc(q), False
    return (esc(q[:m.start()]) + f'<mark class="keyspan">{esc(m.group(0))}</mark>' + esc(q[m.end():]), True)


def _testchip(label: str, state) -> str:
    """One receipt-test chip (docs/19 §4b req 3). state True -> passing (✓), False -> failing (✗),
    None -> a neutral count (no claim of pass/fail, e.g. how many shown quotes carry the phrase)."""
    cls = {True: "ok", False: "no", None: "info"}[state]
    mark = {True: "✓ ", False: "✗ ", None: ""}[state]
    return f'<span class="tchip {cls}">{mark}{esc(label)}</span>'


def receipts_strip(party: str, talking_points: list, caucus: int | None = None) -> str:
    """Build the receipts strip from a party's talking_points (the visual signature). `caucus` is the
    party's caucus size, so every count travels with its denominator ("10 of 263 · 3.8%")."""
    tps = [tp for tp in (talking_points or []) if isinstance(tp, dict)]
    if not tps:
        return ""
    rows = []
    for tp in tps[:4]:
        count = tp.get("member_count")
        topics = tp.get("topics") or []
        topics_html = ""
        if topics:
            topics_html = (
                '<div class="rtopics">'
                + " · ".join(topic_label(t) for t in topics[:3])
                + "</div>"
            )
        # "carried", not "said": a release can quote third parties (award presenters, bill text), so
        # the exact claim is that the phrase appeared IN these members' statements. Denominator travels
        # with the count so a peak never reads as typical. §Session-8.
        if isinstance(count, int):
            frac = (f' <span class="faint">&middot; {esc(count)} of {esc(caucus)} ({round(100 * count / caucus, 1)}%)</span>'
                    if isinstance(caucus, int) and caucus > 0 else "")
            count_html = f'<span class="rcount">{esc(count)} members&rsquo;</span> statements carried{frac}'
        else:
            count_html = "members&rsquo; statements carried"
        # Citation-or-silence made VISIBLE (Art. XII), quote BOUND to source (§Session-7 C-ii): each
        # row is one member's OWN verbatim quote next to their name and their .gov link, so a reader
        # can click and confirm that exact quote — never a decoupled quote/citation pair.
        key = tp.get("label", "")
        cites = [c for c in (tp.get("citations") or []) if isinstance(c, dict)]
        lis = []
        span_present = urls_present = 0
        for c in cites[:3]:
            nm = esc(c.get("member"))
            pp, st = c.get("party"), c.get("state")
            suffix = f" ({esc(pp)}-{esc(st)})" if pp and st else (f" ({esc(st)})" if st else "")
            url = _safe_http_url(c.get("url"))
            if url:
                # source + an archival fallback (Wayback), so a rotted .gov link never dead-ends a
                # receipt; the full text is also in our immutable data release. §Session-8.
                urls_present += 1
                src = (f'<a href="{esc(url)}" rel="nofollow noopener">source</a> · '
                       f'<a href="{esc(_wayback_url(url, c.get("date")))}" rel="nofollow noopener">archived</a>')
            else:
                src = '<span class="faint">source</span>'
            q = c.get("quote")
            # docs/19 §4b req 3 — highlight the exact key span in the quote, so a reader sees precisely
            # what licensed the row. A quote may be a DIFFERENT attributable fragment of the same
            # statement, so absence of the span in this quote is honest, not a failure.
            if q:
                qh, present = _mark_key(q, key)
                span_present += 1 if present else 0
                qhtml = f'<div class="quote">{qh}</div>'
            else:
                qhtml = ""
            lis.append(
                f'<li>{qhtml}<div class="citemeta">{nm}{suffix} '
                f'<span class="faint">· {esc(c.get("date"))} ·</span> {src}</div></li>'
            )
        cites_html = ('<ul class="cites">' + "".join(lis) + "</ul>") if lis else ""
        # docs/19 §4b req 3 — a per-test breakdown, not one opaque "verified" badge: the key is a
        # message (admissible), >=SYNC_MIN distinct families carry it, each shown receipt links its
        # source, and the highlighted phrase is shown where a quote carries it. A reader sees which
        # test each row rests on rather than trusting an aggregate.
        shown = len(lis)
        admissible = not boilerplate.is_scaffold_key(key)
        families_ok = (count >= config.SYNC_MIN_MEMBERS) if isinstance(count, int) else None
        sourced_ok = (urls_present == shown) if shown else None
        # docs/19 §4b req 3 (2nd pass) — the aggregate is a DERIVED CONJUNCTION: it is "verified" only
        # when every check is independently computed AND passes; ANY failed OR unavailable (None) check
        # makes it UNAVAILABLE, never a reduced-confidence "mostly verified". Then the per-test chips
        # below show exactly which test each row rests on — a reader never trusts an opaque badge.
        checks = [admissible, families_ok, sourced_ok]
        # Binary by design: "verified" iff every check passes; ANYTHING else (a failed OR an
        # unavailable check) is UNAVAILABLE — there is deliberately NO reduced-confidence middle state,
        # so the aggregate can never soft-pass. The per-test chips below show which check is at issue.
        agg = (_testchip("publication verified", True) if all(c is True for c in checks)
               else _testchip("verification unavailable", None))
        chips = [agg, _testchip("message key", admissible)]
        if isinstance(count, int):
            chips.append(_testchip(f"{count} families", families_ok))
        if shown:
            chips.append(_testchip(f"phrase shown {span_present}/{shown}", None))
            chips.append(_testchip(f"sourced {urls_present}/{shown}", sourced_ok))
        tests_html = f'<div class="rtests">{"".join(chips)}</div>'
        more_html = ""
        if isinstance(count, int) and count > len(lis) and lis:
            more_html = f'<div class="rmore"><small>showing {len(lis)} of {esc(count)} members</small></div>'
        # Fallback for historical days assembled before per-citation quotes existed: render the
        # verbatim fragment quotes so NO talking point ever renders empty receipts. §Session-7 (#7).
        if not lis:
            frags = [f for f in (tp.get("fragments") or []) if isinstance(f, dict) and f.get("text")]
            cites_html = "".join(f'<div class="quote">{esc(f.get("text"))}</div>' for f in frags[:2])
        rows.append(
            f'<div class="receipt"><div class="rhead">{count_html}</div>'
            f'{tests_html}{topics_html}{cites_html}{more_html}</div>'
        )
    return (
        '<div class="receipts"><div class="rlabel">Receipts</div>'
        + "".join(rows)
        + "</div>"
    )


def daily_line_panel(party: str, day_data, caucus: int | None = None) -> str:
    # Render-time correction, BEFORE anything is rendered: privacy_correct_line drops both suppressed
    # (Art. XIII) AND connective/attribution scaffold (docs/19 §4b) talking points, and re-derives the
    # composite from the surviving set so the PROSE never narrates a phrase whose receipt was removed.
    line, tps, pstate = privacy_correct_line(party, day_data)

    who = f'<div class="who">{esc(PARTY_NAME.get(party, party))}</div>'
    if pstate == "withheld":
        return (
            f'<div class="line {esc(party)}">{who}'
            f'<p class="composite muted">This Daily Line is <strong>withheld under the privacy '
            f'floor</strong>: the phrases it would have been composed from name a private '
            f'individual. OnScript measures elected officials&rsquo; public statements and never '
            f'publishes a private citizen as a data point. The underlying record of what members '
            f'said is retained unaltered; only this instrument&rsquo;s ranking of it is withheld.</p>'
            f'</div>'
        )
    if not isinstance(line, dict):
        return (
            f'<div class="line {esc(party)}">{who}'
            f'<p class="composite muted">No Daily Line was generated for this day. '
            f'The deterministic phrase engine still ran — see the synchronized phrases below.</p></div>'
        )
    composite = line.get("composite") or ""
    flags = []
    flags += _voice_flags(line)
    if line.get("quiet"):
        flags.append("quiet day")
    if line.get("fallback"):
        flags.append("fallback")
    ver = line.get("verifier") or {}
    if ver.get("checked"):
        flags.append("verifier: passed" if ver.get("passed") else "verifier: FAILED")
    flags_html = f'<div class="metaflags">{" · ".join(flags)}</div>' if flags else ""

    # In-card composite disclaimer (A3): a cropped screenshot of a single card must carry its own
    # "this is a composite, not a member quote" caption — the composite is machine-written; only the
    # quoted spans in the receipts are verbatim.
    cnote = ('<p class="cnote">A composite voice, machine-composed from the day&rsquo;s measured '
             'phrases. No member spoke these exact sentences; the quoted spans are verbatim (see receipts).</p>')

    # Zero-cluster honesty (A2): a party with statements but no published talking points has nothing
    # to cite — say so, so the "every talking point is citation-backed" promise is never contradicted
    # by a receipt-free card.
    body_tail = receipts_strip(party, tps, caucus=caucus)
    if not [t for t in (tps or []) if isinstance(t, dict)]:
        # "Nothing cleared the threshold" is a measured ABSENCE claim, and stating it when the list was
        # emptied by OUR OWN filter — privacy or the docs/19 §4b scaffold gate — is a fabricated silence
        # finding authored by the fix (Art. II). Each reason gets its own honest message.
        if pstate == "readmitted":
            body_tail = ('<p class="nocite">This day&rsquo;s talking points were bound by connective or '
                         'attribution phrasing rather than a shared message, and have been removed '
                         '&mdash; nothing to cite here. See the corrections log.</p>')
        elif pstate != "clean":     # privacy withheld / recomposed
            body_tail = ('<p class="nocite">Talking points for this day are withheld under the privacy '
                         'floor &mdash; nothing to cite here.</p>')
        else:
            body_tail = (f'<p class="nocite">No talking point cleared the {config.SYNC_MIN_MEMBERS}-member '
                         f'threshold today &mdash; nothing to cite.</p>')

    return (
        f'<div class="line {esc(party)}">{who}'
        f'<p class="composite">{esc(composite)}</p>'
        f'{cnote}'
        f'{flags_html}'
        f'{body_tail}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Top synchronized phrases table (with sparklines)
# ---------------------------------------------------------------------------
def _series_last_present(series, k=14):
    """Return the last k present-day rows (chronological) from a phrase series."""
    rows = [r for r in (series or []) if isinstance(r, dict) and r.get("day")]
    return rows[-k:]


def _nomenclature_chip(verdict) -> str:
    """docs/19 §2b — the display-time nomenclature marker. Rendered ONLY when a row carries a verdict,
    which happens ONLY when FEATURES["nomenclature_tags"] is on and nomenclature.tag() ran at render
    time. The tag NEVER deletes a row (docs/16 §7): it labels an official name so a reader can see that
    a bill title / committee name is not a coordinated message. Every tag cites the official record
    that licensed it."""
    if not isinstance(verdict, dict):
        return ""
    lane = verdict.get("lane")
    cite = verdict.get("cite") or ""
    if lane == "committee":
        label, cite_txt = "committee name", cite.split(":", 1)[-1]
    else:
        label, cite_txt = "official name", cite.upper()
    tip = (f"Official {'committee' if lane == 'committee' else 'bill'} name, not a coordinated "
           f"message — cites {cite} (nomenclature ratio {verdict.get('ratio')}).")
    body = esc(label) + (f" · {esc(cite_txt)}" if cite_txt else "")
    return f' <span class="nomtag" title="{esc(tip)}">{body}</span>'


def sync_table(day_data, slugs_with_pages, depth: int) -> str:
    ts = [r for r in (day_data.get("top_synchronized") or []) if isinstance(r, dict)]
    # Re-apply the CURRENT near-dup collapse at render time, so already-built (historical) day pages
    # reflect the latest merge rules without re-running the engine — the display-time refresh pattern.
    ts = build.collapse_and_rank(ts, k=20)
    # docs/19 §2b — nomenclature display-time tag, DARK until FEATURES["nomenclature_tags"]. Render-time
    # only + flag-gated: with the flag OFF this is a no-op and the page is byte-identical (docs/19 §3.4
    # golden); with it ON, every historical page gains the tag with no ledger rebuild. Tag COPIES (never
    # the caller's stored rows) so a dark render can never see a stale key from a live one, and gate the
    # chip on the same flag — belt and suspenders on "flag off => zero bytes". tag() NEVER drops a row.
    show_nom = config.feature_on("nomenclature_tags") and bool(day_data.get("day"))
    if show_nom:
        ts = [dict(r) for r in ts]
        nomenclature.tag(ts, congress=util.congress_for_date(day_data["day"]))
    if not ts:
        return '<p class="muted">No synchronized phrases recorded for this day.</p>'
    root = "../" * depth
    head = (
        "<tr><th>Phrase</th><th>Party</th><th class='num'>Peak</th>"
        "<th class='num'>D</th><th class='num'>R</th><th class='num'>Velocity</th>"
        "<th>First seen</th><th>14-day trend</th></tr>"
    )
    body = []
    for r in ts[:20]:
        ngram = r.get("ngram", "")
        slug = r.get("slug", "")
        party = r.get("party", "")
        counts = r.get("counts") or {}
        peak = r.get("day_peak")
        vel = r.get("velocity")
        fs = r.get("first_seen") or {}
        fs_date = fs.get("date", "")

        # sparkline from the row's own 14-day series (carried by build.top_synchronized), colored by
        # the phrase's leading party — EVERY row gets a trend, not just phrases with a detail page.
        series = [int(v) for v in (r.get("series") or []) if v is not None]
        spark = sparkline_svg(series, party=party) if len(series) >= 2 else '<span class="faint">—</span>'

        if slug in slugs_with_pages:
            phrase_cell = f'<a href="{root}phrases/{esc(slug)}.html">{esc(ngram)}</a>'
        else:
            phrase_cell = esc(ngram)
        if show_nom:
            phrase_cell += _nomenclature_chip(r.get("nomenclature"))

        vel_txt = f"{vel:.1f}" if isinstance(vel, (int, float)) else esc(vel)
        body.append(
            f"<tr><td>{phrase_cell}</td>"
            f'<td><span class="pill {esc(party)}">{esc(party)}</span></td>'
            f'<td class="num">{esc(peak)}</td>'
            f'<td class="num">{esc(counts.get("D", 0))}</td>'
            f'<td class="num">{esc(counts.get("R", 0))}</td>'
            f'<td class="num">{esc(vel_txt)}</td>'
            f'<td class="muted"><small>{esc(fs_date)}</small></td>'
            f"<td>{spark}</td></tr>"
        )
    return (
        '<div class="scroll"><table>'
        f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"
    )


# ---------------------------------------------------------------------------
# The Today / per-day view (shared)
# ---------------------------------------------------------------------------
def phrase_search_index() -> list[dict]:
    """The client-side search index: one compact row per phrase that HAS a page.

    Scoped to real pages on purpose. The ledger holds ~2.8M n-grams and cannot be shipped to a
    browser; every row here resolves to a page a reader can actually open, so the search can never
    offer a result that 404s. Keys are one letter because this ships inside the HTML."""
    rows = []
    pdir = DERIVED / "phrases"
    if not pdir.exists():
        return rows
    for p in sorted(pdir.glob("*.json")):
        if p.stem == "top":
            continue
        d = _load_json(p)
        # Mirrors the phrase-page loop's guard below. A malformed phrase JSON (a list, a bare
        # string) must skip ONE row, never crash build_site: the page loop already fails soft, so
        # without this the index is the only place a single bad file takes the whole site down.
        if not isinstance(d, dict):
            continue
        ngram = d.get("ngram")
        if not ngram:
            continue
        # Art. XIII: dark today (FEATURES["phrase_search"]), but this globs the same JSONs and would
        # ship a client-side name-lookup payload the instant the flag flips.
        if privacy.is_suppressed(ngram):
            continue
        window = public_phrase_window(d)
        if not window["series"]:
            continue
        rows.append({"q": ngram, "s": d.get("slug") or p.stem,
                     "p": _num(window["peak_units"]), "f": window["first_day"]})
    rows.sort(key=lambda r: (-r["p"], r["q"]))
    return rows


def phrase_search_body(rows: list[dict]) -> str:
    """Phrase search (1.7b) — dark until FEATURES["phrase_search"].

    The site is STATIC (no server, no query endpoint), so search is a prebuilt index filtered in the
    browser. The index is embedded rather than fetched: it works with the page, needs no second
    request, and cannot half-load.

    Two safety rules, both load-bearing because every phrase is UNTRUSTED text lifted from a press
    release: the JSON is embedded with "<" escaped so no phrase can close the <script> element early,
    and results are built with textContent/createElement — never innerHTML — so a phrase is always
    rendered as text and never as markup."""
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    return f"""<h1>Phrase search</h1>
<p class="subhead">Search every phrase with a tracked page &mdash; {len(rows)} of them. Each result opens
that phrase&rsquo;s public-window adoption curve and first record; where at least three distinct offices
can be grounded, the page also carries peak-day source receipts.</p>
<p class="muted"><small>This searches phrases we have built pages for, not the full n-gram ledger:
a phrase becomes trackable once at least three members of one party used it on a day. So a phrase
being absent here means it never cleared that bar &mdash; not that nobody ever said it.</small></p>
<input id="q" type="search" placeholder="Try: rule of law" autocomplete="off"
       style="width:100%; padding:10px 12px; font-size:16px; border:1px solid var(--line); border-radius:6px; background:transparent; color:var(--ink)">
<p class="muted" id="count" style="margin-top:10px"></p>
<div id="results"></div>
<script id="phrase-index" type="application/json">{payload}</script>
<script>
(function () {{
  var rows = JSON.parse(document.getElementById("phrase-index").textContent);
  var q = document.getElementById("q"), out = document.getElementById("results"), cnt = document.getElementById("count");
  var LIMIT = 50;
  function render() {{
    var term = q.value.trim().toLowerCase();
    var hits = term ? rows.filter(function (r) {{ return r.q.indexOf(term) !== -1; }}) : rows;
    out.textContent = "";
    cnt.textContent = term
      ? hits.length + " phrase" + (hits.length === 1 ? "" : "s") + " matching \\u201C" + term + "\\u201D"
        + (hits.length > LIMIT ? " \\u00B7 showing the first " + LIMIT : "")
      : rows.length + " tracked phrases \\u00B7 showing the " + Math.min(LIMIT, rows.length) + " most synchronized";
    hits.slice(0, LIMIT).forEach(function (r) {{
      var d = document.createElement("div");
      d.className = "receipt";
      var a = document.createElement("a");
      a.href = r.s + ".html";
      a.textContent = r.q;                      // textContent: a phrase is text, never markup
      var meta = document.createElement("div");
      meta.className = "rhead";
      meta.textContent = "peak " + r.p + " members" + (r.f ? " \\u00B7 first seen " + r.f : "");
      d.appendChild(a); d.appendChild(meta); out.appendChild(d);
    }});
  }}
  q.addEventListener("input", render);
  render();
}})();
</script>"""


def duet_panel(day_data, depth: int = 0) -> str:
    """1.7a The Duet — the same phrase, both parties, the same day, side by side.

    Renders NOTHING unless FEATURES["duet"] is on (build dark / release by gate). Two rules the markup
    enforces:
      * the PHRASE is printed unquoted — it is a code-computed ledger n-gram, and quoting it would
        attribute a computed string to a member (HIGH-1; the same rule P2 v1.2 carries for the voice);
      * each side's sentence is that member's OWN verbatim words, next to their name and .gov link, so
        a reader can click through and confirm it.

    We describe what the phrase IS (both parties used it) and never what it MEANS. The exhibit's whole
    argument is the two columns; any adjective we added would be us, not the record."""
    if not config.feature_on("duet"):
        return ""
    duets = [d for d in (day_data.get("duets") or []) if isinstance(d, dict)]
    # Art. XIII, at SENTENCE level and not just on the phrase: a duet renders each member's whole
    # quoted sentence, which can carry a private name the duet phrase itself does not. Drop the whole
    # duet rather than a side — a one-sided duet is not a duet, and dropping one side's receipts
    # would publish an asymmetric cross-party claim.
    duets = [d for d in duets if not privacy.is_suppressed(d.get("ngram") or "")
             and not any(privacy.is_suppressed((c or {}).get("quote") or "")
                         for p in ("D", "R")
                         for c in ((d.get("sides") or {}).get(p) or []) if isinstance(c, dict))]
    if not duets:
        return ""
    out = ["<h2>The Duet</h2>",
           '<p class="subhead">Phrases that three or more members of <em>each</em> party used on this '
           'day &mdash; the same words, from both sides. Each quote is that member&rsquo;s own '
           'sentence; read them next to each other and draw your own conclusion.</p>']
    for d in duets:
        counts = d.get("counts") or {}
        out.append('<div class="duet">')
        out.append(
            f'<div class="duet-head"><span class="duet-phrase">{esc(d.get("ngram"))}</span>'
            f'<span class="faint">&nbsp;&middot;&nbsp;{esc(_num(counts.get("D")))} D &amp; '
            f'{esc(_num(counts.get("R")))} R members</span></div>'
        )
        out.append('<div class="lines">')
        for party in ("D", "R"):
            cites = [c for c in ((d.get("sides") or {}).get(party) or []) if isinstance(c, dict)]
            col = [f'<div class="line {party}"><div class="rlabel"><span class="pill {party}">{party}</span></div>']
            for c in cites:
                nm = esc(c.get("member"))
                pp, st = c.get("party"), c.get("state")
                suffix = f" ({esc(pp)}-{esc(st)})" if pp and st else ""
                url = _safe_http_url(c.get("url"))
                src = (f' &middot; <a href="{esc(url)}" rel="nofollow noopener">source</a>'
                       f' &middot; <a href="{esc(_wayback_url(url, c.get("date")))}" rel="nofollow noopener">archived</a>'
                       if url else "")
                col.append(f'<div class="receipt"><div class="rhead">{nm}{suffix}{src}</div>'
                           f'<div class="quote">{esc(c.get("quote"))}</div></div>')
            col.append("</div>")
            out.append("".join(col))
        out.append("</div></div>")
    return "".join(out)


def _party_column(party, rows, slugs_with_pages, depth, caucus_size) -> str:
    """One party's column for the per-party synchronized-phrase display (R3). Each row is that party's
    OWN member count for the phrase, with the caucus denominator so a raw count never reads as a rate."""
    root = "../" * depth
    lis = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        ngram, slug = r.get("ngram", ""), r.get("slug", "")
        cnt = (r.get("counts") or {}).get(party, 0)
        denom = (f' <span class="faint">of {caucus_size} ({round(100 * cnt / caucus_size, 1)}%)</span>'
                 if isinstance(caucus_size, int) and caucus_size else "")
        cell = (f'<a href="{root}phrases/{esc(slug)}.html">{esc(ngram)}</a>'
                if slug in slugs_with_pages else esc(ngram))
        series = [int(v) for v in (r.get("series") or []) if v is not None]
        spark = sparkline_svg(series, party=party) if len(series) >= 2 else ""
        lis.append(f'<li><span class="pcount">{esc(cnt)}</span>{denom} {cell} {spark}</li>')
    body = "".join(lis) or '<li class="muted">No phrase reached the threshold for this party today.</li>'
    return (f'<div class="pcol"><h3><span class="pill {esc(party)}">{esc(party)}</span> '
            f'most synchronized</h3><ol class="pcol-list">{body}</ol></div>')


def party_columns_table(day_data, slugs_with_pages, depth, caucus) -> str:
    """R3 / #146 — per-party side-by-side columns: each party's OWN top-k synchronized phrases, ranked by
    that party's member count, each row with its N-of-caucus denominator. Removes the pooled
    rank-and-truncate artifact (the larger caucus structurally filling a single table). SYNC_MIN
    untouched. Uses the build-time `sync_by_party`; falls back to deriving per-party top-k from the
    stored pooled top_synchronized for historical days written before it existed."""
    by_party = day_data.get("sync_by_party")
    cols = []
    for p in config.COMPOSITE_PARTIES:
        rows = (by_party or {}).get(p) if isinstance(by_party, dict) else None
        if rows is None:
            pooled = build.collapse_and_rank(
                [r for r in (day_data.get("top_synchronized") or []) if isinstance(r, dict)], k=10_000)
            rows = sorted((r for r in pooled if (r.get("counts") or {}).get(p, 0) >= config.SYNC_MIN_MEMBERS),
                          key=lambda r: (r.get("counts") or {}).get(p, 0), reverse=True)[:10]
        cols.append(_party_column(p, rows, slugs_with_pages, depth, (caucus or {}).get(p)))
    return ('<p class="subhead">Each party&rsquo;s own most-synchronized phrases, ranked within the '
            'party so the larger caucus can&rsquo;t fill the table — every count travels with its '
            f'caucus denominator.</p><div class="pcols">{"".join(cols)}</div>')


def day_view_body(day, day_data, slugs_with_pages, depth, prev_day=None, next_day=None, is_today=False):
    symmetry = _load_json(DERIVED / "symmetry" / f"{day}.json")
    root = "../" * depth

    title_line = "Today on OnScript" if is_today else f"OnScript · {esc(day)}"
    parts = [f"<h1>{title_line}</h1>"]
    parts.append(f'<p class="subhead">What each party said on {esc(day)}, compressed to one voice, with receipts.</p>')

    # Cadence note (A5): the header says "Today" but a day's press releases are only complete the next
    # morning, so the freshest complete reading is yesterday. Say so, so the page never looks stale.
    if is_today:
        parts.append(
            f'<div class="banner">Press releases for a given day are complete the next morning, so this '
            f'&ldquo;today&rdquo; reading covers the most recent complete day: <strong>{esc(day)}</strong>.</div>'
        )

    parts.append(banner_html(day_data, symmetry, depth=depth))

    # Two Daily Lines side by side (caucus sizes from the day's symmetry audit → denominators in view)
    caucus = {p: ((symmetry or {}).get("parties", {}).get(p, {}) or {}).get("caucus_size")
              for p in ("D", "R")} if isinstance(symmetry, dict) else {}
    parts.append('<div class="lines">')
    parts.append(daily_line_panel("D", day_data, caucus=caucus.get("D")))
    parts.append(daily_line_panel("R", day_data, caucus=caucus.get("R")))
    parts.append("</div>")

    # Art. VIII (no silent edits): disclose that something was withheld, in AGGREGATE only. Never a
    # per-row placeholder — a row reading "1 phrase withheld, 10 members" is itself a pointer to the
    # person. The count names nobody.
    n_withheld = privacy.filter_rows(day_data.get("top_synchronized") or [])[1]
    if n_withheld:
        parts.append(
            f'<p class="muted"><small>{n_withheld} phrase famil'
            f'{"y" if n_withheld == 1 else "ies"} withheld from this day under the '
            f'<a href="{root}methodology.html">privacy floor</a> (phrases naming a private '
            f'individual). Content-neutral protection applied identically to both parties: no '
            f'threshold changed and no finding was produced.</small></p>'
        )

    # discipline (on-script index) if present
    disc = day_data.get("discipline")
    if isinstance(disc, dict):
        cells = []
        for p in ("D", "R"):
            d = disc.get(p)
            if isinstance(d, dict) and d.get("index") is not None:
                cells.append(
                    f'<span class="pill {p}">{p}</span> on-script index '
                    f'<strong>{esc(d.get("index"))}</strong> '
                    f'<span class="faint">({esc(d.get("on_message_units"))}/{esc(d.get("statements"))} statements)</span>'
                )
        if cells:
            parts.append('<p class="muted" style="margin-top:14px">' + " &nbsp;·&nbsp; ".join(cells) + "</p>")

    # links to audit + methodology
    audit_link = (
        f'<a href="{root}methodology.html">symmetry audit &amp; methodology</a>'
        if not symmetry
        else f'<a href="{root}methodology.html">nightly symmetry audit</a>'
    )
    parts.append(f'<p class="muted"><small>Neutrality armor: {audit_link}. Every distilled talking point above is citation-backed.</small></p>')

    # Top synchronized phrases
    parts.append("<h2>Top synchronized phrases</h2>")
    parts.append(
        '<p class="subhead">Content phrases used by three or more independent members of one party '
        "on this day. The sparkline is the phrase's 14-day trajectory (higher of the two parties' daily counts).</p>"
    )
    # R3 / #146 — per-party columns, DARK until FEATURES["party_columns"]. Flag OFF => the current
    # pooled sync_table (byte-identical), so the redesign ships dark and the flip stays Michael's.
    if config.feature_on("party_columns"):
        parts.append(party_columns_table(day_data, slugs_with_pages, depth, caucus))
    else:
        parts.append(sync_table(day_data, slugs_with_pages, depth))

    # 1.7a The Duet — dark until FEATURES["duet"]; returns "" both when the flag is off and on the
    # (common) days where no phrase clears the bar on both sides.
    parts.append(duet_panel(day_data, depth))

    # prev/next nav (day pages only)
    if not is_today:
        prev_html = (
            f'<a href="{root}day/{esc(prev_day)}.html">&larr; {esc(prev_day)}</a>' if prev_day else "<span></span>"
        )
        next_html = (
            f'<a href="{root}day/{esc(next_day)}.html">{esc(next_day)} &rarr;</a>' if next_day else "<span></span>"
        )
        parts.append(f'<div class="nav-pn">{prev_html}{next_html}</div>')
    else:
        # The homepage is the ENTRY POINT to the permanent day chain. Without these two links,
        # index.html referenced zero day pages and the prev/next chain had no way in — every day we
        # have ever published was reachable only by typing its URL. `prev_day` here is the previously
        # published day (the day before this "today" reading), so the archive is one click deep.
        prev_html = (
            f'<a href="{root}day/{esc(prev_day)}.html">&larr; {esc(prev_day)}</a>' if prev_day else "<span></span>"
        )
        parts.append(
            f'<div class="nav-pn">{prev_html}'
            f'<a href="{root}day/index.html">Every published day &rarr;</a></div>'
        )
        parts.append(
            f'<p class="muted" style="margin-top:26px"><a href="{root}phrases/index.html">Browse all tracked phrases &rarr;</a></p>'
        )

    return "".join(parts)


# ---------------------------------------------------------------------------
# The date archive (/day/index.html)
# ---------------------------------------------------------------------------
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December")


def _month_label(day: str) -> str:
    """'2026-07-18' -> 'July 2026'. Falls back to the raw day on anything unparseable — a malformed
    day string must never crash the archive index."""
    try:
        y, m, _ = str(day).split("-")
        return f"{_MONTH_NAMES[int(m) - 1]} {y}"
    except Exception:
        return str(day)


def days_index_body(rendered) -> str:
    """The date archive: every published day, newest first, grouped by month.

    ``rendered`` is the same [(day, data)] list build_site() renders pages from (ascending), so the
    index and the pages cannot drift — every entry here has a page, and every page is listed here.
    That correspondence is the locked test in tests/test_day_nav.py.

    Days carrying no Daily Lines (the composite voice did not run, or nothing cleared the citation
    threshold) are marked as such rather than omitted: dropping them would silently rewrite the
    record of which days we published, and the whole archive is the compounding asset."""
    if not rendered:
        return ("<h1>Every published day</h1>"
                "<p class='muted'>No days have been published yet.</p>")

    newest_first = list(reversed(rendered))
    n = len(newest_first)
    parts = ["<h1>Every published day</h1>"]
    parts.append(
        f'<p class="subhead">Every day OnScript has published, newest first — {n} '
        f'day{"" if n == 1 else "s"}, from {esc(rendered[0][0])} to {esc(rendered[-1][0])}. '
        f'Each day keeps its own page with that day&rsquo;s composites, receipts, and synchronized '
        f'phrases.</p>'
    )

    current_month = None
    open_list = False
    for day, data in newest_first:
        month = _month_label(day)
        if month != current_month:
            if open_list:
                parts.append("</ul>")
            parts.append(f"<h2>{esc(month)}</h2>")
            parts.append('<ul class="daylist">')
            current_month, open_list = month, True
        note = "" if has_daily_lines(data) else ' <span class="faint">— phrases only</span>'
        parts.append(f'<li><a href="{esc(day)}.html">{esc(day)}</a>{note}</li>')
    if open_list:
        parts.append("</ul>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Phrase pages
# ---------------------------------------------------------------------------
# 1.3 origination (R2 / docs/21 §3.2), DARK until FEATURES["authors_vessels"]. The author LEADERBOARD is
# dropped (#143: it was tenure- + chamber-confounded and nomenclature-contaminated — "Chip Roy authored
# the SAVE Act" is a member typing a bill's name first, not authoring a message). What survives is
# per-phrase origination under three controls: (a) SPAN — a nomenclature phrase gets NO authorship claim;
# (b) a coordination FLOOR — below it, first-use is a chamber artifact (at peak>=2 the "authors" are all
# senators), not origination; (c) BORN-COORDINATED — multiple day-0 first-sayers means no single author.
ORIGINATION_PEAK_FLOOR = 15   # #143 confound control (its only prior home was an incidental default)


def _origination_line(pdata) -> str:
    """The SPAN-gated, floor-gated, born-coordinated origination string for a phrase's 'First recorded' row
    (1.3 / R2). Returns display HTML. Party-blind; reads only the phrase's own record + the committed
    nomenclature tables (usable even while the display tagger is dark)."""
    fs = pdata.get("first_seen") or {}
    fs_date, fs_bio, tie = fs.get("date", ""), fs.get("bioguide"), fs.get("tie") or []
    ngram, peak = pdata.get("ngram", ""), pdata.get("peak_units")
    cong = pdata.get("congress") or (util.congress_for_date(fs_date) if fs_date else None)
    if cong and ngram and nomenclature.is_nomenclature(ngram, int(cong)):
        return (f'{esc(fs_date)} <span class="faint">(first recorded — an official name, '
                f'not an authored phrase)</span>')
    if not isinstance(peak, int) or peak < ORIGINATION_PEAK_FLOOR:
        return (f'{esc(fs_date)} <span class="faint">(first recorded — below the '
                f'{ORIGINATION_PEAK_FLOOR}-member coordination floor, so first use is not origination)</span>')
    if tie:
        names = ", ".join(member_name(b) for b in (([fs_bio] + list(tie)) if fs_bio else list(tie)))
        return (f'{esc(fs_date)} — <strong>born coordinated</strong> '
                f'<span class="faint">(no single author; first said together by {names})</span>')
    return f"{esc(fs_date)} by {member_name(fs_bio)}"


def phrase_evidence_body(pdata: dict, evidence: dict | None = None) -> str:
    """Render a bounded, metadata-only peak-day receipt set, or nothing below quorum."""
    ngram, slug = pdata.get("ngram") or "", pdata.get("slug") or ""
    # Art. XIII is intentionally repeated at render even though the builder checks before write.
    if not ngram or privacy.is_suppressed(ngram):
        return ""
    source = PHRASE_EVIDENCE if evidence is None else evidence
    records = source.get("phrases", {}) if isinstance(source, dict) else {}
    record = records.get(slug) if isinstance(records, dict) else None
    if not isinstance(record, dict) or int(record.get("grounded_units") or 0) < 3:
        return ""

    safe = []
    for receipt in record.get("receipts") or []:
        if not isinstance(receipt, dict):
            continue
        url = _safe_http_url(receipt.get("url"))
        values = [receipt.get(k) for k in ("member", "party", "state", "date", "url")]
        if not url or privacy.is_suppressed(" ".join(str(v or "") for v in values)):
            continue
        safe.append({**receipt, "url": url})
    if len(safe) < 3:
        return ""

    # At most three per side: bounded and symmetric even when one party supplied most of the units.
    visible = []
    for party in config.COMPOSITE_PARTIES:
        visible.extend([r for r in safe if r.get("party") == party][:3])
    if len(visible) < 3:
        visible = safe[:6]
    total = int(record.get("grounded_units") or 0)
    day = record.get("peak_day") or ""

    symmetry = _load_json(DERIVED / "symmetry" / f"{day}.json") if day else None
    parties = symmetry.get("parties", {}) if isinstance(symmetry, dict) else {}
    count_bits = []
    for party in config.COMPOSITE_PARTIES:
        count = int((record.get("counts") or {}).get(party) or 0)
        if not count:
            continue
        denom = (parties.get(party) or {}).get("caucus_size") if isinstance(parties, dict) else None
        count_bits.append(f"{esc(party)}: {esc(count)} of {esc(denom)}" if denom else f"{esc(party)}: {esc(count)}")
    denominator_line = f' <span class="faint">({"; ".join(count_bits)})</span>' if count_bits else ""

    rows = []
    for receipt in visible:
        party, state = receipt.get("party"), receipt.get("state")
        archived = _wayback_url(receipt["url"], receipt.get("date"))
        rows.append(
            '<div class="receipt"><div class="rhead">'
            f'{esc(receipt.get("member"))} ({esc(party)}-{esc(state)}) &middot; {esc(receipt.get("date"))} '
            f'&middot; <a href="{esc(receipt["url"])}" rel="nofollow noopener">source</a> '
            f'&middot; <a href="{esc(archived)}" rel="nofollow noopener">archived</a>'
            '</div></div>'
        )
    return (
        '<h2>Peak-day evidence</h2>'
        f'<p class="subhead">On {esc(day)}, this exact phrase is grounded in {esc(total)} distinct '
        f'source unit{"" if total == 1 else "s"} (an office or joint-release family). The Peak figure '
        'above is the largest count for either party; this evidence total counts grounded units across '
        'both parties on that same day. Showing '
        f'{esc(len(visible))} of {esc(total)} source receipts.{denominator_line}</p>'
        + "".join(rows)
    )


def phrase_page_body(pdata, depth=1, evidence=None):
    ngram = pdata.get("ngram", "")
    fs = pdata.get("first_seen") or {}
    source_fs_date = fs.get("date", "")
    fs_bio = fs.get("bioguide")
    window = public_phrase_window(pdata)
    fs_date = window["first_day"]
    peak = window["peak_units"]
    peak_day = window["peak_day"]
    dfw = pdata.get("df_weight")
    series = window["series"]

    parts = [f'<h1>&ldquo;{esc(ngram)}&rdquo;</h1>']
    # docs/19 §2b — nomenclature tag on the phrase/curve page (DARK until FEATURES["nomenclature_tags"]).
    # Congress from the row if present, else the first-seen date; skip silently if neither resolves.
    if config.feature_on("nomenclature_tags") and ngram:
        _cong = pdata.get("congress") or (util.congress_for_date(fs_date) if fs_date else None)
        _v = nomenclature.is_nomenclature(ngram, int(_cong)) if _cong else None
        if _v:
            parts.append(f'<p class="nomnote">{_nomenclature_chip(_v).strip()}</p>')
    parts.append('<p class="subhead">Adoption curve: how many independent members of each party used this exact phrase, by day. '
                 'Where at least three distinct offices can be grounded, peak-day source receipts appear below.</p>')

    parts.append('<div class="chartbox scroll">')
    parts.append(curve_svg(series))
    parts.append(
        '<p class="legend"><span class="sw" style="border-color:#2b4c7e"></span>Democrats'
        '&nbsp;&nbsp;<span class="sw" style="border-color:#8a2f2f"></span>Republicans</p>'
    )
    parts.append("</div>")

    source_first_is_public = bool(source_fs_date and source_fs_date >= config.STAGE1_EPOCH)
    tie = (fs.get("tie") or []) if source_first_is_public else []
    tie_html = ""
    if tie:
        tie_html = ' <span class="faint">(tied with ' + ", ".join(member_name(b) for b in tie) + ")</span>"

    parts.append('<dl class="kv">')
    # 1.3 origination (R2), DARK until FEATURES["authors_vessels"]: SPAN-gated + coordination-floored +
    # born-coordinated. Flag OFF => the current unchanged line (byte-identical), so the redesign ships
    # dark and the release flip stays Michael's (docs/21 §3.2).
    if not series:
        parts.append(
            f'<dt>Public-window record</dt><dd>No observations in the public window beginning '
            f'{esc(config.STAGE1_EPOCH)}.</dd>'
        )
    elif not source_first_is_public:
        parts.append(
            f'<dt>First recorded in the public window</dt><dd>{esc(fs_date)} '
            '<span class="faint">(first active day in the public window; this derived record does not '
            'identify that day&rsquo;s first carrier)</span></dd>'
        )
    elif config.feature_on("authors_vessels"):
        parts.append(f"<dt>First recorded in our corpus</dt><dd>{_origination_line(pdata)}</dd>")
    else:
        parts.append(f"<dt>First recorded in our corpus</dt><dd>{esc(fs_date)} by {member_name(fs_bio)}{tie_html}</dd>")
    if peak is not None:
        peak_data = _load_json(DERIVED / "days" / f"{peak_day}.json") if peak_day else None
        peak_has_page = isinstance(peak_data, dict) and (
            has_daily_lines(peak_data) or bool(peak_data.get("top_synchronized")))
        peak_date = (f'<a href="{"../" * depth}day/{esc(peak_day)}.html">{esc(peak_day)}</a>'
                     if peak_has_page else esc(peak_day))
        parts.append(f'<dt>Peak</dt><dd>{esc(peak)} members in one day'
                     f'<span class="faint"> &middot; {peak_date}</span></dd>')
    if dfw is not None:
        parts.append('<dt>Distinctiveness</dt><dd><span class="faint">The full-history weight is withheld '
                     'until the Archive release; it is not part of these public-window statistics.</span></dd>')
    parts.append(f"<dt>Data points</dt><dd>{len([r for r in series if isinstance(r, dict)])} active days</dd>")
    parts.append("</dl>")

    parts.append(phrase_evidence_body(pdata, evidence=evidence))

    parts.append(
        f'<p class="muted"><small>Public Stage-1 phrase statistics begin {esc(config.STAGE1_EPOCH)}. '
        'Coverage for the same window is shown on the '
        f'<a href="../methodology.html">Methodology</a> page. (The full-history &ldquo;Alexandria&rdquo; '
        "backfill to 2001 is staged for a later phase.)</small></p>"
    )
    parts.append('<p style="margin-top:22px"><a href="../phrases/index.html">&larr; All phrases</a></p>')
    return "".join(parts)


def phrases_index_body(top):
    parts = ["<h1>Tracked phrases</h1>"]
    parts.append(
        '<p class="subhead">First-appearance tracking and adoption curves across members. '
        "When a phrase jumps from a handful of members to dozens in a day, the convergence is the measurement — "
        "we record who said what, and when, and let you draw your own conclusions about why.</p>"
    )

    def render_table(rows, heading, sort_label):
        rows = [r for r in (rows or []) if isinstance(r, dict)]
        if not rows:
            return ""
        out = [f"<h2>{esc(heading)}</h2>"]
        out.append(f'<p class="subhead">{esc(sort_label)}</p>')
        head = (
            "<tr><th>Phrase</th><th>Party</th><th class='num'>Peak</th>"
            "<th class='num'>Velocity</th><th>First seen</th></tr>"
        )
        body = []
        for r in rows[:40]:
            slug = r.get("slug", "")
            ngram = r.get("ngram", "")
            party = r.get("party", "")
            fs = r.get("first_seen") or {}
            vel = r.get("velocity")
            vel_txt = f"{vel:.1f}" if isinstance(vel, (int, float)) else esc(vel)
            cell = (
                f'<a href="{esc(slug)}.html">{esc(ngram)}</a>'
                if slug in SLUGS_WITH_PAGES
                else esc(ngram)
            )
            body.append(
                f"<tr><td>{cell}</td>"
                f'<td><span class="pill {esc(party)}">{esc(party)}</span></td>'
                f'<td class="num">{esc(r.get("day_peak"))}</td>'
                f'<td class="num">{esc(vel_txt)}</td>'
                f'<td class="muted"><small>{esc(fs.get("date",""))}</small></td></tr>'
            )
        out.append(
            '<div class="scroll"><table>'
            f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"
        )
        return "".join(out)

    # Art. XIII: the one display path that does NOT route through build.collapse_and_rank (the peak
    # table below does), so it needs its own filter.
    parts.append(render_table(privacy.filter_rows(top.get("by_velocity") or [])[0], "Fastest-spreading", "Ranked by adoption velocity — phrases going viral within a caucus."))
    # collapse near-dups on the peak table (render-time refresh); the velocity table keeps its own order.
    parts.append(render_table(build.collapse_and_rank(top.get("by_peak") or [], k=40),
                              "Most synchronized", "Ranked by peak single-day member count."))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Methodology page (the neutrality armor)
# ---------------------------------------------------------------------------
def symmetry_table(sym):
    if not isinstance(sym, dict):
        return '<p class="muted">No symmetry audit is available yet.</p>'
    parties = sym.get("parties") or {}
    head = (
        "<tr><th>Metric</th><th class='num'>Democrats</th><th class='num'>Republicans</th></tr>"
    )
    d = parties.get("D") or {}
    r = parties.get("R") or {}

    def row(label, key, fmt=None):
        dv = d.get(key)
        rv = r.get(key)
        if fmt == "pct":
            dv, rv = _pct(dv), _pct(rv)
        else:
            dv, rv = esc(dv if dv is not None else "—"), esc(rv if rv is not None else "—")
        return f"<tr><td>{esc(label)}</td><td class='num'>{dv}</td><td class='num'>{rv}</td></tr>"

    # Every row is scoped to the audited day (labeled so no one reads a cumulative corpus total as
    # "ingested today"); caucus size is the full corpus caucus proxy, so Coverage = the share of the
    # caucus that spoke that day. §Session-5.
    rows = [
        row("Statements ingested (this day)", "statements_ingested"),
        row("Members covered (this day)", "members_covered"),
        row("Caucus size (corpus)", "caucus_size"),
        row("Coverage (this day)", "coverage_pct", "pct"),
        row("Tokens in (this day)", "tokens_in"),
        row("Tokens out (this day)", "tokens_out"),
        row("Claims published (this day)", "claims_published"),
        row("Claims dropped (this day)", "claims_dropped"),
    ]
    return (
        '<div class="scroll"><table>'
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def methodology_body():
    sym = _load_json(DERIVED / "symmetry" / "latest.json")
    coverage = _load_json(DERIVED / "coverage.json") or {}

    parts = ["<h1>Methodology</h1>"]
    parts.append(
        '<p class="subhead">OnScript is a symmetric instrument. The same pipeline, the same prompts, and the '
        "same thresholds run for both parties. Asymmetric findings are allowed — a symmetric instrument producing "
        "asymmetric readings is a fact about the world, not about the instrument. This page is that guarantee, in public.</p>"
    )
    parts.append('<p class="subhead">Daily readings are also available in the <a href="feed.xml">Atom feed</a>.</p>')

    # (a) two-lane model
    parts.append("<h2>The two-lane model</h2>")
    parts.append(
        "<p><strong>Lane 1 — press releases.</strong> Official member press releases (mirrored from an open "
        "corpus) are the only source that exists symmetrically for both parties. <em>Every cross-party number "
        "on this site comes from Lane 1 and Lane 1 only.</em></p>"
    )
    parts.append(
        "<p><strong>Lane 2 — Bluesky &amp; floor speech.</strong> These enrich individual context but are "
        "<em>machine-blocked from every comparative metric</em>. Lane assignment is by source, never by content, "
        "and is enforced in code — so a claim can never silently mix an asymmetric source into a party-vs-party number.</p>"
    )
    parts.append(
        f"<p><strong>Public phrase window.</strong> Stage-1 phrase statistics and coverage begin "
        f"<strong>{esc(config.STAGE1_EPOCH)}</strong>. Earlier retained observations remain out of the public "
        "phrase views until the Archive and its lane disclosures are released.</p>"
    )

    # (a2) what we measure — three standing positions, inscribed before the findings arrive
    parts.append("<h2>What OnScript measures — and what it does not</h2>")
    parts.append(
        "<p><strong>Verbatim coordination, not paraphrase.</strong> OnScript measures exact shared wording — the "
        "same phrase appearing in multiple members' published statements. This is what makes every count checkable: "
        "you can read the releases and see the words. It also means a <em>decline</em> in verbatim overlap once the "
        "instrument is watching is itself a finding, not a failure — when members stop reaching for identical "
        "language, we record that too. Any future instrument that tried to measure paraphrased or semantic "
        "coordination would be a separate tool with a weaker guarantee, and it would be labeled as such. It would "
        "never be folded silently into these numbers.</p>"
    )
    parts.append(
        "<p><strong>No number on this site is produced by a language model.</strong> Every count, first-appearance "
        "date, adoption curve, and coverage figure is computed by deterministic code directly from the raw text. The "
        "language model does exactly one thing: render the day's already-measured phrases into readable prose. It "
        "cannot introduce a topic, a claim, or a figure the engine did not measure — a deterministic verifier blocks "
        "any line whose quotes aren't verbatim or whose numbers aren't code-computed, dropping it to a plain "
        "fallback rather than publishing it. The measurement path stays model-free through every model change.</p>"
    )
    parts.append(
        "<p><strong>Method changes are versioned.</strong> When a threshold or a rule changes, it is a dated, "
        "public, diffable change (prompts and thresholds are hashed on this page). Because the pipeline is "
        "deterministic, a method change can be re-run against the <em>entire</em> corpus, and the commitment is to "
        "publish both the old and new series side by side when one is made — so a change is a versioned, public "
        "event, never a silent re-score. No method has changed since launch; when one does, the diff and both "
        "series will appear here.</p>"
    )

    # (b) nightly symmetry audit
    parts.append("<h2>Nightly symmetry audit</h2>")
    if isinstance(sym, dict):
        statement = sym.get("statement", "")
        day = sym.get("day", "")
        if statement:
            parts.append(f'<p style="font-size:16px"><em>{esc(statement)}</em></p>')
        if day:
            parts.append(f'<p class="promptmeta">Audit for {esc(day)}.</p>')
        parts.append(symmetry_table(sym))
        # identical shas for both parties
        psha = sym.get("prompts_sha") or {}
        tsha = sym.get("thresholds_sha")
        parts.append(
            '<p class="muted" style="margin-top:12px"><small>The following hashes are computed once and applied '
            "identically to both parties. If they ever differ between parties, the instrument is broken.</small></p>"
        )
        parts.append('<dl class="kv">')
        for k in ("P1", "P2", "P3"):
            if psha.get(k):
                parts.append(f'<dt>{esc(k)} prompt sha</dt><dd class="sha">{esc(psha.get(k))}</dd>')
        if tsha:
            parts.append(f'<dt>thresholds sha</dt><dd class="sha">{esc(tsha)}</dd>')
        parts.append(f'<dt>Lane-1 only</dt><dd>{esc(sym.get("lane1_only"))}</dd>')
        parts.append(f'<dt>Degraded</dt><dd>{esc(sym.get("degraded"))}</dd>')
        parts.append("</dl>")
        # Model-voice spend, made public (radical-transparency + a live budget monitor). The composite
        # voice is a Sonnet call bounded by a $9 code ceiling and the $10 Console cap; on days it is the
        # deterministic template instead, spend is $0.
        _month = str(sym.get("day", ""))[:7]
        _cost = _load_json(DERIVED / "cost" / f"{_month}.json") if _month else None
        if isinstance(_cost, dict) and _cost.get("total_usd") is not None:
            parts.append(
                f'<p class="muted" style="margin-top:12px"><small>Model-voice spend this month '
                f'({esc(_month)}): <strong>${esc(format(float(_cost["total_usd"]), ".4f"))}</strong> — '
                f'the composite is a Sonnet call bounded by a $9 code ceiling and a $10 hard cap; on '
                f'deterministic-template days it is $0.</small></p>'
            )
    else:
        parts.append('<p class="muted">No symmetry audit is available yet.</p>')

    # per-year coverage
    if coverage:
        parts.append("<h3>Corpus coverage by year</h3>")
        parts.append(
            f'<p class="subhead">Per-year Lane-1 statement counts in the public phrase window beginning '
            f'{esc(config.STAGE1_EPOCH)}. Cross-era claims remain gated on coverage.</p>'
        )
        years = sorted(y for y in coverage.keys() if str(y) >= config.STAGE1_EPOCH[:4])
        head = "<tr><th>Year</th><th class='num'>Democrats</th><th class='num'>Republicans</th><th class='num'>Independents</th></tr>"
        body = []
        for y in years:
            c = coverage.get(y) or {}
            body.append(
                f"<tr><td>{esc(y)}</td>"
                f'<td class="num">{esc(c.get("D", 0))}</td>'
                f'<td class="num">{esc(c.get("R", 0))}</td>'
                f'<td class="num">{esc(c.get("I", 0))}</td></tr>'
            )
        parts.append('<div class="scroll"><table>' + f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>")

    # (c) live prompt text, verbatim
    parts.append("<h2>Live prompt text</h2>")
    parts.append(
        "<p>These are the exact prompts running in the pipeline, versioned and public. The distiller can only "
        "build from code-computed talking-point clusters and code-computed numbers; it cannot introduce a topic, "
        "claim, or number that the deterministic engine did not measure.</p>"
    )
    # Drive the displayed files from the SAME registry that computes the published prompts_sha
    # (llm._PROMPT_FILES) so the text shown here always matches the hash on this page — an auditor who
    # re-hashes the displayed prompt gets the published value. Never hardcode versions here. §S7 (#8).
    from pipeline import llm as _llm
    prompt_files = [
        ("P1 — fragment extraction", _llm._PROMPT_FILES["P1"]),
        ("P2 — Daily Line", _llm._PROMPT_FILES["P2"]),
        ("P3 — quiet day", _llm._PROMPT_FILES["P3"]),
    ]
    for label, fname in prompt_files:
        text = _read_text(PROMPTS_DIR / fname)
        parts.append(f"<h3>{esc(label)}</h3>")
        parts.append(f'<p class="promptmeta mono">{esc(fname)}</p>')
        if text:
            parts.append(f"<pre class='prompt'>{esc(text)}</pre>")
        else:
            parts.append('<p class="muted">Prompt file not found.</p>')

    # (d) taxonomy
    parts.append("<h2>Topic taxonomy (v1)</h2>")
    topics = TAXONOMY.get("topics", [])
    if topics:
        note = TAXONOMY.get("note")
        if note:
            parts.append(f'<p class="subhead">{esc(note)}</p>')
        parts.append("<ul class='tight'>")
        for t in topics:
            parts.append(f"<li><span class='mono'>{esc(t.get('id'))}</span> — {esc(t.get('label'))}</li>")
        parts.append("</ul>")
    else:
        parts.append('<p class="muted">Taxonomy not found.</p>')

    # (d2) the privacy floor (Art. XIII) — the rule, the count, the dates, the guarantees. Never a name.
    pmeta = privacy.meta()
    n_persons = pmeta.get("persons") or 0
    n_forms = sum(int((e or {}).get("forms") or 0) for e in (pmeta.get("entries") or []))
    added = ", ".join(sorted({str((e or {}).get("added")) for e in (pmeta.get("entries") or []) if e.get("added")}))
    parts.append("<h2>The privacy floor</h2>")
    parts.append(
        "<p>OnScript measures what elected officials say in public. It never publishes a private individual as a "
        "data point &mdash; regardless of how interesting. When a phrase our engine tracks contains the name of a "
        "private individual, that phrase family is withheld from every published surface: the tables, the phrase "
        "pages, the receipts, the composites, and the accounts.</p>"
    )
    parts.append(
        "<p>That includes the published data releases. The raw mirror and the phrase ledger are built from "
        "statements that sometimes name a private individual, so the same rule runs over the release assets "
        "every time they are rebuilt: each occurrence is <strong>replaced in place with a label</strong>, not "
        "deleted, so the record still shows that a name was there and how the phrase behaved. Nothing else in "
        "the payload is altered &mdash; an untouched record keeps its original bytes.</p>"
    )
    parts.append(
        f"<p>The suppression list holds <strong>{esc(n_persons)} people / {esc(n_forms)} name forms</strong>"
        f"{f' (added {esc(added)})' if added else ''}. It is applied identically to both parties, it changes no "
        "threshold and produces no finding, and it is checked on load against the full member roster and against a "
        "public list of legitimate phrases &mdash; so it provably cannot silence an elected official or an "
        "official&rsquo;s own words. The list itself is published in one-way keyed form: you can audit its size, its "
        "dates, its code, and its guarantees, but it does not disclose the names. That one omission is for the same "
        "reason as the suppression &mdash; publishing a curated list of private individuals would be the violation, "
        "not the fix.</p>"
    )

    # (e) corrections policy + public log (neutrality armor: corrections are dated posts, never silent edits)
    parts.append("<h2>Corrections</h2>")
    parts.append(
        "<p>Every distilled talking point is anchored to at least three real source statements (member, date, source). "
        "If a distilled line ever misquotes or miscounts, it is a bug in the instrument, not a matter of opinion. Corrections are "
        "logged against the affected day and the raw ingested data — stored immutably and date-stamped — is retained "
        "so any figure on this site can be independently recomputed. Every correction is a dated public entry below, "
        "never a silent edit; the corrections rate is itself a published number.</p>"
    )
    n_corr = len(CORRECTIONS)
    if not n_corr:
        parts.append(
            "<p class='muted'>Corrections to date: <strong>0</strong>. No published line has yet required a "
            "correction. The first that does appears here — dated, with the affected day and the fix.</p>"
        )
    else:
        parts.append(f"<p>Corrections to date: <strong>{n_corr}</strong>.</p>")
        parts.append('<div class="scroll"><table><thead><tr><th>Logged</th><th>Affected day</th>'
                     "<th>What</th><th>Status</th></tr></thead><tbody>")
        for c in sorted(CORRECTIONS, key=lambda c: c.get("logged", ""), reverse=True):
            parts.append(
                "<tr><td class='mono'>{logged}</td><td class='mono'>{day}</td><td>{what}</td>"
                "<td>{status}</td></tr>".format(
                    logged=esc(c.get("logged", "")), day=esc(c.get("day", "—")),
                    what=esc(c.get("description", "")),
                    status=esc(c.get("resolution") or c.get("status", "open")),
                )
            )
        parts.append("</tbody></table></div>")

    # (f) data downloads pointer
    parts.append("<h2>Data</h2>")
    parts.append(
        f"<p>The derived JSON that powers this site is committed to the project's "
        f"<a href='{esc(config.REPO_URL)}'>public source repository</a>; raw ingested statements and the full phrase "
        f"ledger are published as immutable, date-stamped "
        f"<a href='{esc(config.REPO_URL)}/releases/tag/data-latest'>release assets</a> so the entire time-series is "
        "rebuildable from source. The pipeline is deterministic: same inputs, same outputs.</p>"
    )
    parts.append(
        "<p><strong>Source links and the archive.</strong> Each receipt links to the member's own .gov release "
        "and, alongside it, to a Wayback Machine capture. Member sites migrate and delete, so a live link can rot "
        "over time — but the exact text we quoted is preserved verbatim in the immutable data release above — "
        "verbatim except for privacy-floor redactions, each labeled in place — so a "
        "dead source link never means lost evidence. A release that is <em>deleted after we cited it</em> is not a "
        "gap in our record; it is a finding, and surfacing those is a planned feature.</p>"
    )

    # The Concordance (1.4 / R4) — described here only once released, so the Methodology never
    # documents a page the reader can't see (dark until FEATURES["concordance"]).
    if config.feature_on("concordance"):
        parts.append("<h2>The Concordance (per-member on-script index)</h2>")
        parts.append(
            "<p>The <a href='concordance.html'>Concordance</a> reports, for each member with enough solo "
            f"releases to be scored (at least {esc(config.CONCORDANCE_MIN_STATEMENTS)}), the share of those "
            "releases that used a phrase <strong>their party genuinely converged on</strong> — one that at "
            f"least {esc(config.CONCORDANCE_PEAK_FLOOR)} members reached for on a single day. That "
            "coordination floor matters: without it, generic political language a handful of offices happen "
            "to share would count, and nearly every member would read as 100&percnt; on-script — a "
            "measurement artifact, not a finding. Three more rules keep it honest: <strong>official names "
            "are excluded</strong> (a bill title or committee name is not a talking point, so typing one is "
            "never scored as on-script); <strong>joint and co-signed releases are excluded</strong> (that is "
            "coordination, not a member's own voice); and every score is shown with its raw counts and "
            "receipts, so a small sample can't hide behind a percentage. It is a descriptive overlap, applied "
            "identically to both parties — never a claim about motive, direction, or who influenced whom.</p>")

    # The Unison & The Void (1.5 / R2) — described here only once released (dark until FEATURES["awards"]).
    if config.feature_on("awards"):
        parts.append("<h2>The Unison &amp; The Void (weekly awards)</h2>")
        parts.append(
            "<p>The <a href='awards.html'>Unison &amp; the Void</a> are two symmetric weekly awards, "
            "picked by the data on identical rules for both parties — the replacements for a "
            "member-level &ldquo;most on-script&rdquo; award, which we dropped because it shames "
            "individuals for a measurement that is really about chamber, tenure, and bill-naming. "
            "<strong>The Unison</strong> is a phrase award: each party&rsquo;s single largest "
            f"<em>office-share</em> phrase over the week — of the offices that published a solo release on "
            f"a given day, the share that used one exact phrase (only days with at least "
            f"{esc(config.UNISON_MIN_ACTIVE)} active offices are eligible, so a quiet day can&rsquo;t win). "
            "Official names are excluded (naming a bill is not a talking point), joint releases are "
            "excluded (that is coordination, not one office&rsquo;s wording), and every card shows its raw "
            "numerator and denominator. <strong>The Void</strong> is a topic award drawn from the absence "
            "map: the week&rsquo;s loudest silence in both directions — what the news carried that neither "
            "party would touch, and what a party pushed that the news ignored. When the absence map has no "
            "scored board for the week, The Void is shown as unavailable rather than invented — a gap is "
            "never reported as a silence. No award names an individual member; the unit is the phrase or "
            "the topic, and each is a descriptive overlap, not a claim about motive.</p>")

    return "".join(parts)


def about_body():
    parts = ["<h1>About OnScript</h1>"]
    parts.append(
        '<p class="subhead">This is what each party said today, compressed to one voice, with receipts.</p>'
    )
    parts.append('<p class="subhead">Daily readings are also available in the <a href="feed.xml">Atom feed</a>.</p>')
    parts.append(
        "<p><strong>Compression, not parody.</strong> OnScript ingests what elected U.S. officials publicly say "
        "and distills each party's real talking points into one composite voice. The comedy, where there is any, "
        "is emergent: the source material is real, and we never editorialize. We are analysis of speech, not a "
        "substitute for it.</p>"
    )
    parts.append(
        "<p><strong>The data is the story.</strong> When dozens of members converge on the same phrase within a day, "
        "that convergence is the measurement — independent members reaching for identical language. We record it; we "
        "do not assert its cause. We track first appearances, plot adoption curves, and score how on-script each "
        "party's language runs, day over day.</p>"
    )
    parts.append(
        "<p><strong>Citation-backed.</strong> Every distilled talking point links to at least three real source "
        "statements — member, date, source. If a claim can't be cited, it doesn't ship.</p>"
    )
    parts.append(
        "<p><strong>A symmetric instrument.</strong> The identical pipeline, prompts, and thresholds run for both "
        "parties, audited nightly in public on the <a href='methodology.html'>Methodology</a> page. Asymmetric "
        "findings are allowed; an asymmetric instrument is not.</p>"
    )
    parts.append("<h2>Who operates OnScript</h2>")
    parts.append(
        "<p>OnScript is built and operated by <strong>Michael King</strong> as an independent project. It is not "
        "affiliated with any party, campaign, committee, PAC, or newsroom. It accepts <strong>no political money — "
        "ever</strong>, from any party, campaign, committee, or PAC; any philanthropic or infrastructure grant it "
        "ever accepts will be disclosed on this page. "
        "<strong>The operator's personal political views appear nowhere on this instrument</strong> — not in the "
        "composites, not on the accounts, not in the rankings. The instrument is symmetric by construction; if it "
        "is ever caught being otherwise, that is a bug, and the fix is logged in public. This page is the "
        "operator disclosure of record.</p>"
    )
    parts.append(
        "<p><strong>Contact &amp; corrections</strong> run through the corrections process on the "
        f"<a href='methodology.html'>Methodology</a> page and the project's "
        f"<a href='{esc(config.REPO_URL)}'>public source repository</a> — every correction is a dated public entry, "
        "never a silent edit. OnScript has no comment section and solicits no engagement; it broadcasts a "
        "measurement and links its receipts.</p>"
    )
    parts.append("<h2>The accounts</h2>")
    parts.append(
        "<p>Two automated composite accounts on Bluesky — one per party, the identical instrument, only the field "
        "color differs — plus the house account for project announcements:</p>"
    )
    parts.append(
        "<ul class='tight'>"
        "<li><strong><a href='https://bsky.app/profile/blue.onscript.news'>blue.onscript.news</a></strong> — "
        "the composite voice of Democratic members of Congress</li>"
        "<li><strong><a href='https://bsky.app/profile/red.onscript.news'>red.onscript.news</a></strong> — "
        "the composite voice of Republican members of Congress</li>"
        "<li><strong><a href='https://bsky.app/profile/onscript.news'>onscript.news</a></strong> — "
        "the house account for releases and instrument notices</li>"
        "</ul>"
    )
    parts.append(
        "<p>The composite accounts post daily citation-backed threads, labeled automated. They follow only the "
        "other OnScript accounts and never like or repost; their bios point here for disclosure.</p>"
    )
    parts.append("<h2>How it's built</h2>")
    parts.append(
        "<p>Three layers, in order: (1) a <strong>deterministic phrase engine</strong> that measures which exact "
        "phrases spread across members and when each first appeared; (2) an <strong>LLM voice</strong> that renders "
        "the day's measured clusters into one composite paragraph, permitted to use only the code-computed clusters "
        "and code-computed numbers; and (3) a <strong>deterministic verifier</strong> that blocks any line whose "
        "quotes or counts don't check out against the source.</p>"
    )
    parts.append(
        f"<p>The <a href='{esc(config.REPO_URL)}'>source repository</a> and the rolling "
        f"<a href='{esc(config.REPO_URL)}/releases/tag/data-latest'>data release</a> are public so the "
        "instrument can be inspected and rebuilt independently.</p>"
    )
    parts.append(
        '<div class="banner">Honest disclosure: the composite voice is live, but on rare degraded days a line may '
        "use a <strong>deterministic fallback</strong>. Whenever that happens the day's page is plainly labeled; "
        "the numbers, quotes, and receipts under every line are always real and verified.</div>"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Signed post archive (§Session-8): the on-domain mirror of every posted thread — forgery defense.
# ---------------------------------------------------------------------------
def posted_threads() -> list:
    """Post-manifest records classified by what the manifest can actually authenticate."""
    out = []
    mdir = DERIVED / "manifest"
    if not mdir.exists():
        return out
    for p in sorted(mdir.glob("post-*.json")):
        m = _load_json(p)
        if not isinstance(m, dict):
            continue
        for r in (m.get("results") or []):
            if not isinstance(r, dict):
                continue
            posted = r.get("posted") is True
            partial = r.get("partial") is True
            root_uri = r.get("root_uri") if isinstance(r.get("root_uri"), str) else ""
            root_uri = root_uri.strip()
            if not (posted or partial):
                continue
            if partial and root_uri:
                status = "partial"
            elif posted and root_uri:
                status = "authenticated"
            else:
                status = "unverifiable"
            out.append({"day": m.get("day"), "generated_at": m.get("generated_at"),
                        "party": r.get("party"), "thread": r.get("thread") or [],
                        "root_uri": root_uri, "status": status})
    out.sort(key=lambda r: (str(r.get("day")), str(r.get("party"))), reverse=True)
    return out


def _bsky_web_url(uri):
    """at://did/app.bsky.feed.post/rkey -> https://bsky.app/profile/did/post/rkey (best-effort)."""
    if isinstance(uri, str) and uri.startswith("at://"):
        rest = uri[len("at://"):]
        did, sep, tail = rest.partition("/app.bsky.feed.post/")
        if sep and did and tail:
            return f"https://bsky.app/profile/{did}/post/{tail}"
    return None


def posts_log_body(threads) -> str:
    parts = ["<h1>Posted threads &mdash; signed archive</h1>"]
    parts.append(
        '<p class="subhead">This archive reflects the posting manifests available when this page was built. '
        "A complete entry with a Bluesky root link is the authenticated record. A same-run refresh failure "
        "can delay a new entry until the next build; partial and unverifiable records are labeled and never "
        "presented as complete. The accounts never reply, like, or repost outside their published threads.</p>"
    )
    if not threads:
        parts.append('<p class="muted">No posts recorded in this build.</p>')
        return "".join(parts)
    for t in threads:
        party = t.get("party")
        status = t.get("status") or ("authenticated" if t.get("root_uri") else "unverifiable")
        head = (f'<span class="pill {esc(party)}">{esc(party)}</span> <strong>{esc(t.get("day"))}</strong> '
                f'<span class="faint">&middot; {esc(t.get("generated_at"))}</span>')
        web = _bsky_web_url(t.get("root_uri"))
        link = f' &middot; <a href="{esc(web)}" rel="nofollow noopener">on Bluesky</a>' if web else ""
        if status == "authenticated":
            badge = ' &middot; <strong>authenticated</strong>'
            body = "".join(f'<div class="quote">{esc(p)}</div>' for p in (t.get("thread") or []))
        elif status == "partial":
            badge = ' &middot; <strong>partial</strong>'
            body = ('<p class="muted"><small>The root is live, but this manifest does not prove that the '
                    'intended replies were all posted. Only the root link is shown.</small></p>')
        else:
            badge = ' &middot; <strong>unverifiable</strong>'
            body = ('<p class="muted"><small>The manifest reports a post but records no root URI, so no '
                    'thread text is presented as authenticated.</small></p>')
        parts.append(f'<div class="receipt"><div class="rhead">{head}{badge}{link}</div>{body}</div>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
SLUGS_WITH_PAGES = phrase_page_slugs()
_POSTED_THREADS = posted_threads()
HAS_POSTS = bool(_POSTED_THREADS)


# --- The Archive (dark feature 1.1, docs/11) — 25-year era/month chapters + era fingerprints --------
def _load_chapters() -> list[dict]:
    """Every verifier-CLEAN chapter (the 1.1 release gate is 'zero uncited fragments' → only
    verifier.passed chapters render). Eras first (newest Congress first), then months."""
    out = []
    cdir = DERIVED / "chapters"
    if cdir.exists():
        for f in sorted(cdir.glob("*.json")):
            c = _load_json(f)
            if c and (c.get("verifier") or {}).get("passed"):
                out.append(c)
    out.sort(key=lambda c: (c.get("kind") != "era", -(c.get("congress") or 0),
                            c.get("label") or "", c.get("party") or ""))
    return out


def _fingerprint(top_phrases, k=5) -> str:
    items = "".join(
        f'<li>{esc(p.get("phrase"))} <span class="faint">&middot; {esc(p.get("peak_members"))} members, '
        f'first {esc(p.get("first_date"))}</span></li>' for p in (top_phrases or [])[:k])
    return f"<ul>{items}</ul>" if items else '<p class="muted">—</p>'


def archive_index_body(chapters) -> str:
    eras = [c for c in chapters if c.get("kind") == "era"]
    by_congress: dict = {}
    for c in eras:
        by_congress.setdefault(c.get("congress"), {})[c.get("party")] = c
    parts = ["<h1>The Archive</h1>",
             '<p class="subhead">Twenty-five years of what each party said, distilled one Congress at a '
             'time. Every phrase count is computed by deterministic code from the raw record; the prose is '
             'a language model held to the same citation rule as everything else — and only verifier-clean '
             'chapters appear here.</p>',
             "<h2>Era fingerprints</h2>"]
    for cong in sorted(by_congress, reverse=True):
        d, r = by_congress[cong].get("D"), by_congress[cong].get("R")
        label = (d or r or {}).get("label", f"{cong}th Congress")
        parts.append(f"<h3>{esc(label)}</h3>")
        for party, ch in (("D", d), ("R", r)):
            head = (f'<a href="{esc(ch["id"])}.html">{esc((ch.get("stats") or {}).get("statements"))} '
                    f'statements &rarr;</a>' if ch else '<span class="muted">no verifier-clean chapter</span>')
            parts.append(f'<p><span class="pill {party}">{party}</span> {head}</p>')
            if ch:
                parts.append(_fingerprint((ch.get("stats") or {}).get("top_phrases")))
    months = [c for c in chapters if c.get("kind") == "month"]
    if months:
        links = " · ".join(f'<a href="{esc(c["id"])}.html">{esc(c.get("label"))} {esc(c.get("party"))}</a>'
                           for c in months)
        parts.append(f"<h2>Monthly chapters</h2><p class='subhead'>{len(months)} verifier-clean monthly "
                     f"distillations.</p><p class='muted'><small>{links}</small></p>")
    return "".join(parts)


def chapter_page_body(ch) -> str:
    stats = ch.get("stats") or {}
    party = ch.get("party")
    parts = ['<p class="muted"><a href="index.html">&larr; The Archive</a></p>',
             f'<h1>{esc(ch.get("label"))} <span class="pill {esc(party)}">{esc(party)}</span></h1>']
    for para in (ch.get("text") or "").split("\n"):
        if para.strip():
            parts.append(f"<p>{esc(para.strip())}</p>")
    tps = stats.get("top_phrases") or []
    if tps:
        rows = "".join(
            f"<tr><td>{esc(p.get('phrase'))}</td><td class='num'>{esc(p.get('peak_members'))}</td>"
            f"<td>{esc(p.get('peak_day'))}</td><td>{esc(p.get('first_date'))}</td>"
            f"<td>{esc(p.get('first_sayer'))}</td></tr>" for p in tps)
        parts.append("<h2>Most synchronized phrases</h2><div class='scroll'><table><thead><tr><th>Phrase</th>"
                     "<th class='num'>Peak members</th><th>Peak day</th><th>First recorded</th>"
                     f"<th>First sayer</th></tr></thead><tbody>{rows}</tbody></table></div>")
    parts.append(f'<p class="muted"><small>{esc(stats.get("statements"))} statements this era. Phrase figures '
                 f'deterministic; prose generator {esc(ch.get("generator"))} ({esc(ch.get("prompt_version"))}); '
                 "verifier: passed (zero uncited fragments).</small></p>")
    return "".join(parts)


# --- 1.2 The Silence Detector + "Shouting Into the Void" (dark, docs/11) --------------------------
def _silence_rows(rows, empty_msg) -> str:
    if not rows:
        return f'<p class="muted">{empty_msg}</p>'
    body = "".join(
        f'<tr><td>{esc(r.get("label") or r.get("topic"))}</td>'
        f'<td class="num">{esc(r.get("news_volume"))}</td>'
        f'<td class="num">{esc(r.get("D"))}</td><td class="num">{esc(r.get("R"))}</td></tr>' for r in rows)
    return ("<div class='scroll'><table><thead><tr><th>Topic</th><th class='num'>News volume</th>"
            "<th class='num'>D statements</th><th class='num'>R statements</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>")


def silence_board_body(board) -> str:
    """Both directions on one page — the release gate is that silence and its mirror ship together."""
    day = board.get("day")
    parts = [f"<h1>The absence map <span class='faint'>{esc(day)}</span></h1>",
             '<p class="subhead">Left: topics the day\'s news is full of that <em>neither</em> party\'s '
             'members will touch. Right: topics our members are pushing that the news isn\'t covering. '
             'Both are computed by deterministic code from one published topic list — the same seeds '
             'define the news query and our own match, so you can reproduce either claim.</p>']
    if not board.get("scored"):
        parts.append('<p class="muted"><strong>Not scored for this day.</strong> '
                     f'{esc((board.get("gates") or {}).get("note"))}</p>')
        return "".join(parts)
    parts.append("<h2>Nobody will say it</h2>")
    parts.append(_silence_rows(board.get("silent"), "No topic cleared the silence gate today."))
    parts.append("<h2>Shouting into the void</h2>")
    parts.append(_silence_rows(board.get("void"), "No topic cleared the void gate today."))
    ex = board.get("excluded") or []
    if ex:
        parts.append("<h3>Excluded from scoring</h3><ul>" + "".join(
            f'<li>{esc(e.get("topic"))} <span class="faint">&middot; {esc(e.get("reason"))}</span></li>'
            for e in ex) + "</ul>")
    g = board.get("gates") or {}
    parts.append('<p class="muted"><small>A gap is not a silence: a topic whose news pull failed, or a '
                 'day whose corpus is too thin or one-party, is excluded rather than reported as '
                 f'avoidance. Gates: news&ge;{esc(g.get("news_floor"))}, party quiet&le;'
                 f'{esc(g.get("quiet_max"))}, void&ge;{esc(g.get("void_min"))} with news&le;'
                 f'{esc(g.get("void_news_max"))}. News baseline: GDELT DOC 2.0 (CC-licensed, '
                 "reproducible).</small></p>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# 1.4 The Concordance (R4 / docs/21 §3.2) — the per-member on-script index. DARK until
# FEATURES["concordance"]. A reference INDEX (denominators every line, no motive claim, SPAN-gated,
# both parties together, receipts per named member) — NOT the single-winner author leaderboard /
# Ventriloquism Award that #143/R2 retired. Data (derived/concordance.json) is built every run; only
# this render is gated, so the flip is a pure release act.
# ---------------------------------------------------------------------------
def _member_label(m: dict) -> str:
    """Hardened member label from the concordance row. '(P-ST) · Chamber'."""
    name = member_name(m.get("bioguide"), m.get("name"), include_suffix=False)
    party, state, chamber = m.get("party"), m.get("state"), m.get("chamber")
    if party and state:
        suffix = f" ({esc(party)}-{esc(state)})"
    elif state:
        suffix = f" ({esc(state)})"
    else:
        suffix = ""
    ch = {"house": "House", "senate": "Senate"}.get(chamber or "", "")
    ch_html = f' <span class="faint">{ch}</span>' if ch else ""
    return f"{name}{suffix}{ch_html}"


def _concordance_column(party: str, rows: list, root: str) -> str:
    """One party's column of the Concordance: each named member's on-script share, ranked within the
    party, with the raw counts on every line and expandable receipts."""
    lis = []
    for m in rows:
        if not isinstance(m, dict):
            continue
        st, on = _num(m.get("statements")), _num(m.get("on_script"))
        pct = round(100 * float(m.get("index") or 0), 1)
        receipts = [r for r in (m.get("receipts") or []) if isinstance(r, dict)]
        rc = ""
        if receipts:
            items = []
            for r in receipts:
                url = _safe_http_url(r.get("url"))
                link = f' <a href="{url}" rel="nofollow noopener">source</a>' if url else ""
                items.append(f'<li>&ldquo;{esc(r.get("phrase"))}&rdquo; '
                             f'<span class="faint">{esc(r.get("date"))}</span>{link}</li>')
            rc = (f'<details class="receipts"><summary>{len(receipts)} receipt'
                  f'{"" if len(receipts) == 1 else "s"}</summary><ul>{"".join(items)}</ul></details>')
        lis.append(f'<li><span class="pcount">{esc(pct)}%</span> '
                   f'<span class="faint">{esc(on)} of {esc(st)} statements</span> '
                   f'{_member_label(m)}{rc}</li>')
    body = "".join(lis) or '<li class="muted">No member reached the statement floor for this party.</li>'
    return (f'<div class="pcol"><h3><span class="pill {esc(party)}">{esc(party)}</span> '
            f'on-script share</h3><ol class="pcol-list">{body}</ol></div>')


def concordance_body(cdata: dict, depth: int = 0) -> str:
    """The Concordance page body (1.4 / R4). Every R4 guarantee is on the page: a denominator on every
    line, an explicit no-motive/no-prediction caveat, the SPAN-gate + joint-exclusion disclosure, both
    parties side by side, and the below-floor count named in aggregate (never a per-member zero)."""
    root = "../" * depth
    members = [m for m in (cdata.get("members") or []) if isinstance(m, dict)]
    win = cdata.get("window") or {}
    minst = cdata.get("min_statements")
    floor = cdata.get("peak_floor")
    parts = ["<h1>The Concordance</h1>"]
    parts.append(
        '<p class="subhead">For every member with at least '
        f'{esc(minst)} solo press releases in our corpus, the share of those releases that used a phrase '
        '<strong>their party genuinely converged on</strong> &mdash; one that at least '
        f'{esc(floor)} members reached for on a single day somewhere in our record. Official names (bill '
        'titles, committee names) are excluded, so naming a bill is never counted as being on-script.</p>')
    # R4: no predictive claim. State it plainly, on the page, before any number.
    parts.append(
        '<div class="banner">This is a descriptive measurement of <em>overlap</em> &mdash; not a claim '
        'about motive, direction, or influence. A high share means a member&rsquo;s own releases often '
        'reached for the same phrasing their party converged on; it does <strong>not</strong> mean they '
        'were told to, or that they led. Every score shows its raw counts so you can weigh the sample '
        'yourself.</div>')
    idxv = cdata.get("nomenclature_index_version")
    name_note = (f'the committed nomenclature index ({esc(idxv)})' if idxv
                 else 'the committed nomenclature index (none present in this build &mdash; no names excluded)')
    parts.append(
        f'<p class="muted"><small>Window: {esc(win.get("start"))} &rarr; {esc(win.get("end"))}. '
        f'Official-name exclusion uses {name_note}. Joint / co-signed releases are excluded &mdash; a '
        'signed-together letter is coordination, not a member&rsquo;s solo voice. Both parties are scored '
        'by the identical rule and shown together.</small></p>')
    cols = [_concordance_column(p, [m for m in members if m.get("party") == p], root)
            for p in config.COMPOSITE_PARTIES]
    parts.append(f'<div class="pcols">{"".join(cols)}</div>')
    excl = _num((cdata.get("counts") or {}).get("excluded_below_floor"))
    if excl:
        parts.append(
            f'<p class="muted"><small>{esc(excl)} member{"" if excl == 1 else "s"} had fewer than '
            f'{esc(minst)} solo releases and {"is" if excl == 1 else "are"} not scored here &mdash; too '
            'few statements for a stable share, and too few to cite. Omitted rather than shown at a noisy '
            'or zero score.</small></p>')
    parts.append(f'<p class="muted" style="margin-top:20px"><a href="{root}methodology.html">'
                 'How this is measured &rarr;</a></p>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# 1.5 The Unison + The Void (R2 / docs/21 §3.2) — the symmetric weekly awards that replaced the killed
# Ventriloquism Award. DARK until FEATURES["awards"]. THE UNISON: each party's largest single-day
# office-share phrase (denominator on its face, SPAN-gated, phrase-level so no member is shamed). THE
# VOID: the window's loudest silence, both directions, from the 1.2 board (degrades honestly to
# unavailable). Data (derived/awards.json) is built every run; only this render is gated, so the flip is
# a pure release act.
# ---------------------------------------------------------------------------
def _unison_offices(row) -> str:
    """The offices that said it — the receipts for a Unison card (>= SYNC_MIN by construction)."""
    mem = [m for m in (row.get("members") or []) if isinstance(m, dict)]
    if not mem:
        return ""
    chips = []
    for m in mem:
        nm = member_name(m.get("bioguide"), m.get("name"), include_suffix=False)
        st = f' <span class="faint">({esc(m.get("state"))})</span>' if m.get("state") else ""
        chips.append(f"<li>{nm}{st}</li>")
    more = _num(row.get("members_more"))
    more_html = f'<li class="faint">+{esc(more)} more</li>' if more else ""
    n = _num(row.get("offices_using"))
    return (f'<details class="receipts"><summary>{esc(n)} office{"" if n == 1 else "s"} said it'
            f'</summary><ul>{"".join(chips)}{more_html}</ul></details>')


def _unison_phrase(row, root, slugs) -> str:
    ngram, slug = row.get("ngram", ""), row.get("slug", "")
    if slugs and slug in slugs:
        return f'<a href="{root}phrases/{esc(slug)}.html">{esc(ngram)}</a>'
    return esc(ngram)


def _unison_denoms(row, caucus) -> tuple:
    """(share_pct, denominator-on-its-face string) — offices-using / offices-active, plus the caucus."""
    using, active, day = _num(row.get("offices_using")), _num(row.get("offices_active")), row.get("day")
    share = round(100 * float(row.get("office_share") or 0), 1)
    cd = f" &middot; of {esc(caucus)} in the caucus" if isinstance(caucus, int) and caucus else ""
    return share, f"{esc(using)} of {esc(active)} offices that published on {esc(day)}{cd}"


def _unison_column(party, rows, caucus, root, slugs) -> str:
    """One party's Unison: the award (top office-share phrase) as a card, runners-up as a compact list."""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    head = f'<h3><span class="pill {esc(party)}">{esc(party)}</span> The Unison</h3>'
    if not rows:
        return (f'<div class="pcol">{head}<p class="muted">No phrase reached the office-share threshold '
                'for this party this week — no single-day unison cleared the floor.</p></div>')
    award = rows[0]
    share, denom = _unison_denoms(award, caucus)
    card = (f'<div class="banner"><span class="pcount">{esc(share)}%</span> office-share<br>'
            f'&ldquo;{_unison_phrase(award, root, slugs)}&rdquo;<br>'
            f'<span class="faint">{denom}</span>{_unison_offices(award)}</div>')
    extra = ""
    if len(rows) > 1:
        lis = []
        for r in rows[1:]:
            s, dn = _unison_denoms(r, caucus)
            lis.append(f'<li><span class="pcount">{esc(s)}%</span> '
                       f'&ldquo;{_unison_phrase(r, root, slugs)}&rdquo; '
                       f'<span class="faint">{dn}</span>{_unison_offices(r)}</li>')
        extra = ('<p class="faint" style="margin-top:10px">Also in unison this week</p>'
                 f'<ol class="pcol-list">{"".join(lis)}</ol>')
    return f'<div class="pcol">{head}{card}{extra}</div>'


def _void_table(rows, empty_msg) -> str:
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return f'<p class="muted">{empty_msg}</p>'
    body = "".join(
        f'<tr><td>{esc(r.get("label") or r.get("topic"))}</td>'
        f'<td class="num">{esc(r.get("news_volume"))}</td>'
        f'<td class="num">{esc(r.get("D"))}</td><td class="num">{esc(r.get("R"))}</td>'
        f'<td class="faint">{esc(r.get("day"))}</td></tr>' for r in rows)
    return ("<div class='scroll'><table><thead><tr><th>Topic</th><th class='num'>News volume</th>"
            "<th class='num'>D statements</th><th class='num'>R statements</th><th>Day</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>")


def _void_section(void) -> str:
    parts = ["<h2>The Void</h2>"]
    if not void or not void.get("available"):
        note = (void or {}).get("note") or "The absence map has not been built for this window."
        return "".join(parts) + (f'<p class="muted"><strong>Unavailable this week.</strong> {esc(note)} '
                                 'This award appears once the absence map (the silence detector) is '
                                 'running for the window.</p>')
    parts.append(f'<p class="subhead">{esc(void.get("note"))}</p>')
    ls = void.get("loudest_silence")
    if ls:
        parts.append('<div class="banner">The week&rsquo;s loudest silence: <strong>'
                     f'{esc(ls.get("label") or ls.get("topic"))}</strong> was {esc(ls.get("news_volume"))} '
                     f'of the day&rsquo;s national news on {esc(ls.get("day"))}, and neither party would '
                     f'touch it (D {esc(ls.get("D"))}, R {esc(ls.get("R"))} statements).</div>')
    parts.append("<h3>Nobody would say it</h3>")
    parts.append(_void_table(void.get("silence_top"), "No topic cleared the silence gate this week."))
    parts.append("<h3>Shouting into the void</h3>")
    parts.append(_void_table(void.get("void_top"), "No topic cleared the void gate this week."))
    parts.append(f'<p class="muted"><small>Rolled up from {esc(_num(void.get("boards_scored")))} scored '
                 'daily absence-map boards in this window. A gap is never a silence: a day whose news pull '
                 'failed or whose corpus is too thin is excluded, never reported as avoidance.</small></p>')
    return "".join(parts)


def awards_body(adata, slugs_with_pages=None, depth: int = 0) -> str:
    """The Unison & The Void page (1.5 / R2). Symmetric by construction: both parties scored by one rule,
    every number carries its denominator, no individual member is named as a 'vessel' (the unit is the
    PHRASE / the TOPIC), and the award is explicitly a descriptive overlap — never a claim about motive."""
    root = "../" * depth
    adata = adata or {}
    win = adata.get("window") or {}
    caucus = adata.get("caucus") or {}
    unison = adata.get("unison") or {}
    parts = ["<h1>The Unison &amp; The Void</h1>"]
    parts.append('<p class="subhead">Two symmetric awards, picked by the data on identical rules for both '
                 'parties. <strong>The Unison</strong>: each party&rsquo;s single most-synchronized phrase '
                 'of the week — of the offices that published a release that day, the share that reached '
                 'for one exact phrase. <strong>The Void</strong>: the week&rsquo;s loudest silence — what '
                 'the news was full of that neither party would touch.</p>')
    parts.append('<div class="banner">These are awards about <em>phrases and topics</em>, never about '
                 'individual members. A high office-share means many of a party&rsquo;s offices used the '
                 'same wording that day — a descriptive measurement of overlap, not a claim about motive '
                 'or who told whom. Every number shows its denominator.</div>')
    parts.append(f'<h2>The Unison <span class="faint">{esc(win.get("start"))} &rarr; '
                 f'{esc(win.get("end"))}</span></h2>')
    cols = [_unison_column(p, unison.get(p), caucus.get(p), root, slugs_with_pages)
            for p in config.COMPOSITE_PARTIES]
    parts.append(f'<div class="pcols">{"".join(cols)}</div>')
    ma = adata.get("min_active")
    idxv = adata.get("nomenclature_index_version")
    name_note = (f"the committed nomenclature index ({esc(idxv)})" if idxv
                 else "the committed nomenclature index")
    parts.append('<p class="muted"><small>Office-share = a party&rsquo;s offices using the phrase that day '
                 '&divide; its offices that published any solo release that day. Only days with at least '
                 f'{esc(ma)} active offices are eligible, so a quiet weekend can&rsquo;t win on a '
                 f'two-of-three share. Official names (bill titles, committee names) are excluded via '
                 f'{name_note}, so naming a bill is never a unison. Joint / co-signed releases are excluded '
                 '— that is coordination, not a single office&rsquo;s own wording. Both parties are scored '
                 'by the identical rule.</small></p>')
    parts.append(_void_section(adata.get("void")))
    parts.append(f'<p class="muted" style="margin-top:20px"><a href="{root}methodology.html">'
                 'How this is measured &rarr;</a></p>')
    return "".join(parts)


def build_site():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "day").mkdir(parents=True, exist_ok=True)
    (OUT / "phrases").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FAVICON_SOURCE, OUT / "favicon.png")

    # Art. XIII: delete contaminated phrase pages AND their rendered twins before anything renders.
    # A render-time SKIP is not enough — build_site only ever WRITES (nothing here unlinks) and
    # site/public is git-tracked and deployed, so a skipped page stays live at its public URL.
    purged = privacy.purge_derived()
    if purged:
        print(f"[privacy] purged {len(purged)} contaminated derived/rendered file(s)")

    written = []

    days = all_day_files()  # sorted ascending by day
    day_index = {d: data for d, data in days}
    day_order = [d for d, _ in days]

    # The set of days that ACTUALLY get a page. Computed BEFORE index.html so the homepage can link
    # the previously published day — index.html is the only entry point into the day chain, and it
    # linked to none of it until this was hoisted above the index block.
    rendered = [(d, data) for d, data in days if has_daily_lines(data) or data.get("top_synchronized")]
    rendered_order = [d for d, _ in rendered]

    # ---- index.html (Today = most recent day WITH daily_lines) ----
    today_day = None
    for d, data in reversed(days):
        if has_daily_lines(data):
            today_day = d
            break
    if today_day is None and days:
        today_day = days[-1][0]  # fall back to most recent day at all

    if today_day is not None:
        data = day_index[today_day]
        # The day published before this one. today_day is normally the last rendered day, but the
        # fallback above can pick a day with no page at all — hence the guarded lookup, not [-2].
        try:
            _i = rendered_order.index(today_day)
            home_prev = rendered_order[_i - 1] if _i > 0 else None
        except ValueError:
            home_prev = rendered_order[-1] if rendered_order else None
        body = day_view_body(today_day, data, SLUGS_WITH_PAGES, depth=0,
                             prev_day=home_prev, is_today=True)
        (OUT / "index.html").write_text(
            page(f"OnScript — Today ({today_day})", body, depth=0,
                 description=f"What each U.S. party said on {today_day}, compressed to one voice, with receipts.",
                 path="index.html"),
            encoding="utf-8",
        )
    else:
        (OUT / "index.html").write_text(
            page("OnScript", "<h1>OnScript</h1><p class='muted'>No day data is available yet.</p>", depth=0,
                 path="index.html"),
            encoding="utf-8",
        )
    written.append("index.html")

    # ---- day/<day>.html for every day (with daily_lines OR at least top_synchronized) ----
    # prev/next must reference only days that ACTUALLY get a page (a stub day with neither daily_lines
    # nor top_synchronized is skipped) — else the newest page links a 404 "next day". §Session-7 (D).
    for i, (d, data) in enumerate(rendered):
        prev_day = rendered_order[i - 1] if i > 0 else None
        next_day = rendered_order[i + 1] if i < len(rendered_order) - 1 else None
        body = day_view_body(d, data, SLUGS_WITH_PAGES, depth=1,
                             prev_day=prev_day, next_day=next_day, is_today=False)
        (OUT / "day" / f"{d}.html").write_text(
            page(f"OnScript · {d}", body, depth=1,
                 description=f"What each U.S. party said on {d}.", path=f"day/{d}.html"),
            encoding="utf-8",
        )
        written.append(f"day/{d}.html")

    # ---- day/index.html — the date archive ----
    # Built from the SAME `rendered` list the pages above come from, so the index can never list a
    # 404 or omit a live page (locked in tests/test_day_nav.py). Ungated: this is the table of
    # contents for pages that are already public, not a new feature.
    (OUT / "day" / "index.html").write_text(
        page("OnScript · Every published day", days_index_body(rendered), depth=1,
             description="Every day OnScript has published: composites, receipts, and synchronized phrases, by date.",
             path="day/index.html"),
        encoding="utf-8",
    )
    written.append("day/index.html")

    # ---- phrases/index.html ----
    top = _load_json(DERIVED / "phrases" / "top.json") or {}
    if not (top.get("by_peak") or top.get("by_velocity")):
        # A thin focus day leaves top.json empty; fall back to the most recent rendered day's top
        # phrases so the linked hub is never a blank page. §Session-7 (D).
        for d, data in reversed(rendered):
            ts = data.get("top_synchronized")
            if ts:
                top = {"day": d, "by_peak": ts, "by_velocity": []}
                break
    (OUT / "phrases" / "index.html").write_text(
        page("OnScript · Tracked phrases", phrases_index_body(top), depth=1,
             description="First-appearance tracking and adoption curves for coordinated political phrases.",
             path="phrases/index.html"),
        encoding="utf-8",
    )
    written.append("phrases/index.html")

    # ---- phrases/search.html (1.7b) — dark until FEATURES["phrase_search"] ----
    # Not written at all while dark: an unlinked page still gets crawled and shared, so "built dark"
    # has to mean absent from the output, not merely absent from the nav.
    if config.feature_on("phrase_search"):
        idx = phrase_search_index()
        (OUT / "phrases" / "search.html").write_text(
            page("OnScript · Phrase search", phrase_search_body(idx), depth=1,
                 description="Search tracked political phrases: public-window curves and conditional peak-day source receipts.",
                 path="phrases/search.html"),
            encoding="utf-8",
        )
        written.append("phrases/search.html")

    # ---- phrases/<slug>.html for every phrase page ----
    pdir = DERIVED / "phrases"
    if pdir.exists():
        for p in sorted(pdir.glob("*.json")):
            if p.stem == "top":
                continue
            pdata = _load_json(p)
            if not isinstance(pdata, dict) or not pdata.get("ngram"):
                continue
            # Art. XIII belt to purge_derived's braces: a restored/re-generated JSON can never render.
            if privacy.is_suppressed(pdata.get("ngram") or ""):
                continue
            body = phrase_page_body(pdata, depth=1)
            (OUT / "phrases" / f"{p.stem}.html").write_text(
                page(f"OnScript · “{pdata.get('ngram')}”", body, depth=1,
                     description=f"Adoption curve for the phrase “{pdata.get('ngram')}”.",
                     path=f"phrases/{p.stem}.html"),
                encoding="utf-8",
            )
            written.append(f"phrases/{p.stem}.html")

    # ---- concordance.html (1.4 The Concordance / R4) — dark until FEATURES["concordance"] ----
    # Not written at all while dark: an unlinked page is still crawlable/shareable, so "built dark"
    # means absent from the output, not merely absent from the nav (same rule as phrases/search.html).
    if config.feature_on("concordance"):
        cdata = _load_json(DERIVED / "concordance.json") or {}
        (OUT / "concordance.html").write_text(
            page("OnScript · The Concordance", concordance_body(cdata, depth=0), depth=0,
                 description="The per-member on-script index: each member's share of party-synchronized language, with receipts.",
                 path="concordance.html"),
            encoding="utf-8",
        )
        written.append("concordance.html")

    # ---- awards.html (1.5 The Unison + The Void / R2) — dark until FEATURES["awards"] ----
    # Not written at all while dark: an unlinked page is still crawlable/shareable, so "built dark"
    # means absent from the output, not merely absent from the nav (same rule as concordance.html).
    if config.feature_on("awards"):
        adata = _load_json(DERIVED / "awards.json") or {}
        (OUT / "awards.html").write_text(
            page("OnScript · The Unison & The Void", awards_body(adata, SLUGS_WITH_PAGES, depth=0), depth=0,
                 description="The week's symmetric awards: each party's most-synchronized phrase, and the loudest silence.",
                 path="awards.html"),
            encoding="utf-8",
        )
        written.append("awards.html")

    # ---- methodology.html ----
    (OUT / "methodology.html").write_text(
        page("OnScript · Methodology", methodology_body(), depth=0,
             description="The two-lane model, the nightly symmetry audit, and the live prompt text.",
             path="methodology.html"),
        encoding="utf-8",
    )
    written.append("methodology.html")

    # ---- about.html ----
    (OUT / "about.html").write_text(
        page("OnScript · About", about_body(), depth=0,
             description="Compression, not parody. A symmetric, citation-backed instrument.", path="about.html"),
        encoding="utf-8",
    )
    written.append("about.html")

    # ---- posts.html (signed post archive) — always rendered so the URL is stable; linked in nav
    # only once HAS_POSTS. §Session-8.
    (OUT / "posts.html").write_text(
        page("OnScript · Posted threads", posts_log_body(_POSTED_THREADS), depth=0,
             description="The on-domain signed archive of every thread the composite accounts have posted.",
             path="posts.html"),
        encoding="utf-8",
    )
    written.append("posts.html")

    # ---- The Archive (dark feature 1.1, docs/11) — renders ONLY when FEATURES["archive"] is on
    # (build-dark, §0.2: a dark feature does not render publicly until its flag flips). §BUILD-PROGRAM 1.1.
    if config.feature_on("archive"):
        (OUT / "archive").mkdir(parents=True, exist_ok=True)
        chapters = _load_chapters()
        (OUT / "archive" / "index.html").write_text(
            page("OnScript · The Archive", archive_index_body(chapters), depth=1,
                 description="Twenty-five years of each party's language, distilled per era, with receipts.",
                 path="archive/index.html"),
            encoding="utf-8")
        written.append("archive/index.html")
        for ch in chapters:
            (OUT / "archive" / f"{ch['id']}.html").write_text(
                page(f"OnScript · {ch.get('label')} ({ch.get('party')})", chapter_page_body(ch), depth=1,
                     description=f"{ch.get('label')} — the {ch.get('party')} composite voice for this era, with receipts.",
                     path=f"archive/{ch['id']}.html"),
                encoding="utf-8")
            written.append(f"archive/{ch['id']}.html")

    # ---- 1.2 The absence map (dark) — renders ONLY when FEATURES["silence_board"] is on. Both
    # directions ship together (the release gate); the newest scored board is the landing page.
    if config.feature_on("silence_board"):
        (OUT / "silence").mkdir(parents=True, exist_ok=True)
        boards = sorted((DERIVED / "silence").glob("*.json")) if (DERIVED / "silence").exists() else []
        latest = None
        for f in boards:
            b = _load_json(f)
            if not b:
                continue
            (OUT / "silence" / f"{b.get('day')}.html").write_text(
                page(f"OnScript · The absence map ({b.get('day')})", silence_board_body(b), depth=1,
                     description=f"What the news was full of on {b.get('day')} that neither party would touch.",
                     path=f"silence/{b.get('day')}.html"),
                encoding="utf-8")
            written.append(f"silence/{b.get('day')}.html")
            latest = b
        (OUT / "silence" / "index.html").write_text(
            page("OnScript · The absence map",
                 silence_board_body(latest or {"scored": False, "gates": {"note": "No board has been built yet."}}),
                 depth=1, description="What the news is full of that neither party will touch — and the inverse.",
                 path="silence/index.html"),
            encoding="utf-8")
        written.append("silence/index.html")

    # ---- static-host fallback ----
    (OUT / "404.html").write_text(
        page("OnScript · Page not found",
             '<h1>Page not found</h1><p>The requested page is not in this public record.</p>'
             '<p><a href="index.html">Return to OnScript</a></p>',
             depth=0, description="The requested OnScript page was not found.", path="404.html"),
        encoding="utf-8")
    written.append("404.html")

    # ---- machine-readable discovery surfaces (W2-B) ----
    # Feed entries are driven by the SAME `rendered` set as day pages and contain only deterministic
    # dates + aggregate counts. The sitemap is driven by `written`, so it cannot invent or omit a page.
    (OUT / "feed.xml").write_text(atom_feed(rendered), encoding="utf-8")
    (OUT / "sitemap.xml").write_text(sitemap(written), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {config.SITE_URL}/sitemap.xml\n", encoding="utf-8")

    return written


def main():
    written = build_site()
    print(f"OnScript site built -> {OUT}")
    print(f"Pages written: {len(written)}")
    # Summarize by section to keep the log readable.
    counts = {}
    for w in written:
        section = w.split("/")[0] if "/" in w else w
        counts[section] = counts.get(section, 0) + 1
    for section in sorted(counts):
        print(f"  {section}: {counts[section]}")


if __name__ == "__main__":
    main()
