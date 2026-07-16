"""GDELT DOC 2.0 news-agenda ingest (v2 feature 1.2, docs/11). Keyless, $0, stdlib-only.

R5-validated: GDELT DOC 2.0 is keyless, free, and redistributable with attribution, so the news
baseline is third-party-reproducible and the methodology is publishable. Each taxonomy topic's query
comes from `data/reference/gdelt_theme_map.json` — built from the SAME taxonomy seeds that drive our
corpus-side match, so both sides of a silence claim share one published definition.

HARD RATE LIMIT: GDELT asks for **one request per 5 seconds** (it returns HTTP 429 otherwise). That is
enforced here; a 24-topic daily pull takes ~2 minutes. Raw pulls are stored immutably (append-only,
date-stamped) so the baseline is rebuildable.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

API = "https://api.gdeltproject.org/api/v2/doc/doc"
MIN_INTERVAL_S = 5.2                      # GDELT: "one request every 5 seconds"
UA = "onscript-research/1.0 (+https://onscript.news)"
MAP_PATH = config.REPO_ROOT / "data" / "reference" / "gdelt_theme_map.json"
RAW_DIR = config.STATE / "gdelt"          # immutable raw pulls (on X: via the state junction)
BASELINE_DIR = config.DERIVED / "news_baseline"


def load_theme_map() -> dict:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_timeline(query: str, timespan: str = "1d") -> dict | None:
    """Normalized Volume Intensity timeline for a query (matched articles ÷ all monitored articles —
    already coverage-normalized by GDELT, which is why it is a fair cross-topic baseline).

    ALWAYS returns None on a failed/rate-limited pull rather than raising — GDELT answers a 429 with an
    HTTP error (and a plain-text body, not JSON). A None propagates to the silence board as an EXCLUDED
    topic, which is the whole 'a gap is not a silence' guard; a raise would defeat it."""
    url = f"{API}?{urllib.parse.urlencode({'query': query, 'mode': 'timelinevol', 'format': 'json', 'timespan': timespan})}"
    try:
        raw = _get(url)
    except Exception:
        return None                        # 429 / network / timeout -> honest gap, never a claim
    try:
        return json.loads(raw)
    except Exception:
        return None                        # GDELT returns a plain-text error body, not JSON


def timeline_mean(doc: dict | None) -> float | None:
    """Mean Volume Intensity across the returned series. None if the pull failed (an honest gap — the
    silence board must never read a failed pull as 'no news')."""
    if not doc:
        return None
    for series in doc.get("timeline") or []:
        pts = [p.get("value") for p in (series.get("data") or []) if p.get("value") is not None]
        if pts:
            return sum(pts) / len(pts)
    return None


def build_news_baseline(day: str, timespan: str = "1d", progress: bool = True) -> dict:
    """{topic_id: volume|None} for `day`, one polite GDELT pull per topic. Raw stored immutably.
    A None volume means the pull FAILED and that topic is excluded from silence scoring (gap ≠ silence)."""
    tmap = load_theme_map()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    out = {"schema_version": 1, "kind": "news-baseline", "day": day,
           "taxonomy_version": tmap.get("taxonomy_version"), "source": "GDELT DOC 2.0 (keyless)",
           "timespan": timespan, "topics": {}, "failed": []}
    raw_all = {}
    for tid, spec in (tmap.get("topics") or {}).items():
        doc = None
        try:
            doc = fetch_timeline(spec["query"], timespan=timespan)
        except Exception as e:
            if progress:
                print(f"  [gdelt] {tid} FAILED: {e}", flush=True)
        vol = timeline_mean(doc)
        out["topics"][tid] = vol
        if vol is None:
            out["failed"].append(tid)
        raw_all[tid] = doc
        if progress:
            print(f"  [gdelt] {tid}: {vol}", flush=True)
        time.sleep(MIN_INTERVAL_S)          # GDELT politeness: 1 req / 5s
    (RAW_DIR / f"{day}.json").write_text(json.dumps(raw_all), encoding="utf-8")
    (BASELINE_DIR / f"{day}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out
