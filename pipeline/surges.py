"""Deterministic phrase statistics and separate rankings."""
from __future__ import annotations

import math
from datetime import date as date_type

from . import config


# v3: the baseline is computed per party with no shared state, and the rankings split into
# qualified_surges and largest_statistical_deviations (R-36.7). Both the numbers on
# divergent-history days and the output shape change, so the method version moves.
METHOD_VERSION = "phrase-statistics-v3"
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


def baseline_days(denominators: dict, party: str, day: str, *, trailing_days: int,
                  mode: str = "calendar") -> list[str]:
    """Return the denominator-defined risk set, including phrase-zero days."""
    eligible = sorted(value for value, trials in (denominators.get(party) or {}).items()
                      if value < day and int(trials or 0) > 0)
    if mode == "calendar":
        return eligible[-trailing_days:]
    if mode == "weekday":
        weekday = date_type.fromisoformat(day).weekday()
        matching = [value for value in eligible
                    if date_type.fromisoformat(value).weekday() == weekday]
        return matching[-trailing_days:]
    raise ValueError("baseline mode must be calendar or weekday")


def phrase_metrics(ledger: dict, denominators: dict, day: str,
                   trailing_days: int = TRAILING_DAYS,
                   baseline_mode: str = "calendar") -> list[dict]:
    """Compute office, publication, family, surge, skew, and spread metrics for one day."""
    rows = []
    for phrase, entry in sorted(ledger.items()):
        daily = entry.get("daily") or {}
        current = daily.get(day) or {}
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
            # R-36.7: compute each party's baseline from its OWN denominator history, bound to this
            # party. A single prior_days left over from an earlier loop would give one party the
            # other's calendar on divergent histories (docs/37 rule 12).
            prior_days = baseline_days(
                denominators, party, day, trailing_days=trailing_days, mode=baseline_mode
            )
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
                "baseline_mode": baseline_mode,
                "baseline_calendar_days": len(prior_days),
                "baseline_observed_days": sum(
                    1 for value in prior_days if _denominator(denominators, party, value) > 0
                ),
                "baseline_phrase_occurrence_days": sum(
                    1 for value in prior_days if int((daily.get(value) or {}).get(party) or 0) > 0
                ),
                "baseline_successes": baseline_successes,
                "baseline_trials": baseline_trials,
                "baseline_share": round(baseline_share, 8),
                "surge_ratio": round((successes / trials) / baseline_share, 8),
                "absolute_change": round(successes / trials - baseline_share, 8),
                "p_value": binomial_tail(successes, trials, baseline_share),
                "party_skew": round(skew, 8),
                "spread_change": round(successes / trials - previous_share, 8),
                "first_observed": first_observed(entry),
            })
    adjusted = benjamini_hochberg([row["p_value"] for row in rows])
    for row, q_value in zip(rows, adjusted):
        row["q_value"] = q_value
        row["bh_family_definition"] = f"all party-phrase hypotheses offered for {day}"
        row["bh_family_size"] = len(rows)
        row["screening_statistic"] = "binomial tail screening statistic"
        row["practical_gates"] = {
            "minimum_absolute_change": config.SURGE_MIN_ABSOLUTE_CHANGE,
            "minimum_ratio": config.SURGE_MIN_RATIO,
            "maximum_q_value": config.SURGE_MAX_Q_VALUE,
            "status": "provisional_frozen",
        }
        row["passes_practical_gate"] = (
            row["absolute_change"] >= config.SURGE_MIN_ABSOLUTE_CHANGE
            and row["surge_ratio"] >= config.SURGE_MIN_RATIO
            and q_value <= config.SURGE_MAX_Q_VALUE
        )
    return rows


def legacy_occurrence_baseline(entry: dict, denominators: dict, party: str, day: str,
                               trailing_days: int = TRAILING_DAYS) -> dict:
    """Reproduce the superseded occurrence-only risk set for migration evidence."""
    daily = entry.get("daily") or {}
    days = sorted(value for value in daily if value < day)[-trailing_days:]
    successes = sum(int((daily.get(value) or {}).get(party) or 0) for value in days)
    trials = sum(_denominator(denominators, party, value) for value in days)
    return {"days": days, "successes": successes, "trials": trials}


def calibrate_overdispersion(payload: dict, *, baseline_mode: str = "calendar") -> dict:
    """Estimate Pearson dispersion over bounded phrase-party baseline panels."""
    day = payload["day"]
    denominators = payload.get("denominators") or {}
    estimates = []
    for phrase, entry in sorted((payload.get("ledger") or {}).items()):
        daily = entry.get("daily") or {}
        for party in config.COMPOSITE_PARTIES:
            days = baseline_days(denominators, party, day, trailing_days=TRAILING_DAYS,
                                 mode=baseline_mode)
            observations = [(int((daily.get(value) or {}).get(party) or 0),
                             _denominator(denominators, party, value)) for value in days]
            observations = [(successes, trials) for successes, trials in observations if trials > 0]
            total_trials = sum(trials for _, trials in observations)
            if len(observations) < 3 or not total_trials:
                continue
            probability = sum(successes for successes, _ in observations) / total_trials
            if probability <= 0.0 or probability >= 1.0:
                continue
            pearson = sum(
                (successes - trials * probability) ** 2
                / (trials * probability * (1.0 - probability))
                for successes, trials in observations
            )
            estimates.append({
                "phrase": phrase, "party": party,
                "dispersion_ratio": round(pearson / (len(observations) - 1), 8),
                "days": len(observations),
            })
    return {
        "schema_version": 1,
        "method_version": "surge-overdispersion-calibration-v1",
        "screening_method_version": METHOD_VERSION,
        "baseline_mode": baseline_mode,
        "target": "evaluate binomial screening variance before any model swap",
        "estimates": estimates,
    }


def rank_metrics(rows: list[dict], limit: int = 50) -> dict:
    """Return independent rankings. No composite score is computed.

    R-36.7: the statistical screening ranking is never called a surge. qualified_surges are
    the rows that passed the practical gate; largest_statistical_deviations is screening only.
    qualified_surges is a strict subset, so a gate-failing screening row never appears as a surge.
    """
    common = lambda row: (row["phrase"], row["party"])
    deviations = sorted(
        rows, key=lambda row: (row["q_value"], -row["surge_ratio"], -row["office_count"], common(row))
    )
    return {
        "method_version": METHOD_VERSION,
        "most_repeated": sorted(
            rows, key=lambda row: (-row["office_count"], -row["office_share"], common(row))
        )[:limit],
        "largest_statistical_deviations": deviations[:limit],
        "qualified_surges": [row for row in deviations if row["passes_practical_gate"]][:limit],
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
    baseline_mode = payload.get("baseline_mode") or "calendar"
    rows = phrase_metrics(payload.get("ledger") or {}, payload.get("denominators") or {}, day,
                          baseline_mode=baseline_mode)
    return {
        "schema_version": 2,
        "method_version": METHOD_VERSION,
        "day": day,
        "trailing_days": TRAILING_DAYS,
        "baseline_mode": baseline_mode,
        "rankings": rank_metrics(rows),
    }
