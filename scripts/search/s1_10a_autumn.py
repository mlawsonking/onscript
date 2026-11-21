"""S1.10a, the autumn re-registration of S1.10 (Bipartisanship Has a Season). REVISION 2.

CONFIRMATORY MEASUREMENT SCRIPT. Frozen together with PREREG.md and s1_10a-registration.json.
Written and tested on SYNTHETIC fixtures only (test_s1_10a_fixture.py). Never run on the corpus.
Do not run it on the corpus until the registration is committed and hashed in an earlier commit;
the run lands in a separate later commit (the HX.5 / S4.4 freeze-then-measure pattern).

Revision 2 replaces the anchor-contrast statistic S(y) of revision 1. That statistic telescoped:
consecutive 90-day contrasts share windows, so the Feb/May/Aug terms cancelled and S reduced to
autumn and winter levels already committed in revalidate_s1_4_s1_10.json (Fable review, 2026-11-13).
Revision 2 measures four fixed, non-overlapping seasons and decides on the spring and summer levels,
which no committed artifact contains.

Seasons of calendar year y (inclusive dates; Nov 4 and Feb 3-6 belong to no season):
  Q1 spring  y-02-07 .. y-05-07     (90 days; 91 in leap years)
  Q2 summer  y-05-08 .. y-08-05     (90 days)
  Q3 autumn  y-08-06 .. y-11-03     (90 days; = the committed S1.10 pre-Nov-4 window)
  Q4 winter  y-11-05 .. (y+1)-02-02 (90 days; = the committed S1.10 post-Nov-4 window)
Q1 and Q2 are disjoint from every window S1.10 ever measured (its earliest pre window starts Aug 6;
its latest post window ends Feb 6).

rate(Q) = statements with >=1 frozen phrase / all D+R statements in Q and its lane (share, 0..1).
Per year:
  D_summer = Q2 - Q3      autumn below the preceding summer     (blind: Q2 never measured)
  D_spring = Q1 - Q3      autumn below the preceding spring     (blind: Q1 never measured)
  T        = mean(Q2, Q4) - Q3   autumn below summer and winter (half blind: Q4 - Q3 is committed;
                                 cannot bind in C1, guards a falling within-year ramp in C2/C3)
  W        = Q4 - Q3      the committed contrast, recounted under strict lanes (reported, not decisive)
A year SUPPORTS H1 iff D_summer > DELTA and D_spring > DELTA and T > DELTA.

Lanes (docs/12 L1; R-S50.1): each season is measured in ONE isolated lane.
  legacy  : season wholly in 2013-01-03 .. 2020-12-31, counting date_source == "legacy" only
  scraper : season wholly on or after 2021-01-04, counting date_source == "scraper" only
  otherwise invalid (only 2020's winter, which crosses the seam).

Re-runnable (after the registration commit):
  C:\\ProgramData\\miniconda3\\python.exe scripts/search/s1_10a_autumn.py --test C1 --confirmatory

Committed S74-8 (R-74.6) beside its registration, data/reference/search/s1_10a-registration.json,
whose sha256 is pinned below: the script refuses to measure against any other bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Must equal pipeline.search.wave_s1._BIPARTISAN at the registration commit (asserted at run time).
PHRASES = ("bipartisan", "across the aisle", "both sides of the aisle", "reach across the aisle",
           "my republican colleague", "my democratic colleague", "republican and democratic colleague")

# The committed registration (R-74.6). The run refuses unless the file's bytes hash to this value.
REGISTRATION_PATH = "data/reference/search/s1_10a-registration.json"
REGISTRATION_SHA256 = "67c364fd7e5e4651144f987b0b95942d5e506247e2cbaa3d2c785469db6cb0bc"

SEASONS = ("Q1", "Q2", "Q3", "Q4")
DELTA = 0.01                 # minimum size, absolute share (one percentage point), every criterion
FLOOR = 200                  # D+R statements per season per lane (docs/12 §1.6)
MIN_YEARS_C1 = 8
SHARE = 0.9                  # C1: supporting years >= ceil(SHARE * n)

LEGACY_LO, LEGACY_HI = "2013-01-03", "2020-12-31"
SCRAPER_LO = "2021-01-04"

TESTS = {
    "C1": (list(range(2013, 2026)), "2026-11-13"),
    "C2": ([2026], "2027-02-16"),
    "C3": ([2027], "2028-02-16"),
}


def season_bounds(year: int, q: str) -> tuple[str, str]:
    return {
        "Q1": (f"{year}-02-07", f"{year}-05-07"),
        "Q2": (f"{year}-05-08", f"{year}-08-05"),
        "Q3": (f"{year}-08-06", f"{year}-11-03"),
        "Q4": (f"{year}-11-05", f"{year + 1}-02-02"),
    }[q]


def lane_for(lo: str, hi: str) -> str | None:
    if lo >= LEGACY_LO and hi <= LEGACY_HI:
        return "legacy"
    if lo >= SCRAPER_LO:
        return "scraper"
    return None


def has_phrase(text: str) -> int:
    low = (text or "").lower()
    return 1 if any(p in low for p in PHRASES) else 0


def measure(records, years, *, robustness_folded=False):
    """records: iterable of {date, party, text, date_source}. Pure function of its input, so the
    synthetic fixtures exercise exactly the code the confirmatory run executes."""
    plan = []                                   # (lo, hi, lane, year, q)
    invalid = {}
    for y in years:
        for q in SEASONS:
            lo, hi = season_bounds(y, q)
            lane = lane_for(lo, hi)
            if lane is None:
                invalid[(y, q)] = f"{lo}..{hi} crosses the seam or precedes 2013-01-03"
            else:
                plan.append((lo, hi, lane, y, q))
    sources = {"legacy": {"legacy"},
               "scraper": {"scraper", "page_html"} if robustness_folded else {"scraper"}}
    cells = defaultdict(lambda: defaultdict(lambda: [0, 0]))     # (y,q) -> party -> [hits, n]
    for r in records:
        p = r.get("party")
        if p not in ("D", "R"):
            continue
        d = (r.get("date") or "")[:10]
        if len(d) != 10:
            continue
        src = r.get("date_source")
        for lo, hi, lane, y, q in plan:          # seasons are disjoint: at most one match
            if lo <= d <= hi and src in sources[lane]:
                c = cells[(y, q)][p]
                c[0] += has_phrase(r.get("text"))
                c[1] += 1
                break

    out = {}
    for y in years:
        row = {"seasons": {}, "valid": True, "reasons": []}
        for q in SEASONS:
            lo, hi = season_bounds(y, q)
            if (y, q) in invalid:
                row["seasons"][q] = {"invalid": invalid[(y, q)]}
                row["valid"] = False
                row["reasons"].append(f"{q}: {invalid[(y, q)]}")
                continue
            entry = {"window": [lo, hi], "lane": lane_for(lo, hi)}
            for scope, parties in (("pooled", ("D", "R")), ("D", ("D",)), ("R", ("R",))):
                h = sum(cells[(y, q)][x][0] for x in parties)
                n = sum(cells[(y, q)][x][1] for x in parties)
                entry[scope] = {"rate": (h / n) if n else None, "n": n, "powered": n >= FLOOR}
            if not entry["pooled"]["powered"]:
                row["valid"] = False
                row["reasons"].append(f"{q}: pooled season below the {FLOOR}-statement floor")
            row["seasons"][q] = entry
        for scope in ("pooled", "D", "R"):
            rates = {q: (row["seasons"][q].get(scope) or {}) for q in SEASONS}
            if row["valid"] and all(rates[q].get("powered") for q in SEASONS):
                q1, q2, q3, q4 = (rates[q]["rate"] for q in SEASONS)
                stats = {"D_summer": q2 - q3, "D_spring": q1 - q3, "T": (q2 + q4) / 2 - q3, "W": q4 - q3}
                stats["supports"] = (stats["D_summer"] > DELTA and stats["D_spring"] > DELTA
                                     and stats["T"] > DELTA)
                # Reported only (registration "reported_only"): each difference in binomial
                # standard-error units. Never part of the decision.
                var = {q: rates[q]["rate"] * (1 - rates[q]["rate"]) / rates[q]["n"] for q in SEASONS}
                se = {"D_summer": math.sqrt(var["Q2"] + var["Q3"]),
                      "D_spring": math.sqrt(var["Q1"] + var["Q3"]),
                      "T": math.sqrt((var["Q2"] + var["Q4"]) / 4 + var["Q3"]),
                      "W": math.sqrt(var["Q4"] + var["Q3"])}
                stats["se_units"] = {k: (stats[k] / s if s > 0 else None) for k, s in se.items()}
            else:
                stats = None
            row[f"stats_{scope}"] = stats
        out[y] = row
    return out


def binom_tail(k: int, n: int) -> float:
    """P(X >= k), X ~ Binomial(n, 1/2). Descriptive only."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def verdict_c1(rows: dict) -> dict:
    valid = [y for y, r in rows.items() if r["stats_pooled"] is not None]
    n = len(valid)
    need = math.ceil(SHARE * n) if n else None

    def count(key, scope="pooled"):
        return sum(1 for y in valid
                   if rows[y][f"stats_{scope}"] is not None and rows[y][f"stats_{scope}"][key] > DELTA)
    k_all = sum(1 for y in valid if rows[y]["stats_pooled"]["supports"])
    if n < MIN_YEARS_C1:
        v = "UNDERPOWERED"
    elif k_all >= need:
        v = "CONFIRMED"
    else:
        v = "REFUTED"
    party = {}
    for p in ("D", "R"):
        pv = [y for y in valid if rows[y][f"stats_{p}"] is not None]
        party[p] = {"n": len(pv), "k_supports": sum(1 for y in pv if rows[y][f"stats_{p}"]["supports"]),
                    "k_D_summer": count("D_summer", p), "k_D_spring": count("D_spring", p),
                    "k_T": count("T", p)}
    return {"valid_years": valid, "n": n, "need": need, "delta": DELTA,
            "k_supports": k_all, "k_D_summer": count("D_summer"), "k_D_spring": count("D_spring"),
            "k_T": count("T"), "k_W_strict_lane": count("W"),
            "binom_tail_k_supports": binom_tail(k_all, n) if n else None,
            "per_party_descriptive": party, "verdict": v}


def verdict_single(rows: dict, year: int) -> dict:
    r = rows.get(year)
    if not r or r["stats_pooled"] is None:
        return {"year": year, "verdict": "UNDERPOWERED", "reasons": (r or {}).get("reasons")}
    s = r["stats_pooled"]
    return {"year": year, **{k: s[k] for k in ("D_summer", "D_spring", "T", "W")},
            "se_units": s["se_units"], "verdict": "PASS" if s["supports"] else "FAIL"}


def _repo_root() -> Path:
    env = os.environ.get("ONSCRIPT_REPO")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    if (here.parents[2] / "pipeline").is_dir():
        return here.parents[2]
    raise SystemExit("set ONSCRIPT_REPO to the repository root")


def main(argv=None):
    ap = argparse.ArgumentParser(description="S1.10a confirmatory run (revision 2)")
    ap.add_argument("--test", choices=sorted(TESTS), required=True)
    ap.add_argument("--confirmatory", action="store_true",
                    help="required to touch the corpus; asserts the registration is committed")
    ap.add_argument("--registration", default=REGISTRATION_PATH)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if not a.confirmatory:
        raise SystemExit("refusing: frozen confirmatory script. Pass --confirmatory only after the "
                         "registration is committed in an earlier commit.")
    years, earliest = TESTS[a.test]
    today = date.today().isoformat()
    if today < earliest:
        raise SystemExit(f"refusing: {a.test} may not run before {earliest} (today {today}).")
    root = _repo_root()
    sys.path.insert(0, str(root))
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", a.registration],
                             capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", a.registration],
                           capture_output=True, text=True).stdout.strip()
    if tracked.returncode != 0 or dirty:
        raise SystemExit("refusing: the registration must be committed and unmodified before the run")
    reg_sha = hashlib.sha256((root / a.registration).read_bytes()).hexdigest()
    if reg_sha != REGISTRATION_SHA256:
        raise SystemExit(f"refusing: {a.registration} hashes to {reg_sha}, not the committed "
                         f"registration {REGISTRATION_SHA256}")
    from pipeline.search import harness as H
    from pipeline.search import wave_s1
    if tuple(wave_s1._BIPARTISAN) != PHRASES:
        raise SystemExit("refusing: wave_s1._BIPARTISAN differs from the frozen phrase list")

    def records():
        yield from H.iter_statements(congresses=None, with_text=True, lane=None)
    rows = measure(records(), years)
    result = {"id": "S1.10a", "revision": 2, "test": a.test, "registration_sha256": reg_sha,
              "run_date": today, "years": {str(y): r for y, r in rows.items()}}
    result["decision"] = verdict_c1(rows) if a.test == "C1" else verdict_single(rows, years[0])
    # Labelled robustness view (R-S50.1): post-seam years on folded scraped. Never decisive.
    folded = measure(records(), [y for y in years if y >= 2021], robustness_folded=True)
    result["robustness_folded_scraped"] = {str(y): r["stats_pooled"] for y, r in folded.items()}
    dest = Path(a.out) if a.out else root / "data" / "derived" / "search" / f"s1_10a_{a.test.lower()}.json"
    dest.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(f"S1.10a {a.test}: registration sha256 {reg_sha}")
    print(json.dumps(result["decision"], indent=1, default=str))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
