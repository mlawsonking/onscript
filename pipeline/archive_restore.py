"""Validate release archives in isolation, then merge only runtime-owned paths."""
from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ARCHIVES = {
    "state.tar.gz": ("data/state", "data/reference"),
    "raw.tar.gz": ("data/raw",),
}
RUNTIME_REFERENCE_FILES = frozenset({"data/reference/roster.json"})


def _member_path(member: tarfile.TarInfo, allowed_prefixes: tuple[str, ...]) -> PurePosixPath:
    path = PurePosixPath(member.name)
    if (path.is_absolute() or ".." in path.parts or member.issym() or member.islnk()
            or not (member.isdir() or member.isfile())):
        raise ValueError(f"unsafe archive member: {member.name}")
    normalized = str(path).rstrip("/")
    if not any(normalized == prefix or normalized.startswith(prefix + "/")
               for prefix in allowed_prefixes):
        raise ValueError(f"archive member is outside the allowlist: {member.name}")
    return path


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".restore-tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def restore_archive(archive: Path, checkout: Path) -> list[str]:
    """Extract under a temporary root, validate, then merge approved runtime files."""
    allowed_prefixes = ARCHIVES.get(archive.name)
    if allowed_prefixes is None:
        raise ValueError(f"unknown release archive: {archive.name}")
    checkout = checkout.resolve()
    merged: list[str] = []
    with tempfile.TemporaryDirectory(prefix="onscript-restore-") as temporary_name:
        temporary = Path(temporary_name)
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            paths = [_member_path(member, allowed_prefixes) for member in members]
            bundle.extractall(temporary, members=members, filter="data")

        # Repository-owned files in an archive are NEVER restored (the merge loop below skips
        # them), so a stale copy cannot roll the checkout back no matter what this loop does.
        # A differing copy is therefore reported loudly and SKIPPED, not raised: every archive
        # built before the W3 authority split legitimately carries data/reference, and raising
        # here deadlocks the pipeline (2026-07-26, first post-W3 cycle: both runs died on the
        # pre-W3 data-latest archive, and the archive is only rebuilt by a run that gets past
        # this line). Skip-and-log is the Constitution's reliability posture; protection lives
        # in the merge allowlist, not in this report.
        for relative in paths:
            source = temporary.joinpath(*relative.parts)
            key = relative.as_posix()
            if (source.is_file() and key.startswith("data/reference/")
                    and key not in RUNTIME_REFERENCE_FILES):
                destination = checkout.joinpath(*relative.parts)
                if not destination.is_file() or source.read_bytes() != destination.read_bytes():
                    print(f"[restore] repository-authority file in archive differs and is "
                          f"IGNORED (repository wins): {key}")

        for relative in paths:
            source = temporary.joinpath(*relative.parts)
            if not source.is_file():
                continue
            key = relative.as_posix()
            destination = checkout.joinpath(*relative.parts)
            if key.startswith("data/reference/") and key not in RUNTIME_REFERENCE_FILES:
                continue
            _copy_file(source, destination)
            merged.append(key)
    return sorted(merged)


def restore_release(directory: Path, checkout: Path) -> list[str]:
    merged: list[str] = []
    for archive_name in ARCHIVES:
        archive = directory / archive_name
        if archive.exists():
            merged.extend(restore_archive(archive, checkout))
    return sorted(merged)


STAGE_TIMING_RELPATH = "data/state/stage-timings.json"


def publish_restore_timing(checkout: Path, seconds: float) -> Path | None:
    """Hand the restore's cost to the collect process, which runs as a separate workflow step.

    Written with stdlib json ON PURPOSE: this module validates untrusted archives and stays
    importable without the rest of the pipeline, so it does not grow a dependency on
    pipeline.config (which builds directories at import) just to emit one number. The shape is
    what util.adopt_stage_timings() reads, and a test asserts that contract across the seam
    rather than trusting two copies of it to stay in step."""
    path = Path(checkout) / STAGE_TIMING_RELPATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z")
        path.write_text(json.dumps({"schema_version": 1, "generated_at": generated_at,
                                    "stages": {"restore": round(seconds, 1)}},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except OSError as e:
        # A restore that cannot report its own duration is still a completed restore.
        print(f"[timing] could not publish the restore timing (non-fatal): {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_directory", type=Path)
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    args = parser.parse_args()
    started = time.perf_counter()
    merged = restore_release(args.release_directory, args.checkout)
    elapsed = time.perf_counter() - started
    print(f"restored {len(merged)} runtime file(s) through the allowlist")
    print(f"[timing] restore elapsed_s={elapsed:.1f}", flush=True)
    publish_restore_timing(args.checkout, elapsed)


if __name__ == "__main__":
    main()
