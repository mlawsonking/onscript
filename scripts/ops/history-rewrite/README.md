# history-rewrite tooling (Article XIII)

The two scripts here performed the 2026-07-17 `git filter-repo` rewrite that replaced two
private-individual name forms with their redaction labels (`<private-individual-A>` /
`<private-individual-B>`) across all history — the Article XIII privacy floor applied to the git
object database, not just the working tree.

**These scripts contain NO names.** They display only SHA-8 hashes and counts, and they read the
actual name strings at runtime from `scratchpad/replacements.txt` — which is gitignored and was never
committed. Verified name-free against the live salted-HMAC privacy gate (`pipeline/privacy.py`): no
2–4-gram in either file trips `privacy.is_suppressed`. They are tracked here (re-homed from the
untracked `scratchpad/` per docs/18 §6) so the mechanism that enforced the floor is itself auditable
in the public repo — the same principle as the public `privacy-forms.json` (hashed) / `privacy-allowlist.json`.

- `extract_names.py` — slides 2–4-gram windows from every historical blob through the live gate; the
  minimal tripping spans ARE the gated names by construction; emits `scratchpad/replacements.txt`.
- `scan_all_blobs.py` — scans every object in the database for any residual literal form (run before
  the rewrite to complete the replacements list, and after to confirm zero remain).

Both assume the repo root as CWD and a populated `scratchpad/replacements.txt`. They are historical
record; the rewrite is done (0 occurrences remain, HEAD tree byte-identical).
