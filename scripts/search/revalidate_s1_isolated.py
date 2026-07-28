"""E1: the eleven S1 re-validations on the R-S50.1 ISOLATED three-lane substrate (docs/18 §4).

Session 19 (docs/13, "Shard-lanes revalidation") ran the eleven within the two INSTRUMENT-FOLDED
lanes: `propublica` (== legacy) and `scraped` (== scraper + page_html folded together). R-S50.1
(Fable, Session 51, binding) demoted that fold to a labelled robustness view and rebuilt the primary
substrate as three ISOLATED source lanes, filtered on the raw `date_source`:

    legacy      == the propublica set EXACTLY (instrument propublica = {legacy}); shards are a
                   byte-for-byte copy of the propublica shards, so its caches and every verdict are
                   identical to the Session-19 propublica column. Running it is the identity check.
    scraper     == scraped minus page_html. This is the real isolation test: page_html is the most
                   party-skewed lane in the corpus (D:R 12.465 in half A), and the question E1 answers
                   is whether removing it moves any Session-19 scraped verdict.
    page_html   == the removed sliver, run standalone. It is tiny (454/794/1012 records for 117/118/119),
                   so no phrase reaches the peak>=15 coordination floor; its member index is empty and
                   every coordination hypothesis is UNDERPOWERED. That is the accurate cost of full
                   isolation and the empirical reason R-S50.1 isolates page_html rather than analysing
                   it as a comparative lane.

This driver reuses revalidate_s1_shards.run_lane (the SAME estimator, so the comparison is valid) but
adds the empty-substrate guard page_html needs, and writes an append-only evidence file plus the
folded-vs-isolated comparison that IS the finding. It never touches the Session-19 evidence file.

Freeze-before-measure: the lane definitions, halves, cutoffs, floors, and predicted verdicts are
registered in data/reference/search/e1-isolated-registration.json and committed BEFORE this runs.

Deterministic, $0, no Anthropic call. Reads the per-lane shards on X: (via the data/state junction);
writes only data/derived/search/revalidate_s1_isolated.json and the lane-suffixed intermediate caches
(the big .jsonl caches are gitignored). Pin the hash seed so verbatim/5-gram grouping is reproducible:

  PYTHONHASHSEED=0 python scripts/search/revalidate_s1_isolated.py
  PYTHONHASHSEED=0 python scripts/search/revalidate_s1_isolated.py legacy scraper
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria as A, config
from pipeline.search import harness as H
from pipeline.search import wave_s1 as S1
import revalidate_s1_shards as R  # sibling module; the shared reader (run_lane) and LANE_CUTOFF

CACHE = config.DERIVED / "search"
ISOLATED_LANES = ("legacy", "scraper", "page_html")
FOLDED_OF = {"legacy": "propublica", "scraper": "scraped", "page_html": "scraped"}
# order matches revalidate_s1_shards.run_lane so the empty-substrate placeholder lines up
ELEVEN = ["S1.1", "S1.3", "S1.1'", "S1.3'", "S1.2", "S1.5", "S1.6", "S1.7", "S1.8", "S1.11", "S1.4"]


def build_guarded(lane):
    """Build the per-lane caches, but stop after phrase/member index if the member index is empty
    (page_html): build_daily_series RAISES on an empty member index, and an empty member index means
    no phrase reaches peak>=15, so every coordination hypothesis is UNDERPOWERED anyway."""
    congs = list(S1.LANE_CONGRESSES[lane])
    missing = [c for c in congs if not A.lane_shard_path("shard", c, lane).exists()]
    if missing:
        return {"error": f"per-lane shards missing for congresses {missing}"}
    H.build_phrase_index(congresses=congs, lane=lane, progress=False)
    H.build_member_index(congresses=congs, lane=lane, progress=False)
    n_phrase = sum(1 for _ in H.iter_phrase_index(lane=lane))
    n_member = sum(1 for _ in H.iter_member_index(lane=lane))
    info = {"congresses": congs, "phrase_index_rows": n_phrase, "member_index_rows": n_member}
    if n_member == 0:
        info["empty_member_index"] = True
        return info
    H.build_daily_series(lane=lane, congresses=congs, progress=False)
    H.build_cross_party_daily(lane=lane, congresses=congs, progress=False)
    H.build_statement_meta(congresses=congs, lane=lane, progress=False)
    info["empty_member_index"] = False
    return info


def run_isolated(lane, elections):
    info = build_guarded(lane)
    if info.get("error"):
        return {"substrate": info, "verdicts": None}
    if info.get("empty_member_index"):
        verdicts = [{"id": i, "verdict": "UNDERPOWERED",
                     "reason": "empty member index: no phrase reaches the peak>=15 coordination floor "
                               "in this isolated lane (substrate too sparse)"} for i in ELEVEN]
        return {"substrate": info, "verdicts": verdicts}
    return {"substrate": info, "verdicts": R.run_lane(lane, elections)}


def verdict_map(rows):
    return {r["id"]: r["verdict"] for r in (rows or [])}


def main():
    want = [a for a in sys.argv[1:] if a in ISOLATED_LANES] or list(ISOLATED_LANES)
    elections = json.loads((config.REFERENCE / "search" / "elections.json").read_text(encoding="utf-8"))["general"]

    # Session-19 folded verdicts (append-only source; never modified here)
    folded_path = CACHE / "revalidate_s1_shards.json"
    folded = json.loads(folded_path.read_text(encoding="utf-8")) if folded_path.exists() else {}
    folded_v = {ln: verdict_map(folded.get(ln)) for ln in ("propublica", "scraped")}

    result = {"generated_by": "scripts/search/revalidate_s1_isolated.py",
              "registration": "data/reference/search/e1-isolated-registration.json",
              "substrate": "R-S50.1 isolated 3-lane (legacy/scraper/page_html)",
              "supersedes": "data/derived/search/revalidate_s1_shards.json (Session 19, folded 2-lane)",
              "lanes": {}, "comparison": {}}

    for lane in want:
        print(f"\n================= {lane} (isolated) =================", flush=True)
        res = run_isolated(lane, elections)
        result["lanes"][lane] = res
        iso_v = verdict_map(res["verdicts"])
        fold = folded_v.get(FOLDED_OF[lane], {})
        cmp = []
        for i in ELEVEN:
            f, o = fold.get(i), iso_v.get(i)
            cmp.append({"id": i, "folded": f, "isolated": o, "changed": bool(f and o and f != o)})
        result["comparison"][f"{lane}_vs_{FOLDED_OF[lane]}"] = cmp
        for r in (res["verdicts"] or []):
            print(f"  {r['id']:7} {r['verdict']}", flush=True)

    dest = CACHE / "revalidate_s1_isolated.json"
    dest.write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    print(f"\nwrote {dest}", flush=True)

    # summary of changes (the E1 finding)
    print("\n--- folded -> isolated verdict changes ---", flush=True)
    any_change = False
    for key, rows in result["comparison"].items():
        changed = [r for r in rows if r["changed"]]
        if changed:
            any_change = True
            for r in changed:
                print(f"  {key}: {r['id']} {r['folded']} -> {r['isolated']}", flush=True)
    if not any_change:
        print("  none: no isolated verdict differs from its Session-19 folded verdict", flush=True)
    return result


if __name__ == "__main__":
    main()
