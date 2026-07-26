"""Deterministic phrase statistics and separate rankings."""
from __future__ import annotations

import math

from . import config


METHOD_VERSION = "phrase-statistics-v1"
TRAILING_DAYS = 28
SMOOTHING_ALPHA = 0.5
SMOOTHING_BETA = 0.5


def binomial_tail(successes: int, trials: int, probability: float) -> float:
    """Return P[X >= successes] for X drawn from Binomial(trials, probability)."""
    if successes <= 0:
        return 1.0
    if successes > trials:
        return 0.0
    probability = min(1.0, max(0.0, probability))
    if probability == 0.0:
        return 0.0
    if probability == 1.0:
        return 1.0
    logs = [
        math.lgamma(trials + 1) - math.lgamma(value + 1) - math.lgamma(trials - value + 1)
        + value * math.log(probability) + (trials - value) * math.log1p(-probability)
        for value in range(successes, trials + 1)
    ]
    largest = max(logs)
    return min(1.0, math.exp(largest) * sum(math.exp(value - largest) for value in logs))


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Adjust p-values with deterministic Benjamini-Hochberg false-discovery control."""
    count = len(p_values)
    adjusted = [1.0] * count
    ordered = sorted(enumerate(p_values), key=lambda item: (item[1], item[0]))
    running = 1.0
    for position in range(count - 1, -1, -1):
        index, value = ordered[position]
        rank = position + 1
        running = min(running, value * count / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def first_observed(entry: dict, *, default_lane: int = 1,
                   default_corpus_start: str | None = None) -> dict:
    """Normalize first-observed metadata and withhold a tied day-precision originator."""
    source = entry.get("first_seen") or {}
    precision = source.get("precision") or "day"
    primary = source.get("bioguide")
    ties = sorted({value for value in ([primary] + list(source.get("tie") or [])) if value})
    tied_at_day_precision = precision == "day" and len(ties) > 1
    return {
        "date": source.get("date"),
        "lane": source.get("lane", default_lane),
        "corpus_start": source.get("corpus_start") or default_corpus_start or config.ALEXANDRIA_EPOCH,
        "precision": precision,
        "ties": ties if tied_at_day_precision else list(source.get("tie") or []),
        "originator_bioguide": None if tied_at_day_precision else primary,
        "attribution_status": "tied observations" if tied_at_day_precision else "first observed office",
    }


def _denominator(denominators: dict, party: str, day: str | None) -> int:
    if not day:
        return 0
    return int((denominators.get(party) or {}).get(day) or 0)


def phrase_metrics(ledger: dict, denominators: dict, day: str,
                   trailing_days: int = TRAILING_DAYS) -> list[dict]:
    """Compute office, publication, family, surge, skew, and spread metrics for one day."""
    rows = []
    for phrase, entry in sorted(ledger.items()):
        daily = entry.get("daily") or {}
        current = daily.get(day) or {}
        prior_days = sorted(value for value in daily if value < day)[-trailing_days:]
        shares = {}
        for party in config.COMPOSITE_PARTIES:
            trials = _denominator(denominators, party, day)
            successes = int(current.get(party) or 0)
            shares[party] = successes / trials if trials else 0.0
        skew = abs(shares.get("D", 0.0) - shares.get("R", 0.0))
        for party in config.COMPOSITE_PARTIES:
            trials = _denominator(denominators, party, day)
            successes = int(current.get(party) or 0)
            if not trials or not successes:
                continue
            baseline_successes = sum(int((daily.get(value) or {}).get(party) or 0) for value in prior_days)
            baseline_trials = sum(_denominator(denominators, party, value) for value in prior_days)
            baseline_share = (
                (baseline_successes + SMOOTHING_ALPHA)
                / (baseline_trials + SMOOTHING_ALPHA + SMOOTHING_BETA)
            )
            previous_day = prior_days[-1] if prior_days else None
            previous_trials = _denominator(denominators, party, previous_day)
            previous_count = int((daily.get(previous_day) or {}).get(party) or 0) if previous_day else 0
            previous_share = previous_count / previous_trials if previous_trials else 0.0
            publications = int(current.get(f"publications_{party}") or successes)
            families = int(current.get(f"families_{party}") or successes)
            rows.append({
                "phrase": phrase,
                "party": party,
                "day": day,
                "office_count": successes,
                "eligible_offices": trials,
                "office_share": round(successes / trials, 8),
                "publication_count": publications,
                "family_count": families,
                "family_spread": round(families / publications, 8) if publications else 0.0,
                "baseline_share": round(baseline_share, 8),
                "surge_ratio": round((successes / trials) / baseline_share, 8),
                "p_value": binomial_tail(successes, trials, baseline_share),
                "party_skew": round(skew, 8),
                "spread_change": round(successes / trials - previous_share, 8),
                "first_observed": first_observed(entry),
            })
    adjusted = benjamini_hochberg([row["p_value"] for row in rows])
    for row, q_value in zip(rows, adjusted):
        row["q_value"] = q_value
    return rows


def rank_metrics(rows: list[dict], limit: int = 50) -> dict:
    """Return five independent rankings. No composite score is computed."""
    common = lambda row: (row["phrase"], row["party"])
    return {
        "method_version": METHOD_VERSION,
        "most_repeated": sorted(
            rows, key=lambda row: (-row["office_count"], -row["office_share"], common(row))
        )[:limit],
        "largest_surge": sorted(
            rows, key=lambda row: (row["q_value"], -row["surge_ratio"], -row["office_count"], common(row))
        )[:limit],
        "most_skewed": sorted(
            rows, key=lambda row: (-row["party_skew"], -row["office_count"], common(row))
        )[:limit],
        "fastest_spread": sorted(
            rows, key=lambda row: (-row["spread_change"], -row["office_count"], common(row))
        )[:limit],
        "widest_family_spread": sorted(
            rows, key=lambda row: (-row["family_count"], -row["family_spread"], common(row))
        )[:limit],
    }


def build_rankings(payload: dict) -> dict:
    """Build a stable export from a ledger fixture or production-shaped payload."""
    day = payload["day"]
    rows = phrase_metrics(payload.get("ledger") or {}, payload.get("denominators") or {}, day)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "day": day,
        "trailing_days": TRAILING_DAYS,
        "rankings": rank_metrics(rows),
    }
