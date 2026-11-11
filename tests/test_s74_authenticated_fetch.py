"""S74, task #343: RUN A authenticates to api.github.com and to nothing else.

On 2026-10-08 the collect job died on `HTTP Error 403: rate limit exceeded` from
api.github.com/repos/dwillis/congress-press: unauthenticated calls share the runner IP's 60/hour
limit. The fix sends the Actions token on api.github.com requests only. The second half is the
load-bearing one: the token must never reach a member's press-release host or any other origin.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import util  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _with_token(value):
    old = os.environ.get("GITHUB_TOKEN")
    if value is None:
        os.environ.pop("GITHUB_TOKEN", None)
    else:
        os.environ["GITHUB_TOKEN"] = value
    return old


def _restore(old):
    if old is None:
        os.environ.pop("GITHUB_TOKEN", None)
    else:
        os.environ["GITHUB_TOKEN"] = old


def test_the_github_api_gets_the_token():
    old = _with_token("tok-123")
    try:
        hdrs = util._base_headers("https://api.github.com/repos/dwillis/congress-press")
        assert hdrs["Authorization"] == "Bearer tok-123"
        assert "User-Agent" in hdrs
    finally:
        _restore(old)


def test_no_other_host_ever_gets_the_token():
    old = _with_token("tok-123")
    try:
        for url in ("https://adams.house.gov/media-center/press-releases",
                    "https://raw.githubusercontent.com/dwillis/congress-press/main/x.json",
                    "https://github.com/dwillis/congress-press",
                    "https://api.github.com.evil.example/repos/x",
                    "https://evil.example/?u=https://api.github.com/"):
            assert "Authorization" not in util._base_headers(url), url
    finally:
        _restore(old)


def test_no_token_means_no_header():
    old = _with_token(None)
    try:
        assert "Authorization" not in util._base_headers("https://api.github.com/repos/x")
    finally:
        _restore(old)


def test_collect_workflow_hands_the_token_to_the_job():
    text = (ROOT / ".github" / "workflows" / "collect.yml").read_text(encoding="utf-8")
    assert "GITHUB_TOKEN: ${{ github.token }}" in text


def test_every_workflow_is_pinned_off_ubuntu_latest():
    # ubuntu-latest moved to 26.04, which has no setup-python 3.12.10; every run from 2026-10-28
    # failed at setup until the pin. A floating image is how the instrument went dark.
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        assert "ubuntu-latest" not in wf.read_text(encoding="utf-8"), wf.name
