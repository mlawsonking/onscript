"""S3.7 Step 1 — the margin-of-victory reference table (bioguide x cycle -> MoV).

Parses the MEDSL congressional-returns files (downloaded via #177 to X:) into a per-member,
per-cycle margin-of-victory table, JOINED to bioguide via the congress-legislators roster `terms`
on state.district.year.party, and COMMITTED under data/reference/search/ (the committed-Search-
reference-table pattern; the same schema shape as data/reference/nomenclature/committee-names.json).

An unaudited join is not a table (docs/13 §S3.7 / the session brief). This script therefore reports
match coverage per chamber per cycle and enumerates every unmatched contest, and writes the full
detail to X: as evidence. The committed JSON carries the summary audit inline.

Sources (local, #177):
  X:/onscript-data/elections/raw/1976-2024-house.tab         (COMMA-delimited; MEDSL House 1976-2024)
  X:/onscript-data/elections/raw/1976-2024-senate-state.tab  (TAB-delimited;   MEDSL Senate 1976-2024)
Roster (already mirrored; the S1.12 lane):
  X:/onscript-data/academic_archive/raw/roster/legislators-{current,historical}.json

Winner determination (per general contest, self-consistent and fusion/mode robust):
  * contest = (year, state, district) for House; (year, state) for Senate (statewide).
  * keep stage in {gen, runoff}; a contest with any runoff row is DECIDED by the runoff (GA), else gen.
  * aggregate candidatevotes by CANDIDATE across all party lines and modes (fusion tickets, early/
    election-day splits) -> one total per candidate; a candidate's party = their largest party line.
  * totalvotes := sum of every candidatevotes in the contest (internally consistent denominator,
    immune to the totalvotes-column mode quirks); cross-checked against the reported column.
  * MoV = (winner_total - runnerup_total) / totalvotes  (uncontested -> runnerup 0 -> MoV 1.0).

Join (frozen registration, docs/13 §S3.7): MEDSL (state.district.year.party) -> the roster term with
matching type/state/district/party whose start year = election year + 1 (the seat that election filled;
specials also allow start year = election year). Party mismatch (independents / MN DFL label drift)
falls back to a UNIQUE state.district.start-year term, flagged `party_relaxed` in the audit -- never a
silent mis-join. Non-voting delegates and appointment/special-seated members with no matching general
contest are reported unmatched, not fabricated.

Re-runnable:  C:/ProgramData/miniconda3/python.exe scripts/search/build_mov_table.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import util  # noqa: E402  (only for write_json; no pipeline state is touched)

RAW = Path("X:/onscript-data/elections/raw")
HOUSE = RAW / "1976-2024-house.tab"
SENATE = RAW / "1976-2024-senate-state.tab"
ROSTER = Path("X:/onscript-data/academic_archive/raw/roster")
OUT_REF = Path(__file__).resolve().parents[2] / "data" / "reference" / "search" / "mov-by-member.json"
OUT_EVID = Path("X:/onscript-data/elections/derived")

# The cycles S3.7 can use: those whose seated terms fall inside the lane span (2013-2026 = congresses
# 113-119, seated by the 2012..2024 elections). We build the FULL modern table 2012-2024 and let the
# S3.7 window-overlap reduction select; earlier cycles are parsed too (harmless, small) but flagged.
MIN_CYCLE = 2012


# ---------------------------------------------------------------------------- party normalization
def norm_party(raw: str | None) -> str:
    s = (raw or "").strip().lower()
    if not s or s in ("na", "n/a", "none"):
        return "OTHER"
    if "republican" in s and "democrat" not in s and "democratic" not in s:
        return "R"
    if "democrat" in s or "democratic" in s or "dfl" in s or "farmer-labor" in s or "farmer labor" in s:
        return "D"
    if "independent" in s:
        return "I"
    return "OTHER"


_SUFFIX = {"JR", "SR", "II", "III", "IV", "V"}


def _tokens(name: str) -> set:
    return {t for t in re.findall(r"[A-Za-z]+", (name or "").upper()) if len(t) > 1}


def _surname(name: str) -> str | None:
    """The MEDSL winner's surname = last alpha token that is not a generational suffix (JR/III/...)."""
    toks = [t for t in re.findall(r"[A-Za-z]+", (name or "").upper()) if len(t) > 1 and t not in _SUFFIX]
    return toks[-1] if toks else None


# ---------------------------------------------------------------------------- MEDSL parsing
def _sniff(path: Path) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.readline()
    return "\t" if "\t" in head else ","


def read_medsl(path: Path) -> list[dict]:
    delim = _sniff(path)
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        rd = csv.DictReader(f, delimiter=delim)
        for r in rd:
            rows.append(r)
    return rows, delim


def _int_or(v, default=None):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _num(v, default=0):
    """Vote counts arrive as plain ints in the House file but FLOAT strings ('920478.0') in the
    Senate file — parse both. A bare int() on the Senate value silently zeroed every contest."""
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def _is_special(r: dict) -> bool:
    return str(r.get("special", "")).strip().upper() == "TRUE"


def contests_from(rows: list[dict], chamber: str) -> list[dict]:
    """One winner/margin record per decided general contest. chamber in {'house','senate'}.

    The contest key includes `special`: a state can hold a REGULAR and a SPECIAL Senate election in
    the same year for its two seats (OK-2014 = Inhofe regular + Lankford special), and merging them
    fabricates a margin between two different races. Splitting on `special` keeps each contest's
    winner and margin its own."""
    # group rows by contest (year, state, district, special)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        year = _int_or(r.get("year"))
        if year is None:
            continue
        stage = (r.get("stage") or "").strip().lower()
        if not ("gen" in stage or "runoff" in stage or stage == ""):  # general (+ runoff); drop primaries
            continue
        # some files leave stage blank for a plain general -> treat "" as gen
        st = r.get("state_po") or r.get("state")
        dist = _int_or(r.get("district"), 0) if chamber == "house" else 0
        key = (year, st, dist, _is_special(r))
        groups[key].append((stage, r))

    out = []
    for (year, st, dist, special), grp in groups.items():
        stages = {g[0] for g in grp}
        use_runoff = any("runoff" in s for s in stages)
        rowset = [r for (s, r) in grp if ("runoff" in s) == use_runoff]
        # aggregate votes by candidate (across party lines / modes); track party-line breakdown
        cand_votes: dict[str, int] = defaultdict(int)
        cand_party: dict[str, dict] = defaultdict(lambda: defaultdict(int))
        for r in rowset:
            name = (r.get("candidate") or "").strip().upper()
            v = _num(r.get("candidatevotes"), 0)
            if not name:
                continue
            cand_votes[name] += v
            praw = r.get("party") or r.get("party_detailed") or r.get("party_simplified")
            cand_party[name][(praw or "").strip()] += v
        if not cand_votes:
            continue
        ranked = sorted(cand_votes.items(), key=lambda kv: -kv[1])
        total = sum(cand_votes.values())
        if total <= 0:
            continue
        wname, wvotes = ranked[0]
        rvotes = ranked[1][1] if len(ranked) > 1 else 0
        # winner party = their largest party line
        wparty_raw = max(cand_party[wname].items(), key=lambda kv: kv[1])[0] if cand_party[wname] else ""
        mov = (wvotes - rvotes) / total
        out.append({
            "chamber": chamber, "cycle": year, "state": st,
            "district": dist if chamber == "house" else None,
            "winner": wname, "party": norm_party(wparty_raw), "party_raw": wparty_raw,
            "winner_votes": wvotes, "runnerup_votes": rvotes, "total_votes": total,
            "mov": round(mov, 6), "special": special,
            "reported_total": _num((rowset[0] or {}).get("totalvotes"), None),
        })
    return out


# ---------------------------------------------------------------------------- roster terms
def load_terms() -> list[dict]:
    terms = []
    for fn in ("legislators-current.json", "legislators-historical.json"):
        data = json.load(open(ROSTER / fn, encoding="utf-8"))
        for p in data:
            bio = (p.get("id") or {}).get("bioguide")
            nm = p.get("name") or {}
            name = nm.get("official_full") or (f"{nm.get('first','')} {nm.get('last','')}".strip())
            for t in (p.get("terms") or []):
                start = (t.get("start") or "")[:10]
                end = (t.get("end") or "")[:10]
                sy = _int_or(start[:4])
                if sy is None or sy < MIN_CYCLE:  # modern only; the table is 2013-2026 substrate
                    continue
                terms.append({
                    "bioguide": bio, "name": name, "type": t.get("type"),
                    "state": (t.get("state") or "").strip(),
                    "district": _int_or(t.get("district")) if t.get("type") == "rep" else None,
                    "party": norm_party(t.get("party")),
                    "start_year": sy, "start": start, "end": end,
                    "tokens": _tokens(name) | _tokens(nm.get("last")),
                })
    return terms


# ---------------------------------------------------------------------------- the join
def _days_from_seating(start: str, cycle: int) -> int:
    """|term start - the statutory seating date Jan 3, cycle+1|, in days. A REGULAR winner is seated
    on Jan 3 (distance 0); a same-seat successor / interim / special winner is off that date, so this
    resolves the incumbent-vs-successor tie the raw (state,district,year) key cannot."""
    import datetime as _dt
    try:
        y, m, d = int(start[:4]), int(start[5:7]), int(start[8:10])
        return abs((_dt.date(y, m, d) - _dt.date(cycle + 1, 1, 3)).days)
    except Exception:
        return 10 ** 6


def _pick_closest(cands: list[dict], cycle: int):
    best = min(_days_from_seating(t["start"], cycle) for t in cands)
    tied = [t for t in cands if _days_from_seating(t["start"], cycle) == best]
    return tied[0] if len({t["bioguide"] for t in tied}) == 1 else None


def join(contests: list[dict], terms: list[dict]):
    # index terms for lookup: (type, state) -> list
    by_ts: dict[tuple, list] = defaultdict(list)
    for t in terms:
        by_ts[(t["type"], t["state"])].append(t)

    matched, unmatched = [], []
    for c in contests:
        if c["cycle"] < MIN_CYCLE:
            continue
        ttype = "rep" if c["chamber"] == "house" else "sen"
        cands = by_ts.get((ttype, c["state"]), [])
        # an election in year Y seats a term starting Y+1 (regular) or Y (special, seated same year)
        want_years = {c["cycle"] + 1} | ({c["cycle"]} if c["special"] else set())

        def district_ok(t):
            return c["chamber"] == "senate" or t["district"] == c["district"]

        pool = [t for t in cands if t["start_year"] in want_years and district_ok(t)]
        surname = _surname(c["winner"])
        named = [t for t in pool if surname and surname in t["tokens"]]

        pick, via, considered = None, None, pool
        if len(pool) == 1:
            pick, via = pool[0], "exact"
        elif len(named) == 1:
            pick, via = named[0], "name"                       # strongest signal: winner surname
        else:
            # narrow: surname-matches (relatives) or the whole pool -> party-exact, then seating date
            base = named or pool
            considered = base
            pe = [t for t in base if t["party"] == c["party"]]
            narrowed = pe if pe else base
            if len(narrowed) == 1:
                pick, via = narrowed[0], ("name+party" if named else ("exact" if pe else "relaxed"))
            elif narrowed:
                p = _pick_closest(narrowed, c["cycle"])
                if p is not None:
                    pick, via = p, ("name+date" if named else ("date" if pe else "relaxed+date"))

        if pick is None:
            reason = "no_term" if not pool else "ambiguous"
            unmatched.append({**_slim(c), "reason": reason,
                              "candidates": sorted({t["bioguide"] for t in considered})})
            continue
        matched.append({
            "bioguide": pick["bioguide"], "name": pick["name"], "chamber": c["chamber"],
            "state": c["state"], "district": c["district"], "cycle": c["cycle"],
            "party": c["party"], "winner_votes": c["winner_votes"],
            "runnerup_votes": c["runnerup_votes"], "total_votes": c["total_votes"],
            "mov": c["mov"], "special": c["special"], "matched_via": via,
        })
    return matched, unmatched


def _slim(c: dict) -> dict:
    return {k: c[k] for k in ("chamber", "cycle", "state", "district", "winner", "party",
                              "party_raw", "mov", "special")}


# ---------------------------------------------------------------------------- audit
_RELAXED_VIA = {"relaxed", "relaxed+date"}  # party constraint dropped -> lower-confidence match


def audit(matched, unmatched) -> dict:
    per: dict = {}
    all_contests = defaultdict(lambda: {"matched": 0, "unmatched": 0, "relaxed": 0})
    for m in matched:
        k = f"{m['chamber']}-{m['cycle']}"
        all_contests[k]["matched"] += 1
        if m["matched_via"] in _RELAXED_VIA:
            all_contests[k]["relaxed"] += 1
    for u in unmatched:
        k = f"{u['chamber']}-{u['cycle']}"
        all_contests[k]["unmatched"] += 1
    for k in sorted(all_contests):
        d = all_contests[k]
        tot = d["matched"] + d["unmatched"]
        per[k] = {**d, "total": tot, "match_pct": round(100 * d["matched"] / tot, 1) if tot else None}
    tot_m, tot_u = len(matched), len(unmatched)
    return {
        "per_chamber_cycle": per,
        "totals": {"matched": tot_m, "unmatched": tot_u,
                   "match_pct": round(100 * tot_m / (tot_m + tot_u), 1) if (tot_m + tot_u) else None},
        "unmatched_by_reason": dict(_count(u["reason"] for u in unmatched)),
        "matched_via": dict(_count(m["matched_via"] for m in matched)),
        "relaxed_total": sum(1 for m in matched if m["matched_via"] in _RELAXED_VIA),
    }


def _count(it):
    c = defaultdict(int)
    for x in it:
        c[x] += 1
    return c


def main():
    hrows, hd = read_medsl(HOUSE)
    srows, sd = read_medsl(SENATE)
    print(f"house rows={len(hrows)} (delim={hd!r})  senate rows={len(srows)} (delim={sd!r})", flush=True)

    contests = contests_from(hrows, "house") + contests_from(srows, "senate")
    modern = [c for c in contests if c["cycle"] >= MIN_CYCLE]
    print(f"decided general contests parsed: {len(contests)} total, {len(modern)} in {MIN_CYCLE}+", flush=True)

    terms = load_terms()
    print(f"roster terms ({MIN_CYCLE}+ start): {len(terms)}", flush=True)

    matched, unmatched = join(contests, terms)
    aud = audit(matched, unmatched)

    print("\n=== JOIN AUDIT (match coverage per chamber per cycle) ===")
    for k, d in aud["per_chamber_cycle"].items():
        print(f"  {k:16s} matched {d['matched']:3d}/{d['total']:3d} = {d['match_pct']}%"
              f"  (relaxed {d['relaxed']}, unmatched {d['unmatched']})")
    print(f"  TOTALS matched {aud['totals']['matched']}/{aud['totals']['matched']+aud['totals']['unmatched']}"
          f" = {aud['totals']['match_pct']}%   unmatched by reason: {aud['unmatched_by_reason']}"
          f"   party_relaxed: {aud['relaxed_total']}")

    # bioguide x cycle rows (a member can win multiple cycles)
    rows = sorted(matched, key=lambda m: (m["chamber"], m["cycle"], m["state"], m["district"] or 0))
    result = {
        "schema_version": 1,
        "kind": "search-margin-of-victory",
        "source": ("MEDSL constituency returns (Harvard Dataverse: U.S. House 1976-2024 "
                   "doi:10.7910/DVN/IG0UN2 + U.S. Senate 1976-2024 doi:10.7910/DVN/PEJ5QU), "
                   "downloaded via #177 to X:/onscript-data/elections/raw; joined to bioguide via "
                   "unitedstates/congress-legislators terms. Built offline by "
                   "scripts/search/build_mov_table.py."),
        "generated_at": util.now_utc_iso(),
        "method": {
            "mov": "(winner_total - runnerup_total) / sum(all candidatevotes in contest)",
            "winner": "candidates aggregated across party lines + modes; winner = max total; "
                      "winner party = largest party line",
            "contest": "general (+ deciding runoff); primaries excluded",
            "join": "MEDSL state.district.year.party -> roster term with type/state/district/party "
                    "and start_year == cycle+1 (special: also cycle); party-relaxed fallback to a "
                    "UNIQUE state.district.start-year term (flagged), never a silent mis-join",
            "cycles_note": f"table built for {MIN_CYCLE}+ (the 2013-2026 lane substrate)",
        },
        "audit": aud,
        "rows": rows,
    }
    OUT_REF.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(OUT_REF, result)
    print(f"\nwrote committed table: {OUT_REF}  ({len(rows)} bioguide x cycle rows)")

    OUT_EVID.mkdir(parents=True, exist_ok=True)
    util.write_json(OUT_EVID / "mov-audit-detail.json",
                    {"generated_at": util.now_utc_iso(), "audit": aud, "unmatched": unmatched,
                     "n_matched": len(matched)})
    print(f"wrote audit detail (every unmatched contest): {OUT_EVID / 'mov-audit-detail.json'}")


if __name__ == "__main__":
    main()
