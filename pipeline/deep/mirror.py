"""Mirror-first ingest of the cross-check lanes (docs/15 §D0.3). Immutable, hash-manifested, polite,
resumable. These upstreams can vanish (DCinbox dumps stopped 2021-09; Grimmer/Wang are single-repo
academic artifacts) — so the moment a lane is touched, its source is mirrored to X: and hashed.

Run as a background job; safe to re-run (the CrawlManifest skips already-fetched, hash-verified units).
$0, keyless, local. Nothing here touches the daily pipeline or GitHub Actions.
"""
from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

from . import lanes


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": lanes.POLITE["user_agent"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def mirror_urls(source: str, urls: list[tuple[str, str]], progress=True) -> dict:
    """Fetch (uid, url) pairs into lane_raw(source), recording sha256 + bytes in the crawl manifest.
    Resumable: already-manifested uids are skipped. Returns {fetched, skipped, failed}."""
    raw = lanes.lane_raw(source)
    raw.mkdir(parents=True, exist_ok=True)
    man = lanes.CrawlManifest(lanes.lane_state(source) / "mirror-manifest.jsonl")
    fetched = skipped = failed = 0
    for uid, url in urls:
        if man.seen(uid):
            skipped += 1
            continue
        try:
            data = _get(url)
            (raw / uid).write_bytes(data)
            man.record(uid, lanes.sha256(data), len(data), meta={"url": url})
            fetched += 1
            if progress:
                print(f"  [{source}] {uid} ({len(data)} bytes)", flush=True)
            time.sleep(lanes.POLITE["min_interval_s"])
        except Exception as e:  # skip-and-log; resumable on the next run
            failed += 1
            print(f"  [{source}] FAILED {uid}: {e}", flush=True)
    summary = {"source": source, "fetched": fetched, "skipped": skipped, "failed": failed,
               "total_manifested": len(man)}
    return summary


def discover_dcinbox_csvs() -> list[tuple[str, str]]:
    """Scrape the DCinbox downloads page for the monthly CSV links (both-party e-newsletters, 2009+)."""
    page = _get("https://www.lindseycormack.com/dcinbox-data-downloads").decode("utf-8", "ignore")
    urls = []
    for m in re.finditer(r'href=["\']([^"\']+\.csv)["\']', page, re.I):
        u = m.group(1)
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = "https://www.lindseycormack.com" + u
        uid = u.rsplit("/", 1)[-1]
        urls.append((uid, u))
    # de-dup preserving order
    seen = set()
    return [(uid, u) for uid, u in urls if not (uid in seen or seen.add(uid))]


def mirror_dcinbox(progress=True) -> dict:
    csvs = discover_dcinbox_csvs()
    if progress:
        print(f"[dcinbox] discovered {len(csvs)} CSV links", flush=True)
    return {"discovered": len(csvs), **mirror_urls("dcinbox", csvs, progress=progress)}
