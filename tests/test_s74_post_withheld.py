"""S74, ruling #392: the outage-backfilled days stay site-only once posting comes back on.

RUN C posts whatever assemble-latest.json names and runs after a no-op assemble too. When posting
came back on, assemble-latest named 2026-11-10, a backfilled day. Without the withheld list, the
first no-op pass would have posted it.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import post_bluesky  # noqa: E402
from test_wave0 import _DAY_JSON, _env, _run_main_with  # noqa: E402

_LIVE = dict(POSTING_ENABLED="true", BSKY_BLUE_HANDLE="b", BSKY_BLUE_PASSWORD="x",
             BSKY_RED_HANDLE="r", BSKY_RED_PASSWORD="y")


def _boom(*_a, **_k):
    raise AssertionError("a withheld day touched the network")


def test_the_withheld_set_is_exactly_the_backfilled_days():
    d, want = date(2026, 10, 28), set()
    while d <= date(2026, 11, 10):
        want.add(d.isoformat())
        d += timedelta(days=1)
    assert post_bluesky.WITHHELD_DAYS == want
    assert "2026-10-27" not in post_bluesky.WITHHELD_DAYS   # last scheduled, posted day
    assert "2026-11-11" not in post_bluesky.WITHHELD_DAYS   # first day back must post


def test_a_withheld_day_never_posts_with_every_gate_open():
    restore = _env(**_LIVE)
    pages = []
    try:
        rc, manifest = _run_main_with("2026-11-10", _DAY_JSON, {}, authenticate=_boom,
                                      post_thread=_boom, ntfy_sink=pages)
    finally:
        restore()
    assert rc == 0
    assert {r["party"] for r in manifest["results"]} == {"D", "R"}       # symmetric hold
    assert not any(r.get("posted") or r.get("root_uri") for r in manifest["results"])
    assert all("ruling #392" in r["reason"] for r in manifest["results"])
    assert pages == []                                                   # an intended hold never pages


def test_the_first_day_back_still_posts():
    restore = _env(**_LIVE)
    try:
        rc, manifest = _run_main_with("2026-11-11", _DAY_JSON, {}, ntfy_sink=[])
    finally:
        restore()
    assert rc == 0
    assert all(r.get("posted") and r.get("root_uri") for r in manifest["results"]), manifest
