"""Small stdlib-only utilities: hashing, JSONL/gzip IO, HTTP GET, day boundary."""
from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - py<3.9
    ZoneInfo = None  # type: ignore

from . import config


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def statement_id(url: str, text: str) -> str:
    """Stable id for a statement = sha256 of (url + '\\n' + text). (§3)"""
    return "sha256:" + sha256_hex((url or "") + "\n" + (text or ""))


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def product_day(reference: datetime | None = None) -> str:
    """Product day = the prior America/New_York calendar day (§2)."""
    if ZoneInfo is not None:
        ny = datetime.now(ZoneInfo(config.TIMEZONE)) if reference is None else reference.astimezone(ZoneInfo(config.TIMEZONE))
    else:  # pragma: no cover
        ny = (reference or datetime.now(timezone.utc))
    return (ny - timedelta(days=1)).strftime("%Y-%m-%d")


def daterange_months(start: str, end: str) -> list[tuple[int, int]]:
    """Inclusive list of (year, month) tuples spanning two YYYY-MM-DD dates."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out: list[tuple[int, int]] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def congress_for_date(iso_date: str) -> int:
    """Congress number for a YYYY-MM-DD date. The 107th seated 2001-01-03; each Congress
    is two years, seated ~Jan 3 of odd years. 119th = 2025-01-03 onward."""
    y = int(iso_date[:4])
    m = int(iso_date[5:7])
    d = int(iso_date[8:10])
    # A Congress seated in Jan of an odd year Y runs [Y, Y+2). Before ~Jan 3 of an odd
    # year the *previous* Congress is still seated.
    seat_year = y if (y % 2 == 1) else y - 1
    if y % 2 == 1 and (m, d) < (1, 3):
        seat_year -= 2
    # 107th Congress seated 2001 -> congress = 107 + (seat_year-2001)/2
    return 107 + (seat_year - 2001) // 2


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def http_get(url: str, *, timeout: int = 60, retries: int = 3, headers: dict | None = None) -> bytes:
    """GET with exponential backoff (skip-and-log philosophy: caller decides degrade)."""
    hdrs = {"User-Agent": config.USER_AGENT}
    if headers:
        hdrs.update(headers)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"GET failed after {retries} tries: {url}: {last_err}")


# ---------------------------------------------------------------------------
# JSONL / gzip IO
# ---------------------------------------------------------------------------
def iter_jsonl(path: Path) -> Iterator[dict]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:  # type: ignore[operator]
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict], *, gzipped: bool | None = None) -> int:
    gzipped = str(path).endswith(".gz") if gzipped is None else gzipped
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gzipped else open
    n = 0
    tmp = path.with_suffix(path.suffix + ".tmp")
    with opener(tmp, "wt", encoding="utf-8") as fh:  # type: ignore[operator]
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            n += 1
    tmp.replace(path)  # atomic swap (§4 A4: atomic writes)
    return n


def write_json(path: Path, obj: Any, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=indent)
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
