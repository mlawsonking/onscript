"""docs/19 §4b req 4 — audit ALL published days for inadmissible (connective/attribution scaffold)
talking-point keys, and (with --write-corrections) append a dated corrections-log entry.

The connective-cluster defect is systemic to 4/5-gram cluster keys, not a single 07-17 event: any day
whose distiller admitted a scaffold key (a frame that terminates before its object, or an attribution
frame) published a talking point whose receipts do not support its line's meaning, even though every
string check passed. run_assemble now gates these at generation and site.daily_line_panel drops them at
render, so the site self-corrects on the next build; this script is the audit + the disclosure.

Read-only by default. Prints every flagged talking point per day.

    python scripts/audit_connective_keys.py                    # audit, print findings
    python scripts/audit_connective_keys.py --write-corrections # + append the corrections-log entry
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import boilerplate, config  # noqa: E402

DAYS = config.DERIVED / "days"
CORR = config.REFERENCE / "corrections.json"


def audit() -> list[dict]:
    flagged = []
    for p in sorted(DAYS.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {p.name}: {e}")
            continue
        day = data.get("day") or p.stem
        tps_by_party = data.get("talking_points") or {}
        for party, tps in tps_by_party.items():
            for tp in tps or []:
                if not isinstance(tp, dict):
                    continue
                label = tp.get("label", "")
                reason = boilerplate.scaffold_reason(label)
                if reason:
                    flagged.append({"day": day, "party": party, "label": label, "reason": reason,
                                    "member_count": tp.get("member_count"),          # would-have-been reach
                                    "n_citations": len(tp.get("citations") or [])})
    return flagged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-corrections", action="store_true",
                    help="append a dated corrections-log entry summarizing the correction")
    ap.add_argument("--logged", default=None, help="corrections 'logged' date (default: today via config)")
    args = ap.parse_args(argv)

    flagged = audit()
    days = sorted({f["day"] for f in flagged})
    from collections import Counter
    by_reason = Counter(f["reason"] for f in flagged)
    by_party = Counter(f["party"] for f in flagged)
    print(f"[audit] scanned {len(list(DAYS.glob('*.json')))} published day JSON(s)")
    print(f"[audit] flagged {len(flagged)} inadmissible (scaffold) talking-point key(s) across "
          f"{len(days)} day(s)")
    # docs/19 §4b (2nd pass) — CATEGORIZE by reason code, don't merely count. This is the honest
    # false-negative view for a conservative gate: which class each rejection falls in, both parties.
    print(f"[audit] by reason: {dict(by_reason)}")
    print(f"[audit] by party (Art. IV — the gate is party-blind; the skew tracks the caucus): {dict(by_party)}")
    for f in flagged:
        print(f"   {f['day']} [{f['party']}] {f['reason']} key={f['label']!r} "
              f"members={f['member_count']} citations={f['n_citations']}")
    # The rejected-candidates log: reason + would-have-been output (member reach), a dark-shelf view.
    log = config.DERIVED / "search" / "rejected_cluster_keys.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"scanned_days": len(list(DAYS.glob('*.json'))),
                               "by_reason": dict(by_reason), "by_party": dict(by_party),
                               "rejected": flagged}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[audit] rejected-candidates log -> {log}")

    if args.write_corrections:
        if not flagged:
            print("[corrections] nothing flagged — no corrections entry written")
            return 0
        from datetime import date
        logged = args.logged or date.today().isoformat()
        entry = {
            "logged": logged,
            "day": ", ".join(days) if len(days) <= 6 else f"{len(days)} days ({days[0]}…{days[-1]})",
            "description": (
                "Some daily talking points were bound by a connective or attribution phrase rather than "
                "a message — e.g. “into the trump administration’s” or “democratic "
                "colleagues in demanding the”. Each such key is string-valid (every cited statement "
                "contains it verbatim, which is why they clustered) and cleared the >=3 quorum, but the "
                "shared span is grammar, not a shared message, so the receipts pointed at unrelated "
                "topics. The citation verifier checks verbatim-ness, quorum and attribution — not whether "
                f"the shared span is a message — so no receipts audit could have caught it. Flagged "
                f"talking points: {len(flagged)} across {len(days)} day(s), categorized by reason "
                f"({dict(by_reason)}), both parties ({dict(by_party)} — the gate is party-blind; the "
                f"skew tracks the caucus)."),
            "resolution": (
                "A deterministic, party-blind key-admission gate now rejects connective/attribution "
                "scaffold keys at generation (run_assemble), and the quorum now counts only distinct "
                "document families whose source actually carries the key, so transitively-chained "
                "interlopers no longer count toward it. Already-published days are corrected at render "
                "time (the same display-time refresh the boilerplate and privacy guards use), so the "
                "affected talking points are dropped from every page on the next build. No number was "
                "changed and no record altered; the underlying statements are retained unaltered (Art. "
                "VI). The gate is applied identically to both parties (Art. IV)."),
        }
        existing = json.loads(CORR.read_text(encoding="utf-8")) if CORR.exists() else []
        existing.append(entry)
        CORR.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[corrections] appended entry logged {logged} -> {CORR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
