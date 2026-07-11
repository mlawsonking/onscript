"""Regenerate deterministic derived JSON for a focus day from saved state (statements + ledger
+ discipline), without re-running the ~30-min engine. Useful to render any archived day.

  python scripts/regen_derived.py 2026-06-30
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import build, config, util  # noqa: E402

day = sys.argv[1] if len(sys.argv) > 1 else util.product_day()
statements = list(util.iter_jsonl(config.STATE / "statements.jsonl.gz"))
ledger = util.read_json(config.STATE / "ledger.json", {})
discipline = util.read_json(config.DERIVED / "discipline.json", {})
summary = build.build_derived(statements, ledger, discipline, config.DERIVED, focus_day=day)
print(f"regenerated derived for {day}: {summary}")
