"""Time the ledger-build stage over a fixed corpus snapshot, and report its denominators.

Collect wall time grew from ~60m to ~100m+ and hit the 120m workflow ceiling on 2026-07-28/29.
The growth was invisible because the stage published no cost of its own; P1 fixed the reporting
and this script makes the number reproducible outside a workflow run, so a change to the phrase
engine or the privacy scan can be measured before it ships rather than after it pages.

The default window is the PRODUCTION window: the daily collect calls
fetch.pull_range(config.STAGE1_EPOCH, today), so the runner's mirror holds the epoch months and
nothing earlier. Measuring the whole local 25-year mirror would report a number the daily run
never pays.

Writes nothing to data/derived and nothing to the ledger. The only file it can touch is the
clean-scan cache under data/state, and --no-cache suppresses even that.

  <interpreter> scripts/measure_ledger_build.py                    # epoch window, cache as configured
  <interpreter> scripts/measure_ledger_build.py --no-cache         # force a full rescan every text
  <interpreter> scripts/measure_ledger_build.py --months 2026-06 2026-07
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import config, normalize, privacy, roster, util  # noqa: E402
from pipeline.phrases import PhraseEngine  # noqa: E402


def _epoch_months() -> list[str]:
    return [f"{year:04d}-{month:02d}"
            for year, month in util.daterange_months(config.STAGE1_EPOCH, date.today().isoformat())]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", nargs="*", default=None,
                        help="explicit YYYY-MM month files; defaults to the epoch window")
    parser.add_argument("--no-cache", action="store_true",
                        help="disable the clean-statement scan cache for this measurement")
    parser.add_argument("--label", default="", help="free-text label echoed into the output")
    args = parser.parse_args(argv)

    months = args.months or _epoch_months()
    privacy.load()
    rmap = roster.load()

    records = []
    missing = []
    with util.stage_timer("mirror_read"):
        for month in months:
            path = config.RAW / "congress-press" / f"{month}.jsonl"
            if not path.exists():
                missing.append(month)
                continue
            records.extend(util.iter_jsonl(path))

    print(f"label:          {args.label or '(none)'}")
    print(f"months:         {len(months) - len(missing)} present "
          f"({months[0]}..{months[-1]}), {len(missing)} missing")
    print(f"records:        {len(records):,}")

    with util.stage_timer("normalize"):
        statements = normalize.normalize_records(records, run_id="measure", roster=rmap)

    eligible = [s for s in statements
                if s.get("lane") == 1 and not s.get("syndicated")
                and (s.get("member") or {}).get("party") in config.ALL_PARTIES]
    chars = sum(len(s.get("text", "")) for s in eligible)
    print(f"statements:     {len(statements):,}")
    print(f"lane-1 units:   {len(eligible):,}   (the ledger-build denominator)")
    print(f"lane-1 chars:   {chars:,}")

    cache_state = "disabled for this measurement"
    if not args.no_cache:
        try:
            cache_state = privacy.activate_scan_cache()
        except AttributeError:
            cache_state = "absent (pre-P2 tree)"
    print(f"scan cache:     {cache_state}")

    engine = PhraseEngine()
    privacy.reset_span_stats()

    def _detail() -> str:
        stats = privacy.span_stats()
        return (f"span_scan_s={stats['person_spans_s']:.1f} "
                f"span_scan_calls={int(stats['person_spans_calls'])} "
                f"admitted_form_s={stats['admitted_form_s']:.1f} "
                f"admitted_form_scans={int(stats['admitted_form_scans'])}")

    with util.stage_timer("ledger_build", detail_fn=_detail):
        ledger = engine.build(statements, progress=len(statements) > 100_000)

    if not args.no_cache:
        from pipeline import scan_cache
        print(f"cache flush:    {privacy.flush_scan_cache()}")
        print(f"cache stats:    {scan_cache.stats()}")

    timings = util.stage_timings()
    print(f"\nledger phrases: {len(ledger):,}")
    print(f"stage timings:  {timings}")
    span = privacy.span_stats()
    build_s = timings.get("ledger_build", 0.0) or 1e-9
    print(f"span-scan share of ledger_build: "
          f"{100.0 * span['person_spans_s'] / build_s:.1f}%")
    print(f"per-unit ledger cost: "
          f"{1000.0 * build_s / max(1, len(eligible)):.1f} ms/lane-1 unit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
