"""Regenerate deterministic derived JSON for a focus day from saved state (statements + ledger
+ discipline), without re-running the ~30-min engine. Useful to render any archived day.

  python scripts/regen_derived.py 2026-06-30
  python scripts/regen_derived.py 2026-06-30 --force   # rebuild a PUBLISHED day's day JSON

A PUBLISHED day is immutable by default (docs/23 §7.5 R-C): this script writes days/{day}.json with
`daily_lines: None`, so running it on a published day is the clobber defect in manual form — it would
delete that day's composites. Without --force the day JSON is skipped (everything else still
regenerates). Prefer the real repair path, which restores rather than blanks:

  python -m pipeline.run_assemble --day 2026-06-30
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import build, config, util  # noqa: E402

argv = [a for a in sys.argv[1:] if a != "--force"]
force = "--force" in sys.argv[1:]
day = argv[0] if argv else util.product_day()
if force and util.day_is_final(day):
    print(f"[--force] {day} is PUBLISHED — overwriting its day JSON with a composite-less summary. "
          f"To RESTORE composites instead, use: python -m pipeline.run_assemble --day {day}")
statements = list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
ledger = util.read_json(config.STATE / "ledger.json", {})
discipline = util.read_json(config.DERIVED / "discipline.json", {})
summary = build.build_derived(statements, ledger, discipline, config.DERIVED, focus_day=day,
                              allow_final_overwrite=force)
print(f"regenerated derived for {day}: {summary}")
