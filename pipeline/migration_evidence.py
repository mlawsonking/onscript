"""Build machine-readable migration evidence from committed run manifests."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


PARTIES = ("D", "R")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _post_complete(manifest: dict) -> bool:
    results = manifest.get("results") or []
    by_party = {row.get("party"): row for row in results if isinstance(row, dict)}
    return (
        manifest.get("posting_enabled") is True
        and manifest.get("atomic_hold") is False
        and manifest.get("asymmetric") is False
        and all(by_party.get(party, {}).get("posted") is True for party in PARTIES)
    )


def _assemble_complete(manifest: dict) -> bool:
    readiness = manifest.get("readiness") or {}
    return (
        manifest.get("final") is True
        and manifest.get("degraded") is False
        and readiness.get("ready") is True
    )


def find_latest_complete_cycle(manifest_dir: Path) -> tuple[str, dict[str, Path]]:
    """Return the newest day with healthy collect, final assemble, and symmetric post evidence."""
    candidates: list[tuple[str, dict[str, Path]]] = []
    for post_path in manifest_dir.glob("post-????-??-??.json"):
        day = post_path.stem.removeprefix("post-")
        assemble_path = manifest_dir / f"assemble-{day}.json"
        if not assemble_path.is_file():
            continue
        post = _read(post_path)
        assemble = _read(assemble_path)
        if post.get("day") != day or assemble.get("day") != day:
            continue
        if not _post_complete(post) or not _assemble_complete(assemble):
            continue
        collects = []
        for collect_path in manifest_dir.glob("collect-????-??-??.json"):
            collect = _read(collect_path)
            if (
                collect.get("focus_day") == day
                and collect.get("degraded") is False
                and not collect.get("alerts")
                and collect.get("volume", {}).get("anomalously_low") is False
            ):
                collects.append((collect.get("generated_at", ""), collect_path))
        if collects:
            collect_path = max(collects)[1]
            candidates.append((day, {
                "collect": collect_path,
                "assemble": assemble_path,
                "post": post_path,
            }))
    if not candidates:
        raise ValueError("no complete recorded production cycle")
    return max(candidates, key=lambda row: row[0])


def build_manifest(manifest_dir: Path, *, repository_root: Path) -> dict:
    day, paths = find_latest_complete_cycle(manifest_dir)
    collect = _read(paths["collect"])
    assemble = _read(paths["assemble"])
    post = _read(paths["post"])
    results = {row["party"]: row for row in post["results"]}
    evidence = {}
    for stage, path in paths.items():
        evidence[stage] = {
            "path": path.resolve().relative_to(repository_root.resolve()).as_posix(),
            "sha256": _sha256(path),
            "generated_at": _read(path).get("generated_at"),
        }
    return {
        "schema_version": 1,
        "manifest_kind": "migration_evidence",
        "migration_id": "w-stack-production-cycle",
        "migration_state": "completed",
        "production_day": day,
        "evidence": evidence,
        "checks": {
            "collect": {
                "degraded": collect["degraded"],
                "alerts": collect["alerts"],
                "anomalously_low": collect["volume"]["anomalously_low"],
            },
            "assemble": {
                "final": assemble["final"],
                "degraded": assemble["degraded"],
                "ready": assemble["readiness"]["ready"],
                "forced_finalize": assemble["forced_finalize"],
            },
            "post": {
                "posting_enabled": post["posting_enabled"],
                "atomic_hold": post["atomic_hold"],
                "asymmetric": post["asymmetric"],
                "party_posted": {party: results[party]["posted"] for party in PARTIES},
                "party_posts_written": {party: results[party]["posts_written"] for party in PARTIES},
            },
        },
    }


def canonical_bytes(payload: dict) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return text.replace("\n", os.linesep).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/derived/manifest"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    payload = build_manifest(args.manifest_dir, repository_root=args.repository_root)
    rendered = canonical_bytes(payload)
    if args.check:
        if not args.check.is_file() or args.check.read_bytes() != rendered:
            print(f"migration evidence differs: {args.check}")
            return 1
        print(f"migration evidence matches: {args.check}")
        return 0
    print(rendered.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
