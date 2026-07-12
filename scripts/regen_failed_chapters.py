"""Recover the chapters that failed the deterministic verifier (invented digits / quoted
non-fragments) by regenerating ONLY those with the hardened P4 v1.1 prompt.

Self-contained, hang-proof (claude -p, no tools -> no permission prompts), subscription only —
never touches ANTHROPIC_API_KEY. A regenerated chapter is accepted ONLY if it now passes the
identical deterministic gate, so this can never make the corpus worse; stubborn ones keep their
prior (failed) text and stay failed. Then finalize_chapters rewrites every chapter + index.json
consistently.

  python scripts/regen_failed_chapters.py
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import chapters, config, llm, util  # noqa: E402

CLAUDE = r"C:\Users\bobdo\.local\bin\claude.exe"
CONCURRENCY = 12
ROUNDS = 3


def build_prompt(inp: dict) -> str:
    sysrules = llm.load_prompt("P4")["system"].replace("{party}", inp["party"]).replace("{label}", inp["label"])
    return (f"{sysrules}\n\nERA: {inp['label']} · PARTY: {inp['party']}\n"
            f"STATS (the ONLY numbers you may use, verbatim): {json.dumps(inp['stats'])}\n"
            f"PHRASES (the ONLY words you may quote, <=10 words each, copied exactly): {json.dumps(inp['fragments'])}\n\n"
            f"Write the era chapter now. Output ONLY the chapter text — no preamble, no title, no markdown.")


def generate_one(inp: dict) -> tuple[str, str | None]:
    prompt = build_prompt(inp)
    for attempt in range(3):
        try:
            r = subprocess.run([CLAUDE, "-p", prompt], capture_output=True, text=True,
                               timeout=240, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
            out = (r.stdout or "").strip()
            if out and r.returncode == 0:
                return inp["id"], out
        except Exception as e:
            print(f"[regen] {inp['id']} attempt {attempt+1} failed: {e}", flush=True)
        time.sleep(3 * (attempt + 1))
    return inp["id"], None


def main() -> int:
    inputs = util.read_json(config.DERIVED / "chapter_inputs.json", [])
    by_id = {i["id"]: i for i in inputs}
    generated = util.read_json(config.DERIVED / "generated_chapters.json", {})
    index = util.read_json(chapters.CHAPTERS_DIR / "index.json", {})
    failed_ids = [r["id"] for r in index.get("report", []) if r.get("status") == "verify_failed"]
    print(f"[regen] {len(failed_ids)} failed chapters to recover with P4 "
          f"{llm.load_prompt('P4')['version']}", flush=True)

    still = failed_ids
    for rnd in range(1, ROUNDS + 1):
        if not still:
            break
        print(f"[regen] round {rnd}: {len(still)} chapters", flush=True)
        todo = [by_id[c] for c in still if c in by_id]
        new_still: list[str] = []
        recovered = 0
        with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            for cid, text in ex.map(generate_one, todo):
                inp = by_id[cid]
                if text and chapters.verify_chapter(inp, text)["passed"]:
                    generated[cid] = text   # accept only a VERIFYING replacement
                    recovered += 1
                else:
                    new_still.append(cid)   # keep prior text; remains failed
        still = new_still
        print(f"[regen] round {rnd}: recovered {recovered}, {len(still)} still failing", flush=True)
        util.write_json(config.DERIVED / "generated_chapters.json", generated)

    summary = chapters.finalize_chapters(inputs, generated)
    print(f"[regen] FINAL: {summary['published']} published, {summary['stubbed']} stubs, "
          f"{summary['failed']} failed (was {index.get('failed','?')})", flush=True)

    root = str(config.REPO_ROOT)
    try:
        subprocess.run(["git", "-C", root, "add", "data/derived", "pipeline/llm.py",
                        "pipeline/prompts/P4_era_chapter.v1.1.txt"], check=False)
        subprocess.run(["git", "-C", root, "commit", "-q", "-m",
                        f"data(alexandria): recover failed chapters via P4 v1.1 -> "
                        f"{summary['published']} published, {summary['failed']} failed"], check=False)
        p = subprocess.run(["git", "-C", root, "push", "origin", "main"], check=False, timeout=180)
        print(f"[regen] push rc={p.returncode}", flush=True)
    except Exception as e:
        print(f"[regen] commit/push best-effort failed: {e}", flush=True)
    print("[regen] DONE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
