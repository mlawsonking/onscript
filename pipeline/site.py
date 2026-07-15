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
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make ``from pipeline import config`` work when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config  # noqa: E402

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
TOPIC_LABEL = {t.get("id"): t.get("label", t.get("id")) for t in TAXONOMY.get("topics", [])}


def member_name(bioguide) -> str:
    """Resolve a bioguide id to a display name, else return the id itself."""
    if not bioguide:
        return "—"
    entry = ROSTER.get(bioguide) if isinstance(ROSTER, dict) else None
    if isinstance(entry, dict):
        name = entry.get("name")
        if name:
            state = entry.get("state")
            party = entry.get("party")
            suffix = ""
            if party and state:
                suffix = f" ({esc(party)}-{esc(state)})"
            elif state:
                suffix = f" ({esc(state)})"
            return f"{esc(name)}{suffix}"
    return esc(bioguide)


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
.spark{display:block}

.nav-pn{display:flex; justify-content:space-between; gap:12px; margin:26px 0; font-size:15px}
.chartbox{border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:12px; margin:16px 0}
.legend{font-size:13px; color:var(--muted); margin:6px 0 0}
.legend .sw{display:inline-block; width:22px; height:0; border-top:3px solid; vertical-align:middle; margin-right:5px}

.kv{display:grid; grid-template-columns:auto 1fr; gap:4px 16px; font-size:14.5px; margin:10px 0}
.kv dt{color:var(--faint)}
.kv dd{margin:0}

pre.prompt{white-space:pre-wrap; word-wrap:break-word; background:#f6f5f1; border:1px solid var(--line);
  border-radius:6px; padding:12px 14px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:13px; line-height:1.5; color:#2a2a2a; overflow-x:auto}
.promptmeta{font-size:12.5px; color:var(--faint); margin:4px 0 2px}

ul.tight{margin:8px 0; padding-left:22px}
ul.tight li{margin:3px 0}

footer.site{border-top:1px solid var(--line); margin-top:50px; padding-top:16px; color:var(--faint); font-size:13px}
footer.site a{color:var(--muted)}
""".strip()


def page(title: str, body: str, depth: int = 0, description: str = "") -> str:
    """Wrap page ``body`` in the shared shell. ``depth`` = subdir levels below
    the site root (0 for /index.html, 1 for /day/*.html and /phrases/*.html)."""
    root = "../" * depth
    # Dark features (docs/11-BUILD-PROGRAM.md) link into the nav only once their FEATURES flag
    # flips True in a commit (the release act). Built-but-unreleased => no public link.
    dark_nav = ""
    if config.feature_on("archive"):
        dark_nav += f'<a href="{root}archive/index.html">Archive</a>'
    # The signed post log links into the nav only once the accounts have actually posted (§Session-8);
    # pre-launch it exists at /posts.html but isn't advertised as an empty page.
    if HAS_POSTS:
        dark_nav += f'<a href="{root}posts.html">Posts</a>'
    nav = (
        f'<a href="{root}index.html">Today</a>'
        f'<a href="{root}phrases/index.html">Phrases</a>'
        f'{dark_nav}'
        f'<a href="{root}methodology.html">Methodology</a>'
        f'<a href="{root}about.html">About</a>'
    )
    desc = esc(description) if description else "OnScript — what each party said today, compressed to one voice, with receipts."
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="site">
  <div class="brand"><a href="{root}index.html">OnScript</a></div>
  <div class="tag">This is what each party said today, compressed to one voice, with receipts.</div>
</header>
<nav class="top">{nav}</nav>
{body}
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
            f'role="img" aria-label="no series">'
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
        f'role="img" aria-label="{n}-day trend, peak {vmax}">'
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
        f'role="img" aria-label="adoption curve" preserveAspectRatio="xMinYMin meet" '
        f'style="min-width:{width}px">'
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


def banner_html(day_data, symmetry) -> str:
    need, msg, has_stub_voice = honesty_state(day_data, symmetry)
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
        cites = [c for c in (tp.get("citations") or []) if isinstance(c, dict)]
        lis = []
        for c in cites[:3]:
            nm = esc(c.get("member"))
            pp, st = c.get("party"), c.get("state")
            suffix = f" ({esc(pp)}-{esc(st)})" if pp and st else (f" ({esc(st)})" if st else "")
            url = _safe_http_url(c.get("url"))
            if url:
                # source + an archival fallback (Wayback), so a rotted .gov link never dead-ends a
                # receipt; the full text is also in our immutable data release. §Session-8.
                src = (f'<a href="{esc(url)}" rel="nofollow noopener">source</a> · '
                       f'<a href="{esc(_wayback_url(url, c.get("date")))}" rel="nofollow noopener">archived</a>')
            else:
                src = '<span class="faint">source</span>'
            q = c.get("quote")
            qhtml = f'<div class="quote">{esc(q)}</div>' if q else ""
            lis.append(
                f'<li>{qhtml}<div class="citemeta">{nm}{suffix} '
                f'<span class="faint">· {esc(c.get("date"))} ·</span> {src}</div></li>'
            )
        cites_html = ('<ul class="cites">' + "".join(lis) + "</ul>") if lis else ""
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
            f'{topics_html}{cites_html}{more_html}</div>'
        )
    return (
        '<div class="receipts"><div class="rlabel">Receipts</div>'
        + "".join(rows)
        + "</div>"
    )


def daily_line_panel(party: str, day_data, caucus: int | None = None) -> str:
    dl = day_data.get("daily_lines") or {}
    line = dl.get(party) if isinstance(dl, dict) else None
    tps = (day_data.get("talking_points") or {}).get(party, []) if isinstance(day_data.get("talking_points"), dict) else []

    who = f'<div class="who">{esc(PARTY_NAME.get(party, party))}</div>'
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


def sync_table(day_data, slugs_with_pages, depth: int) -> str:
    ts = [r for r in (day_data.get("top_synchronized") or []) if isinstance(r, dict)]
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

    parts.append(banner_html(day_data, symmetry))

    # Two Daily Lines side by side (caucus sizes from the day's symmetry audit → denominators in view)
    caucus = {p: ((symmetry or {}).get("parties", {}).get(p, {}) or {}).get("caucus_size")
              for p in ("D", "R")} if isinstance(symmetry, dict) else {}
    parts.append('<div class="lines">')
    parts.append(daily_line_panel("D", day_data, caucus=caucus.get("D")))
    parts.append(daily_line_panel("R", day_data, caucus=caucus.get("R")))
    parts.append("</div>")

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
    parts.append(sync_table(day_data, slugs_with_pages, depth))

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
        parts.append(
            f'<p class="muted" style="margin-top:26px"><a href="{root}phrases/index.html">Browse all tracked phrases &rarr;</a></p>'
        )

    return "".join(parts)


# ---------------------------------------------------------------------------
# Phrase pages
# ---------------------------------------------------------------------------
def phrase_page_body(pdata, depth=1):
    ngram = pdata.get("ngram", "")
    fs = pdata.get("first_seen") or {}
    fs_date = fs.get("date", "")
    fs_bio = fs.get("bioguide")
    peak = pdata.get("peak_units")
    dfw = pdata.get("df_weight")
    series = pdata.get("series") or []

    parts = [f'<h1>&ldquo;{esc(ngram)}&rdquo;</h1>']
    parts.append('<p class="subhead">Adoption curve: how many independent members of each party used this exact phrase, by day.</p>')

    parts.append('<div class="chartbox scroll">')
    parts.append(curve_svg(series))
    parts.append(
        '<p class="legend"><span class="sw" style="border-color:#2b4c7e"></span>Democrats'
        '&nbsp;&nbsp;<span class="sw" style="border-color:#8a2f2f"></span>Republicans</p>'
    )
    parts.append("</div>")

    tie = fs.get("tie") or []
    tie_html = ""
    if tie:
        tie_html = ' <span class="faint">(tied with ' + ", ".join(member_name(b) for b in tie) + ")</span>"

    parts.append('<dl class="kv">')
    parts.append(f"<dt>First said</dt><dd>{esc(fs_date)} by {member_name(fs_bio)}{tie_html}</dd>")
    if peak is not None:
        parts.append(f"<dt>Peak</dt><dd>{esc(peak)} members in one day</dd>")
    if dfw is not None:
        parts.append(f"<dt>Distinctiveness (df_weight)</dt><dd>{esc(dfw)}</dd>")
    parts.append(f"<dt>Data points</dt><dd>{len([r for r in series if isinstance(r, dict)])} active days</dd>")
    parts.append("</dl>")

    parts.append(
        '<p class="muted"><small>Our corpus begins 2025-01. Historical coverage by year is shown on the '
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

    parts.append(render_table(top.get("by_velocity"), "Fastest-spreading", "Ranked by adoption velocity — phrases going viral within a caucus."))
    parts.append(render_table(top.get("by_peak"), "Most synchronized", "Ranked by peak single-day member count."))
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
            '<p class="subhead">Per-year Lane-1 statement counts by party. Cross-era claims are gated on coverage.</p>'
        )
        years = sorted(coverage.keys())
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
        "<p>The derived JSON that powers this site is committed to the project's source repository; raw ingested "
        "statements and the full phrase ledger are published as immutable, date-stamped release assets (repository "
        "and assets are public at launch) so the entire time-series is rebuildable from source. The pipeline is "
        "deterministic: same inputs, same outputs.</p>"
    )
    parts.append(
        "<p><strong>Source links and the archive.</strong> Each receipt links to the member's own .gov release "
        "and, alongside it, to a Wayback Machine capture. Member sites migrate and delete, so a live link can rot "
        "over time — but the exact text we quoted is preserved verbatim in the immutable data release above, so a "
        "dead source link never means lost evidence. A release that is <em>deleted after we cited it</em> is not a "
        "gap in our record; it is a finding, and surfacing those is a planned feature.</p>"
    )
    return "".join(parts)


def about_body():
    parts = ["<h1>About OnScript</h1>"]
    parts.append(
        '<p class="subhead">This is what each party said today, compressed to one voice, with receipts.</p>'
    )
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
        "<a href='methodology.html'>Methodology</a> page (and the project's source repository, which is public "
        "at launch) — every correction is a dated public entry, "
        "never a silent edit. OnScript has no comment section and solicits no engagement; it broadcasts a "
        "measurement and links its receipts.</p>"
    )
    parts.append("<h2>The accounts</h2>")
    parts.append(
        "<p>Two automated composite accounts on Bluesky — one per party, the identical instrument, only the field "
        "color differs:</p>"
    )
    parts.append(
        "<ul class='tight'>"
        "<li><strong>blue.onscript.news</strong> — the composite voice of Democratic members of Congress</li>"
        "<li><strong>red.onscript.news</strong> — the composite voice of Republican members of Congress</li>"
        "</ul>"
    )
    parts.append(
        "<p>At public launch, each will post one citation-backed thread per day, labeled automated, following only "
        "the other, and never replying, liking, or reposting. The accounts are live but have not begun posting; "
        "their bios point here for disclosure.</p>"
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
        '<div class="banner">Honest disclosure: the composite voice is live, but on rare degraded days a line may '
        "fall back to a <strong>dry-run</strong> deterministic stub. Whenever that happens the day's page labels it "
        "plainly; the numbers, quotes, and receipts under every line are always real and verified.</div>"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Signed post archive (§Session-8): the on-domain mirror of every posted thread — forgery defense.
# ---------------------------------------------------------------------------
def posted_threads() -> list:
    """Every thread the composite accounts have actually posted, from the post manifests."""
    out = []
    mdir = DERIVED / "manifest"
    if not mdir.exists():
        return out
    for p in sorted(mdir.glob("post-*.json")):
        m = _load_json(p)
        if not isinstance(m, dict):
            continue
        for r in (m.get("results") or []):
            if r.get("posted") and r.get("thread"):
                out.append({"day": m.get("day"), "generated_at": m.get("generated_at"),
                            "party": r.get("party"), "thread": r.get("thread"), "root_uri": r.get("root_uri")})
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
        '<p class="subhead">Every thread the composite accounts have posted, mirrored here on the domain '
        "and timestamped. <strong>Any post attributed to these accounts that does not appear here is not "
        "ours.</strong> The accounts never reply, like, or repost &mdash; there is nothing else to authenticate.</p>"
    )
    if not threads:
        parts.append('<p class="muted">No posts yet. The accounts are live but have not begun posting.</p>')
        return "".join(parts)
    for t in threads:
        party = t.get("party")
        head = (f'<span class="pill {esc(party)}">{esc(party)}</span> <strong>{esc(t.get("day"))}</strong> '
                f'<span class="faint">&middot; {esc(t.get("generated_at"))}</span>')
        web = _bsky_web_url(t.get("root_uri"))
        link = f' &middot; <a href="{esc(web)}" rel="nofollow noopener">on Bluesky</a>' if web else ""
        posts = "".join(f'<div class="quote">{esc(p)}</div>' for p in (t.get("thread") or []))
        parts.append(f'<div class="receipt"><div class="rhead">{head}{link}</div>{posts}</div>')
    return "".join(parts)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
SLUGS_WITH_PAGES = phrase_page_slugs()
_POSTED_THREADS = posted_threads()
HAS_POSTS = bool(_POSTED_THREADS)


def build_site():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "day").mkdir(parents=True, exist_ok=True)
    (OUT / "phrases").mkdir(parents=True, exist_ok=True)

    written = []

    days = all_day_files()  # sorted ascending by day
    day_index = {d: data for d, data in days}
    day_order = [d for d, _ in days]

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
        body = day_view_body(today_day, data, SLUGS_WITH_PAGES, depth=0, is_today=True)
        (OUT / "index.html").write_text(
            page(f"OnScript — Today ({today_day})", body, depth=0,
                 description=f"What each U.S. party said on {today_day}, compressed to one voice, with receipts."),
            encoding="utf-8",
        )
    else:
        (OUT / "index.html").write_text(
            page("OnScript", "<h1>OnScript</h1><p class='muted'>No day data is available yet.</p>", depth=0),
            encoding="utf-8",
        )
    written.append("index.html")

    # ---- day/<day>.html for every day (with daily_lines OR at least top_synchronized) ----
    # prev/next must reference only days that ACTUALLY get a page (a stub day with neither daily_lines
    # nor top_synchronized is skipped) — else the newest page links a 404 "next day". §Session-7 (D).
    rendered = [(d, data) for d, data in days if has_daily_lines(data) or data.get("top_synchronized")]
    rendered_order = [d for d, _ in rendered]
    for i, (d, data) in enumerate(rendered):
        prev_day = rendered_order[i - 1] if i > 0 else None
        next_day = rendered_order[i + 1] if i < len(rendered_order) - 1 else None
        body = day_view_body(d, data, SLUGS_WITH_PAGES, depth=1,
                             prev_day=prev_day, next_day=next_day, is_today=False)
        (OUT / "day" / f"{d}.html").write_text(
            page(f"OnScript · {d}", body, depth=1,
                 description=f"What each U.S. party said on {d}."),
            encoding="utf-8",
        )
        written.append(f"day/{d}.html")

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
             description="First-appearance tracking and adoption curves for coordinated political phrases."),
        encoding="utf-8",
    )
    written.append("phrases/index.html")

    # ---- phrases/<slug>.html for every phrase page ----
    pdir = DERIVED / "phrases"
    if pdir.exists():
        for p in sorted(pdir.glob("*.json")):
            if p.stem == "top":
                continue
            pdata = _load_json(p)
            if not isinstance(pdata, dict) or not pdata.get("ngram"):
                continue
            body = phrase_page_body(pdata, depth=1)
            (OUT / "phrases" / f"{p.stem}.html").write_text(
                page(f"OnScript · “{pdata.get('ngram')}”", body, depth=1,
                     description=f"Adoption curve for the phrase “{pdata.get('ngram')}”."),
                encoding="utf-8",
            )
            written.append(f"phrases/{p.stem}.html")

    # ---- methodology.html ----
    (OUT / "methodology.html").write_text(
        page("OnScript · Methodology", methodology_body(), depth=0,
             description="The two-lane model, the nightly symmetry audit, and the live prompt text."),
        encoding="utf-8",
    )
    written.append("methodology.html")

    # ---- about.html ----
    (OUT / "about.html").write_text(
        page("OnScript · About", about_body(), depth=0,
             description="Compression, not parody. A symmetric, citation-backed instrument."),
        encoding="utf-8",
    )
    written.append("about.html")

    # ---- posts.html (signed post archive) — always rendered so the URL is stable; linked in nav
    # only once HAS_POSTS. §Session-8.
    (OUT / "posts.html").write_text(
        page("OnScript · Posted threads", posts_log_body(_POSTED_THREADS), depth=0,
             description="The on-domain signed archive of every thread the composite accounts have posted."),
        encoding="utf-8",
    )
    written.append("posts.html")

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
