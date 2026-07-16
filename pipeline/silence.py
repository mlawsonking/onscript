"""The Silence Detector + its mirror twin "Shouting Into the Void" (v2 feature 1.2, docs/11).

The absence map: topics dominating the day's news that **neither** party's members will touch — and the
inverse, topics our members push that the news isn't covering. Both directions are returned together
(the release gate: "both directions ship together"), and every claim is deterministic + reproducible
from published data (the taxonomy seeds + the GDELT theme map are both committed).

THE LOAD-BEARING GUARD — a gap is not a silence. A topic is excluded from scoring when:
  * the GDELT pull failed (volume None) — we don't know the news, so we can't claim silence; or
  * our corpus coverage for the day is thin/one-party — a corpus hole would masquerade as avoidance.
This is the §10 acceptance: silence claims are machine-gated, never asserted from absence of data.
"""
from __future__ import annotations

import json

from . import config

NEWS_FLOOR = 0.05          # a topic must be genuinely in the news to be callable "silence"
QUIET_MAX = 2              # <= this many statements from a party = that party isn't touching it
VOID_MIN = 5               # a party must be pushing a topic this hard for "shouting into the void"
VOID_NEWS_MAX = 0.01       # ...while the news is effectively not covering it
MIN_PARTY_STATEMENTS = 25  # per-party daily corpus floor: below this the day is too thin to score


def load_taxonomy() -> dict:
    return json.loads((config.REPO_ROOT / "taxonomy_v1.json").read_text(encoding="utf-8"))


def topic_hits(text: str, seeds) -> bool:
    """Deterministic topic match: any committed seed appears in the statement text. The SAME seeds
    drive the GDELT news query, so both sides of a silence claim share one published definition."""
    t = (text or "").lower()
    return any(s.lower() in t for s in (seeds or []))


def corpus_topics(statements, taxonomy=None) -> dict:
    """{topic_id: {'D': n, 'R': n}} — per-party statement counts per topic for a day, deterministic."""
    tax = taxonomy or load_taxonomy()
    out = {t["id"]: {"D": 0, "R": 0} for t in tax["topics"]}
    for s in statements:
        party = ((s.get("member") or {}).get("party"))
        if party not in ("D", "R"):
            continue
        text = f"{s.get('title') or ''} {s.get('text') or ''}"
        for t in tax["topics"]:
            if t["id"] != "other" and topic_hits(text, t.get("seeds")):
                out[t["id"]][party] += 1
    return out


def silence_board(news: dict, corpus: dict, taxonomy=None) -> dict:
    """Both directions, together. `news` = {topic_id: volume|None} (None = failed pull -> excluded).
    `corpus` = {topic_id: {'D': n, 'R': n}}. Returns silent[] + void[] + the gates that were applied."""
    tax = taxonomy or load_taxonomy()
    labels = {t["id"]: t["label"] for t in tax["topics"]}
    totals = {p: sum(c.get(p, 0) for c in corpus.values()) for p in ("D", "R")}
    thin = totals["D"] < MIN_PARTY_STATEMENTS or totals["R"] < MIN_PARTY_STATEMENTS
    silent, void, excluded = [], [], []
    for tid, vol in (news or {}).items():
        c = corpus.get(tid) or {"D": 0, "R": 0}
        if vol is None:
            excluded.append({"topic": tid, "reason": "news pull failed — a gap is not a silence"})
            continue
        if vol >= NEWS_FLOOR and c["D"] <= QUIET_MAX and c["R"] <= QUIET_MAX:
            silent.append({"topic": tid, "label": labels.get(tid), "news_volume": round(vol, 4),
                           "D": c["D"], "R": c["R"]})
        if vol <= VOID_NEWS_MAX and (c["D"] >= VOID_MIN or c["R"] >= VOID_MIN):
            void.append({"topic": tid, "label": labels.get(tid), "news_volume": round(vol, 4),
                         "D": c["D"], "R": c["R"]})
    silent.sort(key=lambda r: -r["news_volume"])
    void.sort(key=lambda r: -(r["D"] + r["R"]))
    return {
        "schema_version": 1, "kind": "silence-board",
        "scored": not thin,
        "silent": [] if thin else silent,
        "void": [] if thin else void,
        "excluded": excluded,
        "gates": {"news_floor": NEWS_FLOOR, "quiet_max": QUIET_MAX, "void_min": VOID_MIN,
                  "void_news_max": VOID_NEWS_MAX, "min_party_statements": MIN_PARTY_STATEMENTS,
                  "party_totals": totals,
                  "note": ("day too thin/one-party to score — a corpus hole must never read as avoidance"
                           if thin else "coverage sufficient; both directions scored")},
    }
