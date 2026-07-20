"""HX.2 · Per-topic script-proneness (docs/05 §3). A descriptive: do some topics generate more
COORDINATION per unit of discussion than others — "immigration travels differently than disaster aid"?

Design (declared before measuring; a descriptive has no CONFIRM/REFUTE gate to hack). For each of the
25 taxonomy_v1 topics (its committed `seeds`), per party, per provenance lane (L1):
  C = coordinated phrases  = distinct peak>=15 phrases (member_index[lane]) whose text contains >=1 of
                             the topic's seeds, credited to the phrase's peak_party.
  V = on-topic volume      = solo/Lane-1 D/R statements (iter_statements[lane]) whose text contains >=1
                             of the topic's seeds.
  script-proneness INDEX   = 1000 * C / V  (coordinated phrase-types per 1,000 on-topic statements) —
                             a RELATIVE index across topics within a party x lane, NOT an absolute rate
                             (C counts phrase-types, V counts statements — different units, on purpose:
                             it asks how much coordination a topic throws off relative to how much it is
                             discussed). Also reported: the median peak of a topic's coordinated phrases
                             (coordination INTENSITY).

Proxy caveat, DISCLOSED: seed-substring tagging misses topical phrases/statements that don't contain the
literal seed ("born in the united states" is about birthright/immigration but carries no seed), so both
C and V are lower bounds; the INDEX is only interpreted comparatively across topics, never absolutely.
Denominators (C and V) ride in the view on every row (#146/R3). Chambers not split here (topic volume
is chamber-mixed by design — a topic-level, not office-level, descriptive); lanes never pooled (L1).

Re-runnable:  PYTHONHASHSEED=0 C:/ProgramData/miniconda3/python.exe scripts/search/hx_2_topic_scriptproneness.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import util  # noqa: E402
from pipeline.search import harness as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = ROOT / "taxonomy_v1.json"
RESULT = ROOT / "scripts" / "search" / "evidence" / "hx_2_topic_scriptproneness.result.json"
EVID = Path("X:/onscript-data/elections/derived")
LANES = ("propublica", "scraped")


def load_topics():
    tx = json.loads(TAXONOMY.read_text(encoding="utf-8"))["topics"]
    out = {}
    for t in tx:
        seeds = [s.lower() for s in (t.get("seeds") or []) if s]
        if seeds:
            out[t.get("id") or t.get("name")] = seeds
    return out


def topics_in(low: str, topics: dict) -> list:
    return [tid for tid, seeds in topics.items() if any(s in low for s in seeds)]


def main():
    topics = load_topics()
    print(f"HX.2 per-topic script-proneness — {len(topics)} taxonomy topics\n", flush=True)

    per_lane = {}
    for lane in LANES:
        # C: coordinated peak>=15 phrases per topic, per peak_party (member_index — fast)
        C = defaultdict(lambda: defaultdict(int))
        peaks = defaultdict(lambda: defaultdict(list))
        for row in H.iter_member_index(lane=lane):
            party = row.get("peak_party")
            if party not in ("D", "R"):
                continue
            low = row["ng"].lower()
            for tid in topics_in(low, topics):
                C[tid][party] += 1
                peaks[tid][party].append(row.get("peak", 0))
        # V: on-topic statement volume per topic, per party (corpus text scan — substring only)
        V = defaultdict(lambda: defaultdict(int))
        n = 0
        for r in H.iter_statements(congresses=None, with_text=True, lane=lane):
            party = r.get("party")
            if party not in ("D", "R") or not r.get("bioguide"):
                continue
            n += 1
            low = (r.get("text") or "").lower()
            for tid in topics_in(low, topics):
                V[tid][party] += 1
            if n % 100000 == 0:
                print(f"  [{lane}] scanned {n} statements", flush=True)
        # index
        rows = {}
        for tid in topics:
            for party in ("D", "R"):
                c, v = C[tid][party], V[tid][party]
                rows[f"{tid}.{party}"] = {
                    "topic": tid, "party": party, "coordinated_phrases": c, "on_topic_statements": v,
                    "script_proneness_index": round(1000 * c / v, 3) if v else None,
                    "median_peak": median(peaks[tid][party]) if peaks[tid][party] else None,
                }
        per_lane[lane] = rows
        # report: rank topics by index within each party
        for party in ("D", "R"):
            ranked = sorted((r for r in rows.values() if r["party"] == party and r["on_topic_statements"] >= 200),
                            key=lambda r: -(r["script_proneness_index"] or 0))
            print(f"  === {lane} / {party} — top script-prone topics (index = coord phrases / 1k on-topic stmts) ===")
            for r in ranked[:8]:
                print(f"    {r['topic']:22s} index={r['script_proneness_index']:.2f} "
                      f"(C={r['coordinated_phrases']}, V={r['on_topic_statements']}, med_peak={r['median_peak']})")
            print(flush=True)

    payload = {"generated_at": util.now_utc_iso(),
               "method": "descriptive; index = 1000*C/V (coordinated peak>=15 phrase-types per 1k on-topic "
                         "statements); seed-substring tagging (proxy, lower bound); interpreted "
                         "comparatively across topics only; chambers mixed (topic-level), lanes isolated.",
               "floors": {"report_topic_if_V>=": 200},
               "per_lane": per_lane}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(RESULT, payload)
    EVID.mkdir(parents=True, exist_ok=True)
    util.write_json(EVID / "hx_2_topic_scriptproneness.result.json", payload)
    print(f"wrote {RESULT}\nwrote {EVID / 'hx_2_topic_scriptproneness.result.json'}")


if __name__ == "__main__":
    main()
