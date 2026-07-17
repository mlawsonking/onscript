"""ADVERSARIAL REPRO pass 2 — anchor-restricted, temporal-granularity, roster-join, union framing.

Targets: legacy D:R = 1.538 (D-share 60.60%), scraper D:R = 1.12 (D-share 52.83%).
"""
import sys, json, collections, datetime as dt
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I", "Democratic": "D"}

REF = "data/reference/search"
scotus = json.load(open(f"{REF}/scotus-landmarks.json", encoding="utf-8"))
shut = json.load(open(f"{REF}/shutdowns.json", encoding="utf-8"))
roster = json.load(open("data/reference/roster.json", encoding="utf-8"))

def dshift(d, n):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()

# --- build date -> anchor-window membership ---
scotus_win = collections.defaultdict(list)   # date -> [(case_id, half, anchors)]
W = scotus.get("_window_days", 7)
for c in scotus["cases"]:
    for k in range(-W, W + 1):
        scotus_win[dshift(c["date"], k)].append((c["id"], c["half"], [a.lower() for a in c["anchors"]]))

shut_win = collections.defaultdict(list)     # date -> [(id, half)]
SW = shut.get("window_days", 14)
for s in shut["shutdowns"]:
    d0, d1 = dshift(s["start"], -SW), dshift(s["end"], SW)
    cur = d0
    while cur <= d1:
        shut_win[cur].append((s["id"], s["half"]))
        cur = dshift(cur, 1)

# accumulators
scotus_hit   = collections.defaultdict(collections.Counter)  # (lane, scope) -> party
scotus_allw  = collections.defaultdict(collections.Counter)  # window, no anchor filter
shut_all     = collections.defaultdict(collections.Counter)
by_year      = collections.defaultdict(collections.Counter)  # (lane, year) -> party
by_month     = collections.defaultdict(collections.Counter)  # (lane, month) -> party
union_era    = collections.defaultdict(collections.Counter)  # era -> party (no lane split)
roster_join  = collections.defaultdict(collections.Counter)  # (lane, window) -> party (roster party)
office_share = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # (lane,win)->bio->party cnt

def windows_for(date):
    w = ["FULL"]
    if "2013-01-01" <= date <= "2020-12-31": w.append("A_2013_2020")
    if "2022-01-01" <= date <= "2026-12-31": w.append("B_2022_2026")
    return w

for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        date = (r.get("date") or "")[:10]
        if len(date) != 10: continue
        lane = r.get("date_source") or "<MISSING>"
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        bio = m.get("bioguide_id")
        if not p: continue
        text = (r.get("text") or "").lower()

        by_year[(lane, date[:4])][p] += 1
        by_month[(lane, date[:7])][p] += 1
        for w in windows_for(date):
            era = "A_2013_2020" if w == "A_2013_2020" else ("B_2022_2026" if w == "B_2022_2026" else "FULL")
            union_era[era][p] += 1
            rp = (roster.get(bio) or {}).get("party") if bio else None
            if rp in ("D", "R", "I"):
                roster_join[(lane, w)][rp] += 1
            if bio:
                office_share[(lane, w)][bio][p] += 1

        # scotus anchor windows
        for cid, half, anchors in scotus_win.get(date, ()):
            scotus_allw[(lane, "ALL_CASES")][p] += 1
            scotus_allw[(lane, f"half{half}")][p] += 1
            if any(a in text for a in anchors):
                scotus_hit[(lane, "ALL_CASES")][p] += 1
                scotus_hit[(lane, f"half{half}")][p] += 1
                scotus_hit[(lane, f"case:{cid}")][p] += 1
        # shutdown windows
        for sid, half in shut_win.get(date, ()):
            shut_all[(lane, "ALL")][p] += 1
            shut_all[(lane, f"half{half}")][p] += 1

def rr(c):
    d, r = c["D"], c["R"]
    return (d / r) if r else float("inf")

def flag(c):
    d, r = c["D"], c["R"]
    if not r: return ""
    x = d / r
    if abs(x - 1.538) < 0.02: return "   <<< 1.538 legacy"
    if abs(x - 1.12) < 0.008: return "   <<< 1.12 scraper"
    return ""

def dump(title, acc, minn=30):
    print(f"\n=== {title} ===")
    for k in sorted(acc, key=lambda z: (str(z[0]), str(z[1]))):
        c = acc[k]
        if c["D"] + c["R"] < minn: continue
        sh = 100 * c["D"] / (c["D"] + c["R"])
        print(f"  {str(k[0]):11s} {str(k[1]):16s} D={c['D']:7,} R={c['R']:7,}  D:R={rr(c):7.3f}  D-share%={sh:6.2f}{flag(c)}")

dump("A. SCOTUS anchor-window, ANCHOR-MATCHED statements", scotus_hit, minn=20)
dump("B. SCOTUS anchor-window, ALL statements in window (no anchor filter)", scotus_allw)
dump("C. SHUTDOWN windows (+/-14d), all statements", shut_all)
dump("D. UNION framing (era only, lanes merged)", union_era)
dump("E. ROSTER-JOIN party (reference/roster.json, not record party)", roster_join)
dump("F. BY YEAR", by_year, minn=100)

print("\n=== G. MEAN OF MONTHLY D:R (unweighted across months) ===")
for lane in ["legacy", "scraper"]:
    for label, lo, hi in [("FULL", "0000", "9999"), ("A_2013_2020", "2013-01", "2020-12"),
                          ("B_2022_2026", "2022-01", "2026-12"), ("from_2018", "2018-01", "9999")]:
        rs = [rr(c) for (l, mo), c in by_month.items()
              if l == lane and lo <= mo <= hi and c["R"] >= 5 and c["D"] + c["R"] >= 30]
        if not rs: continue
        rs = [x for x in rs if x != float("inf")]
        print(f"  {lane:9s} {label:12s} n_months={len(rs):3d}  mean monthly D:R = {sum(rs)/len(rs):.3f}")

print("\n=== H. MEAN OF PER-OFFICE D-SHARE / office-weighted D:R ===")
for lane in ["legacy", "scraper"]:
    for w in ["FULL", "A_2013_2020", "B_2022_2026"]:
        oc = office_share.get((lane, w))
        if not oc: continue
        # office-weighted: each office contributes its own party once, weighted equally
        dn = sum(1 for b, c in oc.items() if c["D"] > c["R"])
        rn = sum(1 for b, c in oc.items() if c["R"] > c["D"])
        if not rn: continue
        print(f"  {lane:9s} {w:12s} offices D={dn:4d} R={rn:4d}  office D:R = {dn/rn:.3f}")

print("\n=== TARGETS: legacy 1.538 (D-share 60.60%) | scraper 1.12 (D-share 52.83%) ===")
