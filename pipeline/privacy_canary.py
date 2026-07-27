"""Fail-closed production privacy canary with aggregate-only telemetry."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from . import privacy, util


CANARY_VERSION = "privacy-production-canary-v1"


class PrivacyCanaryError(privacy.PrivacyGateError):
    """The production canary failed, so publication is refused."""


def run(*, telemetry_path: Path | None = None, seed_failure: bool = False) -> dict:
    """Validate the live gate and write no occurrence-level information."""
    if seed_failure:
        raise PrivacyCanaryError("seeded privacy canary failure")
    privacy.load()
    checks = {
        "gate_loaded": bool(privacy.forms_fingerprint()),
        "redaction_label_suppressed": privacy.is_suppressed("<private-individual-canary>"),
        "ordinary_policy_text_allowed": not privacy.is_suppressed("public budget policy"),
        "typed_entity_hierarchy": len(privacy.ENTITY_TYPES) == 4,
    }
    if not all(checks.values()):
        failed = sorted(key for key, value in checks.items() if not value)
        raise PrivacyCanaryError(f"privacy canary checks failed: {failed}")
    meta = privacy.meta()
    telemetry = {
        "schema_version": 1,
        "canary_version": CANARY_VERSION,
        "passed": True,
        "checks_run": len(checks),
        "checks_passed": sum(checks.values()),
        "form_list_fingerprint": privacy.forms_fingerprint(),
        "admitted_persons": meta.get("persons"),
        "admission_entries": len(meta.get("entries") or []),
        "entity_hierarchy_version": privacy.ENTITY_HIERARCHY_VERSION,
        "occurrence_level_records": 0,
    }
    if telemetry_path is not None:
        util.write_json(telemetry_path, telemetry)
    return telemetry


def publication_rehearsal(publish: Callable[[], object], *, seed_failure: bool = False) -> object:
    """Run the canary before a supplied dry-run publication callback."""
    run(seed_failure=seed_failure)
    return publish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path)
    parser.add_argument("--seed-failure", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = run(telemetry_path=args.telemetry, seed_failure=args.seed_failure)
    print(f"privacy canary passed: {result['checks_passed']}/{result['checks_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
