"""ADVERSARIAL REPRO pass 1 — structural definitions of "legacy D:R=1.538, scraper D:R=1.12".

One stream over the 303 mirror files, accumulating every plausible unit/denominator/window
combination. Deliberately bypasses harness.iter_statements (which drops date_source at
harness.py:399-427) and reads the raw mirror directly.
"""
import sys, json, collections, hashlib, re
sys.path.insert(0, ".")
from pipeline import fetch, util

_PARTY = {"D": "D", "R": "R", "I": "I", "Democrat": "D", "Republican": "R",
          "Independent": "I", "ID": "I", "Democratic": "D"}

TARGET_LEGACY = 1.538
TARGET_SCRAPER = 1.12

_WS = re.compile(r"\s+")

def congress_of(date):
    y = int(date[:4]); m = int(date[5:7]); d = int(date[8:10])
    n = 107 + (y - 2001) // 2
    if (y - 2001) % 2 == 0 and (m, d) < (1, 3):
        n -= 1
    return n

def windows_for(date):
    w = ["FULL"]
    if "2013-01-01" <= date <= "2020-12-31":
        w.append("A_2013_2020")
    if "2022-01-01" <= date <= "2026-12-31":
        w.append("B_2022_2026")
    if date >= "2018-01-01":
        w.append("from_2018")
    if date <= "2021-01-03":
        w.append("pre_seam")
    if date > "2021-01-03":
        w.append("post_seam")
    return w

# accumulators: key = (lane, window)
stmts        = collections.defaultdict(collections.Counter)   # party -> n statements
stmts_text   = collections.defaultdict(collections.Counter)   # only records with text
stmts_dedup_text = collections.defaultdict(collections.Counter)  # global text-hash dedupe
stmts_dedup_url  = collections.defaultdict(collections.Counter)  # global url dedupe
members      = collections.defaultdict(lambda: collections.defaultdict(set))  # party -> bioguides
domains      = collections.defaultdict(lambda: collections.defaultdict(set))  # party -> domains
office_ct    = collections.defaultdict(collections.Counter)   # (lane,window) -> bioguide -> n
office_party = {}                                             # bioguide -> party (last seen)
by_congress  = collections.defaultdict(collections.Counter)   # (lane,congress) -> party
chamber_ct   = collections.defaultdict(collections.Counter)   # (lane,window,chamber) -> party

seen_text = set()
seen_url = set()
n = 0

for f in sorted(fetch.MIRROR.glob("*.jsonl")):
    for r in util.iter_jsonl(f):
        n += 1
        date = (r.get("date") or "")[:10]
        if len(date) != 10:
            continue
        lane = r.get("date_source") or "<MISSING>"
        m = r.get("member") or {}
        p = _PARTY.get(m.get("party"))
        if not p:
            continue
        bio = m.get("bioguide_id")
        dom = r.get("domain")
        text = r.get("text") or ""
        url = r.get("url") or ""
        has_text = bool(text.strip())

        th = hashlib.md5(_WS.sub(" ", text.strip()).lower().encode("utf-8", "ignore")).hexdigest() if has_text else None
        is_dup_text = th is not None and th in seen_text
        if th is not None:
            seen_text.add(th)
        is_dup_url = url in seen_url
        if url:
            seen_url.add(url)

        if bio:
            office_party[bio] = p
        c = congress_of(date)

        for w in windows_for(date):
            k = (lane, w)
            stmts[k][p] += 1
            if has_text:
                stmts_text[k][p] += 1
            if not is_dup_text:
                stmts_dedup_text[k][p] += 1
            if not is_dup_url:
                stmts_dedup_url[k][p] += 1
            if bio:
                members[k][p].add(bio)
                office_ct[k][bio] += 1
            if dom:
                domains[k][p].add(dom)
            ch = m.get("chamber") or "?"
            chamber_ct[(lane, w, ch)][p] += 1
        by_congress[(lane, c)][p] += 1

def ratio(d, r):
    return (d / r) if r else float("inf")

def show(title, getter, keys):
    print(f"\n=== {title} ===")
    print(f"  {'lane':11s} {'window':14s} {'D':>9s} {'R':>9s} {'I':>7s}   {'D:R':>7s}  {'D-share%':>8s}")
    for k in keys:
        d, r, i = getter(k)
        if d + r == 0:
            continue
        sh = 100 * d / (d + r)
        flag = ""
        if abs(ratio(d, r) - TARGET_LEGACY) < 0.02: flag = "  <<< MATCHES legacy 1.538"
        if abs(ratio(d, r) - TARGET_SCRAPER) < 0.01: flag = "  <<< MATCHES scraper 1.12"
        print(f"  {k[0]:11s} {k[1]:14s} {d:9,} {r:9,} {i:7,}   {ratio(d,r):7.3f}  {sh:8.2f}{flag}")

LANES = ["legacy", "scraper", "page_html", "<MISSING>"]
WINS = ["FULL", "A_2013_2020", "B_2022_2026", "from_2018", "pre_seam", "post_seam"]
KEYS = [(l, w) for l in LANES for w in WINS]

print(f"TOTAL RECORDS READ: {n:,}")

show("D1. STATEMENTS (raw)", lambda k: (stmts[k]["D"], stmts[k]["R"], stmts[k]["I"]), KEYS)
show("D2. STATEMENTS with non-empty text", lambda k: (stmts_text[k]["D"], stmts_text[k]["R"], stmts_text[k]["I"]), KEYS)
show("D3. STATEMENTS deduped by normalized text hash (global)", lambda k: (stmts_dedup_text[k]["D"], stmts_dedup_text[k]["R"], stmts_dedup_text[k]["I"]), KEYS)
show("D4. STATEMENTS deduped by url (global)", lambda k: (stmts_dedup_url[k]["D"], stmts_dedup_url[k]["R"], stmts_dedup_url[k]["I"]), KEYS)
show("D5. DISTINCT MEMBERS (bioguide)", lambda k: (len(members[k]["D"]), len(members[k]["R"]), len(members[k]["I"])), KEYS)
show("D6. DISTINCT DOMAINS (offices/websites)", lambda k: (len(domains[k]["D"]), len(domains[k]["R"]), len(domains[k]["I"])), KEYS)

print("\n=== D7. FOLD I INTO D (statements) ===")
for k in KEYS:
    c = stmts[k]
    d, r = c["D"] + c["I"], c["R"]
    if d + r == 0: continue
    print(f"  {k[0]:11s} {k[1]:14s} (D+I):R = {ratio(d,r):7.3f}   D-share%={100*d/(d+r):6.2f}")

print("\n=== D8. PER-OFFICE MEAN STATEMENTS, ratio of means (D mean / R mean) ===")
for k in KEYS:
    oc = office_ct[k]
    if not oc: continue
    dv = [v for b, v in oc.items() if office_party.get(b) == "D"]
    rv = [v for b, v in oc.items() if office_party.get(b) == "R"]
    if not dv or not rv: continue
    dm, rm = sum(dv) / len(dv), sum(rv) / len(rv)
    print(f"  {k[0]:11s} {k[1]:14s} D mean={dm:8.2f} (n={len(dv):4d})  R mean={rm:8.2f} (n={len(rv):4d})   ratio={dm/rm:7.3f}")

print("\n=== D9. PER-CONGRESS, by lane (statements D:R) ===")
for lane in LANES:
    for c in sorted({cc for (l, cc) in by_congress if l == lane}):
        cnt = by_congress[(lane, c)]
        d, r = cnt["D"], cnt["R"]
        if d + r < 50: continue
        flag = ""
        if abs(ratio(d, r) - TARGET_LEGACY) < 0.02: flag = "  <<< 1.538"
        if abs(ratio(d, r) - TARGET_SCRAPER) < 0.01: flag = "  <<< 1.12"
        print(f"  {lane:11s} congress {c}  D={d:7,} R={r:7,}  D:R={ratio(d,r):7.3f}  D-share%={100*d/(d+r):6.2f}{flag}")

print("\n=== D10. BY CHAMBER (statements D:R) ===")
for lane in ["legacy", "scraper"]:
    for w in ["FULL", "A_2013_2020", "B_2022_2026", "from_2018"]:
        for ch in ["House", "Senate", "?"]:
            c = chamber_ct.get((lane, w, ch))
            if not c: continue
            d, r = c["D"], c["R"]
            if d + r < 50: continue
            print(f"  {lane:11s} {w:14s} {ch:7s} D={d:7,} R={r:7,}  D:R={ratio(d,r):7.3f}  D-share%={100*d/(d+r):6.2f}")

# what D:R would produce a 7.7pt D-share gap
print("\n=== TARGET DECODE ===")
print(f"  legacy 1.538 -> D-share = {100*1.538/2.538:.2f}%")
print(f"  scraper 1.12 -> D-share = {100*1.12/2.12:.2f}%")
print(f"  gap = {100*1.538/2.538 - 100*1.12/2.12:.2f} pt  (canon says 7.7pt -> the two ratios are internally consistent as D-shares)")
