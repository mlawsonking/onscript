"""Write and verify SHA-256 sidecars for rolling release assets."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_sidecar(path: Path) -> Path:
    if not path.is_file():
        raise ValueError(f"release asset is not a file: {path}")
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_text(f"{file_sha256(path)}  {path.name}\n", encoding="ascii", newline="\n")
    return sidecar


def verify_sidecar(path: Path) -> bool:
    sidecar = path.with_name(path.name + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        return False
    parts = sidecar.read_text(encoding="ascii").strip().split()
    return len(parts) == 2 and parts[1] == path.name and parts[0] == file_sha256(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("write", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("assets", nargs="+", type=Path)
    args = parser.parse_args()
    if args.command == "write":
        for asset in args.assets:
            print(write_sidecar(asset))
        return 0
    failed = [asset for asset in args.assets if not verify_sidecar(asset)]
    for asset in args.assets:
        print(f"{asset}: {'OK' if asset not in failed else 'FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
