"""Deterministic document-family discovery for same-day publications."""
from __future__ import annotations

from collections import defaultdict
import re
import zlib

from . import config, util


METHOD_VERSION = "document-families-v1"
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
    candidates = candidate_pairs(signatures)
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
        family_id = "njoint:" + util.sha256_hex(
            f"{medoid.get('published_at')}\n{medoid.get('id')}"
        )[:20]
        out.append({
            "schema_version": 1,
            "object_type": "document_family",
            "method_version": METHOD_VERSION,
            "family_id": family_id,
            "medoid_statement_id": medoid.get("id"),
            "statement_ids": [row.get("id") for row in members],
            "office_ids": offices,
            "publication_count": len(members),
        })
    return out


def apply_families(statements: list[dict]) -> int:
    """Assign near-duplicate family IDs within each day and return families formed."""
    by_day: dict[str, list[dict]] = defaultdict(list)
    for statement in statements:
        if statement.get("joint_group") is None and (statement.get("member") or {}).get("bioguide"):
            by_day[statement.get("published_at") or ""].append(statement)
    by_id = {row.get("id"): row for row in statements}
    families = []
    for day in sorted(by_day):
        families.extend(cluster_documents(by_day[day]))
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
        medoid_id = ((existing or {}).get("medoid_statement_id")
                     or min((row.get("id") or "") for row in members))
        metadata = {
            "schema_version": 1,
            "object_type": "document_family",
            "method_version": METHOD_VERSION,
            "family_id": family_id,
            "medoid_statement_id": medoid_id,
            "statement_ids": sorted(row.get("id") for row in members),
            "office_ids": sorted({
                (row.get("member") or {}).get("bioguide") for row in members
                if (row.get("member") or {}).get("bioguide")
            }),
            "publication_count": len(members),
        }
        for row in members:
            row["document_family"] = metadata
