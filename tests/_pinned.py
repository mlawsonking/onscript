"""Read a committed artifact as it stood at a pinned commit (docs/37 rule 3).

Production collects rewrite day records, manifests and audits. A test that reads the live file
breaks the next time production touches it; a test that reads the bytes at a named commit is a real
committed artifact that cannot move. S74-15.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# origin/main when S74-15 Packages 4b, 2 and 3 were built (2026-11-23).
PIN = "1c5694c4b6f4fbb7e907971c19b99ddce04ae509"


def pinned_bytes(path: str, commit: str = PIN) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True,
                          capture_output=True).stdout


def pinned_json(path: str, commit: str = PIN):
    return json.loads(pinned_bytes(path, commit).decode("utf-8"))


def pinned_day(day: str, commit: str = PIN) -> dict:
    return pinned_json(f"data/derived/days/{day}.json", commit)
