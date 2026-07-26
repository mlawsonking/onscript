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

REDACTION (R-L, 2026-07-21). Those same release assets carry the name in their PAYLOAD — the raw
mirror and the ledger are built from statements that name the person, and `git` cannot reach a
release asset. The ruling: published release assets get the same privacy floor as every other
published surface, applied on persist, while the pristine append-only archive on X: stays untouched.
`redact()` is the span-replacing sibling of `is_suppressed()` that makes that possible, and it lives
HERE, next to the predicate, for the same reason `_tokens` reuses verify.fold_typography: a detector
and a redactor that disagree about what a match is would be worse than either alone.

A REDACTION LABEL IS ITSELF SUPPRESSED. `is_suppressed()` returns True for a label, so a redacted
row is dropped, held and purged exactly like the name it replaces. That is what keeps R-L a
release-asset change and nothing more: labels flow back into the cloud's restored state, but no
published site byte moves, because every display path already routes through this predicate.
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
_ALLOWLIST: tuple[str, ...] = ()
_DEFAULT_ROSTER_NAMES: dict[tuple[str, ...], str] | None = None
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
    global _SALT, _HASHES, _MAX_FORM_TOKENS, _META, _ALLOWLIST, _DEFAULT_ROSTER_NAMES, _GEN

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
    _ALLOWLIST = _assert_allowlist(allowlist_path)
    _DEFAULT_ROSTER_NAMES = None
    _assert_roster()


def _assert_allowlist(allowlist_path: Path | None = None) -> tuple[str, ...]:
    """Art. IV kill-fixture: real corpus strings that MUST survive. Admitting `sebastian` as a form
    makes this fail — correctly, since a `sebastian` rule would delete R-side county-delegation
    phrases in order to protect a D-side victim: an asymmetric INSTRUMENT."""
    ap = Path(allowlist_path or ALLOWLIST_PATH)
    try:
        doc = json.loads(ap.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PrivacyGateError(f"privacy allowlist unreadable at {ap}: {e}") from e
    allowed = tuple(str(value) for value in (doc.get("allow") or []))
    for s in allowed:
        if is_suppressed(s):
            raise PrivacyGateError(
                f"privacy form list matches an allowlisted legitimate phrase ({s!r}). A form is "
                "over-broad; narrow it rather than muting real speech."
            )
    return allowed


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


# A redaction label written by redact(). The suffix is the first 8 hex of the form's own HMAC — it
# exists ONLY to keep distinct forms distinct, so that redacting two different names inside two
# different JSON keys can never collapse them into one key (silent data loss on the next parse).
# It discloses nothing: it is a prefix of a value already published in privacy-forms.json.
# The pattern also matches the `<private-individual-A>` labels the 2026-07-21 history rewrite wrote,
# so history and live data are read by one rule.
_LABEL_RE = re.compile(r"<private-individual(?:-[0-9A-Za-z]+)?>")


def label_for(form_hash: str) -> str:
    """The stable, name-free stand-in for one suppressed form."""
    return f"<private-individual-{str(form_hash)[:8]}>"


def is_suppressed(text) -> bool:
    """THE predicate. Accepts any text: an n-gram, a talking-point label, a quote, a member
    sentence, or a paragraph of composite prose.

    Matches on TOKEN WINDOWS, which is exactly equivalent to space-padded substring containment:
    a padded " <surname> " cannot match inside a longer word ("<surname>s", "san<surname>"), while a
    possessive "<surname>’s" folds to tokens ["<surname>", "s"] so the 1-token window still matches.
    Never run this over the raw corpus —
    it is bounded by display rows (~hundreds/day x ~20 windows)."""
    # A redaction label stands in for a name and inherits the name's treatment (see module docstring).
    if isinstance(text, str) and text and _LABEL_RE.search(text):
        if _SALT is None:
            raise PrivacyGateError("privacy gate not loaded")
        return True
    return contains_admitted_form(text)


def contains_admitted_form(text) -> bool:
    """Is an admitted NAME form actually written here?

    The narrower half of is_suppressed(), and the difference matters in exactly one place: the guard
    that scans this repo's own source for plaintext names. A redaction label must be WITHHELD from
    publication (so is_suppressed says yes) while being the very evidence that no name is present
    (so this says no). Conflating them makes the repo-scan guard fire on the code that writes the
    label — a false positive that would train someone to weaken the guard."""
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


# --- redaction (R-L) ---------------------------------------------------------------------------
# `is_suppressed` answers "is a name in here"; `redact` answers "where, exactly". The second question
# is only asked on the persist path, over hundreds of megabytes, so it needs machinery the predicate
# does not: offsets that survive typography folding, and a BOUNDED memo. _MAC_MEMO is deliberately
# unbounded (it serves a few hundred display rows a day); pointing it at the corpus would grow one
# entry per distinct window until the runner died. These two never share a cache.
_SCAN_MEMO: dict[str, str | None] = {}
_SCAN_MEMO_MAX = 400_000
_SCAN_GEN: int = -1

# Whole-string results, for the short repeated strings that dominate the ledger walk: every entry
# carries its n-gram twice (key and "ngram"), and `daily` is millions of bioguides and dates drawn
# from a vocabulary of a few thousand. Hitting here skips tokenization entirely, which is the
# expensive half. Long strings (press-release bodies) are excluded — they are nearly all distinct,
# so caching them would only cost memory.
_TEXT_MEMO: dict[str, tuple] = {}
_TEXT_MEMO_MAX = 300_000
_TEXT_MEMO_MAXLEN = 200

_TOKEN_ANYCASE = re.compile(r"[A-Za-z0-9]+")

# ALIASED, never copied. _tokens() already folds through verify so the gate and the citation
# verifier can never disagree about what a character is; the offset-tracking fold below has to walk
# the same table by hand, and a second copy of it is a second thing to drift.
_TYPOGRAPHY = verify._TYPOGRAPHY
_TYPO_RE = verify._TYPO_RE


def _ensure_generation() -> None:
    """Drop both memos if the gate has been reloaded. Answers computed under a different salt or a
    different form list are not stale-but-close, they are WRONG, and a wrong 'clean' here is a
    published name."""
    global _SCAN_GEN
    if _SCAN_GEN != _GEN:
        _SCAN_MEMO.clear()
        _TEXT_MEMO.clear()
        _SCAN_GEN = _GEN


def _scan_window(window: str) -> str | None:
    """The form hash this exact token window matches, or None. Memoized within one gate generation."""
    _ensure_generation()
    if window in _SCAN_MEMO:
        return _SCAN_MEMO[window]
    h = _mac_with(_SALT, window)               # type: ignore[arg-type]
    hit = h if h in _HASHES else None
    if len(_SCAN_MEMO) >= _SCAN_MEMO_MAX:      # bounded: drop the whole memo rather than grow forever
        _SCAN_MEMO.clear()
    _SCAN_MEMO[window] = hit
    return hit


def _fold_offsets(text: str):
    """Fold typography, tracking where every folded character CAME FROM.

    Required because folding is not length-preserving ("…" -> "...", soft hyphen -> ""), so a span
    found in folded coordinates cannot be cut out of the original without this map. Returns
    (folded, starts, ends); starts/ends are None when the fold is the identity — the overwhelmingly
    common case, and the one worth not allocating two per-character lists for."""
    if not _TYPO_RE.search(text):
        return text, None, None
    out: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    pos = 0
    for m in _TYPO_RE.finditer(text):
        s, e = m.span()
        for i in range(pos, s):
            out.append(text[i]); starts.append(i); ends.append(i + 1)
        for c in _TYPOGRAPHY[m.group(0)]:      # every char of the replacement maps to the whole span
            out.append(c); starts.append(s); ends.append(e)
        pos = e
    for i in range(pos, len(text)):
        out.append(text[i]); starts.append(i); ends.append(i + 1)
    return "".join(out), starts, ends


def _suppressed_spans(text: str) -> list[tuple[int, int, str]]:
    """Leftmost-longest suppressed spans as [start, end) offsets into the ORIGINAL text."""
    folded, starts, ends = _fold_offsets(text)
    low = folded.lower()
    if len(low) == len(folded):
        toks = [(m.start(), m.end(), m.group(0)) for m in _TOKEN.finditer(low)]
    else:
        # Locale-expanding lowercase (U+0130 -> two chars) would desynchronize the offsets. Rare
        # enough to have a slow path, real enough that it must not corrupt one: tokenize the folded
        # text in its own coordinates and lowercase per token.
        toks = [(m.start(), m.end(), m.group(0).lower()) for m in _TOKEN_ANYCASE.finditer(folded)]
    spans: list[tuple[int, int, str]] = []
    sizes = sorted(_FORM_SIZES, reverse=True)   # longest first: a 3-token form beats its 2-token tail
    i, ntok = 0, len(toks)
    while i < ntok:
        for n in sizes:
            if i + n > ntok:
                continue
            hit = _scan_window(" ".join(t[2] for t in toks[i:i + n]))
            if hit:
                a, b = toks[i][0], toks[i + n - 1][1]
                if starts is not None:
                    a, b = starts[a], ends[b - 1]
                spans.append((a, b, hit))
                i += n
                break
        else:
            i += 1
    return spans


_PERSON_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_OFFICE_TITLE = re.compile(
    r"(?:rep\.?|representative|senator|congressman|congresswoman)\s*$", re.IGNORECASE
)
_TITLE_TOKENS = frozenset({"rep", "representative", "senator", "congressman", "congresswoman"})


def _normalized_words(value: str) -> tuple[str, ...]:
    return tuple(match.group(0).lower().strip(".'’-" ) for match in _PERSON_TOKEN.finditer(value or ""))


def _contains_run(container: tuple[str, ...], wanted: tuple[str, ...]) -> bool:
    return bool(wanted) and any(
        container[index:index + len(wanted)] == wanted
        for index in range(len(container) - len(wanted) + 1)
    )


def _roster_names(roster_map: dict | None = None) -> dict[tuple[str, ...], str]:
    global _DEFAULT_ROSTER_NAMES
    provided = roster_map is not None
    if roster_map is None:
        if _DEFAULT_ROSTER_NAMES is not None:
            return _DEFAULT_ROSTER_NAMES
        try:
            from pipeline import roster
            roster_map = roster.load()
        except Exception:
            roster_map = {}
    out: dict[tuple[str, ...], str] = {}
    for bioguide, row in (roster_map or {}).items():
        name = row.get("name") if isinstance(row, dict) else None
        words = _normalized_words(name or "")
        if len(words) >= 2:
            out[words] = str(bioguide)
    if not provided and _DEFAULT_ROSTER_NAMES is None:
        _DEFAULT_ROSTER_NAMES = out
    return out


def person_spans(text: str, statement: dict | None = None,
                 roster_map: dict | None = None) -> list[dict]:
    """Classify deterministic person spans before any n-gram is generated.

    Admitted HMAC forms are private. Roster names pass only for the statement's author or when an
    elected-office title supplies official context. Capitalized sequences that cannot be resolved
    through the roster or public allowlist are quarantined.
    """
    if not isinstance(text, str) or not text:
        return []
    rows: list[dict] = [
        {"start_char": start, "end_char": end, "classification": "private", "source": "hmac"}
        for start, end, _form_hash in _suppressed_spans(text)
    ]
    private_intervals = [(row["start_char"], row["end_char"]) for row in rows]
    roster_names = _roster_names(roster_map)
    author = ((statement or {}).get("member") or {}).get("bioguide")
    allow_runs = [_normalized_words(value) for value in _ALLOWLIST]

    tokens = list(_PERSON_TOKEN.finditer(text))
    index = 0
    while index < len(tokens):
        token = tokens[index].group(0).strip(".'’-" )
        if not token or not token[0].isupper() or token.isupper():
            index += 1
            continue
        end_index = index + 1
        while end_index < len(tokens) and end_index - index < 5:
            gap = text[tokens[end_index - 1].end():tokens[end_index].start()]
            next_token = tokens[end_index].group(0).strip(".'’-" )
            if (not gap.isspace() or not next_token or not next_token[0].isupper()
                    or next_token.isupper()):
                break
            end_index += 1
        if end_index - index < 2:
            index += 1
            continue

        candidate = tokens[index:end_index]
        start_char, end_char = candidate[0].start(), candidate[-1].end()
        if any(start_char < private_end and private_start < end_char
               for private_start, private_end in private_intervals):
            index = end_index
            continue
        words = tuple(match.group(0).lower().strip(".'’-" ) for match in candidate)
        bare_words = words[1:] if words and words[0] in _TITLE_TOKENS else words
        bioguide = roster_names.get(bare_words)
        prefix = text[max(0, start_char - 32):start_char]
        official = bool(bioguide and (bioguide == author or words[0] in _TITLE_TOKENS
                                      or _OFFICE_TITLE.search(prefix)))
        allowlisted = any(_contains_run(allowed, bare_words) or _contains_run(bare_words, allowed)
                          for allowed in allow_runs)
        if official or allowlisted:
            classification = "public_official" if official else "allowlisted"
            source = "roster" if official else "allowlist"
        else:
            classification = "quarantine"
            source = "capitalized_sequence"
        rows.append({
            "start_char": start_char,
            "end_char": end_char,
            "classification": classification,
            "source": source,
        })
        index = end_index
    return sorted(rows, key=lambda row: (row["start_char"], row["end_char"], row["classification"]))


def intervals_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """Return whether two half-open character intervals intersect."""
    return left[0] < right[1] and right[0] < left[1]


def suppress_person_spans(text: str, statement: dict | None = None,
                          roster_map: dict | None = None) -> tuple[str, list[dict]]:
    """Mask private and unresolved person spans with sentence boundaries.

    The mask preserves string length. Every candidate occurrence that intersects a held span is
    removed, and tokens on opposite sides cannot become a new adjacent phrase.
    """
    spans = person_spans(text, statement=statement, roster_map=roster_map)
    held = [row for row in spans if row["classification"] in {"private", "quarantine"}]
    if not held:
        return text, spans
    chars = list(text)
    for row in held:
        start, end = row["start_char"], row["end_char"]
        chars[start:end] = ["."] + [" "] * max(0, end - start - 1)
    return "".join(chars), spans


def redact(text):
    """Replace every suppressed span with its label. Returns (text, replacements).

    Non-strings and clean strings are returned UNCHANGED and untouched — callers rely on that to
    leave the bytes of an uncontaminated record exactly as the archive wrote them. Idempotent: a
    label contains no name tokens, so redacting twice is redacting once."""
    if not isinstance(text, str) or not text:
        return text, 0
    if _SALT is None:
        raise PrivacyGateError("privacy gate not loaded")
    _ensure_generation()
    cacheable = len(text) <= _TEXT_MEMO_MAXLEN
    if cacheable:
        hit = _TEXT_MEMO.get(text)
        if hit is not None:
            return hit
    spans = _suppressed_spans(text)
    if not spans:
        if cacheable:
            if len(_TEXT_MEMO) >= _TEXT_MEMO_MAX:
                _TEXT_MEMO.clear()
            _TEXT_MEMO[text] = (text, 0)
        return text, 0
    out, prev = [], 0
    for a, b, h in spans:
        out.append(text[prev:a])
        out.append(label_for(h))
        prev = b
    out.append(text[prev:])
    res = ("".join(out), len(spans))
    if cacheable:
        if len(_TEXT_MEMO) >= _TEXT_MEMO_MAX:
            _TEXT_MEMO.clear()
        _TEXT_MEMO[text] = res
    return res


def forms_fingerprint() -> str:
    """Identity of the loaded form list. A redaction cache keyed on this cannot survive the day a
    new name is admitted — which is exactly the day every previously-clean file must be rescanned."""
    return hashlib.sha256(
        ("|".join(sorted(_HASHES)) + f"|{_MAX_FORM_TOKENS}").encode("utf-8")
    ).hexdigest()


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
