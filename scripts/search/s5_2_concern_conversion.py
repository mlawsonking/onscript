"""S5.2 measurement — The Concern Conversion Rate. Implements EXACTLY the frozen registration
`data/reference/search/s5_2-registration.json` (committed 2026-07-20 BEFORE this run, commit 5cd27da).
No knob is added here; every parameter is read from the registration.

Pipeline:
  1. Parse govinfo BILLSTATUS 113-119 (local) -> per-member sponsorships (bioguide, introducedDate,
     title/policyArea/legislativeSubjects). Cached raw to X:; tokenized at measure time.
  2. Scan the congress-press corpus: normalize per congress (for the solo/non-syndicated/Lane-1 filter),
     detect concern statements (frozen 31-phrase directed lexicon), extract topic-of-concern from the
     concern sentence(s).
  3. Conversion = the same member sponsors an on-topic bill (>=K shared content tokens between the
     concern topic and the bill's title+policyArea+subjects) with introducedDate in (date, date+180d].
     K=2 primary; K=1/K=3/CRS-tags-only reported as bounds. Right-censoring guard applied.
  4. Aggregate per cell (pooled / D / R / party x era-half), apply the 300 floor + comparative gate.

Re-runnable:  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/s5_2_concern_conversion.py
"""
from __future__ import annotations

import bisect
import datetime
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria, boilerplate, normalize, util  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REG_PATH = ROOT / "data" / "reference" / "search" / "s5_2-registration.json"
BILLS_RAW = Path("X:/onscript-data/bills/raw")
BILLS_DERIVED = Path("X:/onscript-data/bills/derived")
SPONS_CACHE = BILLS_DERIVED / "s5_2-sponsorships.jsonl"
RESULT = ROOT / "scripts" / "search" / "evidence" / "s5_2_concern_conversion.result.json"
EVID = Path("X:/onscript-data/elections/derived")  # reuse the search-evidence dir on X:

HALF_OF = {113: ("propublica", "A"), 114: ("propublica", "A"),
           115: ("propublica", "B"), 116: ("propublica", "B"),
           117: ("scraped", "A"), 118: ("scraped", "B"), 119: ("scraped", "B")}
_YEAR_TAIL = re.compile(r"(\s+of)?\s+(19|20)\d{2}\s*$", re.I)  # registration: titles year-stripped


# ------------------------------------------------------------------ frozen registration -> knobs
REG = json.loads(REG_PATH.read_text(encoding="utf-8"))
P = REG["parameters"]
WINDOW = P["window_days"]
K_PRIMARY = 2
KS = (1, 2, 3)
STOP = boilerplate.STOPWORDS
GENERIC = set(P["generic_stoplist"])


def _toks(text: str) -> list[str]:
    out: list[str] = []
    for sent in boilerplate.sentences(text):
        out.extend(sent)
    return out


# lexicon phrases -> token tuples (same tokenizer); the union of their tokens is excluded from content
LEX_TUPLES = tuple(tuple(_toks(p)) for p in REG["concern_lexicon"])
CONCERN_TOKENS = {t for tup in LEX_TUPLES for t in tup}
# cheap raw-substring gate: every lexicon phrase contains one of these stems (no false negatives)
CONCERN_ROOTS = ("concern", "alarm", "troubl", "worri", "outrag", "dismay", "appall", "disturb")


def content(tok_list) -> set:
    return {t for t in tok_list if t not in STOP and t not in CONCERN_TOKENS and t not in GENERIC}


def _subseq(seq, sub) -> bool:
    n = len(sub)
    if not n:
        return False
    return any(tuple(seq[i:i + n]) == sub for i in range(len(seq) - n + 1))


def _add_days(diso: str, days: int) -> str:
    y, m, d = int(diso[:4]), int(diso[5:7]), int(diso[8:10])
    return (datetime.date(y, m, d) + datetime.timedelta(days=days)).isoformat()


# ------------------------------------------------------------------ Step 1: BILLSTATUS -> sponsorships
def parse_billstatus() -> None:
    """Raw sponsorship fields -> X: cache (one JSON line per bill). Skips if the cache exists."""
    if SPONS_CACHE.exists():
        print(f"sponsorship cache present: {SPONS_CACHE}", flush=True)
        return
    BILLS_DERIVED.mkdir(parents=True, exist_ok=True)
    zips = sorted(BILLS_RAW.glob("BILLSTATUS-*.zip"))
    n_bills = 0
    with open(SPONS_CACHE, "w", encoding="utf-8") as w:
        for zp in zips:
            got = 0
            with zipfile.ZipFile(zp) as z:
                for member in z.namelist():
                    if not member.endswith(".xml"):
                        continue
                    try:
                        root = ET.fromstring(z.read(member))
                    except ET.ParseError:
                        continue
                    bill = root.find(".//bill")
                    if bill is None:
                        continue
                    bio = bill.findtext(".//sponsors/item/bioguideId")
                    date = (bill.findtext("introducedDate") or "")[:10]
                    if not bio or len(date) != 10:
                        continue
                    title = (bill.findtext("title") or "").strip()
                    pa = (bill.findtext(".//policyArea/name") or "").strip()
                    subs = [s.text.strip() for s in bill.findall(
                        ".//subjects/billSubjects/legislativeSubjects/item/name") if s.text]
                    w.write(json.dumps({"bio": bio, "date": date, "title": title, "pa": pa, "subs": subs},
                                       separators=(",", ":")) + "\n")
                    got += 1
                    n_bills += 1
            print(f"  {zp.name}: {got} sponsored bills", flush=True)
    print(f"parsed {n_bills} sponsored bills -> {SPONS_CACHE}", flush=True)


def load_sponsorships():
    """bioguide -> (dates[sorted], full_topics[], tag_topics[]) parallel arrays; + latest introducedDate."""
    dates = defaultdict(list)
    fulls = defaultdict(list)
    tags = defaultdict(list)
    latest = ""
    raw = defaultdict(list)
    with open(SPONS_CACHE, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            title = _YEAR_TAIL.sub("", r["title"])
            tt = content(_toks(title))
            tag = content(_toks((r["pa"] or "") + " . " + " . ".join(r["subs"] or [])))
            raw[r["bio"]].append((r["date"], tt | tag, tag))
            latest = max(latest, r["date"])
    for bio, lst in raw.items():
        lst.sort(key=lambda x: x[0])
        dates[bio] = [x[0] for x in lst]
        fulls[bio] = [x[1] for x in lst]
        tags[bio] = [x[2] for x in lst]
    return dates, fulls, tags, latest


# ------------------------------------------------------------------ Step 2: concern statements
def concern_topic(text: str):
    """None if not a concern statement (no lexicon phrase); else the union content-token set of its
    concern sentence(s) (possibly empty -> a concern with no extractable topic)."""
    low = text.lower()
    if not any(r in low for r in CONCERN_ROOTS):
        return None
    topic = set()
    hit = False
    for sent in boilerplate.sentences(text):
        if any(_subseq(sent, lp) for lp in LEX_TUPLES):
            hit = True
            topic |= content(sent)
    return topic if hit else None


# ------------------------------------------------------------------ Step 3+4: measure
def cells_for(party: str, congress: int):
    out = ["pooled", party]
    hc = HALF_OF.get(congress)
    if hc:
        out.append(f"{party}:{hc[0]}-{hc[1]}")
    return out


def main():
    print(f"registration: {REG_PATH.name}  window={WINDOW}d  K_primary={K_PRIMARY}  "
          f"lexicon={len(LEX_TUPLES)} phrases  floor={REG['floor_and_cells']['floor_per_cell']}", flush=True)
    parse_billstatus()
    dates, fulls, tags, latest = load_sponsorships()
    print(f"sponsorships: {len(dates)} members, latest introducedDate={latest}", flush=True)

    agg = defaultdict(lambda: {"eligible": 0, "conv1": 0, "conv2": 0, "conv3": 0, "convtags": 0})
    excl = {"no_topic": 0, "censored": 0, "concern_stmts": 0}

    for c in range(113, 120):
        recs = alexandria.load_congress_records(c, lane=None)
        stmts = normalize.normalize_records(recs, run_id=f"s5_2-{c}")
        cs = 0
        for s in stmts:
            if s.get("lane") != 1 or s.get("syndicated") or s.get("joint_group"):
                continue
            m = s.get("member") or {}
            party, bio = m.get("party"), m.get("bioguide")
            if party not in ("D", "R") or not bio:
                continue
            topic = concern_topic(s.get("text", ""))
            if topic is None:
                continue
            cs += 1
            excl["concern_stmts"] += 1
            if not topic:
                excl["no_topic"] += 1
                continue
            date = s["published_at"]
            hi = _add_days(date, WINDOW)
            if hi > latest:                      # right-censoring guard
                excl["censored"] += 1
                continue
            conv = {1: False, 2: False, 3: False, "tags": False}
            bd = dates.get(bio)
            if bd:
                lo_i = bisect.bisect_right(bd, date)     # strictly after the concern date
                hi_i = bisect.bisect_right(bd, hi)       # through date+180 inclusive
                bf, bt = fulls[bio], tags[bio]
                for i in range(lo_i, hi_i):
                    ov = len(topic & bf[i])
                    if ov >= 1:
                        conv[1] = True
                        if ov >= 2:
                            conv[2] = True
                            if ov >= 3:
                                conv[3] = True
                    if len(topic & bt[i]) >= 2:
                        conv["tags"] = True
                    if conv[3] and conv["tags"]:
                        break
            for cell in cells_for(party, c):
                a = agg[cell]
                a["eligible"] += 1
                for K in KS:
                    a[f"conv{K}"] += conv[K]
                a["convtags"] += conv["tags"]
        print(f"  congress {c}: {len(stmts)} statements, {cs} concern statements", flush=True)

    # ---- rates + floor + comparative gate
    def rate(a, key):
        return round(a[key] / a["eligible"], 4) if a["eligible"] else None

    floor = REG["floor_and_cells"]["floor_per_cell"]
    cells = {}
    for name, a in agg.items():
        n = a["eligible"]
        r2 = rate(a, "conv2")
        # 95% CI half-width for the PRIMARY (K=2) conversion proportion
        hw = round(1.96 * ((r2 * (1 - r2) / n) ** 0.5), 4) if (r2 is not None and n) else None
        cells[name] = {
            "eligible": n, "powered": n >= floor,
            "conversion_K2": r2, "nonconversion_K2": (round(1 - r2, 4) if r2 is not None else None),
            "ci95_halfwidth_K2": hw,
            "conversion_K1": rate(a, "conv1"), "conversion_K3": rate(a, "conv3"),
            "conversion_tags_only": rate(a, "convtags"),
        }

    # comparative gate, per era-half + overall D vs R
    comps = {}
    for label, (dc, rc) in {"overall": ("D", "R"),
                            "propublica-A": ("D:propublica-A", "R:propublica-A"),
                            "propublica-B": ("D:propublica-B", "R:propublica-B"),
                            "scraped-A": ("D:scraped-A", "R:scraped-A"),
                            "scraped-B": ("D:scraped-B", "R:scraped-B")}.items():
        d, r = cells.get(dc), cells.get(rc)
        if not d or not r or not d["powered"] or not r["powered"]:
            comps[label] = "insufficient (a party cell below 300)"
            continue
        gap = round(d["conversion_K2"] - r["conversion_K2"], 4)
        summed_hw = round((d["ci95_halfwidth_K2"] or 0) + (r["ci95_halfwidth_K2"] or 0), 4)
        comps[label] = {"D_rate": d["conversion_K2"], "R_rate": r["conversion_K2"], "gap": gap,
                        "summed_ci_halfwidth": summed_hw, "passes_gate": abs(gap) > summed_hw}

    pooled = cells.get("pooled", {})
    payload = {
        "generated_at": util.now_utc_iso(),
        "registration": {"file": "data/reference/search/s5_2-registration.json", "commit": "5cd27da",
                         "window_days": WINDOW, "K_primary": K_PRIMARY, "floor": floor},
        "exclusions": excl, "sponsorship_latest_date": latest,
        "cells": cells, "comparative": comps,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    EVID.mkdir(parents=True, exist_ok=True)
    util.write_json(EVID / "s5_2_concern_conversion.result.json", payload)

    # ---- report
    print("\n===== S5.2 THE CONCERN CONVERSION RATE =====")
    print(f"concern statements: {excl['concern_stmts']}  (no-topic excluded: {excl['no_topic']}, "
          f"right-censored excluded: {excl['censored']})")
    print(f"\nPOOLED: n={pooled.get('eligible')}  "
          f"conversion(K2)={pooled.get('conversion_K2')}  "
          f"NON-conversion(K2)={pooled.get('nonconversion_K2')}  "
          f"[bounds K1={pooled.get('conversion_K1')} / K3={pooled.get('conversion_K3')} / "
          f"tags-only={pooled.get('conversion_tags_only')}]")
    print("\nper cell (conversion rate at K=2, powered = n>=300):")
    for name in sorted(cells):
        a = cells[name]
        print(f"  {name:20s} n={a['eligible']:6d} powered={str(a['powered']):5s} "
              f"conv_K2={a['conversion_K2']} (K1={a['conversion_K1']}/K3={a['conversion_K3']}/"
              f"tags={a['conversion_tags_only']})")
    print("\ncomparative gate (party difference publishes only if it passes):")
    for label, v in comps.items():
        print(f"  {label:14s} {v}")
    print(f"\nwrote {RESULT}")
    print(f"wrote {EVID / 's5_2_concern_conversion.result.json'}")


if __name__ == "__main__":
    main()
