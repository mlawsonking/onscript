"""A4 — the phrase engine and first-appearance ledger (the compounding moat, §3/§4 A4).

Deterministic, $0 LLM (per R10). Given normalized statements it produces:
  * a ledger of synchronized content n-grams: first-sayer, per-party per-day distinct-unit
    counts, df_weight, boilerplate flag
  * adoption-curve data (daily distinct-unit counts over time)
  * a per-party per-day discipline index

Independent-adoption counting keys on the *unit* = joint_group (if any) else bioguide, so a
40-member joint release counts once, not forty (§11 trap 2). Syndicated reprints and
statements with no D/R/I party are excluded from coordination counts.

Boilerplate is suppressed three ways: structural strip + n-gram regex (boilerplate.py) plus
a per-(congress,party) document-frequency percentile computed here (§11.9: DF is per-era so
2005's template soup does not poison 2025's coordination scores).
"""
from __future__ import annotations

from collections import defaultdict

from . import boilerplate, config, util


def _doc_ngrams(text: str):
    """Set of (ngram, n) for a document, deduped within the doc, n in [MIN, MAX]."""
    grams: set[tuple[str, int]] = set()
    for toks in boilerplate.sentences(text):
        L = len(toks)
        for n in range(config.NGRAM_MIN, config.NGRAM_MAX + 1):
            for i in range(0, L - n + 1):
                grams.add((" ".join(toks[i : i + n]), n))
    return grams


def _percentile_threshold(values: list[int], top_fraction: float) -> int:
    """Return the DF value at the top `top_fraction` cut; n-grams with df >= it are suppressed."""
    if not values:
        return 1 << 30
    s = sorted(values)
    idx = int(len(s) * (1.0 - top_fraction))
    idx = min(max(idx, 0), len(s) - 1)
    return s[idx]


class PhraseEngine:
    """Accumulate statements, then finalize a ledger. Re-runnable from raw (rebuild-safe)."""

    def __init__(self) -> None:
        # df[(congress, party)][ngram] = document frequency
        self.df: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.docs_in_stratum: dict[tuple[int, str], int] = defaultdict(int)
        # occ[ngram][day][party] = set(unit_key)
        self.occ: dict[str, dict[str, dict[str, set]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        self.ngram_n: dict[str, int] = {}
        # first[ngram] = (day, bioguide, statement_id, precision); ties tracked
        self.first: dict[str, tuple] = {}
        self.first_ties: dict[str, list[str]] = defaultdict(list)
        # statements-per (party, day) and which contained >=1 synchronized phrase
        self.party_day_docs: dict[tuple[str, str], int] = defaultdict(int)
        self._doc_sync_grams: list[tuple[str, str, set]] = []  # (party, day, ngrams) buffered for discipline

    def add(self, stmt: dict) -> None:
        party = (stmt.get("member") or {}).get("party")
        if stmt.get("syndicated") or party not in config.ALL_PARTIES:
            return
        day = stmt["published_at"]
        congress = stmt.get("congress") or util.congress_for_date(day)
        bio = (stmt.get("member") or {}).get("bioguide")
        unit = stmt.get("joint_group") or bio or stmt["id"]
        stratum = (congress, party)
        self.docs_in_stratum[stratum] += 1
        self.party_day_docs[(party, day)] += 1

        grams = _doc_ngrams(stmt.get("text", ""))
        doc_grams: set[str] = set()
        for ngram, n in grams:
            if boilerplate.is_boilerplate_ngram(ngram):
                continue
            self.df[stratum][ngram] += 1
            self.ngram_n[ngram] = n
            self.occ[ngram][day][party].add(unit)
            doc_grams.add(ngram)
            # first-appearance (day precision -> ties recorded, never a false hour-crown, §11.4)
            prev = self.first.get(ngram)
            cand = (day, bio, stmt["id"], stmt.get("precision", "day"))
            if prev is None or day < prev[0]:
                self.first[ngram] = cand
                self.first_ties[ngram] = []
            elif day == prev[0] and bio and bio != prev[1]:
                self.first_ties[ngram].append(bio)
        self._doc_sync_grams.append((party, day, doc_grams))

    # -- finalize -----------------------------------------------------------
    def _boilerplate_df_set(self) -> set[str]:
        """n-grams whose df is in the top percentile of their stratum (per-era, §11.9)."""
        flagged: set[str] = set()
        for stratum, counts in self.df.items():
            if self.docs_in_stratum[stratum] < config.BOILERPLATE_DF_MIN_DOCS:
                continue
            thr = _percentile_threshold(list(counts.values()), config.BOILERPLATE_DF_TOP_PERCENTILE)
            for ngram, c in counts.items():
                if c >= thr:
                    flagged.add(ngram)
        return flagged

    def _df_weight(self, ngram: str) -> float:
        """1 - (max stratum document-frequency share): higher = more distinctive/less ubiquitous."""
        worst = 0.0
        for stratum, counts in self.df.items():
            c = counts.get(ngram)
            if c and self.docs_in_stratum[stratum]:
                worst = max(worst, c / self.docs_in_stratum[stratum])
        return round(1.0 - min(1.0, worst), 3)

    def finalize(self) -> dict[str, dict]:
        """Build the ledger: keep non-boilerplate n-grams that reached SYNC_MIN_MEMBERS
        distinct units on some (party, day), pruned by compaction thresholds (§13)."""
        df_boiler = self._boilerplate_df_set()
        ledger: dict[str, dict] = {}
        for ngram, by_day in self.occ.items():
            if ngram in df_boiler:
                continue
            # peak distinct-unit count on any (party, day)
            peak = 0
            total = 0
            units_seen: set = set()
            daily: dict[str, dict] = {}
            for day, by_party in by_day.items():
                entry = {}
                for party, units in by_party.items():
                    entry[party] = len(units)
                    entry[f"members_{party}"] = sorted(u for u in units if not str(u).startswith("joint:"))
                    peak = max(peak, len(units))
                    total += len(units)
                    units_seen |= units
                daily[day] = entry
            if peak < config.SYNC_MIN_MEMBERS:
                continue  # not synchronized -> not in the ledger
            if total < config.LEDGER_MIN_TOTAL_USES or len(units_seen) < 2:
                continue  # compaction (§13): prune rare / single-unit
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
                "df_weight": self._df_weight(ngram),
                "peak_units": peak,
                "boilerplate": False,
            }
        self.last_finalize_stats = {
            "ngrams_tracked": len(self.occ),
            "df_boilerplate": len(df_boiler),
            "ledger_entries": len(ledger),
        }
        # discipline index needs the finalized synchronized-phrase set
        self._ledger_ngrams = set(ledger)
        return ledger

    def discipline_index(self) -> dict[str, dict]:
        """Per (party, day): share of that party's statements containing >=1 synchronized
        phrase that day. A simple v1 message-alignment metric (A11 precursor)."""
        sync = getattr(self, "_ledger_ngrams", set())
        hits: dict[tuple[str, str], int] = defaultdict(int)
        for party, day, grams in self._doc_sync_grams:
            if grams & sync:
                hits[(party, day)] += 1
        out: dict[str, dict] = defaultdict(dict)
        for (party, day), docs in self.party_day_docs.items():
            h = hits.get((party, day), 0)
            out[party][day] = {"statements": docs, "on_message": h,
                               "index": round(h / docs, 4) if docs else 0.0}
        return out
