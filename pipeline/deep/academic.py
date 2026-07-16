"""Academic-archive lane ingest — Grimmer's Senate press releases, 2005-2007 (docs/15 §D3).

A both-party CROSS-CHECK lane (NEVER a census — the population is survivor-biased: ~112 senators,
tenure-defined; the audit's job is to keep it honest). Files are named `DDMonYYYY<surname><idx>.txt`
(date in the filename, senator = the directory name, text in the body). Senators map to bioguide/party
via congress-legislators (fetched keyless, mirrored). Emits `source=academic_archive` tagged statements
with the file path + name as provenance, then audits per-year symmetry. Stdlib-only, $0, local.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from . import audit as A
from . import lanes

_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_FNAME = re.compile(r"^(\d{1,2})([A-Za-z]{3})(\d{4})([A-Za-z]+?)\d*\.txt$")
# the Grimmer mirror physically lives under DEEP_ROOT/academic/ (the git-clone dest); derived state
# goes to the registry lane_state("academic_archive"). The raw mirror path is fixed here.
GRIMMER = lanes.DEEP_ROOT / "academic" / "raw" / "grimmer-senate" / "raw"
_ROSTER_URLS = {
    "historical": "https://unitedstates.github.io/congress-legislators/legislators-historical.json",
    "current": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
}


# --- roster: senators serving in the Grimmer window -> {name-key: (bioguide, party, state)} --------
def _fetch_roster() -> list[dict]:
    """Mirror congress-legislators (keyless) to the academic lane; reuse the mirror if present."""
    dest = lanes.lane_raw("academic_archive") / "roster"
    dest.mkdir(parents=True, exist_ok=True)
    people = []
    for key, url in _ROSTER_URLS.items():
        f = dest / f"legislators-{key}.json"
        if not f.exists():
            req = urllib.request.Request(url, headers={"User-Agent": lanes.POLITE["user_agent"]})
            with urllib.request.urlopen(req, timeout=60) as r:
                f.write_bytes(r.read())
        people += json.loads(f.read_text(encoding="utf-8"))
    return people


def senator_index(lo="2005-01-03", hi="2009-01-03") -> dict:
    """{name-key: (bioguide, party, state)} for everyone with a SENATE term overlapping [lo, hi).
    Keyed by lowercased last-name AND first+last (so a disambiguated dir like 'BenNelson' resolves)."""
    idx: dict[str, tuple] = {}
    for p in _fetch_roster():
        terms = [t for t in p.get("terms", []) if t.get("type") == "sen"
                 and t.get("start", "") < hi and t.get("end", "") > lo]
        if not terms:
            continue
        bio = p.get("id", {}).get("bioguide")
        party = {"Democrat": "D", "Republican": "R", "Independent": "I"}.get(terms[-1].get("party"))
        state = terms[-1].get("state")
        nm = p.get("name", {})
        last = (nm.get("last") or "").lower().replace(" ", "")
        first = (nm.get("first") or "").lower().replace(" ", "")
        for k in (last, first + last):
            if k and bio and party:
                idx.setdefault(k, (bio, party, state))
    return idx


def parse_filename(fn: str):
    """('YYYY-MM-DD', surname-lower) or None."""
    m = _FNAME.match(fn)
    if not m:
        return None
    day, mon, year, surname = m.groups()
    if mon.capitalize() not in _MON:
        return None
    return f"{year}-{_MON[mon.capitalize()]:02d}-{int(day):02d}", surname.lower()


# --- ingest ---------------------------------------------------------------------------------------
def ingest(progress=True) -> dict:
    idx = senator_index()
    out_dir = lanes.lane_state("academic_archive")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "statements.jsonl"
    stats = {"files": 0, "emitted": 0, "unmatched_dirs": [], "by_year": {}, "by_party": {"D": 0, "R": 0, "I": 0}}
    with open(out, "w", encoding="utf-8") as w:
        for d in sorted(p for p in GRIMMER.iterdir() if p.is_dir()) if GRIMMER.exists() else []:
            key = d.name.lower()
            sen = idx.get(key)
            if not sen:                                    # try last-name only (dir may be a bare surname)
                sen = idx.get(re.sub(r"^[a-z]+?(?=[a-z])", "", key)) or idx.get(key)
            if not sen:
                stats["unmatched_dirs"].append(d.name)
                continue
            bio, party, state = sen
            for f in d.iterdir():
                if f.name == ".DS_Store" or not f.name.endswith(".txt"):
                    continue
                stats["files"] += 1
                pf = parse_filename(f.name)
                if not pf:
                    continue
                date, _surname = pf
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore").strip()
                except Exception:
                    continue
                base = {"id": f"academic:{f.name}", "text": text, "published_at": date, "precision": "day",
                        "member": {"bioguide": bio, "party": party, "state": state, "chamber": "senate"}}
                stmt = lanes.tag(base, "academic_archive",
                                 url=f"file://grimmer-senate/raw/{d.name}/{f.name}", unit_date=date,
                                 stable_id=f.name)
                w.write(json.dumps(stmt, separators=(",", ":"), ensure_ascii=False) + "\n")
                stats["emitted"] += 1
                stats["by_party"][party] = stats["by_party"].get(party, 0) + 1
                stats["by_year"][date[:4]] = stats["by_year"].get(date[:4], 0) + 1
            if progress:
                print(f"  [academic] {d.name} -> {party} {bio} ({stats['emitted']} cumulative)", flush=True)
    (out_dir / "ingest-stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def audit_academic() -> dict:
    """Per-year coverage audit of the ingested academic lane (both-party, distinct members)."""
    from collections import defaultdict
    cov = defaultdict(lambda: {"D": {"members": set(), "statements": 0},
                               "R": {"members": set(), "statements": 0}})
    path = lanes.lane_state("academic_archive") / "statements.jsonl"
    if not path.exists():
        return {"error": "not ingested"}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        p = r["member"]["party"]
        if p in ("D", "R"):
            cov[r["published_at"][:4]][p]["members"].add(r["member"]["bioguide"])
            cov[r["published_at"][:4]][p]["statements"] += 1
    # academic lane provenance is complete (file path + name + date) and fully attributed by construction
    for y in cov:
        cov[y]["provenance_complete"] = True
        cov[y]["attribution_rate"] = 1.0
    return A.audit_coverage({y: cov[y] for y in cov}, "academic_archive")
