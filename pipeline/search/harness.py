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
