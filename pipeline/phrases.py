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

from . import boilerplate, config, util


def _doc_ngrams(text: str):
    """Set of (ngram, n) for a document, deduped within the doc, n in [MIN, MAX],
    with boilerplate-regex n-grams already excluded."""
    grams: set[tuple[str, int]] = set()
    for toks in boilerplate.sentences(text):
        L = len(toks)
        for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
            for i in range(0, L - n + 1):
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
        self.ngram_n: dict[str, int] = {}
        self.df: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.docs_in_stratum: dict[tuple[int, str], int] = defaultdict(int)
        self.party_day_docs: dict[tuple[str, str], int] = defaultdict(int)
        self.first: dict[str, tuple] = {}
        self.first_ties: dict[str, list[str]] = defaultdict(list)
        self._doc_sync_hits: list[tuple[str, str]] = []  # (party, day) for docs with >=1 sync phrase
        self.last_finalize_stats: dict = {}
        self._ledger_ngrams: set[str] = set()

    def _eligible(self, stmt: dict):
        party = (stmt.get("member") or {}).get("party")
        if stmt.get("syndicated") or party not in config.ALL_PARTIES:
            return None
        return party

    def build(self, statements: list[dict]) -> dict:
        # ---- Pass 1: day-scoped candidate discovery ----
        by_day: dict[str, list[dict]] = defaultdict(list)
        for s in statements:
            if self._eligible(s):
                by_day[s["published_at"]].append(s)

        for day, group in by_day.items():
            day_counts: dict[str, dict[str, set]] = {}
            for s in group:
                party = s["member"]["party"]
                unit = _unit_key(s)
                for ngram, _n in _doc_ngrams(s.get("text", "")):
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
        for s in statements:
            party = self._eligible(s)
            if not party:
                continue
            day = s["published_at"]
            congress = s.get("congress") or util.congress_for_date(day)
            bio = (s.get("member") or {}).get("bioguide")
            unit = _unit_key(s)
            stratum = (congress, party)
            self.docs_in_stratum[stratum] += 1
            self.party_day_docs[(party, day)] += 1
            had_sync = False
            for ngram, n in _doc_ngrams(s.get("text", "")):
                if ngram not in self.sync_ngrams:
                    continue
                had_sync = True
                self.ngram_n[ngram] = n
                self.df[stratum][ngram] += 1  # once per doc (_doc_ngrams is a set)
                self.occ.setdefault(ngram, {}).setdefault(day, {}).setdefault(party, set()).add(unit)
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
