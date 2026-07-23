"""B2 — cluster extracted fragments into talking points, per party per day (§3, §4 B2).

Local, $0 (per R10): union-find over fragments that share a distinctive content trigram. A
cluster becomes a publishable talking point only if it spans >= 3 DISTINCT members (the
citation-integrity floor). Deterministic; independent of which generator produced the
fragments.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import boilerplate, config, privacy


def _cluster_grams(text: str) -> set[str]:
    """Distinctive shared-phrase keys for clustering: content 4- and 5-grams. Longer than
    trigrams so fragments only merge on genuinely shared language, not common connectors like
    "the united states" (which chained distinct topics into one giant cluster)."""
    grams: set[str] = set()
    for toks in boilerplate.sentences(text):
        for n in (4, 5):
            for i in range(len(toks) - n + 1):
                g = " ".join(toks[i : i + n])
                if not boilerplate.is_low_content(g) and not boilerplate.is_boilerplate_ngram(g):
                    grams.add(g)
    return grams


class _UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]; i = self.p[i]
        return i
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def _unit(fragment: dict, statement: dict | None = None):
    statement = statement or {}
    return (statement.get("joint_group") or fragment.get("joint_group")
            or (statement.get("member") or {}).get("bioguide") or fragment.get("bioguide"))


def _admissible_support_phrase(gram: str) -> bool:
    """The three generation-time admission gates, applied before a support phrase can win."""
    return (not boilerplate.is_scaffold_key(gram)
            and not boilerplate.is_weak_label(gram)
            and not privacy.is_suppressed(gram))


def cluster_day(party: str, day: str, annotated_fragments: list[dict],
                statements_by_id: dict[str, dict] | None = None) -> list[dict]:
    """Cluster fragments, then bind each component to one support phrase and one support set.

    ``source_text`` on an annotated fragment is used when a full statement map is not supplied. The
    production path supplies both, so phrase containment, carrier counts, quorum, and later citations
    all use the same statement-level ``contains_gram`` predicate.
    """
    frs = annotated_fragments
    if len(frs) < 3:
        return []
    grams = [_cluster_grams(f["text"]) for f in frs]
    index: dict[str, list[int]] = defaultdict(list)
    for i, gs in enumerate(grams):
        for g in gs:
            index[g].append(i)
    uf = _UF(len(frs))
    for members in index.values():
        for j in members[1:]:
            uf.union(members[0], j)

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(len(frs)):
        clusters[uf.find(i)].append(i)

    out: list[dict] = []
    for k, idxs in clusters.items():
        # A transitive component is only a candidate container. It is never itself the public
        # numerator. Components below quorum cannot contain a phrase at quorum, so they still die
        # here as the cheap first cut.
        component_units = {_unit(frs[i], (statements_by_id or {}).get(frs[i].get("statement")))
                           for i in idxs}
        component_units.discard(None)
        if len(component_units) < config.SYNC_MIN_MEMBERS:
            continue

        by_statement: dict[str, dict] = {}
        for i in idxs:
            sid = frs[i].get("statement")
            if not sid or sid in by_statement:
                continue
            source = (statements_by_id or {}).get(sid)
            if source is None:
                source = {
                    "id": sid,
                    "text": frs[i].get("source_text") or frs[i].get("text", ""),
                    "joint_group": frs[i].get("joint_group"),
                    "member": {"bioguide": frs[i].get("bioguide")},
                }
            by_statement[sid] = source

        candidates = sorted({g for i in idxs for g in grams[i]})
        ranked: list[tuple[int, int, int, str, set, set]] = []
        raw_ranked: list[tuple[int, int, int, str, set, set]] = []
        for gram in candidates:
            support_statements = {
                sid for sid, statement in by_statement.items()
                if boilerplate.contains_gram(statement.get("text", ""), gram)
            }
            support_units = {
                _unit(next((frs[i] for i in idxs if frs[i].get("statement") == sid), {}),
                      by_statement.get(sid))
                for sid in support_statements
            }
            support_units.discard(None)
            row = (len(support_units), len(support_statements), len(gram.split()), gram,
                   support_units, support_statements)
            raw_ranked.append(row)
            if _admissible_support_phrase(gram):
                ranked.append(row)

        # Prefer the admissible phrase carried by the most distinct units, then the longer phrase,
        # then lexicographic order. If every candidate fails admission, retain the best raw phrase so
        # the existing assembly gate can reject and log its specific reason. Nothing from that
        # fallback reaches a public surface.
        pool = ranked or raw_ranked
        if not pool:
            continue
        carrier_count, _carriers, _words, label, support_units, support_statements = sorted(
            pool, key=lambda row: (-row[0], -row[1], -row[2], row[3])
        )[0]

        support_idxs = [i for i in idxs if frs[i].get("statement") in support_statements]
        topics = Counter(t for i in support_idxs for t in frs[i].get("topics", []))

        # Keep one representative per support unit. A fragment that visibly carries P wins within
        # its unit; length and text make the remaining choice deterministic. A support statement can
        # carry P outside the extracted fragment, so the fallback remains for verbatim audit only.
        unit_fragments: dict[object, list[int]] = defaultdict(list)
        for i in support_idxs:
            sid = frs[i].get("statement")
            unit = _unit(frs[i], by_statement.get(sid))
            if unit:
                unit_fragments[unit].append(i)
        frags: list[dict] = []
        for unit in sorted(unit_fragments, key=str):
            i = sorted(
                unit_fragments[unit],
                key=lambda n: (not boilerplate.contains_gram(frs[n].get("text", ""), label),
                               len((frs[n].get("text") or "").split()),
                               frs[n].get("text") or "", frs[n].get("statement") or ""),
            )[0]
            frags.append({"text": frs[i]["text"], "statement": frs[i]["statement"]})
        out.append({
            "id": f"{day}-{party}-{len(out):02d}",
            "party": party, "day": day, "label": label,
            "member_count": carrier_count,
            "statements": sorted(support_statements),
            "fragments": frags,
            "topics": [t for t, _ in topics.most_common(3)],
            "leadership_first": False,
        })
    out.sort(key=lambda tp: tp["member_count"], reverse=True)
    # re-id after sort so ids are stable by rank
    for rank, tp in enumerate(out):
        tp["id"] = f"{day}-{party}-{rank:02d}"
    return out
