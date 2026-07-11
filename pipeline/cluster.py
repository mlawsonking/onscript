"""B2 — cluster extracted fragments into talking points, per party per day (§3, §4 B2).

Local, $0 (per R10): union-find over fragments that share a distinctive content trigram. A
cluster becomes a publishable talking point only if it spans >= 3 DISTINCT members (the
citation-integrity floor). Deterministic; independent of which generator produced the
fragments.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import boilerplate, config


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


def cluster_day(party: str, day: str, annotated_fragments: list[dict]) -> list[dict]:
    """annotated_fragments: [{text, topics, statement, bioguide}]. Returns talking_point dicts."""
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
        members = {frs[i]["bioguide"] for i in idxs if frs[i].get("bioguide")}
        if len(members) < config.SYNC_MIN_MEMBERS:
            continue
        # label = most common distinctive trigram across the cluster (grounded in fragments)
        gram_counts = Counter(g for i in idxs for g in grams[i])
        label = gram_counts.most_common(1)[0][0] if gram_counts else frs[idxs[0]]["text"]
        topics = Counter(t for i in idxs for t in frs[i].get("topics", []))
        statements = sorted({frs[i]["statement"] for i in idxs})
        # one representative fragment per member (dedupe so receipts are clean)
        seen_member: set[str] = set()
        frags: list[dict] = []
        for i in idxs:
            b = frs[i].get("bioguide")
            if b and b not in seen_member:
                frags.append({"text": frs[i]["text"], "statement": frs[i]["statement"]})
                seen_member.add(b)
        out.append({
            "id": f"{day}-{party}-{len(out):02d}",
            "party": party, "day": day, "label": label,
            "member_count": len(members),
            "statements": statements,
            "fragments": frags,
            "topics": [t for t, _ in topics.most_common(3)],
            "leadership_first": False,
        })
    out.sort(key=lambda tp: tp["member_count"], reverse=True)
    # re-id after sort so ids are stable by rank
    for rank, tp in enumerate(out):
        tp["id"] = f"{day}-{party}-{rank:02d}"
    return out
