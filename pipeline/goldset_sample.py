"""Deterministic gold-set candidate universe and sealed pilot/full sampling.

This module turns the committed lane-1 corpus into a frozen annotation frame. It is a
one-time build tool, not part of the daily pipeline. It reads the phrase ledger and the
normalized statements, never the network, and spends no API budget.

The candidate unit is one phrase (an n-gram) as carried by one party on that party's
peak public day. The support-unit count from the ledger unit key (joint groups already
collapsed) is the family-evidence count the deterministic classifier uses for the
message quorum. See docs/35 for the sealing protocol and the recorded seed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json

from . import config, contracts, document_families, eligibility, goldset, privacy, util


SAMPLE_METHOD_VERSION = "gold-set-sample-v1"
PARTIES = ("D", "R")
GENERIC_SURVIVORS_PATH = config.REPO_ROOT / "evaluation" / "goldset" / "generic_survivors.json"


def survivor_phrases(path=None) -> set[str]:
    """Generic message-floor survivors registered for public-surface oversampling (R-36.7).

    These phrases pass the deterministic message floor without family evidence. Adding them to
    the public-surface set draws them into the pilot on the next seal, so the gold set can
    adjudicate whether they should be message.
    """
    source = path or GENERIC_SURVIVORS_PATH
    if not source.is_file():
        return set()
    data = json.loads(source.read_text(encoding="utf-8"))
    return {row["ngram"] for row in (data.get("survivors") or []) if row.get("ngram")}
# Impact weights order the ranking inside each stratum so public-impact and rare-class
# cases are drawn before ordinary filler. Higher weight sorts earlier.
IMPACT_WEIGHTS = {
    "public_surface": 8,
    "private": 6,
    "rare_class": 4,
    "family_collapse": 3,
    "boundary_quorum": 2,
}


def candidate_id(ngram: str, party: str, day: str) -> str:
    """Return the stable candidate identifier for one phrase-party-day occurrence."""
    digest = util.sha256_hex(f"{SAMPLE_METHOD_VERSION}\n{ngram}\n{party}\n{day}")[:16]
    return f"cand:{digest}"


def _classify(ngram: str, day: str, units: int, memo: dict) -> dict:
    """Classify one phrase, memoized on phrase, congress, and the quorum bucket."""
    congress = util.congress_for_date(day)
    key = (ngram, congress, min(units, 3))
    hit = memo.get(key)
    if hit is None:
        hit = eligibility.classify_phrase(
            ngram, day=day, congress=congress, family_count=units
        )
        memo[key] = hit
    return hit


def _peak_days(daily: dict, epoch: str) -> dict:
    """Return each party's peak public day: most units, earliest day breaks ties."""
    peaks: dict[str, tuple[str, int, int]] = {}
    for day, row in daily.items():
        if not isinstance(row, dict) or day < epoch:
            continue
        for party in PARTIES:
            units = int(row.get(party) or 0)
            if units <= 0:
                continue
            members = row.get(f"members_{party}") or []
            headcount = len(set(members)) if isinstance(members, list) else units
            current = peaks.get(party)
            if current is None or units > current[1] or (units == current[1] and day < current[0]):
                peaks[party] = (day, units, headcount)
    return peaks


def build_universe(ledger: dict, *, epoch: str | None = None, min_units: int = 1) -> list[dict]:
    """Build the deterministic candidate universe from the phrase ledger.

    One candidate per (phrase, party) at that party's peak public day. ``min_units`` drops
    occurrences below a support-unit floor. Output is sorted by candidate_id for stability.
    """
    epoch = epoch or config.STAGE1_EPOCH
    memo: dict = {}
    universe: list[dict] = []
    for ngram, record in ledger.items():
        if not isinstance(record, dict):
            continue
        daily = record.get("daily") or {}
        peaks = _peak_days(daily, epoch)
        for party, (day, units, headcount) in peaks.items():
            if units < min_units:
                continue
            verdict = _classify(ngram, day, units, memo)
            universe.append({
                "candidate_id": candidate_id(ngram, party, day),
                "ngram": ngram,
                "n": record.get("n"),
                "day": day,
                "year": day[:4],
                "party": party,
                "lane": 1,
                "member_count": units,
                "member_headcount": headcount,
                "family_evidence_count": units,
                "predicted_class": verdict["surface_class"],
                "classifier_rule": verdict["classifier"]["rule"],
            })
    universe.sort(key=lambda row: row["candidate_id"])
    return universe


def _row_phrase(row: dict) -> str | None:
    if isinstance(row, dict):
        label = row.get("label") or row.get("ngram") or row.get("phrase")
        return str(label) if label else None
    return None


def _day_surface_phrases(day_artifacts: list[dict]) -> set[str]:
    """Collect every n-gram that reached a committed day's public talking-point surfaces.

    ``talking_points`` is a party-keyed dict of composite headline rows (each carries a
    ``label``); ``top_synchronized`` is a ranked list of rows (each carries an ``ngram``).
    Both feed the public-impact tag.
    """
    phrases: set[str] = set()
    for day in day_artifacts:
        talking = day.get("talking_points")
        if isinstance(talking, dict):
            for rows in talking.values():
                for row in rows or []:
                    phrase = _row_phrase(row)
                    if phrase:
                        phrases.add(phrase)
        elif isinstance(talking, list):
            for row in talking:
                phrase = _row_phrase(row)
                if phrase:
                    phrases.add(phrase)
        for row in day.get("top_synchronized") or []:
            phrase = _row_phrase(row)
            if phrase:
                phrases.add(phrase)
    return phrases


def tag_impact(universe: list[dict], *, public_phrases: set[str] | None = None) -> None:
    """Attach impact tags and a priority score in place. Determines oversampling order."""
    public_phrases = public_phrases or set()
    for row in universe:
        tags: list[str] = []
        if row["ngram"] in public_phrases:
            tags.append("public_surface")
        if row["predicted_class"] == "private":
            tags.append("private")
        if row["predicted_class"] in ("biographical", "private", "nomenclature"):
            tags.append("rare_class")
        if row["member_headcount"] > row["member_count"]:
            tags.append("family_collapse")
        if row["member_count"] in (2, 3):
            tags.append("boundary_quorum")
        row["impact_tags"] = tags
        row["priority"] = sum(IMPACT_WEIGHTS[tag] for tag in tags)


def stratum_key(row: dict) -> tuple[str, str, str, str]:
    """Stratify by the W10 sampler dimensions: party, predicted class, lane, year."""
    return (
        str(row["party"]),
        str(row["predicted_class"]),
        str(row["lane"]),
        str(row["year"]),
    )


def _rank_key(seed: str, row: dict) -> tuple:
    """Rank within a stratum: highest priority first, then a seeded stable hash."""
    digest = util.sha256_hex(f"{seed}\n{row['candidate_id']}")
    return (-int(row.get("priority") or 0), digest, row["candidate_id"])


def _largest_remainder(weights: dict, total: int, caps: dict) -> dict:
    """Apportion ``total`` across keys proportional to weights, none exceeding its cap.

    Deterministic largest-remainder rounding. When a cap saturates, its unused share is
    reapportioned across the remaining keys in a later pass, so the sum equals
    ``min(total, sum(caps))`` exactly.
    """
    alloc = {key: 0 for key in weights}
    total = min(total, sum(caps.values()))
    if total <= 0 or sum(weights.values()) <= 0:
        return alloc
    remaining = total
    while remaining > 0:
        active = {k: weights[k] for k in weights if alloc[k] < caps[k] and weights[k] > 0}
        if not active:
            break
        weight_sum = sum(active.values())
        quotas = {k: active[k] / weight_sum * remaining for k in active}
        # Integer floor of each quota, clamped to remaining capacity.
        granted = 0
        for key in active:
            grant = min(int(quotas[key]), caps[key] - alloc[key])
            alloc[key] += grant
            granted += grant
        remaining = total - sum(alloc.values())
        if remaining <= 0:
            break
        # Hand out the leftover one at a time by largest fractional remainder.
        order = sorted(
            (k for k in active if alloc[k] < caps[k]),
            key=lambda k: (-(quotas[k] - int(quotas[k])), k),
        )
        if not order:
            break
        progressed = False
        for key in order:
            if remaining <= 0:
                break
            alloc[key] += 1
            remaining -= 1
            progressed = True
        if not progressed:
            break
    return alloc


def _evenly_spaced(length: int, count: int) -> set[int]:
    """Return ``count`` indices spread across ``range(length)`` for representative striding."""
    if count <= 0 or length <= 0:
        return set()
    count = min(count, length)
    return {int((position + 0.5) * length / count) for position in range(count)}


def allocate(universe: list[dict], *, total: int, seed: str, floor: int = 1,
             small_class_cap: int = 200) -> dict:
    """Select ``total`` candidates, stratified with impact ranking and rare-class coverage.

    Returns the ordered selection grouped by stratum. Any predicted class whose entire
    universe pool is at or below ``small_class_cap`` is taken in full, so the rarest classes
    (private, biographical) are fully represented in the confusion matrix. Every other
    stratum receives at least ``min(floor, size)`` slots; the remaining budget is apportioned
    proportional to stratum size, drawing the highest-priority candidates first.
    """
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in universe:
        grouped[stratum_key(row)].append(row)
    ordered = {
        key: sorted(rows, key=lambda row: _rank_key(seed, row))
        for key, rows in grouped.items()
    }
    caps = {key: len(rows) for key, rows in ordered.items()}
    class_sizes = Counter(row["predicted_class"] for row in universe)
    # Fully include the small rare classes; floor the rest.
    reserved = {}
    for key in ordered:
        predicted_class = key[1]
        if class_sizes[predicted_class] <= small_class_cap:
            reserved[key] = caps[key]
        else:
            reserved[key] = min(floor, caps[key])
    remaining_budget = max(0, total - sum(reserved.values()))
    residual_caps = {key: caps[key] - reserved[key] for key in ordered}
    weights = {key: residual_caps[key] for key in ordered}
    extra = _largest_remainder(weights, remaining_budget, residual_caps)
    counts = {key: reserved[key] + extra[key] for key in ordered}
    selection = {key: ordered[key][:counts[key]] for key in ordered}
    return {key: rows for key, rows in selection.items() if rows}


def split_pilot_full(selection: dict, *, pilot_size: int) -> tuple[list[dict], list[dict]]:
    """Partition the stratified selection into disjoint pilot and full sets.

    Pilot items are strided across each stratum's ranked slice so both sets span the full
    priority range. The pilot receives exactly ``pilot_size`` items when the selection is
    large enough, apportioned across strata by largest remainder.
    """
    sizes = {key: len(rows) for key, rows in selection.items()}
    total = sum(sizes.values())
    pilot_size = min(pilot_size, total)
    pilot_counts = _largest_remainder(sizes, pilot_size, sizes)
    pilot: list[dict] = []
    full: list[dict] = []
    for key in sorted(selection):
        rows = selection[key]
        pilot_idx = _evenly_spaced(len(rows), pilot_counts.get(key, 0))
        for index, row in enumerate(rows):
            (pilot if index in pilot_idx else full).append(row)
    pilot.sort(key=lambda row: row["candidate_id"])
    full.sort(key=lambda row: row["candidate_id"])
    return pilot, full


def _load_statements_by_day(statements_path) -> dict:
    """Index normalized statements by publication day for anchor lookup."""
    import gzip

    by_day: dict[str, list[dict]] = defaultdict(list)
    opener = gzip.open if str(statements_path).endswith(".gz") else open
    with opener(statements_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("lane")) != "1":
                continue
            by_day[str(row.get("published_at") or "")[:10]].append(row)
    return by_day


def _tokens_of(statement: dict, cache: dict) -> list[str]:
    sid = statement.get("id") or ""
    hit = cache.get(sid)
    if hit is None:
        hit = [token for token, _s, _e in contracts._token_spans(statement.get("text") or "")]
        cache[sid] = hit
    return hit


def _phrase_in_tokens(tokens: list[str], wanted: list[str]) -> bool:
    width = len(wanted)
    for index in range(len(tokens) - width + 1):
        if tokens[index:index + width] == wanted:
            return True
    return False


def anchor_and_contextualize(rows: list[dict], statements_by_day: dict) -> list[dict]:
    """Attach the anchor statement, document family, and occurrence offsets to each row.

    Families are computed within the row's (day, party) group, which is the unit the
    family-pairwise metric compares. The row is pinned with its predicted family id and
    occurrence coordinates so downstream rendering never recomputes classification.
    """
    # Cache family assignment per (day, party) so co-located rows agree.
    family_cache: dict[tuple[str, str], dict] = {}
    token_cache: dict[str, list[str]] = {}
    out: list[dict] = []
    for row in rows:
        day, party, phrase = row["day"], row["party"], row["ngram"]
        group_key = (day, party)
        group = family_cache.get(group_key)
        if group is None:
            members = [
                dict(statement)
                for statement in statements_by_day.get(day, [])
                if (statement.get("member") or {}).get("party") == party
            ]
            members.sort(key=lambda statement: statement.get("id") or "")
            document_families.apply_families(members)
            document_families.annotate_all_families(members)
            group = {statement.get("id"): statement for statement in members}
            family_cache[group_key] = group
        wanted = phrase.split()
        anchor = None
        for statement in sorted(group.values(), key=lambda statement: statement.get("id") or ""):
            if _phrase_in_tokens(_tokens_of(statement, token_cache), wanted):
                anchor = statement
                break
        pinned = dict(row)
        if anchor is None:
            pinned["anchor_statement_id"] = None
            pinned["predicted_family_id"] = None
            pinned["anchor_resolved"] = False
            out.append(pinned)
            continue
        occurrences = contracts.phrase_occurrences(anchor, phrase, row["candidate_id"])
        first = occurrences[0] if occurrences else {}
        family = anchor.get("document_family") or {}
        pinned.update({
            "anchor_statement_id": anchor.get("id"),
            "anchor_resolved": True,
            "predicted_family_id": family.get("family_id") or anchor.get("id"),
            "predicted_family_revision": family.get("family_revision"),
            "occurrence_start_char": first.get("start_char"),
            "occurrence_end_char": first.get("end_char"),
            "sentence_start_char": first.get("sentence_start_char"),
            "sentence_end_char": first.get("sentence_end_char"),
            "is_quoted": first.get("is_quoted"),
            "quoted_speaker_detected": first.get("quoted_speaker_detected"),
            "stance": first.get("stance"),
        })
        out.append(pinned)
    return out


def redact_for_publish(rows: list[dict]) -> list[dict]:
    """Return copies with every displayed phrase run through the hardened label path.

    Admitted private-person forms never reach a written sample file. The candidate_id is a
    hash of the original phrase, so reproducible identity survives redaction. Applied to
    every row before a sample file is written, per the privacy floor (Article XIII).
    """
    out: list[dict] = []
    for row in rows:
        clean = dict(row)
        redacted, count = privacy.redact(row.get("ngram") or "")
        clean["ngram"] = redacted
        if count:
            clean["phrase_redacted"] = True
        out.append(clean)
    return out


def _universe_fingerprint(universe: list[dict]) -> str:
    """Fingerprint the frame so any corpus change invalidates the seal."""
    payload = "\n".join(
        f"{row['candidate_id']}\t{row['predicted_class']}\t{row['day']}\t{row['party']}"
        for row in sorted(universe, key=lambda row: row["candidate_id"])
    )
    return util.sha256_hex(payload)


def _seal_hash(pilot_ids: list[str], full_ids: list[str], boundaries: dict,
               seed: str, fingerprint: str) -> str:
    """Hash the sealed identity: sorted IDs, split boundaries, seed, and frame fingerprint."""
    payload = json.dumps(
        {
            "method_version": SAMPLE_METHOD_VERSION,
            "seed": seed,
            "universe_fingerprint": fingerprint,
            "split_boundaries": boundaries,
            "pilot_ids": sorted(pilot_ids),
            "full_ids": sorted(full_ids),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return util.sha256_hex(payload)


def seal(universe: list[dict], *, seed: str, pilot_size: int, full_size: int,
         split_boundaries: dict, ledger_source: dict | None = None) -> dict:
    """Produce the sealed sample manifest: disjoint pilot and full sets with a seal hash.

    ``split_boundaries`` freezes the train/validation/test date cut. The returned manifest
    records the seed, the frame fingerprint, per-stratum availability, and the seal hash.
    """
    selection = allocate(universe, total=pilot_size + full_size, seed=seed)
    pilot, full = split_pilot_full(selection, pilot_size=pilot_size)
    train_end = split_boundaries["train_end"]
    validation_end = split_boundaries["validation_end"]
    pilot = goldset.assign_splits(pilot, train_end, validation_end)
    full = goldset.assign_splits(full, train_end, validation_end)
    fingerprint = _universe_fingerprint(universe)
    pilot_ids = [row["candidate_id"] for row in pilot]
    full_ids = [row["candidate_id"] for row in full]
    strata = []
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in universe:
        grouped[stratum_key(row)].append(row)
    selected_ids = set(pilot_ids) | set(full_ids)
    for key in sorted(grouped):
        rows = grouped[key]
        strata.append({
            "party": key[0],
            "predicted_class": key[1],
            "lane": key[2],
            "year": key[3],
            "available": len(rows),
            "selected": sum(1 for row in rows if row["candidate_id"] in selected_ids),
        })
    return {
        "schema_version": 1,
        "method_version": SAMPLE_METHOD_VERSION,
        "seed": seed,
        "universe_size": len(universe),
        "universe_fingerprint": fingerprint,
        "ledger_source": ledger_source or {},
        "split_boundaries": split_boundaries,
        "pilot_size": len(pilot),
        "full_size": len(full),
        "strata": strata,
        "seal_hash": _seal_hash(pilot_ids, full_ids, split_boundaries, seed, fingerprint),
        "pilot": pilot,
        "full": full,
    }
