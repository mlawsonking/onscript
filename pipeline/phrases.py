"""A4 — the phrase engine and first-appearance ledger (the compounding moat, §3/§4 A4).

Deterministic, $0 LLM (per R10). Given normalized statements it produces:
  * a ledger of synchronized content n-grams: first-sayer, per-party per-day distinct-unit
    counts, df_weight, boilerplate flag
  * adoption-curve data (daily distinct-unit counts over time)
  * a per-party per-day discipline index

MEMORY MODEL (two-pass, bounded — the single-pass version OOM'd at Stage-1 volume, 76k
records -> tens of millions of rare n-grams held before compaction; see BUILDLOG 2026-07-10):
  * Pass 1 (day-scoped): for each day independently, count per-(party,ngram) distinct units;
    an n-gram that reaches SYNC_MIN_MEMBERS units on any (party,day) becomes a *candidate*.
    Only the small candidate SET survives the day; the day's dense counts are discarded.
  * Pass 2 (candidates only): re-scan statements, tracking full daily counts + document
    frequency + first-appearance ONLY for candidate n-grams. Peak memory is bounded by the
    number of synchronized phrases (tens/hundreds of thousands), not the raw vocabulary.

Independent-adoption counting keys on the *unit* = joint_group (if any) else bioguide, so a
40-member joint release counts once, not forty (§11 trap 2). Syndicated reprints and
statements with no D/R/I party are excluded. Boilerplate is suppressed by structural strip +
n-gram regex (boilerplate.py) plus a per-(congress,party) document-frequency SHARE cap here.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import accumulate

from . import boilerplate, config, privacy, util


def _sentence_token_spans(text: str) -> list[list[tuple[str, int, int]]]:
    """Tokenized sentences with offsets into the unmodified source string."""
    chars = list(text or "")
    for pattern in boilerplate._STRIP_PATTERNS:
        current = "".join(chars)
        for match in pattern.finditer(current):
            chars[match.start():match.end()] = [" "] * (match.end() - match.start())
    cleaned = "".join(chars)
    boundaries = []
    start = 0
    for match in boilerplate._SENTENCE_SPLIT.finditer(cleaned):
        boundaries.append((start, match.start()))
        start = match.end()
    boundaries.append((start, len(cleaned)))

    sentences = []
    for start, end in boundaries:
        segment = cleaned[start:end]
        dateline = boilerplate._DATELINE.match(segment)
        token_start = start + (dateline.end() if dateline else 0)
        tokens = [
            (match.group(0).lower(), token_start + match.start(), token_start + match.end())
            for match in boilerplate._TOKEN.finditer(cleaned[token_start:end].lower())
        ]
        if tokens:
            sentences.append(tokens)
    return sentences


def _held_prefix(text: str, held: list[tuple[int, int]]) -> list[int]:
    """Running count of HELD character positions, so an occurrence test costs one comparison.

    `intervals_overlap(occurrence, span)` is true exactly when the two half-open ranges share at
    least one integer position, so "does this occurrence touch any held span" is "are there more
    held positions before its end than before its start". That identity is what makes this a
    reformulation rather than an approximation: the answer is the same for every occurrence.

    WHY IT WAS WORTH REFORMULATING. The straightforward version asked the question once per
    occurrence per held span. Real press releases carry a mean of 28 held spans (max 345 measured
    over 2026-06), and the engine walks every document twice, so a 600-token release ran on the
    order of 270k interval comparisons where one prefix walk of its 3.5k characters answers all of
    them. Measured over 2026-06 (4,724 lane-1 units) the n-gram loop went from 101.3s to 56.1s,
    which is BELOW the 64.8s it cost before the check existed at all: skipping a held occurrence
    now happens before the string join and the two boilerplate probes, not after.

    An all-zero prefix (no held spans) answers False for every occurrence, so there is no
    special case and no branch in the hot loop."""
    marks = bytearray(len(text))
    limit = len(text)
    for start, end in held:
        start = 0 if start < 0 else start
        end = limit if end > limit else end
        if end > start:
            marks[start:end] = b"\x01" * (end - start)
    prefix = [0]
    prefix.extend(accumulate(marks))
    return prefix


def _doc_ngrams(text: str, statement: dict | None = None, roster_map: dict | None = None):
    """Set of (ngram, n) for a document, deduped within the doc, n in [MIN, MAX],
    with boilerplate-regex n-grams and person-span intersections already excluded."""
    grams: set[tuple[str, int]] = set()
    person_rows = privacy.person_spans(text, statement=statement, roster_map=roster_map)
    held = [
        (row["start_char"], row["end_char"])
        for row in person_rows if row["classification"] in {"private", "quarantine"}
    ]
    held_before = _held_prefix(text, held)
    for token_rows in _sentence_token_spans(text):
        toks = [row[0] for row in token_rows]
        # Held counts at this sentence's token boundaries, so the inner loop indexes two small
        # lists instead of walking tuples inside the corpus's hottest comparison.
        at_start = [held_before[row[1]] for row in token_rows]
        at_end = [held_before[row[2]] for row in token_rows]
        L = len(toks)
        for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
            for i in range(0, L - n + 1):
                if at_end[i + n - 1] > at_start[i]:
                    continue          # the occurrence touches a held span
                ng = " ".join(toks[i : i + n])
                if not boilerplate.is_boilerplate_ngram(ng) and not boilerplate.is_low_content(ng):
                    grams.add((ng, n))
    return grams


def _unit_key(stmt: dict) -> str:
    m = stmt.get("member") or {}
    return stmt.get("joint_group") or m.get("bioguide") or stmt["id"]


class PhraseEngine:
    def __init__(self) -> None:
        self.sync_ngrams: set[str] = set()
        self.occ: dict[str, dict[str, dict[str, set]]] = {}
        self.family_occ: dict[str, dict[str, dict[str, set]]] = {}
        self.ngram_n: dict[str, int] = {}
        self.df: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.docs_in_stratum: dict[tuple[int, str], int] = defaultdict(int)
        self.party_day_docs: dict[tuple[str, str], int] = defaultdict(int)
        self.first: dict[str, tuple] = {}
        self.first_ties: dict[str, list[str]] = defaultdict(list)
        self._doc_sync_hits: list[tuple[str, str]] = []  # (party, day) for docs with >=1 sync phrase
        self.last_finalize_stats: dict = {}
        self._ledger_ngrams: set[str] = set()
        self.corpus_start: str | None = None

    def _eligible(self, stmt: dict):
        # Two-lane enforcement (§5.1): only Lane 1 (press releases) feeds any cross-party
        # number. Lane 2 (Bluesky/floor) is enrichment/citations only and is machine-blocked
        # from the ledger, adoption curves, and the discipline index here.
        if stmt.get("lane") != 1:
            return None
        party = (stmt.get("member") or {}).get("party")
        if stmt.get("syndicated") or party not in config.ALL_PARTIES:
            return None
        return party

    def build(self, statements: list[dict], *, progress: bool = False) -> dict:
        import sys as _sys
        # ---- Pass 1: day-scoped candidate discovery ----
        by_day: dict[str, list[dict]] = defaultdict(list)
        for s in statements:
            if self._eligible(s):
                by_day[s["published_at"]].append(s)
        if progress:
            print(f"[engine] pass 1 over {len(by_day):,} days ({len(statements):,} statements)…",
                  file=_sys.stderr, flush=True)

        for _di, (day, group) in enumerate(by_day.items()):
            if progress and _di and _di % 500 == 0:
                print(f"[engine] pass 1: {_di:,}/{len(by_day):,} days, {len(self.sync_ngrams):,} candidates",
                      file=_sys.stderr, flush=True)
            day_counts: dict[str, dict[str, set]] = {}
            for s in group:
                party = s["member"]["party"]
                unit = _unit_key(s)
                for ngram, _n in _doc_ngrams(s.get("text", ""), s):
                    d = day_counts.get(ngram)
                    if d is None:
                        d = day_counts[ngram] = {}
                    d.setdefault(party, set()).add(unit)
            for ngram, parties in day_counts.items():
                if ngram in self.sync_ngrams:
                    continue
                if any(len(units) >= config.SYNC_MIN_MEMBERS for units in parties.values()):
                    self.sync_ngrams.add(ngram)
            del day_counts  # release the day's dense structure

        # ---- Pass 2: track candidates only ----
        if progress:
            print(f"[engine] pass 2: {len(self.sync_ngrams):,} candidate phrases to track", file=_sys.stderr, flush=True)
        for _si, s in enumerate(statements):
            if progress and _si and _si % 100_000 == 0:
                print(f"[engine] pass 2: {_si:,}/{len(statements):,} statements", file=_sys.stderr, flush=True)
            party = self._eligible(s)
            if not party:
                continue
            day = s["published_at"]
            if self.corpus_start is None or day < self.corpus_start:
                self.corpus_start = day
            congress = s.get("congress") or util.congress_for_date(day)
            bio = (s.get("member") or {}).get("bioguide")
            unit = _unit_key(s)
            stratum = (congress, party)
            self.docs_in_stratum[stratum] += 1
            self.party_day_docs[(party, day)] += 1
            had_sync = False
            for ngram, n in _doc_ngrams(s.get("text", ""), s):
                if ngram not in self.sync_ngrams:
                    continue
                had_sync = True
                self.ngram_n[ngram] = n
                self.df[stratum][ngram] += 1  # once per doc (_doc_ngrams is a set)
                self.occ.setdefault(ngram, {}).setdefault(day, {}).setdefault(party, set()).add(unit)
                family = ((s.get("document_family") or {}).get("family_id")
                          or s.get("joint_group") or s.get("id"))
                if family:
                    self.family_occ.setdefault(ngram, {}).setdefault(day, {}).setdefault(
                        party, set()
                    ).add(family)
                prev = self.first.get(ngram)
                cand = (day, bio, s["id"], s.get("precision", "day"))
                if prev is None or day < prev[0]:
                    self.first[ngram] = cand
                    self.first_ties[ngram] = []
                elif day == prev[0] and bio and bio != prev[1]:
                    self.first_ties[ngram].append(bio)
            if had_sync:
                self._doc_sync_hits.append((party, day))

        return self._finalize()

    def _df_share(self, ngram: str) -> float:
        worst = 0.0
        for stratum, counts in self.df.items():
            c = counts.get(ngram)
            if c and self.docs_in_stratum[stratum]:
                worst = max(worst, c / self.docs_in_stratum[stratum])
        return worst

    def _finalize(self) -> dict:
        ledger: dict[str, dict] = {}
        df_boiler = 0
        for ngram, by_day in self.occ.items():
            share = self._df_share(ngram)
            if share > config.BOILERPLATE_DF_SHARE_MAX:
                df_boiler += 1
                continue  # ubiquitous template phrase
            peak = 0
            total = 0
            units_seen: set = set()
            daily: dict[str, dict] = {}
            for day, by_party in by_day.items():
                entry = {}
                for party, units in by_party.items():
                    entry[party] = len(units)
                    entry[f"members_{party}"] = sorted(u for u in units if not str(u).startswith(("joint:", "njoint:")))
                    families = self.family_occ.get(ngram, {}).get(day, {}).get(party, set())
                    entry[f"families_{party}"] = len(families)
                    entry[f"family_ids_{party}"] = sorted(families)
                    peak = max(peak, len(units))
                    total += len(units)
                    units_seen |= units
                daily[day] = entry
            if peak < config.SYNC_MIN_MEMBERS or total < config.LEDGER_MIN_TOTAL_USES or len(units_seen) < 2:
                continue  # compaction (§13)
            first = self.first.get(ngram)
            ledger[ngram] = {
                "ngram": ngram,
                "n": self.ngram_n.get(ngram, len(ngram.split())),
                "first_seen": {
                    "date": first[0] if first else None,
                    "bioguide": first[1] if first else None,
                    "statement": first[2] if first else None,
                    "tie": sorted(set(self.first_ties.get(ngram, []))),
                    "precision": first[3] if first else "day",
                    "lane": 1,
                    "corpus_start": self.corpus_start,
                },
                "daily": daily,
                "df_weight": round(1.0 - min(1.0, share), 3),
                "peak_units": peak,
                "boilerplate": False,
            }
        self._ledger_ngrams = set(ledger)
        self.last_finalize_stats = {
            "candidates": len(self.sync_ngrams),
            "df_boilerplate": df_boiler,
            "ledger_entries": len(ledger),
        }
        return ledger

    def discipline_index(self) -> dict[str, dict]:
        """Per (party, day): share of that party's statements containing >=1 kept synchronized
        phrase that day (A11 precursor). Uses only ledger phrases (post-boilerplate)."""
        kept = self._ledger_ngrams
        # _doc_sync_hits used any candidate; recompute hits against kept ledger set via occ.
        hit_units: dict[tuple[str, str], int] = defaultdict(int)
        # Count, per (party, day), distinct units that used >=1 kept phrase.
        seen: dict[tuple[str, str], set] = defaultdict(set)
        for ngram in kept:
            for day, by_party in self.occ[ngram].items():
                for party, units in by_party.items():
                    seen[(party, day)] |= units
        out: dict[str, dict] = defaultdict(dict)
        for (party, day), docs in self.party_day_docs.items():
            u = len(seen.get((party, day), ()))
            out[party][day] = {"statements": docs, "on_message_units": u,
                               "index": round(min(u, docs) / docs, 4) if docs else 0.0}
        return out
