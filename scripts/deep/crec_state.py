"""Authoritative CREC crawl coverage, counted from the statement files (docs/15 §D1).

`crawl-stats.json` is *run bookkeeping* and has been destroyed twice by the `crec.py:217` overwrite,
so it is not evidence. This recounts from `crec/state/E/statements-{year}.jsonl` — the artifacts the
shards are actually built from — and reports, per congress, whether every one of its years is present
and complete enough to build.

"Complete" is deliberately NOT inferred from the statement file (a half-crawled year looks like a small
year). It is read from the crawl manifest's `day-done:` markers against the year's published sitemap
day count, which is the only honest completeness signal available offline.

  $ python scripts/deep/crec_state.py                 # table to stdout
  $ python scripts/deep/crec_state.py --json out.json # machine-readable
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.deep import crec, lanes  # noqa: E402


def day_done_by_year(state: Path) -> dict[int, int]:
    """Days the crawl marked fully processed, per year, from the manifest."""
    out: dict[int, int] = defaultdict(int)
    man = state / "crawl-manifest.jsonl"
    if not man.exists():
        return out
    with open(man, encoding="utf-8") as f:
        for line in f:
            if '"day-done:CREC-' not in line:
                continue
            try:
                uid = json.loads(line)["id"]
            except Exception:
                continue                      # torn line from a hard-killed crawl
            out[int(uid[len("day-done:CREC-"):][:4])] += 1
    return dict(out)


def scan_years(state: Path) -> dict[int, dict]:
    """Per year: statements on disk, distinct dates, party split. Streamed — these files are ~25 MB."""
    years: dict[int, dict] = {}
    for p in sorted((state / "E").glob("statements-*.jsonl")):
        year = int(p.stem.split("-")[-1])
        dates, n, party = set(), 0, defaultdict(int)
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    s = json.loads(line)
                except Exception:
                    continue
                n += 1
                dates.add(s.get("published_at"))
                party[(s.get("member") or {}).get("party")] += 1
        years[year] = {"statements": n, "days_with_statements": len(dates),
                       "D": party.get("D", 0), "R": party.get("R", 0), "I": party.get("I", 0)}
    return years


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="out", default=None)
    ap.add_argument("--congresses", default="107-119")
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.congresses.split("-"))

    state = lanes.lane_state("crec")
    years = scan_years(state)
    done = day_done_by_year(state)

    rows = []
    for c in range(lo, hi + 1):
        ys = crec.congress_years(c)
        present = [y for y in ys if y in years]
        stmts = sum(years[y]["statements"] for y in present)
        rows.append({
            "congress": c, "years": ys,
            "years_present": present, "years_missing": [y for y in ys if y not in years],
            "statements": stmts,
            "days_done": {y: done.get(y, 0) for y in ys},
            "shard_built": (state / f"ledger-{c}.json").exists(),
            "buildable": len(present) == len(ys) and stmts > 0,
        })

    print(f"{'cong':>4}  {'years':<11} {'stmts':>7}  {'days-done':<13} {'shard':<6} status")
    for r in rows:
        dd = "/".join(str(r["days_done"][y]) for y in r["years"])
        status = ("BUILT" if r["shard_built"] else
                  "buildable" if r["buildable"] else
                  f"BLOCKED — no data for {r['years_missing']}")
        print(f"{r['congress']:>4}  {str(r['years'][0]) + '-' + str(r['years'][1]):<11} "
              f"{r['statements']:>7}  {dd:<13} {'yes' if r['shard_built'] else 'no':<6} {status}")

    print(f"\nper-year detail ({len(years)} years on disk):")
    for y in sorted(years):
        v = years[y]
        print(f"  {y}: {v['statements']:>6} stmts  {v['days_with_statements']:>3} days  "
              f"D={v['D']:<6} R={v['R']:<6} I={v['I']:<3} manifest-days-done={done.get(y, 0)}")

    if args.out:
        Path(args.out).write_text(json.dumps({"years": years, "congresses": rows,
                                              "days_done_by_year": done}, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
