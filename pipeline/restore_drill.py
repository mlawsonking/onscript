"""Run the quarterly release restore and deterministic rebuild drill."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import archive_restore, release_provenance


ASSET_NAMES = ("state.tar.gz", "raw.tar.gz")
HASH_LINE = re.compile(r"derived tree hash ([AB]): ([0-9a-f]{64})$")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def assert_clean_clone(root: Path) -> str:
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("quarterly restore drill requires a clean tracked checkout")
    return _git(root, "rev-parse", "HEAD")


def parse_rebuild_hashes(output: str) -> tuple[str, str]:
    found = {}
    for line in output.splitlines():
        match = HASH_LINE.search(line.strip())
        if match:
            found[match.group(1)] = match.group(2)
    if set(found) != {"A", "B"}:
        raise ValueError("rebuild did not report both deterministic tree hashes")
    return found["A"], found["B"]


def run_drill(root: Path, assets_dir: Path) -> dict:
    root = root.resolve()
    assets_dir = assets_dir.resolve()
    commit = assert_clean_clone(root)
    assets = [assets_dir / name for name in ASSET_NAMES]
    failed = [asset.name for asset in assets if not release_provenance.verify_sidecar(asset)]
    if failed:
        raise ValueError(f"release asset provenance failed: {', '.join(failed)}")

    restore_log = io.StringIO()
    with contextlib.redirect_stdout(restore_log):
        restored = archive_restore.restore_release(assets_dir, root)
    result = subprocess.run(
        [sys.executable, "pipeline/rebuild.py"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"deterministic rebuild failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    first_hash, second_hash = parse_rebuild_hashes(result.stdout)
    now = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "report_kind": "quarterly_restore_drill",
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quarter": f"{now.year}-Q{((now.month - 1) // 3) + 1}",
        "checkout_commit": commit,
        "clean_clone_verified": True,
        "assets": {
            asset.name: {
                "bytes": asset.stat().st_size,
                "sha256": release_provenance.file_sha256(asset),
                "sidecar_verified": True,
            }
            for asset in assets
        },
        "restore": {
            "files_restored": len(restored),
            "repository_authority_notices": [
                line for line in restore_log.getvalue().splitlines() if line.strip()
            ],
        },
        "rebuild": {
            "estimator": "SHA-256 over relative path and bytes for deterministic derived JSON",
            "first_sha256": first_hash,
            "second_sha256": second_hash,
            "byte_identical": first_hash == second_hash,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets_dir", type=Path)
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = run_drill(args.checkout, args.assets_dir)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"report_kind": "quarterly_restore_drill", "passed": False,
                          "error": str(error)}, sort_keys=True))
        return 1
    report["passed"] = report["rebuild"]["byte_identical"]
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
