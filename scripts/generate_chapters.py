"""Fully self-contained, hang-proof Alexandria chapter generation (§1.3 subscription policy).

Runs as ONE background process — NO Workflow tool, NO re-invocation, NO permission prompts:
  1. wait for the finalizer's sentinel (chapter_inputs.json ready)
  2. generate each sufficient era/monthly chapter via `claude -p` (subscription CLI, headless,
     no tools -> no prompts), 12 in parallel (the safe concurrency), with retries
  3. run the deterministic verifier + write data/derived/chapters/ (thin eras -> code stubs)
  4. git commit + push (best-effort)

Never touches ANTHROPIC_API_KEY (that's the metered API; this is the subscription CLI).
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import shutil
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

CONCURRENCY = 12          # the safe level (30 overshoots per Michael); batches never exceed this
RETRIES = 3
SENTINEL = config.DERIVED / "manifest" / "finalize-done.json"


def claude_cli() -> str:
    """The subscription CLI binary. Set ONSCRIPT_CLAUDE_BIN when it is not on PATH.

    Resolved rather than hardcoded: the install location differs per machine, and docs/37 rule 16
    keeps operator machine identifiers out of the committed tree.
    """
    return os.environ.get("ONSCRIPT_CLAUDE_BIN") or shutil.which("claude") or "claude"


def build_prompt(inp: dict) -> str:
    sysrules = llm.load_prompt("P4")["system"].replace("{party}", inp["party"]).replace("{label}", inp["label"])
    import json
    return (f"{sysrules}\n\nERA: {inp['label']} · PARTY: {inp['party']}\n"
            f"STATS (the ONLY numbers you may use, verbatim): {json.dumps(inp['stats'])}\n"
            f"PHRASES (the ONLY words you may quote, <=10 words each, copied exactly): {json.dumps(inp['fragments'])}\n\n"
            f"Write the era chapter now. Output ONLY the chapter text — no preamble, no title, no markdown.")


def generate_one(inp: dict) -> tuple[str, str | None]:
    prompt = build_prompt(inp)
    for attempt in range(RETRIES):
        try:
            r = subprocess.run([claude_cli(), "-p", prompt], capture_output=True, text=True,
                               timeout=240, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
            out = (r.stdout or "").strip()
            if out and r.returncode == 0:
                return inp["id"], out
        except Exception as e:
            print(f"[gen] {inp['id']} attempt {attempt+1} failed: {e}", flush=True)
        time.sleep(3 * (attempt + 1))  # backoff on rate limits
    return inp["id"], None


def main() -> int:
    # 1. wait for the finalizer to produce chapter inputs
    waited = 0
    while not SENTINEL.exists() and waited < 6 * 60 * 60:
        print(f"[gen] waiting for finalizer sentinel … ({waited//60}m)", flush=True)
        time.sleep(30)
        waited += 30
    inputs = util.read_json(config.DERIVED / "chapter_inputs.json", [])
    todo = [i for i in inputs if i.get("sufficient")]
    print(f"[gen] {len(inputs)} inputs, {len(todo)} to generate (rest -> code stubs), "
          f"{CONCURRENCY} in parallel via claude -p", flush=True)

    # 2. generate, bounded to CONCURRENCY at a time
    generated: dict[str, str] = {}
    remaining = list(todo)
    for rnd in range(1, 4):  # up to 3 rounds to sweep up rate-limit failures
        if not remaining:
            break
        print(f"[gen] round {rnd}: {len(remaining)} chapters", flush=True)
        with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            for cid, text in ex.map(generate_one, remaining):
                if text:
                    generated[cid] = text
        done_ids = set(generated)
        remaining = [i for i in remaining if i["id"] not in done_ids]
        print(f"[gen] round {rnd} done: {len(generated)}/{len(todo)} generated, {len(remaining)} still missing", flush=True)
        util.write_json(config.DERIVED / "generated_chapters.json", generated)

    # 3. verify + write chapters (stubs for thin eras)
    summary = chapters.finalize_chapters(inputs, generated)
    print(f"[gen] chapters: {summary['published']} published, {summary['stubbed']} stubs, "
          f"{summary['failed']} failed", flush=True)

    # 4. commit + push (best-effort; never fatal)
    root = str(config.REPO_ROOT)
    try:
        # derived is the committed artifact (chapters, coverage, discipline, phrase pages);
        # the big ledger lives in gitignored state on X:, so it is excluded automatically.
        subprocess.run(["git", "-C", root, "add", "data/derived"], check=False)
        subprocess.run(["git", "-C", root, "commit", "-q", "-m",
                        f"data(alexandria): 25-year ledger + {summary['published']} verified era/monthly chapters"],
                       check=False)
        subprocess.run(["git", "-C", root, "push", "origin", "main"], check=False, timeout=180)
        print("[gen] committed + pushed", flush=True)
    except Exception as e:
        print(f"[gen] commit/push best-effort failed (will push in the morning): {e}", flush=True)

    util.write_json(config.DERIVED / "manifest" / "chapters-done.json",
                    {"generated_at": util.now_utc_iso(), **{k: summary[k] for k in ("published", "stubbed", "failed")}})
    print("[gen] DONE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
