"""Add name form(s) to the Article XIII suppression list.

Adding a name is a REVIEWED COMMIT, not a secret edit — the list is version-controlled, diffable and
dated, and the diff shows only opaque hashes. (The rejected alternative, keeping the plaintext list
in an Actions secret, makes every incident a hand-edit of a secrets-UI blob with a second copy on
X: that silently diverges.)

    python scripts/privacy_add.py --reason "..." <surname> <surname>   # plaintext on the CLI only
    python scripts/privacy_add.py --check sebastian                    # gates only, writes nothing

Pass the forms as ARGUMENTS. Never paste them into this file, a comment, a test, or a commit
message: the hashed list is pointless if the plaintext sits in source three files away, and
methodology.html publicly claims the list "does not disclose the names".
(tests/test_privacy.py::test_no_suppressed_name_is_written_anywhere_in_the_repo enforces this.)

BEFORE ADDING A FORM, it must pass all three admission gates (see pipeline/privacy.py):
  (a) no roster member's name contains it        -> checked here and permanently in the test suite
  (b) it matches nothing in the public allowlist -> checked here and at every load()
  (c) an archive scan shows zero legitimate uses -> YOUR JOB: scan the Alexandria ledgers first.
      This is not a formality. `sebastian` fails (c) with 37 legitimate uses (Sebastian Gorka; the
      Arkansas county delegation "perry pope pulaski sebastian and yell") and must never be admitted.

The plaintext never touches the repo. Only the HMACs are written.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import privacy  # noqa: E402


def _archive_hint(form: str) -> None:
    print(f"  [{form}] gate (c) is NOT machine-checked here — confirm zero legitimate uses in the "
          f"Alexandria ledgers before committing.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("forms", nargs="+", help="plaintext name forms (never written to disk)")
    ap.add_argument("--reason", default="private individuals named in members' statements (Art. XIII)")
    ap.add_argument("--check", action="store_true", help="run the gates, write nothing")
    a = ap.parse_args()

    salt = privacy._read_salt()
    doc = json.loads(privacy.FORMS_PATH.read_text(encoding="utf-8"))
    allow = json.loads(privacy.ALLOWLIST_PATH.read_text(encoding="utf-8")).get("allow") or []

    from pipeline import roster
    rmap = roster.load()

    new = []
    for raw in a.forms:
        form = " ".join(privacy._tokens(raw))
        if not form:
            print(f"  [{raw}] empty after tokenization — skipped")
            continue
        n = len(form.split())
        if n > int(doc.get("max_form_tokens") or 3):
            print(f"  [{form}] {n} tokens exceeds max_form_tokens — raise it deliberately or narrow")
            return 1
        # (0) MINIMUM TWO TOKENS — the Article IV structural rule.
        #
        # The first cut of this gate admitted BARE SURNAMES, and adversarial review measured the
        # cost on the real corpus: a lone surname form would have muted 38 victim-free statements
        # (one form), 16 (another), 60 across the four — to protect 11. A surname is not a person;
        # it is a word that a person shares with counties, countries, colleagues and cities. Only a
        # multi-token span identifies an individual, and the same measurement shows the 2-token
        # spans carry ZERO collateral. This rule is structural, not a threshold: it cannot be tuned
        # to admit one more name, because there is no bare surname that is safe.
        if n < 2:
            print(f"  [{form}] REJECTED: single-token form. A bare surname collides with legitimate "
                  f"speech (measured: up to 38 victim-free statements per surname). Article IV "
                  f"forbids an instrument that mutes one side — use the full-name span.")
            return 1
        # (a) roster
        hit = [b for b, m in (rmap or {}).items()
               if form in " ".join(privacy._tokens((m or {}).get("name") or ""))]
        if hit:
            print(f"  [{form}] REJECTED: collides with sitting member(s) {hit} (Art. IV)")
            return 1
        # (b) allowlist
        bad = [s for s in allow if form in " ".join(privacy._tokens(s))]
        if bad:
            print(f"  [{form}] REJECTED: matches allowlisted legitimate phrase(s) {bad} (Art. IV)")
            return 1
        _archive_hint(form)
        h = privacy._mac_with(salt, form)
        if h in set(doc.get("forms") or []):
            print(f"  [{form}] already present — skipped")
            continue
        new.append(h)

    if a.check:
        print(f"\ncheck only: {len(new)} form(s) would be added")
        return 0
    if not new:
        print("\nnothing to add")
        return 0

    doc["forms"] = sorted(set(doc.get("forms") or []) | set(new))
    doc["canary"] = privacy._mac_with(salt, privacy.CANARY_PLAINTEXT)
    doc.setdefault("entries", []).append({
        "added": dt.date.today().isoformat(), "forms": len(new), "reason": a.reason,
    })
    privacy.FORMS_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {len(new)} form(s) to {privacy.FORMS_PATH} (hashes only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
