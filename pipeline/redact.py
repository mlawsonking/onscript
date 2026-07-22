"""R-L — the redacted-view release assets (docs/23; ruled 2026-07-21, revocable, flagged for #110).

THE PROBLEM GIT CANNOT REACH. Both workflows tar `data/state`/`data/reference`/`data/raw` and
`gh release upload` them to the rolling `data-latest` release, refreshed every cron run. Those
payloads are built from statements that name a private individual, so the assets carry the name —
44 occurrences in raw.tar.gz, 42 in state.tar.gz when it was measured (Session 38). A history
rewrite cannot touch a release asset, and the repo goes public.

THE RULING, and why it satisfies the constitution rather than amending it: append-only governs the
ARCHIVE; Article XIII (unamendable) governs every PUBLISHED surface, and a release asset is a
published surface. So the published assets carry the same privacy floor as every other published
surface, each occurrence LABELED IN PLACE rather than dropped, and the pristine append-only archive
on X: stays untouched.

WHY ON PERSIST, EVERY RUN, AND NOT A ONE-TIME EDIT. The eleven contaminated records could have been
hand-edited once. They would have re-leaked on the next converged statement: press releases can name
the person again tomorrow, and the ledger is rebuilt from them. This is a filter on the way out, so
it covers material that does not exist yet.

WHY THE WORKING TREE, NOT A COPY. Redaction runs in place on the runner, whose state was itself
restored from the previous run's asset — so the cloud's store converges on the redacted view and
stays there, which is also what quietly cleans the regenerable search-index rows. Nothing is lost:
the pristine record lives on X:, which no workflow writes to.

NOTHING PUBLISHED MOVES. A redaction label is itself suppressed (pipeline/privacy.py), so every
display path already drops, holds and purges a labeled row exactly as it did the named one. R-L
changes release assets and nothing else.

FAIL CLOSED. Any failure here exits non-zero BEFORE the tar step, so a run that cannot redact does
not upload. A missed upload costs one cycle and is rebuilt by the next run; a leaked one is
permanent.

    python -m pipeline.redact data/state data/reference data/raw   # redact in place
    python -m pipeline.redact --check <dir-or-file> ...            # report only, exit 1 if found
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import privacy, util  # noqa: E402

CACHE_NAME = ".redact-cache.json"

# Parsed per record, never scanned as raw text. A JSON file stores "’" as an escape or a literal
# depending on ensure_ascii, and a text-level scan would see the tokens of the ESCAPE ("u2019s")
# rather than of the value — silently missing exactly the possessive forms the gate exists to catch.
_JSONL_SUFFIXES = (".jsonl", ".ndjson")
_SKIP_NAMES = {CACHE_NAME}
_SKIP_SUFFIXES = (".tmp", ".lock")


class RedactionError(RuntimeError):
    """Redaction could not be completed safely. Never caught to continue publishing."""


# --- object walk --------------------------------------------------------------------------------
def redact_obj(obj):
    """Redact every string in a parsed JSON value, keys included. Returns (obj, replacements).

    Keys matter: in `ledger.json` the n-gram IS the key, so a value-only walk would leave the name
    as the index of its own entry."""
    if isinstance(obj, str):
        return privacy.redact(obj)
    # Unchanged containers are returned AS THEMSELVES, not rebuilt. `ledger.json` parses to ~3.3 GB
    # of Python objects and all but a handful of entries are clean; rebuilding every dict would hold
    # two full copies at once (measured ~7 GB peak) on a 16 GB runner, for nothing.
    if isinstance(obj, list):
        out, n, changed = [], 0, False
        for v in obj:
            v2, k = redact_obj(v)
            changed = changed or v2 is not v
            out.append(v2)
            n += k
        return (out if changed else obj), n
    if isinstance(obj, dict):
        out, n, changed = {}, 0, False
        for k, v in obj.items():
            k2, nk = privacy.redact(k) if isinstance(k, str) else (k, 0)
            v2, nv = redact_obj(v)
            changed = changed or nk or v2 is not v
            if k2 in out:
                # Two distinct keys collapsed into one. Per-form labels make this practically
                # unreachable, but a silent collapse is data loss discovered months later, so it is
                # a hard stop rather than a last-write-wins merge.
                raise RedactionError(f"redaction would merge two distinct keys into {k2!r}")
            out[k2] = v2
            n += nk + nv
        return (out if changed else obj), n
    return obj, 0


# --- file modes ---------------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mode_for(path: Path) -> str | None:
    name = path.name[:-3] if path.name.endswith(".gz") else path.name
    if name.endswith(_JSONL_SUFFIXES):
        return "jsonl"
    if name.endswith(".json"):
        return "json"
    return None


def _redact_jsonl(path: Path, *, check: bool) -> int:
    """Per record. An untouched record keeps its ORIGINAL bytes — re-serializing a clean corpus
    would rewrite hundreds of megabytes every run and churn the asset for nothing."""
    gzipped = path.name.endswith(".gz")
    opener = gzip.open if gzipped else open
    total = 0
    tmp = path.with_name(path.name + ".redact.tmp")
    out_fh = None
    try:
        if not check:
            out_fh = opener(tmp, "wt", encoding="utf-8", newline="\n")  # type: ignore[operator]
        with opener(path, "rt", encoding="utf-8", newline="") as fh:  # type: ignore[operator]
            for lineno, line in enumerate(fh, 1):
                stripped = line.rstrip("\n")
                if not stripped.strip():
                    if out_fh:
                        out_fh.write(line)
                    continue
                try:
                    rec = json.loads(stripped)
                except ValueError:
                    # An unparseable line is still archive content and may still carry the name.
                    # Scan it as raw text rather than passing it through unexamined.
                    red, n = privacy.redact(stripped)
                    if n:
                        print(f"[redact] {path.name}:{lineno} unparseable JSON — redacted as text")
                    total += n
                    if out_fh:
                        out_fh.write((red if n else stripped) + "\n")
                    continue
                red_obj, n = redact_obj(rec)
                total += n
                if out_fh:
                    if n:
                        out_fh.write(json.dumps(red_obj, ensure_ascii=False,
                                                separators=(",", ":")) + "\n")
                    else:
                        out_fh.write(stripped + "\n")
        if out_fh:
            out_fh.close()
            out_fh = None
            if total:
                os.replace(tmp, path)
            else:
                os.unlink(tmp)          # byte-identical rewrite: keep the archive's own bytes
    finally:
        if out_fh:
            out_fh.close()
        if tmp.exists():
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return total


def _redact_json(path: Path, *, check: bool) -> int:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            head = fh.read(4096)
            fh.seek(0)
            doc = json.load(fh)
    except ValueError as e:
        # Fail closed, loudly, with the path. A payload we cannot parse is a payload we cannot
        # prove is clean, and the alternative — skipping it — is the silent miss this exists to end.
        raise RedactionError(f"{path}: unparseable JSON, cannot prove it is clean ({e})") from e
    obj, n = redact_obj(doc)
    if n and not check:
        # Preserve the file's own shape: the ledger is written with indent=None (one line), the
        # reference tables with indent=2. Only a contaminated file is ever rewritten.
        util.write_json(path, obj, indent=None if "\n" not in head else 2)
    return n


def redact_file(path: Path, *, check: bool = False) -> dict:
    mode = _mode_for(path)
    if mode is None:
        return {"path": str(path), "mode": None, "count": 0}
    n = _redact_jsonl(path, check=check) if mode == "jsonl" else _redact_json(path, check=check)
    return {"path": str(path), "mode": mode, "count": n}


# --- tree ---------------------------------------------------------------------------------------
def _iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if name in _SKIP_NAMES or name.endswith(_SKIP_SUFFIXES):
                continue
            yield Path(dirpath) / name


def redact_tree(roots, *, cache_path: Path | None = None, check: bool = False,
                verbose: bool = True) -> dict:
    """Redact every JSON/JSONL file under `roots` in place. Returns a report.

    The cache turns a full rescan into a hash pass over unchanged files. It is keyed on the form
    list's fingerprint as well as the file's, so admitting a new name invalidates every entry — the
    one moment a stale "already clean" answer would be wrong about the whole corpus."""
    t0 = time.time()
    fp = privacy.forms_fingerprint()
    cache = {}
    if cache_path and not check:
        raw = util.read_json(cache_path, {}) or {}
        if raw.get("forms_fingerprint") == fp:
            cache = raw.get("files") or {}
        elif raw:
            print("[redact] form list changed — cache invalidated, full rescan")
    # Entries OUTSIDE the roots this call walks are carried forward untouched. The two workflows
    # share one cache but scan different roots — collect covers data/raw, assemble does not — so a
    # plain overwrite would drop raw's entries on every assemble and make collect rescan 300 MB it
    # had already cleared.
    scanned_roots = [str(Path(r).resolve()).replace("\\", "/").rstrip("/") for r in roots]

    def _under_scanned(key: str) -> bool:
        k = str(Path(key).resolve()).replace("\\", "/") if not key.startswith("/") else key
        return any(k == r or k.startswith(r + "/") for r in scanned_roots)

    new_cache: dict = {k: v for k, v in cache.items() if not _under_scanned(k)}
    report = {"scanned": 0, "skipped": 0, "occurrences": 0, "changed": [],
              "unsupported": [], "files": 0}

    for root in roots:
        root = Path(root)
        if not root.exists():
            print(f"[redact] {root} does not exist — skipped")
            continue
        for path in _iter_files(root):
            report["files"] += 1
            key = str(path).replace("\\", "/")
            if _mode_for(path) is None:
                report["unsupported"].append(key)
                continue
            try:
                sha = _sha256(path)
            except OSError as e:
                raise RedactionError(f"cannot read {path}: {e}") from e
            if cache.get(key) == sha:
                report["skipped"] += 1
                new_cache[key] = sha
                continue
            res = redact_file(path, check=check)
            report["scanned"] += 1
            report["occurrences"] += res["count"]
            if res["count"]:
                report["changed"].append({"path": key, "count": res["count"]})
                if verbose:
                    print(f"[redact] {key}: {res['count']} occurrence(s) "
                          f"{'found' if check else 'redacted'}")
                if not check:
                    # Prove it, per file, instead of trusting that the write did what it said. Only
                    # contaminated files pay for this, so the guarantee is close to free — and the
                    # alternative is publishing an asset on the strength of a return value.
                    left = redact_file(path, check=True)["count"]
                    if left:
                        raise RedactionError(
                            f"{key}: {left} occurrence(s) survived redaction — refusing to continue")
            new_cache[key] = sha if check or not res["count"] else _sha256(path)

    if cache_path and not check:
        try:
            util.write_json(cache_path, {"schema_version": 1, "forms_fingerprint": fp,
                                         "generated_at": util.now_utc_iso(), "files": new_cache})
        except OSError as e:
            print(f"[redact] cache write failed (non-fatal): {e}")
    report["elapsed_s"] = round(time.time() - t0, 1)
    return report


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Redact Article XIII names from release-asset payloads.")
    ap.add_argument("roots", nargs="+", help="files or directories to redact in place")
    ap.add_argument("--check", action="store_true",
                    help="report only, write nothing; exit 1 if any occurrence is found")
    ap.add_argument("--no-cache", action="store_true", help="ignore and do not write the skip cache")
    a = ap.parse_args(argv)

    cache = None
    if not (a.check or a.no_cache):
        first = Path(a.roots[0])
        cache = (first if first.is_dir() else first.parent) / CACHE_NAME

    rep = redact_tree(a.roots, cache_path=cache, check=a.check)
    print(f"[redact] {'checked' if a.check else 'redacted'} {rep['scanned']} file(s), "
          f"skipped {rep['skipped']} unchanged, {rep['occurrences']} occurrence(s) in "
          f"{len(rep['changed'])} file(s), {rep['elapsed_s']}s")
    if rep["unsupported"]:
        # Never a silent skip: a payload type this tool cannot parse is a payload nobody scanned.
        print(f"[redact] NOT SCANNED (unsupported type): {len(rep['unsupported'])} file(s)")
        for p in rep["unsupported"][:20]:
            print(f"           {p}")
    if a.check and rep["occurrences"]:
        print("[redact] CHECK FAILED — admitted forms are present")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
