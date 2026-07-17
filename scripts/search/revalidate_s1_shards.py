"""The eleven BLOCKED-ON-SHARDS S1 re-validations, WITHIN one provenance lane (docs/18 §5).

Session 18 refused to run these on the lane-blind alexandria shards. With per-lane shards built
(scripts/search/build_lane_shards.py), each hypothesis now reads a lane-isolated substrate and splits
on that lane's within-lane halves:
    propublica  congresses 113-116  year-halves 2013-16 / 2017-20  congress-halves {113,114}/{115,116}
    scraped     congresses 117-119  year-halves 2021-23 / 2024-26  congress-halves {117}/{118,119}

LANE-EDGE RULE (docs/18 §5): the propublica lane ENDS at 2021-01-03, so its burst-lifespan cutoff is
the lane edge, not the 2026-07-09 corpus edge — a burst alive at lane-end is right-censored, exactly
as at the corpus cutoff, or its truncated span reads as a false short lifespan.

PRE-REGISTERED FLOORS (L4, numerals, before measurement — these are the hypotheses' own gates, now
applied per-lane): S1.1/S1.1'/S1.3/S1.3' min_cell=8 phrases/year & >=2 powered years/half; S1.2/S1.8
>=2 years/half; S1.5 >=30 ignitions/half; S1.6 >=2 cycles/half/party; S1.7 >=200 Aug statements/half;
S1.11 >=30 phrases/half. A half that cannot meet its floor within the lane is honestly UNDERPOWERED —
that is the cost of isolation, not a failure.

Re-runnable (after the shards exist):  python scripts/search/revalidate_s1_shards.py [propublica|scraped]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import config
from pipeline.search import harness as H
from pipeline.search import wave_s1 as S1

LANE_CUTOFF = {"propublica": "2021-01-03", "scraped": "2026-07-09"}   # docs/18 §5 lane edge
CACHE = config.DERIVED / "search"


def build_caches(lane):
    congs = S1.LANE_CONGRESSES[lane]
    print(f"  [caches] {lane} congresses {list(congs)}", flush=True)
    H.build_phrase_index(congresses=congs, lane=lane, progress=False)
    H.build_member_index(congresses=congs, lane=lane, progress=False)
    H.build_daily_series(lane=lane, congresses=congs, progress=False)
    H.build_cross_party_daily(lane=lane, congresses=congs, progress=False)
    H.build_statement_meta(congresses=congs, lane=lane, progress=False)


def run_lane(lane, elections):
    yh = S1.year_halves_for(lane)
    ch = S1.congress_halves_for(lane)
    congs = S1.LANE_CONGRESSES[lane]
    rows = list(H.iter_phrase_index(lane=lane))
    series_rows = list(H.iter_daily_series(lane=lane))
    member_rows = list(H.iter_member_index(lane=lane))
    meta = json.loads((CACHE / f"stmt_meta.summary.{lane}.json").read_text(encoding="utf-8"))
    active_by_year = meta["active_members_by_year"]
    weekday_baseline = meta["weekday_baseline"]
    monthly = S1.monthly_statement_counts(lane=lane)
    xparty = json.loads((CACHE / f"cross_party_daily.{lane}.json").read_text(encoding="utf-8"))["by_day"]
    disc = H.load_discipline_index(congresses=congs, lane=lane)
    state_of = H.bioguide_states()   # pooled identity map (docs/18 §4)

    out = []
    out.append(S1.s1_1_ignition_width(rows, lane=lane, halves=yh))
    out.append(S1.s1_3_lifespan(rows, lane=lane, halves=yh))
    out.append(S1.s1_1_prime_ignition(series_rows, lane=lane, halves=yh))
    out.append(S1.s1_3_prime_lifespan(series_rows, lane=lane, halves=yh, cutoff=LANE_CUTOFF[lane]))
    out.append(S1.s1_2_sync_ceiling(rows, active_by_year, lane=lane, halves=yh))
    out.append(S1.s1_5_weekend_memo(rows, weekday_baseline, lane=lane, halves=yh))
    out.append(S1.s1_6_ninety_day_snap(disc, elections, lane=lane, halves=yh))
    out.append(S1.s1_7_august_effect(rows, monthly, lane=lane, halves=yh))
    out.append(S1.s1_8_sotu(xparty, lane=lane, halves=yh))
    out.append(S1.s1_11_delegation_echo(member_rows, state_of, lane=lane, chalves=ch))
    out.append(S1.s1_4_proper(congresses=congs, lane=lane, chalves=ch))
    return out


def main():
    lanes = [a for a in sys.argv[1:] if a in ("propublica", "scraped")] or ["scraped", "propublica"]
    elections = json.loads((config.REFERENCE / "search" / "elections.json").read_text(encoding="utf-8"))["general"]
    result = {}
    for lane in lanes:
        # only run a lane whose shards exist
        from pipeline import alexandria as A
        need = list(S1.LANE_CONGRESSES[lane])
        missing = [c for c in need if not A.lane_shard_path("shard", c, lane).exists()]
        if missing:
            print(f"[skip] {lane}: shards not built yet for congresses {missing}", flush=True)
            continue
        print(f"\n================= {lane} =================", flush=True)
        build_caches(lane)
        res = run_lane(lane, elections)
        result[lane] = res
        for r in res:
            print(f"  {r['id']:7} {r['name']:38} {r['verdict']}", flush=True)
    dest = CACHE / "revalidate_s1_shards.json"
    dest.write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    print(f"\nwrote {dest}", flush=True)
    return result


if __name__ == "__main__":
    main()
