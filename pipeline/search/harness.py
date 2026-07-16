"""Query harness for The Search (docs/12 §S0.2). Stdlib-only, constant-memory.

The per-Congress ledger shards are single JSON objects of hundreds of MB to 1 GB (`ngram -> entry`);
`json.load` on the 3 GB monolith is impossible and risky even on the big shards. `iter_ledger_entries`
streams (ngram, entry) pairs in bounded memory via the real JSON decoder (raw_decode) over a
refillable buffer — braces-inside-strings and chunk-boundary splits are handled by the decoder, not by
hand. This is also the Archive/1.1 streaming reader the BUILD-PROGRAM queued.
"""
from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

from .. import config, fetch, util

ALEX = config.STATE / "alexandria"
SEARCH_CACHE = config.DERIVED / "search"
_PARTY = {"Democrat": "D", "Republican": "R", "Independent": "I"}


# --- streaming reader for a big `{ "ngram": {entry}, ... }` shard --------------------------------
class _Refillable:
    """A file-backed string buffer that raw_decode can parse against, refilling from disk on demand
    and trimming the consumed prefix so memory stays bounded regardless of file size."""
    def __init__(self, fh, chunk: int):
        self.fh, self.chunk = fh, chunk
        self.buf, self.pos, self.eof = "", 0, False

    def _refill(self) -> bool:
        if self.eof:
            return False
        more = self.fh.read(self.chunk)
        if not more:
            self.eof = True
            return False
        self.buf = self.buf[self.pos:] + more   # drop the consumed prefix -> bounded memory
        self.pos = 0
        return True

    def peek_nonspace(self, skip: str) -> str | None:
        while True:
            while self.pos < len(self.buf) and self.buf[self.pos] in skip:
                self.pos += 1
            if self.pos < len(self.buf):
                return self.buf[self.pos]
            if not self._refill():
                return None

    def decode(self, dec: json.JSONDecoder):
        while True:
            try:
                val, end = dec.raw_decode(self.buf, self.pos)
                self.pos = end
                return val
            except json.JSONDecodeError:
                if not self._refill():   # truncated value -> pull more; genuine error surfaces at EOF
                    raise


def iter_ledger_entries(path, chunk_size: int = 4 * 1024 * 1024):
    """Yield (ngram, entry) for every top-level key in a `{...}` JSON object file, constant-memory."""
    dec = json.JSONDecoder()
    with open(path, "r", encoding="utf-8") as fh:
        s = _Refillable(fh, chunk_size)
        if s.peek_nonspace(" \t\r\n") != "{":
            return
        s.pos += 1                                   # consume '{'
        if s.peek_nonspace(" \t\r\n") == "}":
            return                                    # empty object
        while True:
            if s.peek_nonspace(" \t\r\n,") == "}":
                return
            key = s.decode(dec)                        # the ngram (a JSON string)
            if s.peek_nonspace(" \t\r\n:") is None:    # skip whitespace + ':' -> pos at the value start
                return
            val = s.decode(dec)                        # the entry object
            yield key, val


# --- compact per-phrase summary (entry -> the few fields every S1 hypothesis needs) --------------
def phrase_summary(ngram: str, entry: dict) -> dict | None:
    """Reduce a ledger entry to {ng, first_date, peak, peak_day, peak_party, last_date, n_days}.
    peak = max same-day member count in EITHER party (the coordination magnitude)."""
    daily = entry.get("daily") or {}
    if not daily:
        return None
    peak, peak_day, peak_party = 0, None, None
    for day, d in daily.items():
        for p in ("D", "R"):
            c = d.get(p, 0)
            if c > peak:
                peak, peak_day, peak_party = c, day, p
    days = sorted(daily.keys())
    fs = (entry.get("first_seen") or {}).get("date")
    return {"ng": ngram, "first_date": fs or days[0], "peak": peak, "peak_day": peak_day,
            "peak_party": peak_party, "last_date": days[-1], "n_days": len(days)}


def build_phrase_index(congresses=range(113, 120), peak_floor: int = 2, progress=True) -> dict:
    """Stream the populated per-Congress shards into data/derived/search/phrase_index.jsonl — one line
    per (phrase, congress) with peak>=floor. Memoized: reused by every S1 hypothesis. Returns stats."""
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    out = SEARCH_CACHE / "phrase_index.jsonl"
    stats = {"congresses": {}, "rows": 0, "peak_floor": peak_floor}
    with open(out, "w", encoding="utf-8") as w:
        for n in congresses:
            shard = ALEX / f"ledger-{n}.json"
            if not shard.exists() or shard.stat().st_size <= 2:
                stats["congresses"][n] = {"rows": 0, "note": "empty/absent shard"}
                continue
            rows = total = 0
            for ng, entry in iter_ledger_entries(shard):
                total += 1
                s = phrase_summary(ng, entry)
                if s and s["peak"] >= peak_floor:
                    s["congress"] = n
                    w.write(json.dumps(s, separators=(",", ":")) + "\n")
                    rows += 1
            stats["congresses"][n] = {"rows": rows, "total_entries": total}
            stats["rows"] += rows
            if progress:
                print(f"  ledger-{n}: {total} entries -> {rows} rows (peak>={peak_floor})", flush=True)
    util.write_json(SEARCH_CACHE / "phrase_index.stats.json", stats)
    return stats


def build_member_index(congresses=range(113, 120), peak_floor=15, progress=True) -> dict:
    """For phrases with peak>=floor, the UNION of members who used it (across all days, joint units
    excluded) + the first-sayer bioguide -> data/derived/search/member_index.jsonl. The substrate for
    S1.11 (delegation echo) and S1.12 (leadership ignites). Re-streams the shards (targeted: high-peak
    only)."""
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    out = SEARCH_CACHE / "member_index.jsonl"
    n = 0
    with open(out, "w", encoding="utf-8") as w:
        for c in congresses:
            shard = ALEX / f"ledger-{c}.json"
            if not shard.exists() or shard.stat().st_size <= 2:
                continue
            for ng, entry in iter_ledger_entries(shard):
                s = phrase_summary(ng, entry)
                if not s or s["peak"] < peak_floor:
                    continue
                members = set()
                for d in (entry.get("daily") or {}).values():
                    for party in ("D", "R"):
                        for u in (d.get(f"members_{party}") or []):
                            if not str(u).startswith(("joint:", "njoint:")):
                                members.add(u)
                w.write(json.dumps({"ng": ng, "congress": c, "peak": s["peak"],
                                    "peak_party": s["peak_party"], "first_bio": (entry.get("first_seen") or {}).get("bioguide"),
                                    "members": sorted(members)}, separators=(",", ":")) + "\n")
                n += 1
            if progress:
                print(f"  member-index ledger-{c}: {n} cumulative phrases (peak>={peak_floor})", flush=True)
    util.write_json(SEARCH_CACHE / "member_index.stats.json", {"phrases": n, "peak_floor": peak_floor})
    return {"phrases": n}


def build_daily_series(progress=True) -> dict:
    """Merged CROSS-ERA daily series for every phrase in the member index (global peak>=15): stream all
    shards, accumulate {date: max(D,R)} per ngram (Congresses have disjoint date ranges, so the merge is
    a clean concatenation). -> data/derived/search/daily_series.jsonl. Fixes the per-Congress boundary
    artifact (A2): first_seen and the full adoption curve are now GLOBAL, enabling event-based ignition
    detection (S1.1'/S1.3'). Filtered by the member-index ngram set so it stays bounded."""
    keep = {r["ng"] for r in iter_member_index()}
    if not keep:
        raise RuntimeError("member index empty — build it first")
    merged: dict = {}
    for c in range(113, 120):
        shard = ALEX / f"ledger-{c}.json"
        if not shard.exists() or shard.stat().st_size <= 2:
            continue
        for ng, entry in iter_ledger_entries(shard):
            if ng not in keep:
                continue
            d = merged.setdefault(ng, {})
            for day, rec in (entry.get("daily") or {}).items():
                d[day] = max(rec.get("D", 0), rec.get("R", 0))
        if progress:
            print(f"  daily-series ledger-{c}: {len(merged)} phrases so far", flush=True)
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    out = SEARCH_CACHE / "daily_series.jsonl"
    with open(out, "w", encoding="utf-8") as w:
        for ng, days in merged.items():
            series = sorted([d, c] for d, c in days.items())
            w.write(json.dumps({"ng": ng, "series": series}, separators=(",", ":")) + "\n")
    util.write_json(SEARCH_CACHE / "daily_series.stats.json", {"phrases": len(merged)})
    return {"phrases": len(merged)}


def build_cross_party_daily(threshold=3, progress=True) -> dict:
    """Per-day count of CROSS-PARTY unison phrases: phrases said by >=threshold members of BOTH parties
    that day (a shared-reality signal). Stream all shards -> data/derived/search/cross_party_daily.json
    ({date: count}). The substrate for S1.8 (SOTU gravity well) — no hardcoded SOTU dates needed; the
    annual peak IS the SOTU day."""
    unison: dict = defaultdict(int)
    for c in range(113, 120):
        shard = ALEX / f"ledger-{c}.json"
        if not shard.exists() or shard.stat().st_size <= 2:
            continue
        for _ng, entry in iter_ledger_entries(shard):
            for day, rec in (entry.get("daily") or {}).items():
                if rec.get("D", 0) >= threshold and rec.get("R", 0) >= threshold:
                    unison[day] += 1
        if progress:
            print(f"  cross-party ledger-{c}: {len(unison)} unison-days so far", flush=True)
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    util.write_json(SEARCH_CACHE / "cross_party_daily.json", {"threshold": threshold, "by_day": dict(sorted(unison.items()))})
    return {"unison_days": len(unison), "threshold": threshold}


def iter_daily_series():
    p = SEARCH_CACHE / "daily_series.jsonl"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def bioguide_states() -> dict:
    """{bioguide: modal state} from the statement-metadata intermediate (roster join for delegation)."""
    from collections import Counter
    counts: dict = defaultdict(Counter)
    for r in iter_stmt_meta():
        if r.get("bioguide") and r.get("state"):
            counts[r["bioguide"]][r["state"]] += 1
    return {b: c.most_common(1)[0][0] for b, c in counts.items()}


def iter_member_index():
    p = SEARCH_CACHE / "member_index.jsonl"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def iter_phrase_index():
    p = SEARCH_CACHE / "phrase_index.jsonl"
    if not p.exists():
        return
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


# --- coverage denominators (from the complete discipline shards, all eras) -----------------------
def load_daily_statements(congresses=range(107, 120)) -> dict:
    """{party: {date: statements}} merged across the discipline shards — the per-day denominators and
    the density-control source. Complete for all eras (unlike the ledger shards)."""
    out: dict[str, dict] = {"D": {}, "R": {}, "I": {}}
    for n in congresses:
        d = util.read_json(ALEX / f"discipline-{n}.json", {}) or {}
        for party, days in d.items():
            for day, rec in days.items():
                out.setdefault(party, {})[day] = rec.get("statements", 0)
    return out


def load_discipline_index(congresses=range(113, 120)) -> dict:
    """{party: {date: {"s": statements, "m": on_message_units}}} merged across discipline shards — the
    daily message-discipline source for S1.6/S1.7 (weighted index = sum m / sum s over any window)."""
    out: dict = {"D": {}, "R": {}}
    for n in congresses:
        d = util.read_json(ALEX / f"discipline-{n}.json", {}) or {}
        for party, days in d.items():
            if party not in out:
                continue
            for day, rec in days.items():
                out[party][day] = {"s": rec.get("statements", 0), "m": rec.get("on_message_units", 0)}
    return out


def yearly_statements(congresses=range(107, 120)) -> dict:
    """{year: {party: statements}} from the coverage shards (per-year denominators)."""
    out: dict = {}
    for n in congresses:
        cov = util.read_json(ALEX / f"coverage-{n}.json", {}) or {}
        for year, parties in cov.items():
            for p, c in parties.items():
                out.setdefault(year, {}).setdefault(p, 0)
                out[year][p] += c
    return out


# --- full-text statement stream (for S2; congress-press ground truth, all eras) ------------------
def build_statement_meta(congresses=range(113, 120), progress=True) -> dict:
    """Text-free per-statement metadata over congress-press -> data/derived/search/stmt_meta.jsonl
    ({date, year, congress, party, bioguide, weekday}). Fast (no text); the substrate for the meta
    hypotheses (weekday baselines, active-member denominators, delegation). Returns summary stats."""
    from datetime import date as _date
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    out = SEARCH_CACHE / "stmt_meta.jsonl"
    n = 0
    active = defaultdict(set)          # year -> {bioguide}
    weekday = defaultdict(int)         # weekday -> count (all statements, the baseline)
    with open(out, "w", encoding="utf-8") as w:
        for r in iter_statements(congresses=congresses, with_text=False):
            try:
                wd = _date.fromisoformat(r["date"]).weekday()
            except Exception:
                continue
            r["weekday"] = wd
            w.write(json.dumps(r, separators=(",", ":")) + "\n")
            n += 1
            if r.get("bioguide"):
                active[r["year"]].add(r["bioguide"])
            weekday[wd] += 1
    summary = {"statements": n, "active_members_by_year": {y: len(s) for y, s in sorted(active.items())},
               "weekday_baseline": {str(k): v for k, v in sorted(weekday.items())}}
    util.write_json(SEARCH_CACHE / "stmt_meta.summary.json", summary)
    if progress:
        print("stmt_meta:", n, "statements;", summary["active_members_by_year"], flush=True)
    return summary


def iter_stmt_meta():
    p = SEARCH_CACHE / "stmt_meta.jsonl"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


_ADJ_INFLATION = ("unprecedented", "historic", "radical", "extreme", "crisis", "existential", "catastrophic")
_CONCERN = ("concerned", "deeply concerned", "gravely concerned", "alarmed", "troubled")
_APOLOGY = ("i apologize", "i regret", "i misspoke", "i was wrong", "i am sorry", "i'm sorry")
_I_SING = frozenset("i me my mine myself".split())
_WE_PLUR = frozenset("we us our ours ourselves".split())
_PRES_TOKENS = {"obama": "obama", "trump": "trump", "biden": "biden"}
_PRES_EUPHEMISM = ("the administration", "the white house", "this president", "the president's")


def build_text_features(congresses=range(113, 120), progress=True) -> dict:
    """One pass over congress-press text -> data/derived/search/text_features.jsonl, one row/statement
    with the counts the text-only S2 hypotheses need (punctuation, pronouns, adjective/concern/apology
    lexicons, 'american people', president-name vs euphemism tokens, emoji/all-caps flags, word/sentence
    counts). Compute once, aggregate many times. Deterministic, stdlib-only."""
    import re
    word_re = re.compile(r"[a-z']+")
    emoji_re = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF]")
    allcaps_re = re.compile(r"\b[A-Z]{4,}\b")
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    out = SEARCH_CACHE / "text_features.jsonl"
    n = 0
    with open(out, "w", encoding="utf-8") as w:
        for r in iter_statements(congresses=congresses, with_text=True):
            if r.get("party") not in ("D", "R", "I") or not r.get("bioguide"):
                continue
            raw = r.get("text") or ""
            low = raw.lower()
            words = word_re.findall(low)
            nw = len(words)
            if nw < 20:
                continue
            wc = defaultdict(int)
            for tok in words:
                wc[tok] += 1
            feats = {
                "y": r["year"], "p": r["party"], "b": r["bioguide"], "d": r["date"], "c": r["congress"],
                "nw": nw, "ns": low.count(".") + low.count("!") + low.count("?") or 1,
                "excl": raw.count("!"), "semic": raw.count(";"), "quest": raw.count("?"),
                "isg": sum(wc[t] for t in _I_SING), "wpl": sum(wc[t] for t in _WE_PLUR),
                "adj": {t: (low.count(t) if " " in t else wc[t]) for t in _ADJ_INFLATION},
                "concern": {t: low.count(t) for t in _CONCERN},
                "apol": sum(low.count(t) for t in _APOLOGY),
                "ampeople": low.count("the american people"),
                "pres": {k: wc[v] for k, v in _PRES_TOKENS.items()},
                "euph": sum(low.count(t) for t in _PRES_EUPHEMISM),
                "emoji": 1 if emoji_re.search(raw) else 0,
                "caps": 1 if allcaps_re.search(raw) else 0,
            }
            w.write(json.dumps(feats, separators=(",", ":")) + "\n")
            n += 1
            if progress and n % 100000 == 0:
                print(f"  text-features: {n} statements", flush=True)
    util.write_json(SEARCH_CACHE / "text_features.stats.json", {"statements": n})
    if progress:
        print("text-features DONE:", n, flush=True)
    return {"statements": n}


def iter_text_features():
    p = SEARCH_CACHE / "text_features.jsonl"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def iter_statements(congresses=None, with_text=True):
    """Stream raw/congress-press records as {date, year, party, bioguide, state, chamber, congress,
    text?}. Party normalized to D/R/I. `congresses` filters to a set; None = all."""
    def congress_of(date: str) -> int | None:
        try:
            y = int(date[:4]); m = int(date[5:7]); d = int(date[8:10])
        except Exception:
            return None
        # Congress N seats Jan 3 of 2001+2*(N-107)
        n = 107 + (y - 2001) // 2
        if (y - 2001) % 2 == 0 and (m, d) < (1, 3):
            n -= 1
        return n
    want = set(congresses) if congresses is not None else None
    for f in sorted(fetch.MIRROR.glob("*.jsonl")):
        for r in util.iter_jsonl(f):
            date = (r.get("date") or "")[:10]
            if len(date) != 10:
                continue
            c = congress_of(date)
            if want is not None and c not in want:
                continue
            m = r.get("member") or {}
            rec = {"date": date, "year": date[:4], "congress": c,
                   "party": _PARTY.get(m.get("party")), "bioguide": m.get("bioguide_id"),
                   "state": m.get("state"), "chamber": m.get("chamber")}
            if with_text:
                rec["text"] = r.get("text") or ""
            yield rec
