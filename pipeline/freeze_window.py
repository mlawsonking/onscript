"""Constitution Article VIII: the election freeze, Oct 15 through Nov 10 inclusive.

The freeze is a promise the project makes in public: from Oct 15 through Nov 10 the prompts,
the thresholds, and the machinery that runs them do not move, so a reading taken during the
election cannot be explained by an instrument that changed underneath it. That promise is worth
exactly as much as its enforcement, and until now the only enforcement was prose plus a Claude
Code hook. The hook sees one operator's session; it does not see CI, another shell, another
machine, or a merge, which is precisely the list of ways a change actually lands.

This module is the machine-readable authority for the window and for what it covers. It is
stdlib only and imports nothing from the rest of the pipeline, so the check runs on a bare
checkout with no secrets, no state asset, and no chance of the gate failing for an unrelated
reason. `.claude/hooks/governance_guard.py` keeps its own copy of the dates because it must run
standalone; a test asserts the two agree, so they cannot drift (docs/37 rule 1).

Outside the window every input is allowed and the check is a no-op, which is how it ships:
inert on the day it lands, live on Oct 15 without anybody remembering to arm it.
"""
from __future__ import annotations

import sys
from datetime import date

FREEZE_START = (10, 15)
FREEZE_END = (11, 10)

# What Article VIII freezes: the wording the model is given, the numbers the code compares
# against, and the workflows that decide when either one runs.
FROZEN_PATHS = ("pipeline/prompts/", "pipeline/config.py", ".github/workflows/")

WINDOW_LABEL = "Oct 15 through Nov 10"


def in_freeze(today: date | None = None) -> bool:
    """True on any day from Oct 15 through Nov 10 inclusive, in any year."""
    day = today or date.today()
    return FREEZE_START <= (day.month, day.day) <= FREEZE_END


def normalize_path(path) -> str:
    """Repo-relative, forward slashes. removeprefix, never lstrip: lstrip("./") would eat the
    leading dot of .github and quietly exempt every workflow from the freeze."""
    normalized = str(path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized.removeprefix("./")
    return normalized


def is_frozen_path(path: str) -> bool:
    normalized = normalize_path(path)
    if not normalized:
        return False
    return any(normalized == frozen.rstrip("/") or normalized.startswith(frozen)
               for frozen in FROZEN_PATHS)


def frozen_changes(paths, today: date | None = None) -> list[str]:
    """The frozen paths among `paths`, or nothing at all outside the window."""
    if not in_freeze(today):
        return []
    return sorted({normalize_path(path) for path in paths if is_frozen_path(path)})


def report(paths, today: date | None = None) -> tuple[int, str]:
    """Return (exit code, message) for a set of changed paths."""
    day = today or date.today()
    if not in_freeze(day):
        return 0, (f"freeze check: {day.isoformat()} is outside the election freeze "
                   f"({WINDOW_LABEL}); nothing is frozen today.")
    blocked = frozen_changes(paths, day)
    if not blocked:
        return 0, (f"freeze check: {day.isoformat()} is inside the election freeze "
                   f"({WINDOW_LABEL}) and this push touches no frozen path.")
    listed = "\n".join(f"  {path}" for path in blocked)
    return 1, (f"freeze check: {day.isoformat()} is inside the election freeze "
               f"({WINDOW_LABEL}, Constitution Article VIII) and this push changes "
               f"the instrument:\n{listed}\n"
               f"Frozen during the window: {', '.join(FROZEN_PATHS)}. "
               f"A reading taken during the election must not be explained by an instrument "
               f"that moved underneath it.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    paths = [line for line in sys.stdin.read().splitlines()] if "--stdin" in argv else argv
    code, message = report(paths)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":  # pragma: no cover - exercised through report() in tests
    raise SystemExit(main())
