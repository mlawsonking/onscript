"""Article XIII (the privacy floor) enforcement — the suppression gate.

OnScript measures what ELECTED OFFICIALS say in public. It never publishes a private individual as
a data point, "regardless of how interesting" (docs/06-CONSTITUTION.md, Art. XIII — effectively
unamendable). The engine's n-grams do not know the difference between a member's message and a
crime victim's name, so this gate is the only thing between the ledger and a published name.

WHAT THIS IS NOT, and the distinction is load-bearing:
  * NOT a finding. A suppressed phrase produces no claim, no number, no absence story.
  * NOT a knob or a threshold. Article IV (the symmetric instrument) is untouched — no
    SYNC_MIN_MEMBERS, no DF cap, no per-party anything moves. This is content-neutral protection
    applied identically to both parties, and it is checked on load against the member roster so it
    provably cannot silence an elected official.
  * NOT a citation-integrity mechanism. The citation verifier has NO opinion about privacy, by
    construction — the members really did type these words, so `is_verbatim` passes and a receipts
    audit can never catch this. That is why the gate must sit BEFORE the LLM (see run_assemble):
    otherwise the Sonnet voice launders a private name into fluent, verifier-clean prose.

WHY THE LIST IS HASHED. A plaintext list of crime victims, curated by us and annotated with the
fact that they are worth protecting, committed to a repo that goes public at S3, is categorically
worse than the incidental n-gram it fixes — and `git rm` does not help, because history IS the
publication. So the committed list holds only HMAC-SHA256 of each name form under a 32-byte secret
salt. Public: the rule, the count, the dates, the code, the tests, the allowlist, the roster
guarantee, and the (opaque) list. Not public: the name forms themselves.

WHY HMAC AND NOT sha256(form). Unsalted hashes of low-entropy human names are rainbow-tableable in
minutes from a corpus the adversary already has (the members' own .gov releases we link to). A
keyed MAC is not dictionary-attackable without the salt.

THE CANARY IS THE POINT. A wrong/absent/truncated salt is caught at load by recomputing the canary,
and the run DIES (PrivacyGateError). There is no fail-open path. This is the self-check that the
obvious alternative — keeping the plaintext list itself in an Actions secret — cannot have: two
copies of a hand-edited secret silently diverge, and the failure mode of a diverged privacy list is
SILENT UNDER-SUPPRESSION, i.e. exactly the violation being fixed. Fail loud beats fail silent.

FORM ADMISSION IS EVIDENCE-GATED, not categorical. The tempting rule "never admit a bare surname"
is wrong and was measured to be wrong: full-name-only forms miss 7 of the 16 contaminated pages,
because n-grams slide over a name, stranding a lone surname mid-phrase ("shot <SURNAME> during an
immigration enforcement operation") where no full-name form can reach it. A form of any
token length is admissible iff (a) no roster member's name contains it, (b) it matches nothing in
the public allowlist kill-fixture, and (c) an archive scan shows zero legitimate uses. All three are
locked as permanent tests in tests/test_privacy.py — (c) is why `sebastian` is REJECTED (37
legitimate uses across the 25-year archive: Sebastian Gorka, and the Arkansas county delegation
"perry pope pulaski sebastian and yell"), while a form whose only archive occurrences ARE the
incident is admitted. `sebastian` is safe to name here precisely because it is NOT suppressed — it
is legitimate speech this gate protects, and it lives in the public allowlist for that reason.

NOTHING IN THIS REPO MAY NAME A SUPPRESSED FORM. Not this docstring, not a comment, not a test
fixture, not a commit message. The hashing is pointless if the plaintext is spelled out three files
away, and the methodology page tells the public "it does not disclose the names" — that sentence
must stay true. Tests assert suppression through is_suppressed(), never against literal tokens.

THE SALT LIVES OUTSIDE data/reference/ ON PURPOSE. `.github/workflows/assemble.yml` runs
`tar -czf state.tar.gz data/state data/reference` and uploads it as a RELEASE ASSET — public on a
public repo. A salt placed under data/reference/ would be gitignored (looking safe) and published
anyway, inside a tarball nobody audits. Do not move it there.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path

from pipeline import verify

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "data" / "reference"
DERIVED = ROOT / "data" / "derived"
SITE_PUBLIC = ROOT / "site" / "public"

FORMS_PATH = REFERENCE / "privacy-forms.json"
ALLOWLIST_PATH = REFERENCE / "privacy-allowlist.json"

# Outside the repo AND outside the tarred data/reference/ (see module docstring).
DEFAULT_SALT_FILE = Path(r"X:\onscript-data\reference\privacy-salt.txt")

CANARY_PLAINTEXT = "onscript-privacy-canary-v1"

_TOKEN = re.compile(r"[a-z0-9]+")


class PrivacyGateError(RuntimeError):
    """The privacy gate could not be established. NEVER caught to continue publishing."""


# --- module state -----------------------------------------------------------------------------
_SALT: bytes | None = None
_HASHES: frozenset[str] = frozenset()
_MAX_FORM_TOKENS: int = 3
_FORM_SIZES: list[int] = [1, 2, 3]
_META: dict = {}
_GEN: int = 0            # bumped on every (re)load so the mac memo cannot serve a stale salt
_MAC_MEMO: dict = {}


def _tokens(text: str) -> list[str]:
    """Fold smart punctuation to ASCII, then split into word tokens.

    Reusing verify.fold_typography is MANDATORY, not hygiene: 4 of the 16 contaminated n-grams carry
    U+2019 (a possessive, "<SURNAME>’s"), and sharing the folder with the citation verifier guarantees the privacy
    gate and the verifier can never disagree about what a character is."""
    return _TOKEN.findall(verify.fold_typography(text or "").lower())


def _mac_with(salt: bytes, s: str) -> str:
    return hmac.new(salt, s.encode("utf-8"), hashlib.sha256).hexdigest()


def _mac(s: str) -> str:
    key = (_GEN, s)
    v = _MAC_MEMO.get(key)
    if v is None:
        if _SALT is None:
            raise PrivacyGateError("privacy gate not loaded")
        v = _MAC_MEMO[key] = _mac_with(_SALT, s)
    return v


def _read_salt() -> bytes:
    """Resolve the one secret. PRIVACY_TEST_SALT is the ONLY bypass and is test-only."""
    t = os.environ.get("PRIVACY_TEST_SALT")
    if t:
        return t.encode("utf-8")
    s = os.environ.get("PRIVACY_SALT", "").strip()
    if s:
        return s.encode("utf-8")
    p = Path(os.environ.get("PRIVACY_SALT_FILE") or DEFAULT_SALT_FILE)
    try:
        v = p.read_text(encoding="utf-8").strip()
    except OSError:
        v = ""
    if v:
        return v.encode("utf-8")
    raise PrivacyGateError(
        "PRIVACY_SALT is not set and no salt file was readable. The Article XIII privacy gate "
        "cannot be established, so publishing is refused (there is no fail-open path). Set the "
        f"PRIVACY_SALT secret/env, or place the salt at {p}."
    )


def load(*, forms_path: Path | None = None, allowlist_path: Path | None = None) -> None:
    """Establish the gate. Raises PrivacyGateError on ANY failure — never fails open."""
    global _SALT, _HASHES, _MAX_FORM_TOKENS, _META, _GEN

    salt = _read_salt()
    fp = Path(forms_path or FORMS_PATH)
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PrivacyGateError(f"privacy form list unreadable at {fp}: {e}") from e

    canary = doc.get("canary")
    if not canary or not hmac.compare_digest(_mac_with(salt, CANARY_PLAINTEXT), str(canary)):
        # The check a plaintext-secret list cannot have. A diverged/wrong salt would otherwise
        # silently under-suppress forever.
        raise PrivacyGateError(
            "privacy canary mismatch: the PRIVACY_SALT in this environment does not match the salt "
            "the committed form list was built with. Suppression would silently under-apply, so the "
            "run is refused."
        )

    _SALT = salt
    _HASHES = frozenset(str(h) for h in (doc.get("forms") or []))
    _MAX_FORM_TOKENS = int(doc.get("max_form_tokens") or 3)
    # NOTE: `form_sizes` is deliberately NOT read from the file — see _FORM_SIZES below.
    # Which window sizes actually occur in the list. Hashes do not reveal their own token count, so
    # this is carried in the file. It leaks only a length distribution (max_form_tokens already
    # bounds that) and it is what makes the whole-output sweep affordable: without it every text is
    # hashed at every window size 1..max, most of which can never match anything.
    # FAIL-OPEN KILLED (adversarial review, 2026-07-16). The first cut read the window sizes FROM the
    # forms file, which was pinned to [1]. Every multi-token form would then be hashed at load and
    # NEVER CHECKED at match time — the gate would report itself armed while silently ignoring the
    # only forms Article IV permits (a 3-token full name). It failed OPEN, and the file's own
    # `max_form_tokens: 3` advertised a capability the predicate did not have.
    #
    # The window range is now DERIVED from max_form_tokens and cannot be narrowed by data. A form
    # that is hashed is a form that is checked, by construction. The cost is a few extra hash probes
    # per row — irrelevant next to a gate that lies about being armed.
    global _FORM_SIZES
    _FORM_SIZES = list(range(1, _MAX_FORM_TOKENS + 1))
    _META = {k: doc.get(k) for k in ("version", "persons", "entries")}
    _GEN += 1
    _MAC_MEMO.clear()

    # An EMPTY-but-valid list is a legitimate state, not a fault: it is the state before the first
    # name is ever suppressed, and it is the state `scripts/privacy_add.py` must be able to write
    # into. Raising here made the gate un-bootstrappable (the tool imports this module, the import
    # loads, the load raised — the fail-closed check ate its own tooling). Fail-closed lives where
    # it belongs: a MISSING or CORRUPT file, a bad canary (wrong/absent salt), or an allowlist/roster
    # violation still raise, and is_suppressed() still raises when the gate never loaded at all.
    # An empty list suppresses nothing, which is exactly what it should do.
    _assert_allowlist(allowlist_path)
    _assert_roster()


def _assert_allowlist(allowlist_path: Path | None = None) -> None:
    """Art. IV kill-fixture: real corpus strings that MUST survive. Admitting `sebastian` as a form
    makes this fail — correctly, since a `sebastian` rule would delete R-side county-delegation
    phrases in order to protect a D-side victim: an asymmetric INSTRUMENT."""
    ap = Path(allowlist_path or ALLOWLIST_PATH)
    try:
        doc = json.loads(ap.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PrivacyGateError(f"privacy allowlist unreadable at {ap}: {e}") from e
    for s in doc.get("allow") or []:
        if is_suppressed(s):
            raise PrivacyGateError(
                f"privacy form list matches an allowlisted legitimate phrase ({s!r}). A form is "
                "over-broad; narrow it rather than muting real speech."
            )


def _assert_roster() -> None:
    """Art. IV: the gate can never mute an elected official.

    A MISSING roster is not a privacy failure (it is a data-availability issue, and the permanent
    test in tests/test_privacy.py is the real gate), so we skip-and-log rather than break the run.
    A COLLISION is a hard failure: it means a sworn member shares a name form with a suppressed
    private individual, and the form must be narrowed rather than silently muting that member."""
    try:
        from pipeline import roster
        rmap = roster.load()
    except Exception as e:  # noqa: BLE001
        print(f"[privacy] roster unavailable, skipping the roster collision check ({e})")
        return
    for bioguide, m in (rmap or {}).items():
        name = (m or {}).get("name") if isinstance(m, dict) else None
        if name and is_suppressed(name):
            raise PrivacyGateError(
                f"privacy form list matches a sitting member's name ({bioguide}). The gate must "
                "never silence an elected official (Art. IV); narrow the form."
            )


def is_suppressed(text) -> bool:
    """THE predicate. Accepts any text: an n-gram, a talking-point label, a quote, a member
    sentence, or a paragraph of composite prose.

    Matches on TOKEN WINDOWS, which is exactly equivalent to space-padded substring containment:
    a padded " <surname> " cannot match inside a longer word ("<surname>s", "san<surname>"), while a
    possessive "<surname>’s" folds to tokens ["<surname>", "s"] so the 1-token window still matches.
    Never run this over the raw corpus —
    it is bounded by display rows (~hundreds/day x ~20 windows)."""
    if not isinstance(text, str) or not text:
        return False
    if _SALT is None:
        raise PrivacyGateError("privacy gate not loaded")
    t = _tokens(text)
    for n in _FORM_SIZES:
        for i in range(len(t) - n + 1):
            if _mac(" ".join(t[i:i + n])) in _HASHES:
                return True
    return False


def meta() -> dict:
    """Public, name-free metadata for the methodology page."""
    return dict(_META)


# --- filters ----------------------------------------------------------------------------------
def filter_rows(rows, key: str = "ngram") -> tuple[list, int]:
    """Drop any row whose phrase carries a suppressed name. Returns (kept, dropped_count)."""
    kept, dropped = [], 0
    for r in rows or []:
        val = r.get(key) if isinstance(r, dict) else r
        if is_suppressed(val if isinstance(val, str) else ""):
            dropped += 1
            continue
        kept.append(r)
    return kept, dropped


def _tp_trips(tp) -> bool:
    if not isinstance(tp, dict):
        return False
    if is_suppressed(tp.get("label") or "") or is_suppressed(tp.get("quote") or ""):
        return True
    for f in tp.get("fragments") or []:
        txt = f.get("text") if isinstance(f, dict) else f
        if is_suppressed(txt if isinstance(txt, str) else ""):
            return True
    for c in tp.get("citations") or []:
        if isinstance(c, dict) and is_suppressed(c.get("quote") or ""):
            return True
    return False


def filter_talking_points(tps) -> tuple[list, int]:
    """Drop a whole talking point if ANY of its surfaces names a private individual. The TP is the
    unit because its label, quote, fragments and citations all render together."""
    kept, dropped = [], 0
    for tp in tps or []:
        if _tp_trips(tp):
            dropped += 1
            continue
        kept.append(tp)
    return kept, dropped


def filter_stats(stats) -> tuple[dict, int]:
    """Filter a distill STATS block (stats.talking_points + stats.top_phrase)."""
    if not isinstance(stats, dict):
        return stats, 0
    out = dict(stats)
    tps, dropped = filter_talking_points(stats.get("talking_points") or [])
    out["talking_points"] = tps
    tp = stats.get("top_phrase")
    if isinstance(tp, dict) and is_suppressed(tp.get("text") or ""):
        out["top_phrase"] = None
        dropped += 1
    return out, dropped


def purge_derived(dry_run: bool = False) -> list[str]:
    """Unlink every contaminated derived phrase page AND its rendered HTML twin.

    Required, not belt: nothing in pipeline/site.py ever unlinks (build_site only writes) and
    site/public is git-tracked (Vercel deploys from the repo), so a render-time SKIP alone would
    leave every contaminated phrase page live at its public URL forever."""
    removed: list[str] = []
    pdir = DERIVED / "phrases"
    if not pdir.exists():
        return removed
    for p in sorted(pdir.glob("*.json")):
        if p.stem == "top":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not is_suppressed((d or {}).get("ngram") or ""):
            continue
        twin = SITE_PUBLIC / "phrases" / f"{p.stem}.html"
        for target in (p, twin):
            if target.exists():
                removed.append(str(target.relative_to(ROOT)).replace("\\", "/"))
                if not dry_run:
                    target.unlink()
    return removed


# Establish the gate at import. No fail-open path: a module that imports privacy and keeps running
# has a working gate, or the process is already dead.
load()
