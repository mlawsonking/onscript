"""OnScript house-account brand assets (apex @onscript.news).

Seismograph burst with echo traces — 'many voices, one script'. The house variant is the parent of
the two party composites: a NEUTRAL slate field, the two parties' colors as SYMMETRIC echoes (blue
fanning up, red fanning down) converging into one white voice. Deterministic (pure math, no RNG).
"""
import math
import pathlib

from PIL import Image, ImageDraw, ImageFilter

FIELD = (46, 49, 56)        # #2E3138 neutral slate — clearly neither party
BLUE = (29, 78, 137)        # #1D4E89 (matches the D avatar field)
RED = (166, 25, 46)         # #A6192E (matches the R avatar field)
WHITE = (250, 250, 247)     # #FAFAF7 trace


def trace_points(W, H, cx_frac=0.5, amp_frac=0.30, spread_frac=0.115, n_osc=2.7,
                 ripple_frac=0.020, phase=0.0, n=1400):
    """A wave packet: a Gaussian-enveloped oscillation (the central burst) on a rippled baseline."""
    cx = W * cx_frac
    cy = H * 0.5
    A = H * amp_frac
    spread = W * spread_frac
    k = math.pi * n_osc / spread
    pts = []
    for i in range(n):
        x = W * i / (n - 1)
        env = math.exp(-((x - cx) / spread) ** 2)
        carrier = math.sin((x - cx) * k + phase)
        ripple = ripple_frac * A * math.sin(x * 2 * math.pi * 8 / W + phase)
        y = cy - (A * env * carrier + ripple)
        pts.append((x, y))
    return pts


def _line(draw, pts, color, width, dy=0):
    draw.line([(x, y + dy) for x, y in pts], fill=color, width=width, joint="curve")


def make(W, H, path, amp_frac=0.30):
    img = Image.new("RGB", (W, H), FIELD)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    step = int(H * 0.050)
    lw = max(8, int(H * 0.024))
    base = trace_points(W, H, amp_frac=amp_frac)
    # symmetric echoes: blue fans up, red fans down; fainter + phase-shifted with distance
    for j in range(4, 0, -1):
        a = int(150 * (1 - (j - 1) * 0.22))
        ph = 0.28 * j
        _line(d, trace_points(W, H, amp_frac=amp_frac, phase=ph), BLUE + (a,), lw, dy=-j * step)
        _line(d, trace_points(W, H, amp_frac=amp_frac, phase=-ph), RED + (a,), lw, dy=j * step)
    ov = ov.filter(ImageFilter.GaussianBlur(max(1, H * 0.006)))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    # crisp white main trace on top
    d2 = ImageDraw.Draw(img)
    _line(d2, base, WHITE, int(lw * 1.15))
    img.save(path)
    return path


# Generation runs only as a script. It used to run AT IMPORT, into a hard-coded scratchpad path from a
# long-dead session — so importing this module for its palette silently wrote files nobody would find,
# and the paths could never be reproduced on another machine. Repo-relative + __main__-guarded.
#
# Regeneration is byte-stable (pure math, no RNG), so re-running never churns the committed assets —
# which matters, because the avatars and banners are LIVE on the three Bluesky profiles.
HERE = pathlib.Path(__file__).resolve().parent
PUBLIC = HERE.parent / "public"

TARGETS = [
    # (width, height, path, amp_frac)
    (1000, 1000, HERE / "avatar-brand.png", 0.30),
    (1500, 500, HERE / "banner-brand.png", 0.62),
    # The link-card image: 1200x630 is the Open Graph standard Bluesky, Slack and iMessage all crop to.
    # Geometry only — the crawler renders og:title/og:description as text beside it, so words baked
    # into the image would just collide with them. Lives in site/public so Vercel serves it at
    # https://onscript.news/og.png (see config.OG_IMAGE).
    (1200, 630, PUBLIC / "og.png", 0.42),
]

if __name__ == "__main__":
    for w, h, path, amp in TARGETS:
        path.parent.mkdir(parents=True, exist_ok=True)
        make(w, h, path, amp_frac=amp)
        print(f"wrote {path} ({w}x{h})")
