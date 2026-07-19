"""S1.12 · Leadership Ignites, Backbenches Amplify — within-lane (docs/12 S1.12; docs/17 §2 lanes).

THE FALSE BLOCK (docs/13:506): the leadership roster is on disk —
`X:/onscript-data/academic_archive/raw/roster/legislators-{current,historical}.json` carry
`leadership_roles` (156 dated bioguide-keyed rows, 33 titles). S1 ran the day before it landed and
recorded the field null. This is the ~30-min offline parse + the pre-registered measurement.

============================  PRE-REGISTRATION (floors frozen BEFORE measuring, L4)  ===============
Hypothesis (docs/12 S1.12): "what share of big ignitions start in a leadership office?" First-sayer
office class (leadership vs rest) for peak>=20 phrases; CONFIRM: leadership share of ignitions
>= 3x their statement share, stable in halves. Aggregate framing only.

F1  IGNITION = a (phrase, congress, lane) ledger entry whose phrase_summary peak >= 20 (max same-day
    office count in either party) AND which has a resolvable INDIVIDUAL first-sayer bioguide
    (first_seen.bioguide, not None / not a joint: / njoint: marker). Unit = the ignition event.
F2  LEADERSHIP SET.
    PRIMARY = the 9 core titles the hypothesis names ("Speaker/Leaders/Whips"):
      Speaker of the House; House Majority Leader; House Minority Leader; House Majority Whip;
      House Minority Whip; Senate Majority Leader; Senate Minority Leader; Senate Majority Whip;
      Senate Minority Whip.
    ROBUSTNESS = all 33 titles present in leadership_roles.
    A bioguide is "leadership" on date D iff it held a set-member title with start <= D < end
    (end None => open-ended, D >= start).
F3  REPORTABILITY / POWER. A lane-half cell yields a verdict only if it has >= 50 resolvable
    ignitions AND the null-expected leadership-ignition count mu0 = N_ig * leadership_statement_share
    >= 3. Else "underpowered — no verdict." (mu0>=3 => a true 3x effect predicts >=9 leadership
    ignitions, separable from ~3 under the null; N>=50 guards the share's own precision.)
F4  VERDICT (within a lane). ratio = leadership_ignition_share / leadership_statement_share.
    CONFIRM  iff both halves are well-powered AND ratio >= 3.0 in BOTH (the "stable in halves" clause).
    REFUTE   iff a well-powered half shows ratio < 3.0.
    else MIXED/UNDERPOWERED — reported honestly, never a CONFIRM.
LANES (docs/17 §3, never pooled across the 2021-01-03 seam):
    propublica — years 2013-2020 (shards 113-116); half A 2013-16, half B 2017-20.
    scraped    — years 2021-2026 (shards 117-119); half A 2021-23, half B 2024-26.
ROBUSTNESS RIDERS (frozen): (a) leadership set = 33 titles; (b) exclude boilerplate-flagged ngrams;
    (c) tie-inclusive first-sayer (count leadership if first_seen.bioguide OR any first_seen.tie
    member is leadership). All reported alongside the primary, none replaces it.
FRAMING: aggregate only — "N% of major talking points first appear in a core-leadership office vs
    their M% share of statements (Kx)." No member-level output, no office named.
====================================================================================================

Re-runnable:  PYTHONHASHSEED=0 python scripts/search/s1_12_leadership.py
"""
import sys, json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline.search import harness as H

ROSTER = Path("X:/onscript-data/academic_archive/raw/roster")

CORE_9 = {
    "Speaker of the House",
    "House Majority Leader", "House Minority Leader",
    "House Majority Whip", "House Minority Whip",
    "Senate Majority Leader", "Senate Minority Leader",
    "Senate Majority Whip", "Senate Minority Whip",
}

PEAK_FLOOR = 20          # F1
MIN_IGNITIONS = 50       # F3
MIN_MU0 = 3.0            # F3
RATIO_GATE = 3.0         # F4

LANES = {
    "propublica": {"shards": [113, 114, 115, 116], "years": range(2013, 2021),
                   "halves": {"A": range(2013, 2017), "B": range(2017, 2021)}},
    "scraped":    {"shards": [117, 118, 119],       "years": range(2021, 2027),
                   "halves": {"A": range(2021, 2024), "B": range(2024, 2027)}},
}


def load_leadership():
    """bioguide -> list of (title, start, end). Dates are 'YYYY-MM-DD'; end may be None."""
    rows = defaultdict(list)
    n_rows, titles = 0, set()
    for fn in ("legislators-current.json", "legislators-historical.json"):
        data = json.load(open(ROSTER / fn, encoding="utf-8"))
        for p in data:
            bio = (p.get("id") or {}).get("bioguide")
            for r in (p.get("leadership_roles") or []):
                t = r.get("title")
                rows[bio].append((t, r.get("start"), r.get("end")))
                titles.add(t); n_rows += 1
    return rows, n_rows, titles


def is_leadership(lead, bio, date, title_set):
    if not bio or not date:
        return False
    for (title, start, end) in lead.get(bio, ()):
        if title not in title_set:
            continue
        if start and date < start:
            continue
        if end and date >= end:
            continue
        return True
    return False


def half_of(year, halves):
    for name, yrs in halves.items():
        if year in yrs:
            return name
    return None


def year_of(date):
    try:
        return int(str(date)[:4])
    except Exception:
        return None


def collect_ignitions(lane, cfg, lead):
    """Per half: counts of ignitions and leadership-ignitions under the primary + robustness rules."""
    per = {h: defaultdict(int) for h in cfg["halves"]}
    for c in cfg["shards"]:
        sp = H.shard_path("ledger", c, lane)
        if not sp.exists() or sp.stat().st_size <= 2:
            continue
        for ng, entry in H.iter_ledger_entries(sp):
            s = H.phrase_summary(ng, entry)
            if not s or s["peak"] < PEAK_FLOOR:
                continue
            fs = entry.get("first_seen") or {}
            bio = fs.get("bioguide")
            date = fs.get("date") or s["first_date"]
            if not bio or str(bio).startswith(("joint:", "njoint:")):
                continue
            y = year_of(date)
            if y not in cfg["years"]:
                continue
            h = half_of(y, cfg["halves"])
            if h is None:
                continue
            d = per[h]
            d["n_ig"] += 1
            core = is_leadership(lead, bio, date, CORE_9)
            if core:
                d["lead_core"] += 1
            if is_leadership(lead, bio, date, ALL_TITLES):
                d["lead_all33"] += 1
            if not entry.get("boilerplate"):
                d["n_ig_nobp"] += 1
                if core:
                    d["lead_core_nobp"] += 1
            tie_lead = core or any(
                is_leadership(lead, t, date, CORE_9) for t in (fs.get("tie") or []))
            if tie_lead:
                d["lead_core_tie"] += 1
    return per


def collect_baseline(lane, cfg, lead):
    """Per half: leadership statement share (fraction of statements from a core-leadership office)."""
    per = {h: defaultdict(int) for h in cfg["halves"]}
    for rec in H.iter_statements(congresses=None, with_text=False, lane=lane):
        y = year_of(rec.get("date"))   # iter_statements' `year` is a STRING; year_of() returns int
        if y not in cfg["years"]:
            continue
        h = half_of(y, cfg["halves"])
        if h is None:
            continue
        d = per[h]
        d["n_stmt"] += 1
        if is_leadership(lead, rec.get("bioguide"), rec.get("date"), CORE_9):
            d["lead_stmt_core"] += 1
        if is_leadership(lead, rec.get("bioguide"), rec.get("date"), ALL_TITLES):
            d["lead_stmt_all33"] += 1
    return per


def main():
    lead, n_rows, titles = load_leadership()
    global ALL_TITLES
    ALL_TITLES = set(titles)
    print(f"leadership_roles: {n_rows} rows, {len(titles)} titles, {len(lead)} members\n")

    results = {}
    for lane, cfg in LANES.items():
        print(f"===== LANE {lane} (years {cfg['years'].start}-{cfg['years'].stop-1}) =====", flush=True)
        ign = collect_ignitions(lane, cfg, lead)
        base = collect_baseline(lane, cfg, lead)
        lane_res = {}
        for h in cfg["halves"]:
            ig = ign[h]; bs = base[h]
            n_ig = ig["n_ig"]; n_stmt = bs["n_stmt"]
            stmt_share = (bs["lead_stmt_core"] / n_stmt) if n_stmt else 0.0
            ig_share = (ig["lead_core"] / n_ig) if n_ig else 0.0
            ratio = (ig_share / stmt_share) if stmt_share else float("nan")
            mu0 = n_ig * stmt_share
            powered = n_ig >= MIN_IGNITIONS and mu0 >= MIN_MU0
            # robustness variants
            share33 = (ig["lead_all33"] / n_ig) if n_ig else 0.0
            sshare33 = (bs["lead_stmt_all33"] / n_stmt) if n_stmt else 0.0
            ratio33 = (share33 / sshare33) if sshare33 else float("nan")
            ig_nobp = ig["n_ig_nobp"]
            share_nobp = (ig["lead_core_nobp"] / ig_nobp) if ig_nobp else 0.0
            ratio_nobp = (share_nobp / stmt_share) if stmt_share else float("nan")
            share_tie = (ig["lead_core_tie"] / n_ig) if n_ig else 0.0
            ratio_tie = (share_tie / stmt_share) if stmt_share else float("nan")
            lane_res[h] = dict(n_ig=n_ig, n_stmt=n_stmt, lead_ig=ig["lead_core"],
                               lead_stmt=bs["lead_stmt_core"], ig_share=ig_share,
                               stmt_share=stmt_share, ratio=ratio, mu0=mu0, powered=powered,
                               ratio33=ratio33, ratio_nobp=ratio_nobp, ratio_tie=ratio_tie)
            print(f"  half {h}: ignitions={n_ig} (lead {ig['lead_core']} = {ig_share:.3%}) | "
                  f"statements={n_stmt} (lead {bs['lead_stmt_core']} = {stmt_share:.3%}) | "
                  f"RATIO={ratio:.2f}x | mu0={mu0:.1f} | powered={powered}")
            print(f"           robustness: 33-title ratio={ratio33:.2f}x | no-boilerplate "
                  f"ratio={ratio_nobp:.2f}x | tie-inclusive ratio={ratio_tie:.2f}x")
        # F4 verdict
        halves = list(lane_res.values())
        if all(x["powered"] for x in halves):
            verdict = "CONFIRM" if all(x["ratio"] >= RATIO_GATE for x in halves) else "REFUTE"
        else:
            verdict = "UNDERPOWERED/MIXED"
        lane_res["verdict"] = verdict
        results[lane] = lane_res
        print(f"  --> LANE {lane} VERDICT: {verdict}\n", flush=True)

    Path("scripts/search/evidence").mkdir(parents=True, exist_ok=True)
    out = Path("scripts/search/evidence/s1_12_leadership.result.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
