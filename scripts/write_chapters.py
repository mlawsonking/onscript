"""Post-generation step: take the workflow's generated chapters, run the deterministic verifier,
and write the verified chapters (+ code stubs for thin eras) to data/derived/chapters/.

  python scripts/write_chapters.py
Reads:  data/derived/chapter_inputs.json         (the grounded inputs)
        data/derived/generated_chapters.json     (id -> chapter text, from the agentic workflow)
Writes: data/derived/chapters/<id>.json + index.json
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import chapters, config, util  # noqa: E402

inputs = util.read_json(config.DERIVED / "chapter_inputs.json", [])
generated = util.read_json(config.DERIVED / "generated_chapters.json", {})
summary = chapters.finalize_chapters(inputs, generated)
print(f"chapters written: {summary['published']} published, {summary['stubbed']} stubs, "
      f"{summary['failed']} failed/missing (of {len(inputs)} inputs)")
fails = [r for r in summary["report"] if r["status"] not in ("published",)]
if fails:
    print("non-published:", fails[:20])
