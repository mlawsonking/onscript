"""Deterministic document-family discovery for same-day publications."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re
import zlib

from . import config, util


METHOD_VERSION = "document-families-v2"
_WORD = re.compile(r"[a-z0-9]+(?:['’-][a-z0-9]+)*", re.IGNORECASE)
_PRIME = 4_294_967_311


def shingles(text: str, size: int | None = None) -> frozenset[int]:
    """Return stable word-shingle hashes."""
    width = size or config.DOCUMENT_FAMILY_SHINGLE_K
    tokens = [match.group(0).casefold() for match in _WORD.finditer(text or "")]
    if width < 1 or len(tokens) < width:
        return frozenset()
    return frozenset(
        zlib.crc32(" ".join(tokens[index:index + width]).encode("utf-8"))
        for index in range(len(tokens) - width + 1)
    )


def exact_similarity(left: frozenset[int], right: frozenset[int]) -> float:
    """Compute exact Jaccard similarity after candidate retrieval."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def minhash_signature(values: frozenset[int], count: int | None = None) -> tuple[int, ...]:
    """Return a process-stable MinHash signature using deterministic affine permutations."""
    length = count or config.DOCUMENT_FAMILY_MINHASHES
    if not values:
        return tuple()
    signature = []
    for index in range(length):
        a = 2 * index + 1
        b = zlib.crc32(f"document-family-{index}".encode("ascii"))
        signature.append(min(((a * value + b) % _PRIME) for value in values))
    return tuple(signature)


def candidate_pairs(signatures: list[tuple[int, ...]], bands: int | None = None) -> set[tuple[int, int]]:
    """Retrieve candidate pairs from equal MinHash bands."""
    band_count = bands or config.DOCUMENT_FAMILY_MINHASH_BANDS
    if not signatures:
        return set()
    signature_length = len(signatures[0])
    if signature_length == 0 or signature_length % band_count:
        raise ValueError("MinHash count must be a positive multiple of band count")
    rows = signature_length // band_count
    buckets: dict[tuple[int, tuple[int, ...]], list[int]] = defaultdict(list)
    for doc_index, signature in enumerate(signatures):
        if len(signature) != signature_length:
            raise ValueError("MinHash signatures must have one length")
        for band in range(band_count):
            start = band * rows
            buckets[(band, signature[start:start + rows])].append(doc_index)
    pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        for offset, left in enumerate(members):
            for right in members[offset + 1:]:
                pairs.add((min(left, right), max(left, right)))
    return pairs


def _instant(row: dict) -> datetime:
    value = row.get("published_at") or row.get("date") or "0001-01-01"
    value = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _within_window(left: dict, right: dict, hours: int | None = None) -> bool:
    limit = config.DOCUMENT_FAMILY_WINDOW_HOURS if hours is None else hours
    return abs((_instant(left) - _instant(right)).total_seconds()) <= limit * 3600


def _content_hash(row: dict) -> str:
    normalized = " ".join(match.group(0).casefold() for match in _WORD.finditer(row.get("text") or ""))
    return util.sha256_hex(normalized)


def cluster_documents(documents: list[dict]) -> list[dict]:
    """Cluster candidates against a fixed medoid anchor, never by transitive closure."""
    ordered = sorted(documents, key=lambda row: row.get("id") or "")
    usable = []
    for row in ordered:
        tokens = _WORD.findall(row.get("text") or "")
        values = shingles(row.get("text") or "")
        if len(tokens) >= config.DOCUMENT_FAMILY_MIN_TOKENS and values:
            usable.append((row, values))
    if not usable:
        return []

    signatures = [minhash_signature(values) for _row, values in usable]
    candidates = {
        pair for pair in candidate_pairs(signatures)
        if _within_window(usable[pair[0]][0], usable[pair[1]][0])
    }
    exact = {
        pair: exact_similarity(usable[pair[0]][1], usable[pair[1]][1])
        for pair in sorted(candidates)
    }

    clusters: list[dict] = []
    for index, (row, values) in enumerate(usable):
        choices = []
        for cluster_index, cluster in enumerate(clusters):
            medoid_index = cluster["medoid_index"]
            pair = (min(index, medoid_index), max(index, medoid_index))
            similarity = exact.get(pair, 0.0)
            if similarity >= config.DOCUMENT_FAMILY_JACCARD:
                choices.append((similarity, cluster_index))
        if choices:
            _similarity, chosen = max(choices, key=lambda item: (item[0], -item[1]))
            clusters[chosen]["indexes"].append(index)
        else:
            clusters.append({"medoid_index": index, "indexes": [index]})

    out = []
    for cluster in clusters:
        indexes = cluster["indexes"]
        valid_anchors = []
        for candidate in indexes:
            similarities = [
                exact_similarity(usable[candidate][1], usable[other][1])
                for other in indexes if other != candidate
            ]
            if all(value >= config.DOCUMENT_FAMILY_JACCARD for value in similarities):
                valid_anchors.append((sum(similarities), candidate))
        # The fixed assignment anchor always qualifies. Prefer the valid medoid with the largest
        # within-family similarity sum, then the earliest stable statement ID.
        medoid_index = max(valid_anchors, key=lambda item: (item[0], -item[1]))[1]
        medoid = usable[medoid_index][0]
        members = [usable[index][0] for index in indexes]
        offices = sorted({
            (row.get("member") or {}).get("bioguide") for row in members
            if (row.get("member") or {}).get("bioguide")
        })
        if len(members) < 2 or len(offices) < 2:
            continue
        existing = sorted({
            (row.get("document_family") or {}).get("family_id")
            for row in members if (row.get("document_family") or {}).get("family_id")
        })
        family_id = existing[0] if existing else "njoint:" + _content_hash(medoid)[:24]
        prior_revisions = sorted({
            (row.get("document_family") or {}).get("family_revision")
            for row in members if (row.get("document_family") or {}).get("family_revision")
        })
        member_hashes = sorted(_content_hash(row) for row in members)
        revision = "dfrev:" + util.sha256_hex(family_id + "\n" + "\n".join(member_hashes))[:24]
        similarities = {
            row.get("id"): round(exact_similarity(usable[medoid_index][1], values), 6)
            for row, values in (usable[index] for index in indexes)
        }
        out.append({
            "schema_version": 2,
            "object_type": "document_family",
            "method_version": METHOD_VERSION,
            "family_id": family_id,
            "family_revision": revision,
            "previous_revisions": [value for value in prior_revisions if value != revision],
            "medoid_statement_id": medoid.get("id"),
            "medoid_content_sha256": _content_hash(medoid),
            "statement_ids": [row.get("id") for row in members],
            "office_ids": offices,
            "publication_count": len(members),
            "member_similarities": similarities,
            "retrieval_path": "minhash-band then exact-jaccard",
            "duplicate_class": "near_duplicate",
            "versions": {
                "method": METHOD_VERSION,
                "shingle_k": config.DOCUMENT_FAMILY_SHINGLE_K,
                "minhashes": config.DOCUMENT_FAMILY_MINHASHES,
                "bands": config.DOCUMENT_FAMILY_MINHASH_BANDS,
                "jaccard": config.DOCUMENT_FAMILY_JACCARD,
                "window_hours": config.DOCUMENT_FAMILY_WINDOW_HOURS,
            },
        })
    return out


def apply_families(statements: list[dict]) -> int:
    """Assign near-duplicate families within the bounded temporal candidate window."""
    eligible = []
    for statement in statements:
        group = statement.get("joint_group")
        if (group is None or str(group).startswith(("dfam:", "njoint:"))) \
                and (statement.get("member") or {}).get("bioguide"):
            eligible.append(statement)
    by_id = {row.get("id"): row for row in statements}
    families = cluster_documents(eligible)
    for family in families:
        for statement_id in family["statement_ids"]:
            statement = by_id.get(statement_id)
            if statement is not None:
                statement["joint_group"] = family["family_id"]
                statement["document_family"] = dict(family)
    return len(families)


def annotate_all_families(statements: list[dict]) -> None:
    """Attach additive metadata for exact, near-duplicate, and singleton families."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for statement in statements:
        grouped[statement.get("joint_group") or statement.get("id")].append(statement)
    for family_id, members in sorted(grouped.items()):
        existing = next((row.get("document_family") for row in members if row.get("document_family")), None)
        if len(members) == 1 and not members[0].get("joint_group"):
            family_id = "dfam:" + _content_hash(members[0])[:24]
        medoid_id = ((existing or {}).get("medoid_statement_id")
                     or min((row.get("id") or "") for row in members))
        member_hashes = sorted(_content_hash(row) for row in members)
        revision = "dfrev:" + util.sha256_hex(family_id + "\n" + "\n".join(member_hashes))[:24]
        metadata = {
            "schema_version": 2,
            "object_type": "document_family",
            "method_version": METHOD_VERSION,
            "family_id": family_id,
            "family_revision": revision,
            "previous_revisions": (existing or {}).get("previous_revisions") or [],
            "medoid_statement_id": medoid_id,
            "statement_ids": sorted(row.get("id") for row in members),
            "office_ids": sorted({
                (row.get("member") or {}).get("bioguide") for row in members
                if (row.get("member") or {}).get("bioguide")
            }),
            "publication_count": len(members),
            "member_similarities": ((existing or {}).get("member_similarities")
                                    or {row.get("id"): 1.0 for row in members}),
            "retrieval_path": ((existing or {}).get("retrieval_path") or "exact-content"),
            "duplicate_class": ((existing or {}).get("duplicate_class")
                                or ("exact_duplicate" if len(members) > 1 else "singleton")),
            "versions": ((existing or {}).get("versions") or {"method": METHOD_VERSION}),
        }
        for row in members:
            row["document_family"] = metadata


def recall_report(documents: list[dict], *, max_documents: int = 200) -> dict:
    """Compare MinHash retrieval with exhaustive exact comparison on a bounded subset."""
    bounded = sorted(documents, key=lambda row: (_instant(row), row.get("id") or ""))[:max_documents]
    usable = [(row, shingles(row.get("text") or "")) for row in bounded]
    usable = [(row, values) for row, values in usable if values]
    signatures = [minhash_signature(values) for _row, values in usable]
    retrieved = {pair for pair in candidate_pairs(signatures)
                 if _within_window(usable[pair[0]][0], usable[pair[1]][0])}
    exhaustive = set()
    for left in range(len(usable)):
        for right in range(left + 1, len(usable)):
            if (_within_window(usable[left][0], usable[right][0])
                    and exact_similarity(usable[left][1], usable[right][1])
                    >= config.DOCUMENT_FAMILY_JACCARD):
                exhaustive.add((left, right))
    found = exhaustive & retrieved
    recall = len(found) / len(exhaustive) if exhaustive else 1.0
    return {
        "method_version": METHOD_VERSION,
        "bounded_documents": len(usable),
        "exhaustive_positive_pairs": len(exhaustive),
        "retrieved_positive_pairs": len(found),
        "candidate_pairs": len(retrieved),
        "recall": round(recall, 6),
        "target": config.DOCUMENT_FAMILY_RECALL_TARGET,
        "meets_target": recall >= config.DOCUMENT_FAMILY_RECALL_TARGET,
        "window_hours": config.DOCUMENT_FAMILY_WINDOW_HOURS,
        "denominator": "exhaustive positive pairs in the bounded temporal subset",
    }
