"""Single-human-rater intake, model triage, and provenance stamping (docs/35 section 10).

The ruled pilot mode has one human rater and one model reader. The model reader exists to
find the items worth a second look; it never writes a gold label and its agreement with the
human is never reported as inter-annotator agreement. Every artifact this module produces
carries ``PROVENANCE_LABEL`` verbatim, and ``assert_no_inter_annotator_claim`` refuses to let
a payload ship with a field name that would imply two independent human readings.

Deterministic, no network, no API budget. The model rater itself lives in
``pipeline.goldset_rater``; this module only consumes the answer sheet it produced.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import io
import itertools

from . import eligibility, goldset_metrics


METHOD_VERSION = "gold-set-single-rater-v1"
MODE = "single-human-rater"

# The label docs/35 section 10.3 makes mandatory on every metric this mode produces. The code
# owns the string; the document quotes it, and a test holds the two together.
PROVENANCE_LABEL = "author-annotated, single human rater, provisional"

MODEL_RATER_ROLE = "disagreement triage only; the model never writes a gold label"
GATE_B_STATUS = ("unclaimed: a single-human-rater author-annotated pilot does not release the "
                 "docs/33 R-33.11 validated-instrument gate; independent replication does")
INTERPRETATION = (
    "Agreement between one human rater and one model reader of the same guide. It measures "
    "how often a second reading of the same rules lands on the same label, which is a triage "
    "signal. It is not a reliability statistic and it is not agreement between two humans."
)
RELIABILITY_OMITTED = (
    "Cohen's kappa and Krippendorff's alpha are omitted on purpose. Both are inter-rater "
    "reliability statistics, and this mode has one rater; reporting them here would invite the "
    "reading docs/35 section 10.5 forbids."
)
GATES_NOT_EVALUATED = (
    "The docs/35 section 5 pilot gates measure two independent human annotators. This mode has "
    "one, so the gates are not evaluated and no pass may be reported."
)
REPLICATION_INVITATION = (
    "The sealed bundle, both answer sheets, the triage record, and these labels publish openly. "
    "Anyone may re-annotate the same bundle and publish their labels beside these."
)

# A field name containing any of these would assert a second human reading. Keys only: the
# prose fields above deliberately say the words in order to deny the claim.
FORBIDDEN_KEY_TOKENS = (
    "inter_annotator", "interannotator", "inter-annotator",
    "inter_rater", "interrater", "inter-rater",
    "annotator_agreement", "annotator_reliability",
)

TRIAGE_COLUMNS = ["candidate_id", "resolution", "gold_class", "gold_family_id", "notes"]
TRIAGE_RESOLUTIONS = ("keep", "revise")
AGREEMENT_FIELDS = (
    ("surface_class", "gold_class"),
    ("phrase_complete", "phrase_complete"),
    ("proposition_consistent", "proposition_consistent"),
    ("stance", "stance"),
    ("claim_supported", "claim_supported"),
)


def provenance(*, human_rater: str, model_rater: str | None = None,
               sample: str | None = None, extra: dict | None = None) -> dict:
    """The mandatory provenance block stamped onto every artifact of this mode."""
    block = {
        "mode": MODE,
        "label": PROVENANCE_LABEL,
        "method_version": METHOD_VERSION,
        "human_raters": 1,
        "human_rater_id": human_rater,
        "model_rater_id": model_rater,
        "model_rater_role": MODEL_RATER_ROLE,
        "adjudicator": None,
        "pilot_gates_evaluated": False,
        "pilot_gates_note": GATES_NOT_EVALUATED,
        "gate_b_claimed": False,
        "gate_b_status": GATE_B_STATUS,
        "independent_replication": "none",
        "replication_invitation": REPLICATION_INVITATION,
    }
    if sample:
        block["sample"] = sample
    if extra:
        block.update(extra)
    return block


def assert_no_inter_annotator_claim(payload) -> None:
    """Raise if any field name in ``payload`` would imply two independent human readings."""
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                for token in FORBIDDEN_KEY_TOKENS:
                    if token in lowered:
                        raise ValueError(
                            f"single-rater output may not carry the field {key!r}: this mode has "
                            "one human rater (docs/35 section 10.2)")
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)


def stamp(payload: dict, provenance_block: dict) -> dict:
    """Attach the provenance block and refuse to return a payload that overclaims."""
    stamped = {**payload, "provenance": provenance_block, "label": provenance_block["label"]}
    assert_no_inter_annotator_claim(stamped)
    return stamped


def _index(rows: list[dict]) -> dict:
    return {row["candidate_id"]: row for row in rows if row.get("candidate_id")}


def _observed(pairs: list[tuple]) -> dict:
    agreed = sum(1 for a, b in pairs if a == b)
    return {
        "items": len(pairs),
        "agreed": agreed,
        "disagreed": len(pairs) - agreed,
        "observed_agreement": round(agreed / len(pairs), 6) if pairs else None,
    }


def _family_pairwise(human: dict, model: dict, candidates_by_id: dict) -> list[tuple]:
    """Same-family binary judgments over co-located pairs, one judgment per reader."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for cid in human.keys() & model.keys():
        candidate = candidates_by_id.get(cid) or {}
        groups[(candidate.get("day"), candidate.get("party"))].append(cid)
    pairs = []
    for members in groups.values():
        for left, right in itertools.combinations(sorted(members), 2):
            human_same = human[left].get("gold_family_id") == human[right].get("gold_family_id")
            model_same = model[left].get("gold_family_id") == model[right].get("gold_family_id")
            pairs.append((human_same, model_same))
    return pairs


def human_versus_model_report(human_rows: list[dict], model_rows: list[dict],
                              candidates: list[dict], *, human_rater: str,
                              model_rater: str, sample: str | None = None) -> dict:
    """Observed agreement between the human rater and the model reader, labeled as such."""
    human, model = _index(human_rows), _index(model_rows)
    candidates_by_id = _index(candidates)
    both = human.keys() & model.keys()

    agreement = {}
    for name, field in AGREEMENT_FIELDS:
        pairs = []
        for cid in both:
            left, right = human[cid].get(field), model[cid].get(field)
            if left not in (None, "") and right not in (None, ""):
                pairs.append((left, right))
        agreement[name] = _observed(pairs)
    agreement["document_family_pairwise"] = _observed(
        _family_pairwise(human, model, candidates_by_id))

    queue = triage_queue(human_rows, model_rows, candidates)
    reasons = defaultdict(int)
    for row in queue:
        reasons[row["reason"]] += 1
    report = {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "sample_size": len(candidates),
        "items_rated_by_human": len(human),
        "items_rated_by_model": len(model),
        "items_rated_by_both": len(both),
        "human_versus_model_agreement": agreement,
        "interpretation": INTERPRETATION,
        "reliability_statistics_omitted": RELIABILITY_OMITTED,
        "pilot_gates": {"evaluated": False, "reason": GATES_NOT_EVALUATED},
        "triage": {"queued": len(queue), "by_reason": dict(sorted(reasons.items()))},
    }
    return stamp(report, provenance(human_rater=human_rater, model_rater=model_rater,
                                    sample=sample))


def triage_queue(human_rows: list[dict], model_rows: list[dict],
                 candidates: list[dict]) -> list[dict]:
    """Every item the human rater must look at again, with both readings side by side."""
    human, model = _index(human_rows), _index(model_rows)
    queue: list[dict] = []
    for candidate in candidates:
        cid = candidate.get("candidate_id")
        left, right = human.get(cid), model.get(cid)
        if not left:
            queue.append({"candidate_id": cid, "reason": "missing human label"})
            continue
        if not right:
            # The human label stands; there is simply no second reading to compare it with.
            queue.append({"candidate_id": cid, "reason": "no model reading",
                          "human_gold_class": left.get("gold_class"),
                          "human_gold_family_id": left.get("gold_family_id")})
            continue
        class_differs = left.get("gold_class") != right.get("gold_class")
        family_differs = left.get("gold_family_id") != right.get("gold_family_id")
        if class_differs or family_differs:
            queue.append({
                "candidate_id": cid,
                "reason": "class" if class_differs else "family",
                "human_gold_class": left.get("gold_class"),
                "model_gold_class": right.get("gold_class"),
                "human_gold_family_id": left.get("gold_family_id"),
                "model_gold_family_id": right.get("gold_family_id"),
            })
    return queue


def triage_required_ids(queue: list[dict]) -> set[str]:
    """Only real disagreements need a decision. A missing model reading needs nothing."""
    return {row["candidate_id"] for row in queue if row.get("reason") in ("class", "family")}


def read_triage_csv(text: str) -> list[dict]:
    """Parse the triage decisions sheet the human rater fills after seeing the queue."""
    rows: list[dict] = []
    for raw in csv.DictReader(io.StringIO(text)):
        cid = (raw.get("candidate_id") or "").strip()
        if not cid:
            continue
        rows.append({
            "candidate_id": cid,
            "resolution": (raw.get("resolution") or "").strip().lower(),
            "gold_class": (raw.get("gold_class") or "").strip(),
            "gold_family_id": (raw.get("gold_family_id") or "").strip(),
            "notes": (raw.get("notes") or "").strip(),
        })
    return rows


def render_triage_template(queue: list[dict]) -> str:
    """The blank decisions sheet: one row per real disagreement, both readings shown."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(TRIAGE_COLUMNS)
    for row in queue:
        if row.get("reason") not in ("class", "family"):
            continue
        writer.writerow([row["candidate_id"], "", "", "", ""])
    return buffer.getvalue()


def render_triage_queue(queue: list[dict]) -> str:
    columns = ["candidate_id", "reason", "human_gold_class", "model_gold_class",
               "human_gold_family_id", "model_gold_family_id"]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in queue:
        writer.writerow([row.get(column, "") or "" for column in columns])
    return buffer.getvalue()


def validate_triage(triage_rows: list[dict], required: set[str]) -> list[str]:
    """Return the triage sheet's violations. Empty means every disagreement is resolved."""
    errors: list[str] = []
    seen: set[str] = set()
    for row in triage_rows:
        cid = row["candidate_id"]
        if cid in seen:
            errors.append(f"{cid}: duplicate triage row")
        seen.add(cid)
        if row["resolution"] not in TRIAGE_RESOLUTIONS:
            errors.append(f"{cid}: resolution must be keep or revise, not "
                          f"{row['resolution']!r}")
            continue
        if row["resolution"] == "revise":
            if row["gold_class"] not in eligibility.SURFACE_CLASSES:
                errors.append(f"{cid}: revise needs a valid gold_class, not "
                              f"{row['gold_class']!r}")
            if not row["gold_family_id"]:
                errors.append(f"{cid}: revise needs a gold_family_id")
    for cid in sorted(required - seen):
        errors.append(f"{cid}: disagreement has no triage decision")
    return errors


def apply_triage(human_rows: list[dict], triage_rows: list[dict]) -> list[dict]:
    """Return the human's post-triage labels: his own, kept or revised by his own decision."""
    decisions = {row["candidate_id"]: row for row in triage_rows}
    out: list[dict] = []
    for row in human_rows:
        cid = row.get("candidate_id")
        decision = decisions.get(cid)
        final = dict(row)
        if not decision:
            final["annotation_status"] = "human"
        elif decision["resolution"] == "revise":
            final["gold_class"] = decision["gold_class"]
            final["gold_family_id"] = decision["gold_family_id"]
            final["annotation_status"] = "human-revised-after-triage"
            if decision.get("notes"):
                final["triage_notes"] = decision["notes"]
        else:
            final["annotation_status"] = "human-kept-after-triage"
            if decision.get("notes"):
                final["triage_notes"] = decision["notes"]
        out.append(final)
    return out


def merge_records(candidates: list[dict], final_rows: list[dict]) -> dict:
    """Attach the post-triage human labels to the sealed candidates, ready for metrics."""
    labels = _index(final_rows)
    records, unresolved = [], []
    for candidate in candidates:
        cid = candidate.get("candidate_id")
        label = labels.get(cid)
        if not label or label.get("gold_class") not in eligibility.SURFACE_CLASSES:
            unresolved.append({"candidate_id": cid, "reason": "missing human label"})
            continue
        if not label.get("gold_family_id"):
            unresolved.append({"candidate_id": cid, "reason": "missing gold family"})
            continue
        records.append({
            **candidate,
            "gold_class": label["gold_class"],
            "gold_family_id": label["gold_family_id"],
            "annotation_status": label.get("annotation_status", "human"),
            "annotator_ids": [label.get("annotator_id")],
            "adjudicator_id": None,
        })
    return {"schema_version": 1, "method_version": METHOD_VERSION,
            "records": records, "unresolved": unresolved}


def triage_summary(final_rows: list[dict]) -> dict:
    counts = defaultdict(int)
    for row in final_rows:
        counts[row.get("annotation_status", "human")] += 1
    return {
        "labels_total": len(final_rows),
        "kept_after_triage": counts["human-kept-after-triage"],
        "revised_after_triage": counts["human-revised-after-triage"],
        "never_queued": counts["human"],
    }


def metrics(records: list[dict], final_rows: list[dict], *, human_rater: str,
            model_rater: str | None = None, sample: str | None = None,
            split: str | None = None) -> dict:
    """The docs/33 metric set over the post-triage human labels, stamped with the label."""
    payload = goldset_metrics.metrics_with_intervals(records)
    payload["triage_summary"] = triage_summary(final_rows)
    if split:
        payload["split"] = split
    return stamp(payload, provenance(human_rater=human_rater, model_rater=model_rater,
                                     sample=sample))
