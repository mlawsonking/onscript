"""Citation back-join: attach >=3 real (member, date, URL) citations to the recorded flagship
findings, from the raw congress-press corpus. Deterministic + self-verifying: a citation counts
only if the phrase is a verbatim substring of the release text AND the member's party matches —
the project's citation-or-silence rule applied to the analysis findings (Constitution II / Art. VI:
committed numbers in data/derived/citations.json are reproducible from this committed module).

  python scripts/analysis/citations.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import config  # noqa: E402

RAW = config.RAW / "congress-press"
OUT = config.DERIVED / "citations.json"
_ws = re.compile(r"\s+")
PARTY = {"R": "Republican", "D": "Democrat"}

# (finding, phrase, party_letter, [month files to scan])
TARGETS = [
    ("biggest-unison: AHCA (R, 184, 2017-05-04)", "american health care act", "R", ["2017-05"]),
    ("biggest-unison: TCJA (R, 166, 2017-11-16)", "tax cuts and jobs act", "R", ["2017-11"]),
    ("biggest-unison: DACA (D, 153, 2017-09-05)", "deferred action for childhood arrivals", "D", ["2017-09"]),
    ("biggest-unison: HEROES Act (D, 151, 2020-05-15)", "the heroes act", "D", ["2020-05"]),
    ("forbidden-lexicon-R: by an illegal immigrant", "by an illegal immigrant", "R", ["2015-07"]),
    ("forbidden-lexicon-D: medicare the power to negotiate", "medicare the power to negotiate", "D",
     ["2019-09", "2019-10", "2019-12"]),
    ("forbidden-lexicon-D: pre-existing conditions framing", "discriminate against people with pre-existing",
     "D", ["2017-01", "2017-02"]),
    ("tick-tock: one big beautiful bill (R, 2025-07-03)", "one big beautiful bill", "R", ["2025-07"]),
]


def norm(t: str) -> str:
    return _ws.sub(" ", (t or "").lower()).strip()


def build_citations(targets=TARGETS, raw_dir: Path = RAW) -> dict:
    """Scan the raw corpus for each target phrase; return {label: {..., citations:[...]}}."""
    result = {}
    for label, phrase, pl, months in targets:
        np = norm(phrase)
        cites, seen, scanned = [], set(), 0
        for m in months:
            fp = raw_dir / f"{m}.jsonl"
            if not fp.exists():
                continue
            with fp.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    scanned += 1
                    mem = r.get("member") or {}
                    if not (mem.get("party", "")).startswith(PARTY[pl][:3]):
                        continue
                    if np in norm(r.get("text", "")):
                        u = r.get("url", "")
                        if u in seen:
                            continue
                        seen.add(u)
                        cites.append({"member": mem.get("name"), "bioguide": mem.get("bioguide_id"),
                                      "party": mem.get("party"), "state": mem.get("state"),
                                      "date": r.get("date"), "url": u, "title": r.get("title")})
        cites.sort(key=lambda c: c["date"] or "")
        result[label] = {"phrase": phrase, "party": pl, "n_citations": len(cites),
                         "meets_min_3": len(cites) >= 3, "scanned": scanned, "citations": cites[:6]}
    return result


def main() -> int:
    result = build_citations()
    for label, v in result.items():
        print(f"{'OK ' if v['meets_min_3'] else '!! '}{label}  \"{v['phrase']}\" -> {v['n_citations']} cites")
    config.DERIVED.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    ok = sum(1 for v in result.values() if v["meets_min_3"])
    print(f"WROTE {OUT}\n{ok}/{len(result)} findings now have >=3 real citations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
