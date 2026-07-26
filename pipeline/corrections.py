"""Structured correction ledger and publication-state helpers."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import config, util


SCHEMA_VERSION = 2
SEVERITY_CLASSES = frozenset({"critical", "major", "minor"})
STATUS_CLASSES = frozenset({"open", "resolved"})
_ID = re.compile(r"corr-[a-z0-9][a-z0-9-]+$")
COUNT_FILE = config.REFERENCE / "corrections-count.json"


def validate(rows: list[dict], expected_count: int | None = None) -> list[dict]:
    """Validate the append-only public ledger and return it unchanged."""
    if not isinstance(rows, list):
        raise ValueError("corrections ledger must be a list")
    ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"correction {index} is not an object")
        cid = row.get("correction_id")
        if (row.get("schema_version") != SCHEMA_VERSION or not isinstance(cid, str)
                or not _ID.fullmatch(cid) or cid in ids):
            raise ValueError(f"correction {index} has an invalid or duplicate identity")
        ids.add(cid)
        if row.get("severity") not in SEVERITY_CLASSES:
            raise ValueError(f"correction {cid} has an invalid severity")
        if row.get("status") not in STATUS_CLASSES:
            raise ValueError(f"correction {cid} has an invalid status")
        days = row.get("affected_days")
        if (not isinstance(days, list) or any(
                not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
                for day in days)):
            raise ValueError(f"correction {cid} has invalid affected days")
        for required in ("logged", "day", "description", "resolution"):
            if not row.get(required):
                raise ValueError(f"correction {cid} is missing {required}")
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(
            f"corrections count changed without its monotonic checkpoint: "
            f"ledger={len(rows)} checkpoint={expected_count}"
        )
    return rows


def load(path: Path | None = None, count_path: Path | None = None) -> list[dict]:
    ledger_path = path or (config.REFERENCE / "corrections.json")
    checkpoint_path = count_path or COUNT_FILE
    rows = util.read_json(ledger_path, [])
    checkpoint = util.read_json(checkpoint_path, {})
    expected = checkpoint.get("count") if isinstance(checkpoint, dict) else None
    if not isinstance(expected, int) or expected < 0:
        raise ValueError("corrections count checkpoint is missing or invalid")
    return validate(rows, expected)


def for_day(day: str, rows: list[dict] | None = None) -> list[dict]:
    source = load() if rows is None else validate(rows)
    return [row for row in source if day in row.get("affected_days", [])]


def content_address(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def correction_reply(logged: str, claimed: str, supported: str, permalink: str) -> str:
    """Build the P4 correction reply. This function has no posting side effect."""
    if not all(isinstance(value, str) and value.strip()
               for value in (logged, claimed, supported, permalink)):
        raise ValueError("correction reply fields must be non-empty strings")
    return (
        f"Correction ({logged}): we said {claimed}; the receipts supported {supported}. "
        f"The claim is retracted and the log updated: {permalink}."
    )


def publication_fields(day_payload: dict, prior_manifest: dict | None,
                       correction_rows: list[dict]) -> dict:
    """Build deterministic content identity and a monotonic revision chain for one day."""
    address = content_address(day_payload)
    prior = prior_manifest if isinstance(prior_manifest, dict) else {}
    chain = [dict(row) for row in (prior.get("revision_chain") or []) if isinstance(row, dict)]
    prior_address = prior.get("content_address")
    if prior_address and not chain:
        chain.append({"revision": 1, "content_address": prior_address, "supersedes": None})
    if not chain or chain[-1].get("content_address") != address:
        chain.append({
            "revision": len(chain) + 1,
            "content_address": address,
            "supersedes": chain[-1].get("content_address") if chain else None,
        })
    correction_ids = sorted(row["correction_id"] for row in correction_rows)
    return {
        "publication_state": "corrected" if correction_ids else "published",
        "content_address": address,
        "revision": chain[-1]["revision"],
        "revision_chain": chain,
        "correction_ids": correction_ids,
    }
