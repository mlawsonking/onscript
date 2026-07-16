"""Nomenclature reference-data generator (docs/16 §4) — OFFLINE one-time/weekly capex.

NEVER imported by the daily pipeline. This module touches the network and (for the committee lane)
parses YAML with a third-party library; the daily path reads ONLY the committed JSON it writes to
data/reference/nomenclature/. That split is why the tagger adds ZERO streak risk: govinfo can be down
for a week and the daily run neither knows nor cares. Refresh is a separate workflow_dispatch/weekly
job; between refreshes a brand-new bill title is untagged (bounded, disclosed lag).

Two lanes, both citing an external party-blind official record (Article IV — the acquisition code
cannot see party because the sources do not carry it):
  bills      — govinfo BILLSTATUS bulkdata, congresses 113-119 (the press spine's window). Keyless.
  committee  — unitedstates/congress-legislators committees-{current,historical}.yaml.

Run:  python -m pipeline.nomenclature_build            # both lanes, congresses 113-119
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

from . import boilerplate, config, nomenclature, phrases, util
from .deep import lanes

# govinfo bulkdata. Congress 107 is NOT in this collection (404) and 108-112 is a deferred follow-up
# (docs/16 §7.1: its titleTypeCode vocabulary is unmeasured — verify before extending the allowlist).
BILLSTATUS_URL = "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{t}/BILLSTATUS-{congress}-{t}.zip"
BILL_TYPES = ("hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres")
CONGRESSES = tuple(range(113, 120))

COMMITTEE_YAML = {
    "current": "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/committees-current.yaml",
    "historical": "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/committees-historical.yaml",
}

OUT_DIR = config.REFERENCE / "nomenclature"

# SHORT titles only. Official (6/7/10/259) and Display (45) are PROSE — median 25 tokens vs 6 for a
# short title — and Display silently degrades to the Official prose whenever a bill has no short title
# (856/9,712 bills = 8.8% of congress 119, ~97% byte-identical to the Official title). Letting either in
# puts "to amend the national voter registration act of 1993" in the index, which would tag ordinary
# policy English. Keyed on titleTypeCode (a machine-stable int), NEVER a regex over the prose titleType.
TITLE_TYPE_ALLOW = frozenset({"101", "102", "103", "104", "106", "107", "108", "109",
                              "146", "147", "151", "152", "250", "252", "254", "255", "256", "27", "30"})

# THE 118 BOUNDARY (measured 2026-07-16, and NOT where docs/16 §7.1 expected it). `titleTypeCode` does
# not exist before congress 118: it is present on 1280/1280 and 1385/1385 sampled items in 118/119 and
# on 0/1249, 0/1246, 0/1389, 0/1607, 0/1518 in 113/114/115/116/117. Applying the code allowlist to
# 113-117 silently yields an EMPTY index — the same class of silent-drop failure as the year-tail bug,
# and invisible without a count.
#
# The prose `titleType` is the only discriminator those years carry. docs/16's "NEVER a regex over the
# prose titleType" is VINDICATED and kept: a `startswith('short title')` regex mismatches the allowlist
# 14 ways (it admits banned 105/110 "as Passed Senate" and drops allowed 30 "Popular Titles"). What is
# used instead is not a regex but an EXACT-STRING map calibrated on the 118/119 overlap, where both
# fields exist and prose predicts the code with ZERO ambiguity (every titleType maps to exactly one
# code, measured over both congresses, all 8 bill types).
#
# The legacy vocabulary spells the same concept without the "(s)" and codes it differently ("Short
# Title(s) as Passed House"=104 ALLOW vs "Short Titles as Passed House"=17 BAN). Normalizing "(s)" and
# resolving the 6 resulting legacy/modern collisions toward the MODERN verdict transmits docs/16's
# decisions to the older years rather than inventing new ones — 'short titles as passed senate' stays
# banned (18 and 105 agree) and 'short titles as enacted'(19) stays banned while '... for portions of
# this bill'(27) stays allowed. Yield on 113: 0 -> 6,534 names, with the appropriations/NDAA families
# present. This is a CALIBRATION, not a spec change: 118/119 still key on the code, untouched.
# NOT ruled on (docs/16 §9 posture): whether the legacy codes SHOULD inherit the modern verdict is a
# judgement the spec never faced, so each 113-117 table records index_basis + this rationale for audit.
TITLE_TYPE_PROSE_ALLOW = frozenset({
    "popular titles",
    "short titles as enacted for portions of this bill",
    "short titles as introduced",
    "short titles as introduced for portions of this bill",
    "short titles as passed house",
    "short titles as passed house for portions of this bill",
    "short titles as reported to house",
    "short titles as reported to house for portions of this bill",
    "short titles as reported to senate",
    "short titles as reported to senate for portions of this bill",
    "short titles for portions of this bill from enr (enrolled) bill text",
    "short titles for portions of this bill from pcs (placed on senate calendar) bill text",
    "short titles for portions of this bill from rfs (referred to senate) bill text",
    "short titles from engrossed amendment house bill text",
    "short titles from engrossed amendment senate bill text",
    "short titles from engrossed amendment senate for portions of this bill",
    "short titles from enr (enrolled) bill text",
    "short titles from pcs (placed on senate calendar) bill text",
    "short titles from rfs (referred to senate) bill text",
})

# Index-time year strip. The `(\s+of)?` branch is LOAD-BEARING and is not decoration: appropriations
# titles are COMMA-year ("...Appropriations Act, 2026"), which the tokenizer reduces to a BARE trailing
# year, while authorization titles are "of"-year ("Birthright Citizenship Act of 2025"). A regex that
# only strips "of YYYY" drops the ENTIRE appropriations family from the index and the live #1/#2 rows
# score 0.000. Measured (docs/16 §1a), not theorized.
_YEAR_TAIL = re.compile(r"(\s+of)?\s+(19|20)\d{2}\s*$", re.I)
_ACRONYM = re.compile(r"^[A-Z][A-Z0-9.\-]+$")

_TODAY = date.today().isoformat()


def _toks(s: str) -> tuple[str, ...]:
    """Tokenize with the SAME tokenizer that produced the ledger n-grams. Non-negotiable: an index
    built by any other tokenizer cannot align with the phrases it must cover. boilerplate.sentences()
    strips commas, which is exactly why the subcommittee 'National Security, Department of State, and
    Related Programs' is windowable as the live phrase 'national security department'."""
    out: list[str] = []
    for sent in boilerplate.sentences(s):
        out.extend(sent)
    return tuple(out)


def _content_len(toks) -> int:
    return sum(1 for t in toks if t not in boilerplate.STOPWORDS)


def _indexable(raw_name: str) -> str | None:
    """A raw official name -> its canonical indexed token string, or None if it is too thin to index.
    Year-stripped at index time so 'Water Resources Development Act of 2024' and '... Act, 2026' are
    ONE name."""
    toks = _toks(_YEAR_TAIL.sub("", raw_name))
    if len(toks) < 2 or _content_len(toks) < config.NOMENCLATURE_MIN_NAME_CONTENT_TOKENS:
        return None
    return " ".join(toks)


# --- acquisition ---------------------------------------------------------------------------------
def _get(url: str, timeout: int = 180) -> tuple[bytes, str]:
    """GET returning (body, content_type). The Content-Type is returned rather than swallowed because
    it is the ONLY signal that separates a real payload from a bulkdata error (see fetch_billstatus)."""
    req = urllib.request.Request(url, headers={"User-Agent": lanes.POLITE["user_agent"],
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def fetch_billstatus(congress: int, bill_type: str, dest: Path | None = None) -> Path:
    """Mirror one BILLSTATUS bulk zip to X:\\onscript-data\\bills\\raw\\, hash-manifested + resumable.

    MASKED-ERROR GUARD: the bulkdata service answers an error with **HTTP 200 and an HTML error page**,
    so urlopen does not raise and status is a useless signal. Verified live 2026-07-16: the directory
    endpoint returns 200 + 'text/html;charset=UTF-8' EVEN WITH `Accept: application/json` (the docs/16
    §4 note that the header suppresses it is optimistic — the header is not a fix, the guard is). Only
    the Content-Type separates a zip from a 67 KB HTML apology, which zipfile would then reject with a
    misleading 'not a zip file' 200 pages downstream.
    """
    dest = Path(dest) if dest else lanes.lane_raw("bills")
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"BILLSTATUS-{congress}-{bill_type}.zip"
    man = lanes.CrawlManifest(lanes.lane_state("bills") / "crawl-manifest.jsonl")
    uid = f"billstatus:{congress}:{bill_type}"
    if man.seen(uid) and path.exists():
        return path                      # already mirrored + hashed -> resume without re-fetching
    body, ct = _get(BILLSTATUS_URL.format(congress=congress, t=bill_type))
    if "zip" not in ct and "json" not in ct:
        raise RuntimeError(f"masked bulkdata error: Content-Type={ct!r} for {congress}/{bill_type} "
                           f"({len(body)} bytes, HTTP 200) — the payload is an error page, not data")
    path.write_bytes(body)
    man.record(uid, lanes.sha256(body), len(body), {"congress": congress, "type": bill_type})
    time.sleep(lanes.POLITE["min_interval_s"])
    return path


def fetch_committee_yaml(dest: Path | None = None) -> dict[str, Path]:
    """Mirror the two congress-legislators committee YAMLs (raw.githubusercontent, not the dead
    theunitedstates.io JSON export — that SSL failure is host-specific, pipeline/roster.py:4-5)."""
    dest = Path(dest) if dest else lanes.lane_raw("committees")
    dest.mkdir(parents=True, exist_ok=True)
    man = lanes.CrawlManifest(lanes.lane_state("committees") / "crawl-manifest.jsonl")
    out = {}
    for which, url in COMMITTEE_YAML.items():
        path = dest / f"committees-{which}.yaml"
        body, _ct = _get(url)
        path.write_bytes(body)
        man.record(f"committees:{which}:{_TODAY}", lanes.sha256(body), len(body))
        out[which] = path
        time.sleep(lanes.POLITE["min_interval_s"])
    return out


# --- the bill lane -------------------------------------------------------------------------------
def synthesize_acronym_glosses(shorts_per_bill) -> set[str]:
    """Recover the GLOSSED name a member actually types. A bill carries both its long short-title
    ('Safeguard American Voter Eligibility Act') and its acronym short-title ('SAVE Act'), but members
    write the gloss — 'the Safeguard American Voter Eligibility (SAVE) Act' — which tokenizes to a
    string matching NEITHER indexed name. Splice the acronym in before the shared head noun so the
    glossed form is covered. Same-bill only, so this can never invent a name across two statutes."""
    longs = [s for s in shorts_per_bill if len(s.split()) >= 4]
    acros = [s for s in shorts_per_bill if len(s.split()) <= 3]
    out: set[str] = set()
    for lg in longs:
        lt = lg.split()
        for ac in acros:
            at = ac.split()
            # require a real acronym token and a shared head noun ('... Act' / '... Act')
            if len(at) >= 2 and at[-1].lower() == lt[-1].lower() and _ACRONYM.match(at[0]):
                out.add(" ".join(lt[:-1] + at[:-1] + lt[-1:]))
    return out


def _title_concept(title_type: str) -> str:
    """The (s)-normalized prose key: 'Short Title(s) as Passed House' and the legacy 'Short Titles as
    Passed House' are the same concept spelled two ways."""
    return title_type.lower().replace("(s)", "s").strip()


def _is_short_title(item) -> bool:
    """Is this <titles><item> a SHORT title? Prefers titleTypeCode (docs/16's rule, exact); falls back
    to the overlap-calibrated prose map ONLY when the code is absent, which is every congress < 118."""
    code = (item.findtext("titleTypeCode") or "").strip()
    if code:
        return code in TITLE_TYPE_ALLOW
    return _title_concept(item.findtext("titleType") or "") in TITLE_TYPE_PROSE_ALLOW


def parse_titles(zip_path, stats: dict | None = None) -> dict[str, str]:
    """One BILLSTATUS zip -> {indexed name: cite}. Short titles only, year-stripped, plus the same-bill
    acronym glosses. The cite is the bill designator ('hr22') so every tag the tagger emits points at
    the official record that licensed it. `stats` (optional) collects the basis counts that make an
    empty index loud instead of silent."""
    names: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            if not member.endswith(".xml"):
                continue
            try:
                root = ET.fromstring(z.read(member))
            except ET.ParseError:
                if stats is not None:
                    stats["torn_xml"] = stats.get("torn_xml", 0) + 1
                continue                 # a torn member never kills the build; it is counted, not hidden
            bill = root.find(".//bill")
            if bill is None:
                continue
            cite = ((bill.findtext("type") or "").strip() + (bill.findtext("number") or "").strip()).lower()
            shorts = []
            for it in root.findall(".//titles/item"):
                title = (it.findtext("title") or "").strip()
                if not title:
                    continue
                if stats is not None:
                    basis = "code" if (it.findtext("titleTypeCode") or "").strip() else "prose"
                    stats[f"items_{basis}"] = stats.get(f"items_{basis}", 0) + 1
                if _is_short_title(it):
                    shorts.append(title)
            for raw in set(shorts) | synthesize_acronym_glosses(shorts):
                key = _indexable(raw)
                if key:
                    names.setdefault(key, cite)   # first bill to claim a name keeps the cite
    return names


def build_bill_titles(congress: int, *, progress: bool = True) -> dict:
    """Fetch + parse every bill type for one congress -> the committed bill-titles table."""
    names: dict[str, str] = {}
    stats: dict = {}
    bills = 0
    for t in BILL_TYPES:
        path = fetch_billstatus(congress, t)
        with zipfile.ZipFile(path) as z:
            bills += sum(1 for n in z.namelist() if n.endswith(".xml"))
        got = parse_titles(path, stats)
        names.update({k: v for k, v in got.items() if k not in names})
        if progress:
            print(f"[nomenclature] {congress}/{t}: {len(got)} names ({path.stat().st_size/1e6:.1f} MB)", flush=True)
    # An empty or near-empty index is the silent failure this whole item exists to prevent (a tagger
    # that tags nothing looks exactly like a clean corpus). Refuse to write one.
    if len(names) < 100:
        raise RuntimeError(f"congress {congress}: only {len(names)} names from {bills} bills — the title "
                           f"allowlist did not match this congress's vocabulary (basis counts: {stats}). "
                           f"Refusing to write a silently-empty index.")
    basis = "titleTypeCode" if stats.get("items_prose", 0) == 0 else (
        "titleType-prose (overlap-calibrated on 118/119)" if stats.get("items_code", 0) == 0 else "mixed")
    return _table(
        kind="nomenclature-bill-titles",
        source=f"govinfo BILLSTATUS bulkdata, congress {congress}, types {'/'.join(BILL_TYPES)} (keyless; "
               f"mirrored + sha256-manifested to {lanes.lane_raw('bills')})",
        rationale="Official statute names, so a bill title is never counted as a message. SHORT titles only: "
                  "Official/Display titles are prose and would put ordinary policy English in the index. Names "
                  "are year-stripped at index time so 'Act of 2025' and 'Act, 2026' are one name. Every row "
                  "cites the bill that licensed it.",
        congress=congress,
        index_basis=basis,
        title_type_codes=sorted(TITLE_TYPE_ALLOW),
        title_type_prose=(sorted(TITLE_TYPE_PROSE_ALLOW) if basis != "titleTypeCode" else None),
        bills_parsed=bills,
        title_items=stats,
        names={k: names[k] for k in sorted(names)},
    )


# --- the committee lane --------------------------------------------------------------------------
_QUALIFIERS = ("committee on {}", "subcommittee on {}", "{} committee", "{} subcommittee")


def _committee_row(raw_name: str, cite: str, out: dict[str, str], stats: dict) -> None:
    """Index one committee/subcommittee name under the qualification rule."""
    toks = _toks(raw_name)
    if not toks:
        return
    key = " ".join(toks)
    if _content_len(toks) >= config.COMMITTEE_UNQUALIFIED_MIN_TOKENS:
        out.setdefault(key, cite)
        stats["unqualified"] += 1
        return
    # GENERIC-NAME HAZARD (measured on the real roster): 43 of the 181 current subcommittee names are
    # under 3 tokens and 65 are under 3 CONTENT tokens — 'Defense', 'Readiness', 'Aviation', 'Housing
    # and Insurance'. Indexed bare they would tag ordinary English ('aviation in this country') on the
    # authority of a subcommittee's existence. They enter ONLY qualified, so the word
    # 'committee'/'subcommittee' must appear in the phrase before the tag can fire.
    stats["qualified_only"] += 1
    for form in _QUALIFIERS:
        out.setdefault(" ".join(_toks(form.format(key))), cite)


def build_committee_names(yaml_paths) -> dict:
    """The committee/subcommittee name table from congress-legislators YAML.

    PyYAML is imported HERE, inside the offline generator, and never at module scope: pipeline/ is
    stdlib-only at runtime, PyYAML is absent from Actions, and the daily path reads the JSON this
    commits. Same generator policy as data/reference/deep/crec_granule_classes.json.
    """
    import yaml   # offline-only, one-time: parse once locally, commit JSON (docs/16 §4, CLAUDE.md §1.3)

    out: dict[str, str] = {}
    stats = {"committees": 0, "subcommittees": 0, "unqualified": 0, "qualified_only": 0}
    for which in ("current", "historical"):
        path = yaml_paths.get(which)
        if not path:
            continue
        for c in yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []:
            tid = c.get("thomas_id") or c.get("house_committee_id") or c.get("senate_committee_id") or "?"
            if c.get("name"):
                stats["committees"] += 1
                _committee_row(c["name"], f"cmte:{tid}", out, stats)
            for s in c.get("subcommittees") or []:
                if s.get("name"):
                    stats["subcommittees"] += 1
                    _committee_row(s["name"], f"subcmte:{tid}{s.get('thomas_id') or ''}", out, stats)
    return _table(
        kind="nomenclature-committee-names",
        source="unitedstates/congress-legislators committees-current.yaml + committees-historical.yaml "
               f"(raw.githubusercontent.com; mirrored to {lanes.lane_raw('committees')}); parsed offline "
               "with PyYAML 6.0.3 and committed as JSON — the daily pipeline never parses YAML.",
        rationale="Institution names, so a committee's name is never counted as a message. This lane is "
                  "load-bearing, not a nicety: the bill lane ALONE scores the live #1 phrase 'national "
                  "security department' at 0.109 (a MISS); it is the House Appropriations subcommittee "
                  "'National Security, Department of State, and Related Programs'. Names under "
                  f"{config.COMMITTEE_UNQUALIFIED_MIN_TOKENS} content tokens enter ONLY in qualified form.",
        counts=stats,
        names={k: out[k] for k in sorted(out)},
    )


# --- the verdicts lane ---------------------------------------------------------------------------
# THE DOMAIN. A verdict is a doc-level MEASUREMENT, so it exists only for phrases the corpus can
# measure — and the only phrases the instrument can ever display are the ledger's synchronized ones.
# So the domain is the LEDGER'S OWN candidate rule, taken from phrases.py rather than re-implemented:
# an n-gram used by >= SYNC_MIN_MEMBERS distinct units of one party on one day. Measured on congress
# 119: 461,501 synchronized phrases, of which only 14,178 (3.1%) are covered by an official name at
# all -> a 1.57 MB table. A doc-floor instead of the ledger's rule was measured at 16.55 MB and is an
# invented knob; this is the instrument's own.
VERDICT_MIN_CORPUS_DOCS = 1000   # below this a per-congress ratio is not a measurement (see main())


def _covered_occurrences(toks: list[str], runs) -> dict:
    """{(ngram, i): (class, cite)} for every window that a name run covers. Only windows OVERLAPPING a
    run can be covered, so this enumerates a tiny neighbourhood instead of the document's whole n-gram
    space — the optimization that makes the candidate pass affordable."""
    out: dict[tuple[str, int], tuple[str, str]] = {}
    L = len(toks)
    for r0, r1, _cite in runs:
        for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
            for i in range(max(0, r0 - n + 1), min(r1 + 1, L - n + 1)):
                cls, cite = nomenclature._classify(toks, i, n, runs)
                if cls:
                    out[(" ".join(toks[i:i + n]), i)] = (cls, cite)
    return out


def _sync_domain(by_day: dict, *, progress: bool = True) -> set[str]:
    """The ledger's candidate set for this congress, using phrases.py's OWN rule and tokenizer (an
    independently re-implemented domain would drift from the ledger it must cover). Day-scoped so the
    day's dense counts are discarded and peak memory stays bounded — same reason as phrases.py's
    two-pass model."""
    sync: set[str] = set()
    for di, (_day, group) in enumerate(by_day.items()):
        counts: dict[str, dict[str, set]] = {}
        for s in group:
            unit = phrases._unit_key(s)
            party = s["member"]["party"]
            for ng, _n in phrases._doc_ngrams(s.get("text", "")):
                counts.setdefault(ng, {}).setdefault(party, set()).add(unit)
        for ng, parties in counts.items():
            if ng not in sync and any(len(u) >= config.SYNC_MIN_MEMBERS for u in parties.values()):
                sync.add(ng)
        if progress and di and di % 100 == 0:
            print(f"[nomenclature] verdicts pass 1: {di}/{len(by_day)} days, {len(sync):,} phrases", flush=True)
    return sync


def build_verdicts(congress: int, corpus_path=None, *, progress: bool = True) -> dict:
    """Full-corpus occurrence scan -> the committed verdicts table for one congress.

    ratio = docs where EVERY occurrence is covered / docs containing the phrase (doc-level, matching
    _doc_ngrams' set-dedupe semantics). A document counts as nomenclature only if every occurrence in
    it is covered: conservative, precision-favoring. The ratio is stored and the THRESHOLD is applied
    at read time, so NOMENCLATURE_RATIO_MIN stays a live knob (docs/16 §8.4 forbids locking it here).
    Rows with ratio 0 are omitted — absent means the same thing as 0.000 to is_nomenclature, and the
    domain is 30x larger than the covered set.
    """
    corpus_path = corpus_path or (config.STATE / "statements.jsonl.gz")
    idx = nomenclature.load_index(congress)
    eng = phrases.PhraseEngine()          # borrowed for _eligible: the ledger's lane/party/syndication rule
    by_day: dict[str, list[dict]] = {}
    for s in util.iter_jsonl(corpus_path):
        c = s.get("congress") or util.congress_for_date(s["published_at"])
        if c == congress and eng._eligible(s):
            by_day.setdefault(s["published_at"], []).append(s)
    docs_total = sum(len(g) for g in by_day.values())
    if progress:
        print(f"[nomenclature] verdicts {congress}: {docs_total:,} statements over {len(by_day)} days", flush=True)

    sync = _sync_domain(by_day, progress=progress)
    docs: dict[str, int] = {}
    nom_docs: dict[str, int] = {}
    cites: dict[str, dict[str, int]] = {}
    rules: dict[str, dict[str, int]] = {}
    for di, group in enumerate(by_day.values()):
        for s in group:
            toks = nomenclature._toks(s.get("text", ""))
            runs = nomenclature.name_spans(toks, idx)
            cov = _covered_occurrences(toks, runs) if runs else {}
            here: dict[str, list] = {}
            L = len(toks)
            for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
                for i in range(0, L - n + 1):
                    ng = " ".join(toks[i:i + n])
                    if ng not in sync:
                        continue
                    hit = cov.get((ng, i))
                    e = here.get(ng)
                    if e is None:
                        here[ng] = [hit is not None, hit]
                    else:
                        e[0] = e[0] and hit is not None   # EVERY occurrence in the doc, or the doc is a message
                        e[1] = e[1] or hit
            for ng, (all_covered, hit) in here.items():
                docs[ng] = docs.get(ng, 0) + 1
                if all_covered:
                    nom_docs[ng] = nom_docs.get(ng, 0) + 1
                    cls, cite = hit
                    cites.setdefault(ng, {})[cite] = cites.setdefault(ng, {}).get(cite, 0) + 1
                    rules.setdefault(ng, {})[cls] = rules.setdefault(ng, {}).get(cls, 0) + 1
        if progress and di and di % 100 == 0:
            print(f"[nomenclature] verdicts pass 2: {di}/{len(by_day)} days, {len(nom_docs):,} covered", flush=True)

    verdicts: dict[str, dict] = {}
    hist: dict[str, int] = {}
    for ng in sync:
        d = docs.get(ng, 0)
        ratio = (nom_docs.get(ng, 0) / d) if d else 0.0
        hist[f"{min(int(ratio * 10), 9) / 10:.1f}"] = hist.get(f"{min(int(ratio * 10), 9) / 10:.1f}", 0) + 1
        if not nom_docs.get(ng):
            continue
        # The lane/cite/rule of the record that MOST OFTEN licensed the tag — a phrase can be covered
        # by a bill title in one document and a committee name in another ('national security
        # department' is both), so the receipt names the dominant licensor rather than an arbitrary one.
        cite = max(cites[ng].items(), key=lambda kv: kv[1])[0]
        verdicts[ng] = {"ratio": round(ratio, 4), "lane": nomenclature._lane(cite), "cite": cite,
                        "docs": d, "nom_docs": nom_docs[ng],
                        "rule": max(rules[ng].items(), key=lambda kv: kv[1])[0]}
    versions = sorted(json.loads((OUT_DIR / f"bill-titles-{c}.json").read_text(encoding="utf-8"))["fetch_date"]
                      for c in range(config.NOMENCLATURE_INDEX_CONGRESS_MIN, congress + 1)
                      if (OUT_DIR / f"bill-titles-{c}.json").exists())
    return _table(
        kind="nomenclature-verdicts",
        source=f"occurrence scan of {docs_total:,} congress-{congress} Lane-1 statements against the "
               f"cumulative 108..{congress} name index ({sum(len(v) for v in idx.values()):,} names)",
        rationale="Nomenclature is a property of the OCCURRENCE, not of the phrase: `the save act` is "
                  "nomenclature in 'reintroduced the SAVE Act' and messaging in 'the SAVE Act would gut "
                  "Medicaid'. So a verdict is a doc-level measurement over the real corpus, never a test "
                  "applied to a string. ratio = docs where EVERY occurrence is covered by an official "
                  "name span / docs containing the phrase.",
        congress=congress,
        index_version=versions[-1] if versions else None,
        domain="the ledger's own rule (pipeline/phrases.py): an n-gram used by >= SYNC_MIN_MEMBERS "
               "distinct units of one party on one day. Phrases outside it are not displayable, so they "
               "are not measured; is_nomenclature returns None for them.",
        threshold_at_build={"NOMENCLATURE_RATIO_MIN": config.NOMENCLATURE_RATIO_MIN,
                            "note": "RECORDED, NOT APPLIED — the threshold is a disclosed knob applied "
                                    "at read time by is_nomenclature. docs/16 §8.4 measured "
                                    "'transportation and infrastructure' at 0.802, one thousandth above "
                                    "it, which falsifies the 'nothing lands in the dead zone' claim: the "
                                    "threshold does delicate work and must move without a rebuild."},
        counts={"corpus_statements": docs_total, "sync_phrases": len(sync), "covered_phrases": len(verdicts),
                "tagged_at_build_threshold": sum(1 for v in verdicts.values()
                                                 if v["ratio"] >= config.NOMENCLATURE_RATIO_MIN)},
        ratio_histogram={k: hist[k] for k in sorted(hist)},
        payload_key="verdicts",
        names={k: verdicts[k] for k in sorted(verdicts)},
        amend_policy="regenerated wholesale by `python -m pipeline.nomenclature_build --skip-bills "
                     "--skip-committees`; hand edits are never made to `verdicts` (it is a measurement, "
                     "and a hand-edited row is an unfalsifiable claim). Threshold changes are a config "
                     "knob and need no rebuild; rule changes land as dated amendments here + docs/16 §9.",
        amendments=[
            {"date": "2026-07-16", "by": "Opus, docs/16 §3/§5 tagger build",
             "reason": "initial scan. Reproduces docs/16 §2's measured numbers on the real corpus "
                       "(road-to-housing straddles 0.986/0.985, 'national security department' 0.946 via "
                       "the committee lane, 'child tax credit' 0.003, 'transportation and infrastructure' "
                       "0.802). Differences from §2 are expected and are the index, not the rules: §2 was "
                       "measured on a 119/hr-only index, this table on the specified cumulative 108..119 "
                       "index across all 8 bill types PLUS the committee lane, so coverage is strictly "
                       "higher ('law enforcement officers' 0.002 -> 0.121, still PROTECT). NOTE for "
                       "docs/16 §9.2 (the ACA ruling): 'the affordable care act' measures 0.001 under the "
                       "cumulative index, i.e. PROTECT — the short title in BILLSTATUS 113-119 is "
                       "'Patient Protection and Affordable Care Act' (the ACA was enacted in the 111th, "
                       "outside the index), so 'affordable care act' is not an indexed name and §9.2's "
                       "premise does not hold. Reported, not ruled on."},
        ],
    )


# --- the committed-table header idiom (mirrors data/reference/deep/crec_boilerplate_seeds.json) ---
def _table(*, kind: str, source: str, rationale: str, names: dict, payload_key: str = "names",
           amend_policy: str | None = None, amendments: list | None = None, **extra) -> dict:
    return {
        "schema_version": 1,
        "kind": kind,
        "source": source,
        "fetch_date": _TODAY,
        "rationale": rationale,
        **{k: v for k, v in extra.items() if v is not None},
        payload_key: names,
        "amend_policy": amend_policy or
                        "regenerated wholesale by pipeline/nomenclature_build.py; hand edits are never "
                        "made to `names` (it is a mirror of an official record). Rule/allowlist changes "
                        "land as dated amendments here + in docs/16 §9.",
        "amendments": amendments or [
            {"date": "2026-07-16", "by": "Opus, docs/16 §4 reference-data build",
             "reason": "initial acquisition. Three verified traps drove the code: (1) the bulkdata service "
                       "returns HTTP 200 + text/html on error — confirmed live that `Accept: "
                       "application/json` does NOT suppress it, so fetch_billstatus gates on Content-Type, "
                       "never status; (2) the index-time year strip must remove a BARE trailing year "
                       "('Appropriations Act, 2026'), not just 'of YYYY' — omitting that branch drops the "
                       "whole appropriations family and the live #1/#2 rows score 0.000; (3) titleTypeCode "
                       "DOES NOT EXIST before congress 118 (measured: present on 100% of sampled 118/119 "
                       "items, 0% of 113-117), so docs/16's code allowlist yields an EMPTY index for 5 of "
                       "the 7 congresses it asks for. 113-117 therefore key on an exact-string titleType "
                       "map calibrated against the 118/119 overlap (where prose predicts the code with zero "
                       "ambiguity), NOT on a prose regex — docs/16 is right that a regex is unsafe: "
                       "`startswith('short title')` mismatches the allowlist 14 ways. Congress 107 404s "
                       "(not in bulkdata) and 108-112 stays deferred (docs/16 §7.1)."},
        ],
    }


# --- driver --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the nomenclature reference tables (offline capex).")
    ap.add_argument("--congresses", default=",".join(str(c) for c in CONGRESSES),
                    help="comma-separated congresses (default 113-119; 107 404s, 108-112 deferred)")
    ap.add_argument("--skip-bills", action="store_true")
    ap.add_argument("--skip-committees", action="store_true")
    ap.add_argument("--skip-verdicts", action="store_true")
    ap.add_argument("--corpus", default=None, help="normalized statements (default data/state/statements.jsonl.gz)")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.skip_bills:
        for c in [int(x) for x in args.congresses.split(",") if x.strip()]:
            if c < config.NOMENCLATURE_INDEX_CONGRESS_MIN:
                print(f"[nomenclature] congress {c} < {config.NOMENCLATURE_INDEX_CONGRESS_MIN} "
                      f"(not in BILLSTATUS bulkdata) — skipped", flush=True)
                continue
            table = build_bill_titles(c)
            path = OUT_DIR / f"bill-titles-{c}.json"
            util.write_json(path, table, indent=None)   # compact: a generated table, ~0.6 MB/congress
            print(f"[nomenclature] {path.name}: {len(table['names'])} names from "
                  f"{table['bills_parsed']} bills ({path.stat().st_size/1e6:.2f} MB)", flush=True)
    if not args.skip_committees:
        table = build_committee_names(fetch_committee_yaml())
        path = OUT_DIR / "committee-names.json"
        util.write_json(path, table, indent=None)
        print(f"[nomenclature] {path.name}: {len(table['names'])} names "
              f"({table['counts']}) ({path.stat().st_size/1e3:.0f} KB)", flush=True)
    if not args.skip_verdicts:
        # A verdict is a ratio over documents, so a congress with a handful of statements has no
        # measurable one. The press spine is 75,922/75,989 congress-119 and 67 congress-118: 118 is
        # skipped LOUDLY rather than shipped as a 67-document "measurement".
        for c in [int(x) for x in args.congresses.split(",") if x.strip()]:
            table = build_verdicts(c, args.corpus)
            n = table["counts"]["corpus_statements"]
            if n < VERDICT_MIN_CORPUS_DOCS:
                print(f"[nomenclature] congress {c}: {n} statements in the corpus (< "
                      f"{VERDICT_MIN_CORPUS_DOCS}) — a doc-level ratio over that many documents is not "
                      f"a measurement. No verdicts table written; is_nomenclature returns None there.",
                      flush=True)
                continue
            path = OUT_DIR / f"verdicts-{c}.json"
            util.write_json(path, table, indent=None)
            print(f"[nomenclature] {path.name}: {table['counts']} ({path.stat().st_size/1e6:.2f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
