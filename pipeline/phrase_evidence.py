"""Deterministic peak-day source evidence for public phrase pages.

The published slice contains identity, party/state, date, and source URL only. Source text is used
solely for verifier-grade containment and a cache fingerprint; it is never written to the slice.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

from . import boilerplate, config, document_families, privacy, roster, util
from .phrase_window import public_phrase_window
from .phrases import _unit_key

QUORUM = 3
STORED_PER_PARTY = 6

# S67-6. The published key is the NORMALIZED n-gram, so a dollar figure reaches the front page as
# "1 8 billion" and reads to a stranger as a bug rather than as measurement output. The fix is a
# display-only companion artifact naming one real spelling of the key from the sources.
#
# IT IS A SEPARATE FILE ON PURPOSE. phrase-evidence.json is contractually metadata-only ("identity,
# party/state, date, and source URL only", locked by test_slice_has_only_valid_source_metadata...),
# and a surface form is by definition a fragment of a source statement. Rather than quietly widen
# that contract, the fragment lives in its own artifact with its own name and its own gate, so the
# evidence slice's invariant is untouched and this one is auditable on its own terms.
#
# It participates in the cache key below. Without that, every entry a production run has already
# cached would be served back with no surface in it, and the artifact would populate only for
# phrases whose peak day happened to change: the stale-shape trap docs/37 rule 4 is about.
#
# DELIBERATELY NOT NAMED *METHOD_VERSION, and the distinction is real rather than a way around the
# provider scan in instrument_fingerprint. A METHOD_VERSION identifies a measurement: change one and
# a published NUMBER can move, which is why the instrument fingerprint stamps them all. This picks
# which of several already-measured spellings to display. No count, denominator, quorum or ranking
# reads it, so folding it into the measurement fingerprint would make a cosmetic edit announce
# itself as an instrument change. The artifact stamps its own revision instead, so the file always
# says which rule produced it.
SURFACE_REVISION = "phrase_surface@1"
SURFACE_MAX_LEN = 120

# The quorum counts PROJECT UNITS, so the identity that decides what one unit is belongs in
# this artifact's identity too. It is read live from the stage that owns it and never copied
# (docs/37 rules 1 and 6); a bump there invalidates every cached count here rather than
# serving a quorum measured under the superseded collapse.
UNIT_IDENTITY_METHOD = "document_families.METHOD_VERSION"


def _http_url(value) -> str:
    url = str(value or "").strip()
    return url if url.lower().startswith(("http://", "https://")) else ""


def _name(statement: dict, rmap: dict) -> str:
    member = statement.get("member") or {}
    bio = member.get("bioguide") or ""
    return str(member.get("name") or (rmap.get(bio, {}) or {}).get("name") or "").strip()


def _source_fingerprint(statements: list[dict], rmap: dict) -> str:
    """Stable day fingerprint. Text contributes by hash and is never retained in the cache."""
    digest = hashlib.sha256()
    for statement in sorted(statements, key=lambda s: (str(s.get("id") or ""), str(s.get("url") or ""))):
        member = statement.get("member") or {}
        row = {
            "id": statement.get("id"),
            "joint_group": statement.get("joint_group"),
            "member": _name(statement, rmap),
            "bioguide": member.get("bioguide"),
            "party": member.get("party"),
            "state": member.get("state"),
            "url": statement.get("url"),
            "text_sha256": util.sha256_hex(statement.get("text") or ""),
        }
        digest.update(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _surface_forms(ngram: str, text: str) -> list[str]:
    """Every raw span in ``text`` whose tokens are exactly ``ngram``, as it was actually published.

    Located through the SAME tokenizer the phrase engine measures with (``_sentence_token_spans``
    keeps offsets into the unmodified source), so the span returned is precisely the run of
    characters that produced the key, never a substring search that could straddle a sentence."""
    from .phrases import _sentence_token_spans
    wanted = str(ngram or "").split()
    n = len(wanted)
    if not n or not text:
        return []
    out = []
    for tokens in _sentence_token_spans(text):
        for i in range(len(tokens) - n + 1):
            if [tok for tok, _s, _e in tokens[i:i + n]] != wanted:
                continue
            span = text[tokens[i][1]:tokens[i + n - 1][2]]
            span = " ".join(span.split())
            if span and len(span) <= SURFACE_MAX_LEN:
                out.append(span)
    return out


def _build_one(ngram: str, peak_day: str, statements: list[dict], rmap: dict) -> dict:
    from collections import Counter
    surfaces: Counter = Counter()
    units: dict[str, dict] = {}
    for statement in sorted(statements, key=lambda s: (
            str(_unit_key(s)), str((s.get("member") or {}).get("party") or ""),
            _name(s, rmap), str(s.get("url") or ""))):
        member = statement.get("member") or {}
        party = member.get("party")
        if party not in config.COMPOSITE_PARTIES or statement.get("syndicated"):
            continue
        if not boilerplate.contains_gram(statement.get("text") or "", ngram):
            continue
        name, url = _name(statement, rmap), _http_url(statement.get("url"))
        if not name or not member.get("state") or not url:
            continue
        receipt = {
            "member": name,
            "party": party,
            "state": member.get("state"),
            "date": peak_day,
            "url": url,
        }
        if privacy.is_suppressed(" ".join(str(v or "") for v in receipt.values())):
            continue
        unit = _unit_key(statement)
        if str(unit) not in units:
            # Counted once per UNIT, matching the quorum: a joint release republished by five
            # offices must not make its spelling five times more representative than anyone else's.
            surfaces.update(set(_surface_forms(ngram, statement.get("text") or "")))
        units.setdefault(str(unit), receipt)

    receipts = list(units.values())
    receipts.sort(key=lambda r: (r["party"], r["member"], r["state"], r["url"]))
    counts = {party: sum(1 for r in receipts if r["party"] == party)
              for party in config.COMPOSITE_PARTIES}
    stored = []
    for party in config.COMPOSITE_PARTIES:
        stored.extend([r for r in receipts if r["party"] == party][:STORED_PER_PARTY])
    # Most frequent spelling wins; ties break lexicographically, so the pick is a pure function of
    # the day's sources. Kept in the (private, state-side) cache and stripped before the evidence
    # slice is written; see SURFACE_REVISION.
    surface = min(surfaces.items(), key=lambda kv: (-kv[1], kv[0]))[0] if surfaces else ""
    return {"peak_day": peak_day, "grounded_units": len(units), "counts": counts,
            "receipts": stored, "surface": surface}


def _phrase_records(out_dir: Path) -> list[tuple[str, dict]]:
    rows = []
    for path in sorted((out_dir / "phrases").glob("*.json")):
        if path.stem == "top":
            continue
        data = util.read_json(path, None)
        if isinstance(data, dict) and data.get("ngram"):
            rows.append((data.get("slug") or path.stem, data))
    return rows


def build_phrase_evidence(statements: list[dict], out_dir: Path, *, cache_path: Path | None = None,
                          rmap: dict | None = None) -> tuple[dict, dict]:
    """Build the public slice and prune the incremental cache to currently published phrases."""
    started = time.perf_counter()
    out_dir = Path(out_dir)
    cache_path = cache_path or (config.STATE / "phrase_evidence_cache.json")
    rmap = roster.load() if rmap is None else rmap

    targets = []
    for slug, pdata in _phrase_records(out_dir):
        ngram = pdata.get("ngram") or ""
        if not ngram or privacy.is_suppressed(ngram):
            continue
        window = public_phrase_window(pdata)
        if window["peak_day"]:
            targets.append((slug, ngram, window["peak_day"]))

    peak_days = {day for _, _, day in targets}
    by_day: dict[str, list[dict]] = defaultdict(list)
    for statement in statements:
        day = statement.get("published_at")
        if day in peak_days and statement.get("lane") == 1:
            by_day[day].append(statement)
    fingerprints = {day: _source_fingerprint(by_day.get(day, []), rmap) for day in peak_days}

    unit_identity = document_families.METHOD_VERSION
    prior = util.read_json(cache_path, {})
    prior_entries = prior.get("entries", {}) if isinstance(prior, dict) else {}
    next_cache, published, surfaces = {}, {}, {}
    hits = misses = omissions = 0
    for slug, ngram, peak_day in sorted(targets):
        key = f"{slug}|{peak_day}|{fingerprints[peak_day]}|{unit_identity}|{SURFACE_REVISION}"
        if key in prior_entries:
            result, hits = prior_entries[key], hits + 1
        else:
            result = _build_one(ngram, peak_day, by_day.get(peak_day, []), rmap)
            misses += 1
        next_cache[key] = result
        if int(result.get("grounded_units") or 0) < QUORUM:
            omissions += 1
            print(f"[phrase-evidence] omitted {slug} on {peak_day}: "
                  f"{result.get('grounded_units', 0)} grounded units (<{QUORUM})")
            continue
        # Art. XIII is checked again immediately before the public slice is written.
        if privacy.is_suppressed(ngram):
            continue
        # The surface form leaves the evidence record HERE, so phrase-evidence.json keeps its
        # metadata-only contract byte for byte and the fragment is published only through the
        # artifact that declares itself as carrying one.
        surface = str(result.get("surface") or "")
        published[slug] = {k: v for k, v in result.items() if k != "surface"}
        if surface and not privacy.is_suppressed(surface):
            surfaces[slug] = surface

    artifact = {"phrases": published, "unit_identity_method": unit_identity}
    util.write_json(cache_path, {"entries": next_cache}, indent=None)
    util.write_json(out_dir / "phrase-evidence.json", artifact, indent=None)
    util.write_json(out_dir / "phrase-surfaces.json",
                    {"method_version": SURFACE_REVISION, "surfaces": surfaces}, indent=None)
    stats = {
        "targets": len(targets), "published": len(published), "omitted": omissions,
        "surfaces": len(surfaces),
        "cache_hits": hits, "cache_misses": misses,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    print(f"[phrase-evidence] {stats}")
    return artifact, stats
