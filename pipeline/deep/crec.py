"""CREC (Congressional Record) ingest — the symmetric deep instrument (docs/15 §D1). Extensions-first.

Keyless GovInfo endpoints (verified 2026-07-15): year sitemap lists days; per-day MODS carries every
granule's `granuleClass` + structured `congMember` attribution (bioGuideId/party/chamber/role — NO
name-parsing); granule HTML is the full text. The `/bulkdata` zips are broken (masked HTML errors) —
we use metadata + content + sitemap only.

Resumable + polite + immutable: raw MODS stored per day, the crawl checkpointed by granule accessId, so
a killed 30-hour crawl restarts clean. Emits statements tagged `source=crec`, `crec_section=E|H|S` with
the granule URL + package date as provenance, via `lanes.tag()`.
"""
from __future__ import annotations

import html as _html
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from . import lanes

MODS_NS = "{http://www.loc.gov/mods/v3}"
BASE = "https://www.govinfo.gov"
SECTION = {"EXTENSIONS": "E", "HOUSE": "H", "SENATE": "S"}   # DAILYDIGEST excluded (0% attribution)


# --- endpoints ------------------------------------------------------------------------------------
def sitemap_url(year: int) -> str:
    return f"{BASE}/sitemap/CREC_{year}_sitemap.xml"


def mods_url(pkg: str) -> str:
    return f"{BASE}/metadata/pkg/{pkg}/mods.xml"


def granule_html_url(pkg: str, access_id: str) -> str:
    return f"{BASE}/content/pkg/{pkg}/html/{access_id}.htm"


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": lanes.POLITE["user_agent"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# --- enumerate days from the year sitemap ---------------------------------------------------------
def enumerate_days(year: int) -> list[str]:
    """The CREC-YYYY-MM-DD package ids for a year, sorted, from the published sitemap."""
    xml = _get(sitemap_url(year)).decode("utf-8", "ignore")
    pkgs = re.findall(r"/details/(CREC-\d{4}-\d{2}-\d{2})", xml)
    return sorted(set(pkgs))


# --- parse the day MODS -> granules with structured attribution -----------------------------------
def parse_granules(mods_bytes: bytes, allow=("EXTENSIONS",)) -> list[dict]:
    """Every constituent granule of an allowed class, with its accessId + congMembers (structured
    bioGuideId/party/chamber/role — no name-parsing)."""
    root = ET.fromstring(mods_bytes)
    out = []
    for c in root.findall(f".//{MODS_NS}relatedItem[@type='constituent']"):
        ext = c.find(f".//{MODS_NS}extension")
        if ext is None:
            continue
        gc = ext.find(f"{MODS_NS}granuleClass")
        gclass = gc.text if gc is not None else None
        if gclass not in allow:
            continue
        aid = ext.find(f"{MODS_NS}accessId")
        access_id = aid.text if aid is not None else None
        members = []
        for cm in ext.findall(f"{MODS_NS}congMember"):
            members.append({"bioguide": cm.get("bioGuideId"), "party": cm.get("party"),
                            "chamber": cm.get("chamber"), "role": cm.get("role"),
                            "state": cm.get("state"), "congress": cm.get("congress")})
        out.append({"access_id": access_id, "granule_class": gclass, "congmembers": members})
    return out


def extension_author(granule: dict) -> dict | None:
    """The single author of an Extensions granule = the SPEAKING congMember with a bioguide + party.
    Extensions are single-authored, so this is unambiguous; returns None if unattributed (measured, the
    granule is then skipped and counted toward the attribution rate)."""
    speaking = [m for m in granule["congmembers"]
                if m.get("role") == "SPEAKING" and m.get("bioguide") and m.get("party") in ("D", "R", "I")]
    if speaking:
        return speaking[0]
    attributed = [m for m in granule["congmembers"] if m.get("bioguide") and m.get("party") in ("D", "R", "I")]
    return attributed[0] if len(attributed) == 1 else None


# --- granule HTML -> clean text (strip Record furniture) ------------------------------------------
_BRACKET = re.compile(r"^\[.*\]$")
_UNDERS = re.compile(r"^[_\s]+$")


def strip_furniture(raw_html: bytes | str) -> tuple[str, str]:
    """(title, body) with Congressional Record page furniture removed. Boilerplate n-grams
    ('mr speaker', 'in the house of representatives', …) are suppressed later at n-gram time using the
    crec_boilerplate_seeds reference table — this only strips the page structure (brackets, [[Page]]
    markers, the GPO line, rule separators)."""
    txt = raw_html.decode("utf-8", "ignore") if isinstance(raw_html, bytes) else raw_html
    m = re.search(r"<pre>(.*?)</pre>", txt, re.S | re.I)
    body = m.group(1) if m else txt
    body = _html.unescape(re.sub(r"<[^>]+>", "", body))
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s or _BRACKET.match(s) or _UNDERS.match(s):
            continue
        if s.startswith("From the Congressional Record Online"):
            continue
        lines.append(s)
    # heuristic: first surviving all-caps-ish line is the title; the rest is the statement
    title = lines[0] if lines else ""
    return title, "\n".join(lines).strip()


# --- normalize -> a lane-tagged statement (deep schema) ------------------------------------------
def to_statement(pkg: str, day: str, granule: dict, author: dict, title: str, text: str) -> dict:
    base = {
        "id": f"crec:{granule['access_id']}",
        "title": title, "text": text, "published_at": day, "precision": "day",
        "member": {"bioguide": author["bioguide"], "party": author["party"],
                   "state": author.get("state"), "chamber": author.get("chamber")},
        "congress": int(author["congress"]) if author.get("congress") else None,
        "crec_section": SECTION.get(granule["granule_class"], "?"),
    }
    return lanes.tag(base, "crec", url=granule_html_url(pkg, granule["access_id"]),
                     unit_date=day, stable_id=granule["access_id"])


# --- the resumable Extensions crawl --------------------------------------------------------------
def crawl_extensions(years, *, limit_days=None, progress=True) -> dict:
    """Crawl Extensions-of-Remarks granules for `years` into X:\\onscript-data\\crec\\. Resumable
    (skips manifested days/granules), polite (POLITE interval), immutable (raw MODS kept). Emits
    tagged statements to crec/state/E/statements-{year}.jsonl. Returns a stats summary."""
    import json
    raw_root = lanes.lane_raw("crec")
    state = lanes.lane_state("crec")
    (state / "E").mkdir(parents=True, exist_ok=True)
    man = lanes.CrawlManifest(state / "crawl-manifest.jsonl")
    stats = {"days": 0, "granules": 0, "attributed": 0, "unattributed": 0, "by_year": {}}
    for year in years:
        try:
            days = enumerate_days(year)
        except Exception as e:
            print(f"[crec] sitemap {year} FAILED: {e}", flush=True)
            continue
        if limit_days:
            days = days[:limit_days]
        out_path = state / "E" / f"statements-{year}.jsonl"
        yr = {"days": 0, "granules": 0, "attributed": 0, "unattributed": 0}
        with open(out_path, "a", encoding="utf-8") as w:
            for pkg in days:
                mods_key = f"mods:{pkg}"
                mods_file = raw_root / "mods" / str(year) / f"{pkg}.mods.xml"
                if man.seen(mods_key) and mods_file.exists():
                    mods = mods_file.read_bytes()
                else:
                    try:
                        mods = _get(mods_url(pkg))
                    except Exception as e:
                        print(f"[crec] MODS {pkg} FAILED: {e}", flush=True)
                        continue
                    mods_file.parent.mkdir(parents=True, exist_ok=True)
                    mods_file.write_bytes(mods)
                    man.record(mods_key, lanes.sha256(mods), len(mods))
                    time.sleep(lanes.POLITE["min_interval_s"])
                try:
                    granules = parse_granules(mods, allow=("EXTENSIONS",))
                except Exception as e:
                    print(f"[crec] MODS parse {pkg} FAILED: {e}", flush=True)
                    continue
                stats["days"] += 1
                yr["days"] += 1
                for g in granules:
                    if not g["access_id"] or man.seen(g["access_id"]):
                        continue
                    author = extension_author(g)
                    if not author:
                        yr["unattributed"] += 1
                        stats["unattributed"] += 1
                        man.record(g["access_id"], "unattributed", 0)   # counted, never re-fetched
                        continue
                    try:
                        raw = _get(granule_html_url(pkg, g["access_id"]))
                    except Exception as e:
                        print(f"[crec] granule {g['access_id']} FAILED: {e}", flush=True)
                        continue
                    time.sleep(lanes.POLITE["min_interval_s"])
                    title, text = strip_furniture(raw)
                    stmt = to_statement(pkg, pkg, g, author, title, text)
                    w.write(json.dumps(stmt, separators=(",", ":"), ensure_ascii=False) + "\n")
                    man.record(g["access_id"], lanes.sha256(raw), len(raw))
                    yr["granules"] += 1
                    yr["attributed"] += 1
                    stats["granules"] += 1
                    stats["attributed"] += 1
                if progress and yr["days"] % 20 == 0:
                    print(f"[crec] {year}: {yr['days']} days, {yr['granules']} E-statements", flush=True)
        stats["by_year"][year] = yr
        if progress:
            print(f"[crec] {year} DONE: {yr}", flush=True)
    (state / "crawl-stats.json").write_text(__import__("json").dumps(stats, indent=1), encoding="utf-8")
    return stats
