"""Deterministic gold-set sampling, adjudication, and metrics."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import itertools

from . import eligibility


METHOD_VERSION = "gold-set-harness-v1"
SPLITS = ("train", "validation", "test")


def candidate_stratum(row: dict) -> tuple[str, str, str, str]:
    """Use party, predicted class, lane, and year as the sampling stratum."""
    return (
        str(row.get("party") or "unknown"),
        str(row.get("predicted_class") or "unknown"),
        str(row.get("lane") if row.get("lane") is not None else "unknown"),
        str(row.get("day") or "")[:4] or "unknown",
    )


def sample_candidates(candidates: list[dict], per_stratum: int) -> dict:
    """Select a stable hash-ranked sample within every candidate stratum."""
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    seen = set()
    for row in candidates:
        candidate_id = row.get("candidate_id")
        if not candidate_id or candidate_id in seen:
            raise ValueError("candidate IDs must be present and unique")
        seen.add(candidate_id)
        grouped[candidate_stratum(row)].append(dict(row))
    selected = []
    strata = []
    for stratum in sorted(grouped):
        rows = sorted(
            grouped[stratum],
            key=lambda row: (
                hashlib.sha256(f"{METHOD_VERSION}\n{row['candidate_id']}".encode("utf-8")).hexdigest(),
                row["candidate_id"],
            ),
        )
        chosen = rows[:per_stratum]
        selected.extend(chosen)
        strata.append({
            "party": stratum[0],
            "predicted_class": stratum[1],
            "lane": stratum[2],
            "year": stratum[3],
            "available": len(rows),
            "selected": len(chosen),
        })
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "per_stratum": per_stratum,
        "strata": strata,
        "candidates": selected,
    }


def date_split(day: str, train_end: str, validation_end: str) -> str:
    if not day or train_end >= validation_end:
        raise ValueError("valid day and ordered split boundaries are required")
    if day <= train_end:
        return "train"
    if day <= validation_end:
        return "validation"
    return "test"


def assign_splits(candidates: list[dict], train_end: str, validation_end: str) -> list[dict]:
    return [
        {**row, "split": date_split(row.get("day") or "", train_end, validation_end)}
        for row in candidates
    ]


def validate_annotations(rows: list[dict], expected_annotator: str | None = None) -> dict[str, dict]:
    """Validate one annotator's independent batch and index it by candidate ID."""
    indexed = {}
    for row in rows:
        candidate_id = row.get("candidate_id")
        annotator = row.get("annotator_id")
        if not candidate_id or candidate_id in indexed:
            raise ValueError("annotation candidate IDs must be present and unique")
        if expected_annotator is not None and annotator != expected_annotator:
            raise ValueError("annotation batch contains the wrong annotator")
        if row.get("gold_class") not in eligibility.SURFACE_CLASSES:
            raise ValueError(f"invalid gold class for {candidate_id}")
        if not row.get("gold_family_id"):
            raise ValueError(f"missing gold family for {candidate_id}")
        indexed[candidate_id] = dict(row)
    return indexed


def adjudicate(candidates: list[dict], annotations_a: list[dict], annotations_b: list[dict],
               decisions: list[dict] | None = None) -> dict:
    """Merge two independent batches. Disagreements require an explicit adjudicator decision."""
    left = validate_annotations(annotations_a)
    right = validate_annotations(annotations_b)
    resolved = {row.get("candidate_id"): row for row in (decisions or []) if row.get("candidate_id")}
    output = []
    unresolved = []
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        a, b = left.get(candidate_id), right.get(candidate_id)
        if not a or not b:
            unresolved.append({"candidate_id": candidate_id, "reason": "missing dual annotation"})
            continue
        same = (a.get("gold_class"), a.get("gold_family_id")) == (
            b.get("gold_class"), b.get("gold_family_id")
        )
        choice = a if same else resolved.get(candidate_id)
        if not choice:
            unresolved.append({"candidate_id": candidate_id, "reason": "annotation disagreement"})
            continue
        if choice.get("gold_class") not in eligibility.SURFACE_CLASSES or not choice.get("gold_family_id"):
            raise ValueError(f"invalid adjudication for {candidate_id}")
        output.append({
            **candidate,
            "gold_class": choice["gold_class"],
            "gold_family_id": choice["gold_family_id"],
            "annotation_status": "agreement" if same else "adjudicated",
            "annotator_ids": sorted({a.get("annotator_id"), b.get("annotator_id")}),
            "adjudicator_id": None if same else choice.get("adjudicator_id"),
        })
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "records": output,
        "unresolved": unresolved,
    }


def _division(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def class_metrics(records: list[dict]) -> dict:
    labels = list(eligibility.SURFACE_CLASSES)
    confusion = {gold: {predicted: 0 for predicted in labels} for gold in labels}
    for row in records:
        confusion[row["gold_class"]][row["predicted_class"]] += 1
    precision = {}
    for label in labels:
        true_positive = confusion[label][label]
        predicted = sum(confusion[gold][label] for gold in labels)
        precision[label] = {
            "true_positive": true_positive,
            "predicted": predicted,
            "precision": _division(true_positive, predicted),
        }
    return {"precision_by_class": precision, "confusion_matrix": confusion}


def family_pairwise_metrics(records: list[dict]) -> dict:
    """Score document-family decisions over pairs within the same day and party."""
    tp = fp = fn = 0
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in records:
        groups[(row.get("day") or "", row.get("party") or "")].append(row)
    for rows in groups.values():
        for left, right in itertools.combinations(rows, 2):
            predicted_same = left.get("predicted_family_id") == right.get("predicted_family_id")
            gold_same = left.get("gold_family_id") == right.get("gold_family_id")
            if predicted_same and gold_same:
                tp += 1
            elif predicted_same and not gold_same:
                fp += 1
            elif not predicted_same and gold_same:
                fn += 1
    return {
        "true_positive_pairs": tp,
        "false_positive_pairs": fp,
        "false_negative_pairs": fn,
        "precision": _division(tp, tp + fp),
        "recall": _division(tp, tp + fn),
    }


def party_error_gap(records: list[dict]) -> dict:
    rates = {}
    for party in ("D", "R"):
        rows = [row for row in records if row.get("party") == party]
        errors = sum(1 for row in rows if row.get("predicted_class") != row.get("gold_class"))
        rates[party] = {"errors": errors, "total": len(rows), "error_rate": _division(errors, len(rows))}
    values = [rates[party]["error_rate"] for party in ("D", "R")]
    gap = round(abs(values[0] - values[1]), 6) if all(value is not None for value in values) else None
    return {"by_party": rates, "absolute_error_rate_gap": gap}


def compute_metrics(records: list[dict]) -> dict:
    classes = class_metrics(records)
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "records": len(records),
        **classes,
        "family_pairwise": family_pairwise_metrics(records),
        "party_error_gap": party_error_gap(records),
    }


def run_synthetic(payload: dict) -> dict:
    split = payload.get("split_boundaries") or {}
    candidates = assign_splits(
        payload.get("candidates") or [], split["train_end"], split["validation_end"]
    )
    adjudicated = adjudicate(
        candidates, payload.get("annotations_a") or [], payload.get("annotations_b") or [],
        payload.get("decisions") or [],
    )
    if adjudicated["unresolved"]:
        raise ValueError("synthetic annotated sample has unresolved items")
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "adjudication": adjudicated,
        "metrics": compute_metrics(adjudicated["records"]),
    }
