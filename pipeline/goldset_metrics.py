"""Intake, agreement, and confidence-interval metrics for the gold set.

This layer sits on top of ``pipeline.goldset``. It reads returned answer sheets, validates
them against the annotation schema, computes per-task agreement (Cohen's kappa and
Krippendorff's nominal alpha), builds the adjudication queue for disagreements, and reports
the docs/33 metric set with numerator, denominator, and 95% Wilson confidence intervals.
All deterministic, no network, no API budget.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import io
import itertools
import math

from . import eligibility, goldset


METHOD_VERSION = "gold-set-metrics-v1"
BOOL_TASKS = ("phrase_complete", "proposition_consistent", "claim_supported")
_TRUE = {"true", "yes", "1", "y", "t"}
_FALSE = {"false", "no", "0", "n", "f"}
STANCE_VALUES = {"affirmative", "negated", "mixed"}

# Pilot agreement gates (docs/35). Metric targets are provisional until ratified.
PILOT_GATES = {
    "overall_agreement": 0.80,
    "message_vs_nonmessage_agreement": 0.90,
    "privacy_agreement": 0.99,
}


def _coerce_bool(value):
    text = (value or "").strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def read_answer_csv(text: str, annotator_id: str) -> list[dict]:
    """Parse one annotator's answer sheet into schema-shaped rows."""
    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        candidate_id = (raw.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        row = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "annotator_id": annotator_id,
            "gold_class": (raw.get("gold_class") or "").strip(),
            "gold_family_id": (raw.get("gold_family_id") or "").strip(),
        }
        for task in BOOL_TASKS:
            value = _coerce_bool(raw.get(task))
            if value is not None:
                row[task] = value
        stance = (raw.get("stance") or "").strip().lower()
        if stance:
            row["stance"] = stance
        notes = (raw.get("notes") or "").strip()
        if notes:
            row["notes"] = notes
        rows.append(row)
    return rows


def validate_rows(rows: list[dict]) -> list[str]:
    """Return a list of schema violations. Empty means the batch is valid."""
    errors: list[str] = []
    seen = set()
    for row in rows:
        cid = row.get("candidate_id")
        if not cid:
            errors.append("row missing candidate_id")
            continue
        if cid in seen:
            errors.append(f"{cid}: duplicate candidate_id")
        seen.add(cid)
        if not row.get("annotator_id"):
            errors.append(f"{cid}: missing annotator_id")
        if row.get("gold_class") not in eligibility.SURFACE_CLASSES:
            errors.append(f"{cid}: invalid gold_class {row.get('gold_class')!r}")
        if not row.get("gold_family_id"):
            errors.append(f"{cid}: missing gold_family_id")
        if "stance" in row and row["stance"] not in STANCE_VALUES:
            errors.append(f"{cid}: invalid stance {row['stance']!r}")
        for task in BOOL_TASKS:
            if task in row and not isinstance(row[task], bool):
                errors.append(f"{cid}: {task} must be boolean")
    return errors


# --- agreement ---------------------------------------------------------------

def cohens_kappa(pairs: list[tuple]) -> float | None:
    """Cohen's kappa for two raters over categorical (a, b) label pairs."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    labels = {label for pair in pairs for label in pair}
    count_a = Counter(a for a, _b in pairs)
    count_b = Counter(b for _a, b in pairs)
    expected = sum((count_a[label] / n) * (count_b[label] / n) for label in labels)
    if expected >= 1.0:
        return 1.0
    return round((observed - expected) / (1 - expected), 6)


def krippendorff_alpha(pairs: list[tuple]) -> float | None:
    """Krippendorff's nominal alpha for two coders with no missing values."""
    units = len(pairs)
    if units == 0:
        return None
    disagreements = sum(1 for a, b in pairs if a != b)
    observed = disagreements / units
    n = 2 * units
    marginals = Counter()
    for a, b in pairs:
        marginals[a] += 1
        marginals[b] += 1
    sum_squares = sum(value * value for value in marginals.values())
    if n <= 1:
        return None
    expected = (n * n - sum_squares) / (n * (n - 1))
    if expected <= 0:
        return 1.0
    return round(1 - observed / expected, 6)


def _paired(a_by_id: dict, b_by_id: dict, field: str) -> list[tuple]:
    pairs = []
    for cid in a_by_id.keys() & b_by_id.keys():
        av, bv = a_by_id[cid].get(field), b_by_id[cid].get(field)
        if av is not None and bv is not None and av != "" and bv != "":
            pairs.append((av, bv))
    return pairs


def _family_pairwise_pairs(a_by_id: dict, b_by_id: dict, candidates_by_id: dict) -> list[tuple]:
    """Same-family binary judgments for each co-located pair, per annotator."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for cid in a_by_id.keys() & b_by_id.keys():
        candidate = candidates_by_id.get(cid) or {}
        groups[(candidate.get("day"), candidate.get("party"))].append(cid)
    pairs = []
    for members in groups.values():
        for left, right in itertools.combinations(sorted(members), 2):
            a_same = a_by_id[left].get("gold_family_id") == a_by_id[right].get("gold_family_id")
            b_same = b_by_id[left].get("gold_family_id") == b_by_id[right].get("gold_family_id")
            pairs.append((a_same, b_same))
    return pairs


def agreement_report(annotations_a: list[dict], annotations_b: list[dict],
                     candidates: list[dict]) -> dict:
    """Per-task Cohen's kappa, Krippendorff alpha, observed agreement, and denominators."""
    a_by_id = {row["candidate_id"]: row for row in annotations_a}
    b_by_id = {row["candidate_id"]: row for row in annotations_b}
    candidates_by_id = {row["candidate_id"]: row for row in candidates}

    def _entry(pairs):
        observed = round(sum(1 for a, b in pairs if a == b) / len(pairs), 6) if pairs else None
        return {
            "items": len(pairs),
            "observed_agreement": observed,
            "cohens_kappa": cohens_kappa(pairs),
            "krippendorff_alpha": krippendorff_alpha(pairs),
        }

    tasks = {
        "surface_class": _entry(_paired(a_by_id, b_by_id, "gold_class")),
        "phrase_complete": _entry(_paired(a_by_id, b_by_id, "phrase_complete")),
        "proposition_consistent": _entry(_paired(a_by_id, b_by_id, "proposition_consistent")),
        "stance": _entry(_paired(a_by_id, b_by_id, "stance")),
        "document_family": _entry(_family_pairwise_pairs(a_by_id, b_by_id, candidates_by_id)),
        "claim_supported": _entry(_paired(a_by_id, b_by_id, "claim_supported")),
    }

    class_pairs = _paired(a_by_id, b_by_id, "gold_class")
    binary_message = [((a == "message"), (b == "message")) for a, b in class_pairs]
    privacy_pairs = [((a == "private"), (b == "private")) for a, b in class_pairs]
    gates = {
        "overall_agreement": tasks["surface_class"]["observed_agreement"],
        "message_vs_nonmessage_agreement": _entry(binary_message)["observed_agreement"],
        "privacy_agreement": _entry(privacy_pairs)["observed_agreement"],
    }
    gate_pass = {
        name: (gates[name] is not None and gates[name] >= threshold)
        for name, threshold in PILOT_GATES.items()
    }
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "dual_annotated_items": len(a_by_id.keys() & b_by_id.keys()),
        "tasks": tasks,
        "pilot_gates": {"values": gates, "thresholds": PILOT_GATES, "pass": gate_pass,
                        "all_pass": all(gate_pass.values())},
    }


def adjudication_queue(annotations_a: list[dict], annotations_b: list[dict],
                       candidates: list[dict]) -> list[dict]:
    """Every class or family disagreement, with the candidate ID and the two labels."""
    a_by_id = {row["candidate_id"]: row for row in annotations_a}
    b_by_id = {row["candidate_id"]: row for row in annotations_b}
    queue: list[dict] = []
    for candidate in candidates:
        cid = candidate["candidate_id"]
        a, b = a_by_id.get(cid), b_by_id.get(cid)
        if not a or not b:
            queue.append({"candidate_id": cid, "reason": "missing dual annotation"})
            continue
        class_disagree = a.get("gold_class") != b.get("gold_class")
        family_disagree = a.get("gold_family_id") != b.get("gold_family_id")
        if class_disagree or family_disagree:
            queue.append({
                "candidate_id": cid,
                "reason": "class" if class_disagree else "family",
                "a_gold_class": a.get("gold_class"), "b_gold_class": b.get("gold_class"),
                "a_gold_family_id": a.get("gold_family_id"),
                "b_gold_family_id": b.get("gold_family_id"),
            })
    return queue


# --- metrics with confidence intervals ---------------------------------------

def wilson_interval(successes: int, trials: int, z: float = 1.96) -> list[float] | None:
    """95% Wilson score interval for a binomial proportion."""
    if trials <= 0:
        return None
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))) / denom
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def _proportion(successes: int, trials: int) -> dict:
    return {
        "numerator": successes,
        "denominator": trials,
        "estimate": round(successes / trials, 6) if trials else None,
        "ci95": wilson_interval(successes, trials),
    }


def _newcombe_difference(k1: int, n1: int, k2: int, n2: int) -> list[float] | None:
    """95% CI for the difference of two proportions (Newcombe method 10)."""
    if n1 <= 0 or n2 <= 0:
        return None
    low1, high1 = wilson_interval(k1, n1)
    low2, high2 = wilson_interval(k2, n2)
    p1, p2 = k1 / n1, k2 / n2
    lower = (p1 - p2) - math.sqrt((p1 - low1) ** 2 + (high2 - p2) ** 2)
    upper = (p1 - p2) + math.sqrt((high1 - p1) ** 2 + (p2 - low2) ** 2)
    return [round(lower, 6), round(upper, 6)]


def metrics_with_intervals(records: list[dict]) -> dict:
    """The docs/33 metric set with numerator, denominator, and 95% intervals."""
    base = goldset.compute_metrics(records)
    labels = list(eligibility.SURFACE_CLASSES)
    confusion = base["confusion_matrix"]

    precision_by_class = {}
    for label in labels:
        true_positive = confusion[label][label]
        predicted = sum(confusion[gold][label] for gold in labels)
        precision_by_class[label] = _proportion(true_positive, predicted)

    pairwise = base["family_pairwise"]
    tp = pairwise["true_positive_pairs"]
    fp = pairwise["false_positive_pairs"]
    fn = pairwise["false_negative_pairs"]

    party = base["party_error_gap"]["by_party"]
    d_err, d_total = party["D"]["errors"], party["D"]["total"]
    r_err, r_total = party["R"]["errors"], party["R"]["total"]

    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "records": len(records),
        "message_precision": precision_by_class["message"],
        "precision_by_class": precision_by_class,
        "confusion_matrix": confusion,
        "family_pairwise": {
            "precision": _proportion(tp, tp + fp),
            "recall": _proportion(tp, tp + fn),
            "true_positive_pairs": tp,
            "false_positive_pairs": fp,
            "false_negative_pairs": fn,
        },
        "party_error_gap": {
            "D": _proportion(d_err, d_total),
            "R": _proportion(r_err, r_total),
            "absolute_gap": base["party_error_gap"]["absolute_error_rate_gap"],
            "gap_ci95": _newcombe_difference(d_err, d_total, r_err, r_total),
        },
    }


def merge_records(candidates: list[dict], annotations_a: list[dict], annotations_b: list[dict],
                  decisions: list[dict] | None = None) -> dict:
    """Merge two batches into adjudicated records ready for metrics."""
    return goldset.adjudicate(candidates, annotations_a, annotations_b, decisions or [])
