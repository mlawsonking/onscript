"""Resumable CREC Extensions crawl driver (docs/15 §D1.a) — tracked, not scratchpad.

Prior sessions ran this from `scratchpad/`, which is gitignored, so the driver vanished on every
re-clone and each session hand-rolled it again (the Session-18 "untracked evidence" lesson). This is
the tracked one.

  $ python scripts/deep/crawl_crec.py --years 2009,2010,2011,2012,2022,2023,2024,2025,2026

Properties it guarantees, all of which a hand-rolled driver has gotten wrong at least once here:

* **One writer.** A PID-checked lock at `crec/state/CRAWL-RUNNING.lock`. A lock whose PID is dead is
  reported and rotated aside (`.stale-<pid>.bak`), never silently stolen — the operator sees it.
* **The `crec.py:217` trap is neutralized without touching `crec.py`.** `crawl_extensions()` ends by
  *overwriting* `crawl-stats.json` with only the current run's counters, so every prior run's record is
  destroyed on each resume (this already happened: the live file holds 2003-2008 only, and the whole
  2013-2021 campaign's stats were never written at all because the process died before that line).
  We snapshot the file before the run, write the run's own counters to a dated `crawl-run-*.json`, and
  restore a merged `crawl-stats.json` after. Run bookkeeping is advisory anyway — `crec_state.py`
  recounts coverage from the statement files, which is the ground truth.
* **Resumability is the crawl's, not ours.** `crawl-manifest.jsonl` day-done markers make a resume
  O(new days); we add nothing and assume nothing about where the last run stopped.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.deep import crec, lanes  # noqa: E402

STILL_ACTIVE = 259


def pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def take_lock(state: Path, years: list[int], owner: str, *, force: bool) -> Path:
    lock = state / "CRAWL-RUNNING.lock"
    if lock.exists():
        try:
            held = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            held = {}
        pid = held.get("pid")
        if isinstance(pid, int) and pid_alive(pid) and not force:
            raise SystemExit(f"a crawl is ALREADY RUNNING (pid {pid}, owner {held.get('owner')!r}) — "
                             f"refusing to start a second writer. Kill it or pass --force.")
        bak = state / f"CRAWL-RUNNING.lock.stale-{pid}.bak"
        lock.replace(bak)
        print(f"[lock] stale lock rotated aside -> {bak.name} (pid {pid} not running)", flush=True)
    lock.write_text(json.dumps({
        "pid": os.getpid(),
        "started": datetime.now(timezone.utc).isoformat(),
        "years": years,
        "owner": owner,
    }, indent=1), encoding="utf-8")
    return lock


def merge_stats(prior: dict, run: dict) -> dict:
    """Additive merge. Every granule is manifest-recorded once and never re-counted, so summing runs is
    exactly the cumulative fetch record; a resumed year contributes 0 and leaves the prior total."""
    out = {k: prior.get(k, 0) + run.get(k, 0) for k in ("days", "granules", "attributed", "unattributed")}
    by_year = {str(y): dict(v) for y, v in (prior.get("by_year") or {}).items()}
    for y, v in (run.get("by_year") or {}).items():
        cur = by_year.setdefault(str(y), {"days": 0, "granules": 0, "attributed": 0, "unattributed": 0})
        for k in ("days", "granules", "attributed", "unattributed"):
            cur[k] = cur.get(k, 0) + v.get(k, 0)
    out["by_year"] = dict(sorted(by_year.items()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Resumable CREC Extensions crawl (keyless GovInfo, $0).")
    ap.add_argument("--years", required=True, help="comma-separated, crawled in the order given")
    ap.add_argument("--owner", default="opus deep-archive session")
    ap.add_argument("--limit-days", type=int, default=None, help="smoke-test cap per year")
    ap.add_argument("--force", action="store_true", help="take the lock even if a live crawl holds it")
    args = ap.parse_args()

    years = [int(y) for y in args.years.split(",") if y.strip()]
    state = lanes.lane_state("crec")
    state.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = state / "crawl-2009-2026.log"

    def say(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%SZ')}] {msg}"
        print(line, flush=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    lock = take_lock(state, years, args.owner, force=args.force)
    stats_path = state / "crawl-stats.json"
    prior = {}
    if stats_path.exists():
        prior = json.loads(stats_path.read_text(encoding="utf-8"))
        snap = state / f"crawl-stats.pre-{stamp}.snapshot.json"
        snap.write_text(json.dumps(prior, indent=1), encoding="utf-8")
        say(f"snapshotted prior stats -> {snap.name} (days={prior.get('days')} granules={prior.get('granules')})")

    say(f"CREC crawl START — years {years} · owner={args.owner!r} · pid={os.getpid()}")
    say("keyless govinfo.gov · polite interval · resumable · $0 · zero Anthropic usage")
    t0 = time.time()
    try:
        run = crec.crawl_extensions(years, limit_days=args.limit_days, progress=True)
        (state / f"crawl-run-{stamp}.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
        stats_path.write_text(json.dumps(merge_stats(prior, run), indent=1), encoding="utf-8")
        say(f"CREC crawl DONE in {(time.time() - t0) / 3600:.2f}h — run={run.get('days')} days, "
            f"{run.get('granules')} E-statements; merged stats restored")
        return 0
    except KeyboardInterrupt:
        say("CREC crawl INTERRUPTED — manifest is intact, rerun to resume")
        return 130
    except Exception as e:                                    # noqa: BLE001 — skip-and-log doctrine
        say(f"CREC crawl FAILED: {type(e).__name__}: {e}")
        return 1
    finally:
        # Never leave a lock naming a dead pid: the next session pays for that in confusion.
        try:
            if lock.exists() and json.loads(lock.read_text(encoding="utf-8")).get("pid") == os.getpid():
                lock.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
