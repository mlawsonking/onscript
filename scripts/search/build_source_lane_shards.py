"""Rebuild the per-Congress alexandria shards on the ISOLATED THREE-valued lane domain (R-S50.1).

docs/18 §2 built two lanes: `propublica` (== legacy) and `scraped` (== scraper + page_html FOLDED).
R-S50.1 (Fable, Session 51, binding) demotes that fold to a labelled robustness view and makes the
primary substrate three ISOLATED lanes keyed on the raw `date_source`:

    legacy      (== the existing propublica set, EXACTLY: instrument propublica = {legacy})
    scraper     (the office scraper, page_html EXCLUDED)
    page_html   (scraper-collected, date-parsed from the page body; the most party-skewed lane,
                 D:R 12.465 in half A - folding it is the confound the lane program removes)

Build economy, so the rebuild is a background job not a multi-hour recompute of data we already have:
  * legacy is byte-for-byte the propublica shard (identical record set) -> we COPY, never rebuild, and
    patch the summary's lane field. 118/119 have no legacy (the import dies 2021-01-03) -> empty shard.
  * page_html is tiny (2,839 records across 2014-12..2026) -> a fast fresh build for every congress.
  * scraper is the real rebuild (scraped minus page_html). Post-seam 117-119 are the PRIMARY lane and
    build first; 113-116 are the "2013-2020 scraped tail" (supplementary, never pooled, docs/18 §2) and
    build last.

Resumable: a (congress, lane) whose shard summary already exists is skipped unless --force. Pin the
hash seed for reproducible ledger key order (analysis is order-invariant regardless):

  PYTHONHASHSEED=0 python scripts/search/build_source_lane_shards.py
  PYTHONHASHSEED=0 python scripts/search/build_source_lane_shards.py --only 117,118,119
  PYTHONHASHSEED=0 python scripts/search/build_source_lane_shards.py --force 115
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import alexandria as A, util  # noqa: E402

KINDS = ("ledger", "discipline", "coverage", "shard")
LEGACY_FROM_PROPUBLICA = (113, 114, 115, 116, 117)   # propublica shards exist -> copy to legacy
LEGACY_EMPTY = (118, 119)                             # post-seam: legacy is empty by construction
# page_html first (fast, every congress), then the PRIMARY post-seam scraper, then the supplementary tail
PAGE_HTML = (113, 114, 115, 116, 117, 118, 119)
SCRAPER_PRIMARY = (117, 118, 119)
SCRAPER_TAIL = (113, 114, 115, 116)


def copy_legacy_from_propublica(n: int, force: bool) -> None:
    dst = A.lane_shard_path("shard", n, "legacy")
    if dst.exists() and not force:
        print(f"[skip] legacy congress {n} (copied shard exists)", flush=True)
        return
    src_shard = A.lane_shard_path("shard", n, "propublica")
    if not src_shard.exists():
        print(f"[warn] legacy congress {n}: no propublica shard to copy -> building fresh", flush=True)
        A.run_shard(n, lane="legacy")
        return
    t = time.time()
    for kind in KINDS:
        s = A.lane_shard_path(kind, n, "propublica")
        d = A.lane_shard_path(kind, n, "legacy")
        if s.exists():
            shutil.copy2(s, d)
    # the copied summary still says lane=propublica; stamp it legacy (records count is identical)
    summ = util.read_json(dst, {}) or {}
    summ["lane"] = "legacy"
    summ["derived_from"] = "propublica shard (identical record set; instrument propublica = {legacy})"
    util.write_json(dst, summ)
    print(f"[copy] legacy congress {n} <- propublica: records={summ.get('records')} ({time.time()-t:.0f}s)",
          flush=True)


def build(n: int, lane: str, force: bool) -> None:
    summ = A.lane_shard_path("shard", n, lane)
    if summ.exists() and not force:
        print(f"[skip] {lane} congress {n} (shard summary exists)", flush=True)
        return
    t = time.time()
    print(f"[build] {lane} congress {n} …", flush=True)
    res = A.run_shard(n, lane=lane)
    print(f"[build] {lane} congress {n}: records={res.get('records')} statements={res.get('statements')} "
          f"ledger={res.get('ledger')} ({time.time()-t:.0f}s)", flush=True)


def main() -> int:
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    force_only = {int(a) for a in sys.argv[1:] if a.isdigit()} if force else set()

    def want(n: int) -> bool:
        return (only is None or n in only) and (not force_only or n in force_only)

    t0 = time.time()
    # 1. page_html: isolated, fast, every congress
    for n in PAGE_HTML:
        if want(n):
            build(n, "page_html", force)
    # 2. scraper: primary post-seam first, then the supplementary 2013-2020 tail
    for n in SCRAPER_PRIMARY + SCRAPER_TAIL:
        if want(n):
            build(n, "scraper", force)
    # 3. legacy: copy from propublica (identical set) where it exists; empty post-seam
    for n in LEGACY_FROM_PROPUBLICA:
        if want(n):
            copy_legacy_from_propublica(n, force)
    for n in LEGACY_EMPTY:
        if want(n):
            build(n, "legacy", force)

    # reconcile: the isolated triple must partition the combined set EXACTLY (R-S50.1)
    print("\n[reconcile] source-lane partition (legacy + scraper + page_html == combined)", flush=True)
    for n in range(113, 120):
        if only is not None and n not in only:
            continue
        r = A.reconcile_source_lanes(n)["records"]
        flag = "" if r["exact_partition"] else "  <<< STOP-AND-DIAGNOSE"
        print(f"  c{n}: legacy {r['legacy']} + scraper {r['scraper']} + page_html {r['page_html']} "
              f"= {r['sum_lanes']} vs combined {r['combined']} (delta {r['delta']}, "
              f"exact={r['exact_partition']}){flag}", flush=True)
    print(f"\n[done] {time.time()-t0:.0f}s total", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
