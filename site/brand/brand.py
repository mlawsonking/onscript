"""OnScript house-account brand assets (apex @onscript.news).

Seismograph burst with echo traces — 'many voices, one script'. The house variant is the parent of
the two party composites: a NEUTRAL slate field, the two parties' colors as SYMMETRIC echoes (blue
fanning up, red fanning down) converging into one white voice. Deterministic (pure math, no RNG).
"""
import math
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


OUT = r"C:\Users\bobdo\AppData\Local\Temp\claude\C--Users-bobdo-projects-polispeak\6a185169-5ff7-4f0d-bf33-f87708b4b3e5\scratchpad"
make(1000, 1000, OUT + r"\avatar-brand.png", amp_frac=0.30)
make(1500, 500, OUT + r"\banner-brand.png", amp_frac=0.62)
print("done")
