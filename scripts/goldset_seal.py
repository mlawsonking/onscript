"""Build and seal the deterministic gold-set pilot and full samples.

Reads the committed phrase ledger and normalized statements, builds the candidate
universe, seals a disjoint 200-item pilot and 1400-item full sample with public-impact
oversampling, anchors each selected candidate to a source statement, and writes the
sealed manifests under evaluation/goldset/. No network, no API budget.

Usage:

    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_seal.py build
    C:\\ProgramData\\miniconda3\\python.exe scripts\\goldset_seal.py verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config, goldset, goldset_sample, util  # noqa: E402


SEED = "onscript-goldset-v1"
PILOT_SIZE = 200
FULL_SIZE = 1400
SPLIT_BOUNDARIES = {"train_end": "2025-12-31", "validation_end": "2026-03-31"}

LEDGER_PATH = config.STATE / "ledger.json"
STATEMENTS_PATH = config.STATE / "statements.jsonl.gz"
OUT_DIR = ROOT / "evaluation" / "goldset"


def _file_digest(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": size,
            "sha256": digest.hexdigest()}


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build() -> int:
    ledger_source = _file_digest(LEDGER_PATH)
    print(f"loading ledger {ledger_source['bytes']} bytes ...", flush=True)
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    print(f"ledger ngrams: {len(ledger)}", flush=True)

    universe = goldset_sample.build_universe(ledger, epoch=config.STAGE1_EPOCH)
    print(f"universe candidates: {len(universe)}", flush=True)

    days_dir = config.DERIVED / "days"
    day_artifacts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(days_dir.glob("*.json"))
    ]
    public_phrases = goldset_sample._day_surface_phrases(day_artifacts)
    goldset_sample.tag_impact(universe, public_phrases=public_phrases)
    print(f"public-surface phrases: {len(public_phrases)}", flush=True)

    manifest = goldset_sample.seal(
        universe,
        seed=SEED,
        pilot_size=PILOT_SIZE,
        full_size=FULL_SIZE,
        split_boundaries=SPLIT_BOUNDARIES,
        ledger_source=ledger_source,
    )
    print(f"pilot {manifest['pilot_size']} full {manifest['full_size']} "
          f"seal {manifest['seal_hash'][:16]}", flush=True)

    # Free the ledger and universe before anchoring: only the selected rows and the
    # statements corpus are needed from here, and holding the 3 GB ledger in memory makes
    # the garbage collector thrash during clustering.
    import gc
    del ledger, universe, day_artifacts, public_phrases
    gc.collect()

    print("anchoring selected candidates to source statements ...", flush=True)
    statements_by_day = goldset_sample._load_statements_by_day(STATEMENTS_PATH)
    pilot = goldset_sample.anchor_and_contextualize(manifest["pilot"], statements_by_day)
    full = goldset_sample.anchor_and_contextualize(manifest["full"], statements_by_day)
    unresolved = sum(1 for row in pilot + full if not row.get("anchor_resolved"))
    print(f"anchored; unresolved anchors: {unresolved}", flush=True)

    # Privacy floor: no admitted private-person form reaches a written sample file.
    pilot = goldset_sample.redact_for_publish(pilot)
    full = goldset_sample.redact_for_publish(full)
    redacted = sum(1 for row in pilot + full if row.get("phrase_redacted"))
    print(f"phrase fields redacted: {redacted}", flush=True)

    common = {
        "schema_version": manifest["schema_version"],
        "method_version": manifest["method_version"],
        "seed": manifest["seed"],
        "universe_fingerprint": manifest["universe_fingerprint"],
        "seal_hash": manifest["seal_hash"],
        "split_boundaries": manifest["split_boundaries"],
        "ledger_source": manifest["ledger_source"],
    }
    _write(OUT_DIR / "pilot.sample.json", {**common, "sample": "pilot",
                                           "size": len(pilot), "candidates": pilot})
    _write(OUT_DIR / "full.sample.json", {**common, "sample": "full",
                                          "size": len(full), "candidates": full})
    seal_manifest = {
        **common,
        "universe_size": manifest["universe_size"],
        "pilot_size": manifest["pilot_size"],
        "full_size": manifest["full_size"],
        "statements_source": _file_digest(STATEMENTS_PATH),
        "unresolved_anchors": unresolved,
        "strata": manifest["strata"],
    }
    _write(OUT_DIR / "MANIFEST.json", seal_manifest)
    print(f"wrote {OUT_DIR}", flush=True)
    return 0


def verify() -> int:
    """Rebuild from the committed corpus and confirm the seal hash matches the manifest."""
    manifest = json.loads((OUT_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    universe = goldset_sample.build_universe(ledger, epoch=config.STAGE1_EPOCH)
    days_dir = config.DERIVED / "days"
    day_artifacts = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(days_dir.glob("*.json"))
    ]
    goldset_sample.tag_impact(universe, public_phrases=goldset_sample._day_surface_phrases(day_artifacts))
    rebuilt = goldset_sample.seal(
        universe, seed=manifest["seed"], pilot_size=PILOT_SIZE, full_size=FULL_SIZE,
        split_boundaries=manifest["split_boundaries"],
    )
    ok = rebuilt["seal_hash"] == manifest["seal_hash"]
    fingerprint_ok = rebuilt["universe_fingerprint"] == manifest["universe_fingerprint"]
    print(f"seal_hash match: {ok}")
    print(f"universe_fingerprint match: {fingerprint_ok}")
    print(f"manifest seal: {manifest['seal_hash']}")
    print(f"rebuilt  seal: {rebuilt['seal_hash']}")
    return 0 if (ok and fingerprint_ok) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("verify")
    args = parser.parse_args()
    if args.command == "build":
        return build()
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
