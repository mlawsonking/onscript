# Session history

> Editorial note (2026-07-23): prose normalized under docs/25.
Findings, decisions, and
> chronology are unchanged.
The original wording is available at commit `68ef5ce`.

This file contains OnScript's dated session record.
New sessions append an entry here and keep
the current-status section in `CLAUDE.md` short.
Each entry uses four fields where they apply:
outcome, evidence, decision, and next action.

## History


### 2026-07-23 (Session 44, Fable, ~02:05Z)

documentation voice ruled. `docs/25-DOCUMENTATION-VOICE-BRIEF.md` (binding) authorizes Codex to
rewrite all 29 tracked Markdown files in a plain human voice.
The audit was reproduced before ruling: 2,617 U+2014 across the corpus, per-file counts matching.
Rulings: R-V1 one-time in-place normalization of the historical records (docs/03, docs/04, docs/13,
and the claude.md session history) with a dated note in each citing its pre-rewrite SHA; verdict
words, dates, quantities, SHAs, supersession chains, and entry order are immutable; supersedes
docs/24 §1.6 for style only; grants no authority to revise history.
R-V2: docs/06 gets the strictest gate (article numbers and operative content stable, per-article
before/after table, Michael spot-checks).
R-V3: claude.md splits into a short operating file plus `docs/26-SESSION-HISTORY.md`; every standing
rule and trap is extracted to a consolidated section first, with an operative-facts ledger proving
nothing in force was lost; future sessions append history entries to docs/26 in the docs/25 house
style.
R-V4: terms anchored in code or product keep their names and get plain definitions; unanchored
rhetoric is rewritten; "failure test" becomes failure/regression/mutation test in prose.
Prompt files, registration JSONs, code, and agents.md are out of scope; a narrow carve-out lets
tests that assert doc wording be updated, each listed.
Four staged commits (operating surface → canonical/governance → research/history → subsystem +
consistency), fact-preservation diffs, link checks, suite green per stage, no push.
The docs/24 push plan is unchanged and the micro-commit `166b4de` is confirmed present.
Bus: #197 (Michael reviews stages, then pushes after the stabilization pushes).
Nothing pushed, dispatched, or posted this session.

### 2026-07-23 (Session 43c, Fable, same chat, ~01:35Z)

wave 2 + remediation validated.
NO blockers; docs/24 §10 orders one closing micro-commit; §11 declares the surface program complete
after it.
Suite reproduced 477/0 via the house runner.
The delta adversarial review (opus) confirmed the launch-critical W2-A inverse: "local" is a
presence check on `GITHUB_ACTIONS` (even `=false` takes the production path), the CI flush path is
byte-identical and test-locked, and the local-preview proof is a real-tree byte-identity test, not a
double-stub, the S40 footgun is closed.
Feed entries are counts-only under both a content test and an AST source guard; R1 verified
relocated+wrapped at the sole production caller; workflows untouched by all four commits; the rebase
over the evening cloud commits is undamaged (packet remapped
`2a8e596`/`b39db56`/`224d130`/`03da03d`, docs `c6736c0`/`59a07bb`).
Micro-commit (§10, gates only the wave-2 push): wrap the unwrapped favicon copyfile at
`build_site()` top (a missing brand asset would kill render₁ pre-post and fire a false dead-man.
R1's class), drop 404.html from the sitemap, add a code-computed Atom `<author>`, and darken the
`faint` token to ≥4.5:1 (ruled; decorative dividers/axes stay, 1.4.11-exempt). push plan: tonight
`git push origin 4c16703:main` (docs+packet+remediation; window open, next cron ~09:30Z) → tomorrow
read the 09:30Z collect log (P2 bootstrap timing, R4) and the 11:30Z assemble log (green · two
renders · posts.html carrying the same run's thread, which is also the green posting day W2-A waits
for) → on green, push the rest incl. the micro-commit. §11: no further external-worker surface work
without a new ruling; internal reserved items unchanged (silence_board by 08-03, needs an Opus
session this week; Mon 07-27 flip; sync_by_party; day 07-09).

### 2026-07-22 (Session 43b, Fable, same chat, ~23:15Z)

The codex delivery validated independently (Art. xvi), four commits
`a9d3af6`/`eea390c`/`f32ccc1`/`3ef985b` on top of the rebased S43 docs commit `dacdf73`, all
unpushed.
Scope audit PASS (15 files, zero forbidden paths, rename-detection clean; config diff = one additive
`REPO_URL`; docs additive; packets independently revertable; author = Michael's account).
Suite reproduced: 459/0 via `tests/run_tests.py`, note for every future session: there is NO pytest
on this box; the house runner is the only truthful local invocation (`python -m pytest` fails,
`unittest discover` finds 0).
Adversarial review (opus): P0-A/P0-B/P1 pass in full, incl. the partial-manifest fix verified
against the live manifest schema, the curve-SVG axis-label leak closed, and P2's cache keyed on a
source fingerprint so a removed source re-verifies rather than trusting the cache. one blocker
(docs/24 §8 R1): `build_phrase_evidence` is called unwrapped in `build_derived` before the
day-summary write, a throw fails the unattended run and loses `days/{focus}.json`; the sibling calls
in `deterministic.py:37-48` are wrapped for this (§0 streak invariant); the fix is wrap +
relocate-after-day-write, failure tested.
Riders: R2 dark-path labelers (`_member_label`/`_unison_offices`) can still emit bare bioguides,
must harden before the 08-24/09-07 flips, do it now; R3 peak-vs-grounded adjacent-number reconciling
clause; R4 the P2 cost claim (45.7s bootstrap/0.53s warm) is not locally reproducible, the first
cloud collect is the live measurement, skip-and-log bounds the downside. wave 2 authorized (docs/24
§9): W2-A post_bluesky local-write safety (S40 finding 9; GITHUB_ACTIONS-gated, inverse failure test
vital), W2-B Atom feed/sitemap/robots (og privacy rule extended: code-computed fields only, never
composite prose), W2-C accessibility polish.
Wave 2 pushes only after the first green live P0-B/P2 exercise; W2-A's push also waits for a green
posting day.
Reserved for internal sessions, not Codex: silence_board wiring (r-b deadline Mon 08-03, an Opus
session must run this within days), the 07-27 nomenclature flip + r-a riders, sync_by_party
backfill.
Push window was open at writing (both 22:3xZ crons complete); the remediated packet pushes tonight
on Michael's act (#195), wave 2 after tomorrow's green.

### 2026-07-22 (Session 43, Fable, new chat, ~21:45Z)

the codex packet adjudicated. `docs/24-PUBLIC-SURFACE-STABILIZATION-BRIEF.md` (binding) is the work
order for an external implementer (Codex); every packet premise was independently re-verified before
ruling (Art. xvi, four parallel read-only sweeps, not the requester's summary).
Decisions: P0-A APPROVE (stale posture: About still says "have not begun posting" at `site.py:1910`,
README:71 still claims "no remote exists yet", docs/07 marks S2-current, accounts unlinked, zero
GitHub/`data-latest` links) · P0-B APPROVE (CONFIRMED on HEAD `265e576`: the same commit carries
`post-2026-07-21.json` `posted:true` and a `posts.html` whose newest entry is 07-20, under "any post
that does not appear here is not ours", render is step 5, post step 7, one commit step 9; plus a
defect the request missed: `posted_threads()` ignores `partial`, so a partial manifest would render
its full intended thread as authenticated; fix = second render step post-post/pre-commit with
restore-on-failure, partial-accurate rendering, time-scoped claim) · P1 APPROVE (CONFIRMED and ugly:
51/277 phrase pages carry 2013–2024 observations and 20 render bare bioguides.
"2013-04-17 by S001168" directly above "Our corpus begins 2025-01"; mechanism is `alexandria.merge`
writing the 25-yr ledger into state + `build_derived` with no epoch filter; also a live R6/seam
exposure.
Ruled: render-time `STAGE1_EPOCH` gate only, derived files/ledger/alexandria untouched, pre-epoch
first-sayers render unattributed-accurate, zero-in-window phrases drop from the index but keep their
permanent page) · P2 approve-staged (the search page promises "the members who carried it"; phrase
pages deliver an aggregate count.
Stage A copy-alignment mandatory; Stage B peak-day receipts gated: new deterministic evidence slice,
identity+source only, no quote text, `_unit_key` joint-once counting, verifier-grade containment,
quorum-of-3-or-silence, privacy-before-write, measured cost ≤60s steady/≤15min bootstrap,
defer-not-improvise on any gate failure; wayback via the existing pure `_wayback_url`, no
stored/network) · P3 DEFER (measured: Pillow absent from the stdlib-only CI, per-page PNGs churn a
committed 5.5 MB public tree, the requester's own defer rule applies).
Release stays Michael's act: push in a clean cron window, then the next scheduled assemble is P0-B's
live exercise, read its log per Art. xvi.
Bus: #195 filed (review evidence → push → watch). now.md corrected (still said the repo was
private).
A collect was in flight all session; nothing pushed, nothing dispatched.

### 2026-07-22 (Session 42, Fable, same chat)

the repo IS PUBLIC. #132 closed. the S2→S3 ladder IS complete, every launch act is done: site live
(07-21) · posting live (07-21) · announce live (07-21) · repo public (07-22, Michael's flip,
verified `PUBLIC` via the API).
The protection is now critical in full public view: prompts, thresholds, the nightly symmetry audit,
the corrections log (4 entries), the whole session canon including every defect and every ruling,
the posture the constitution was written for.
What remains is the operating rhythm, all already scheduled: Mon 07-27 `nomenclature_tags` (first
health-gated Monday flip, r-a riders) → 08-03 `archive` + silence_board wiring deadline (r-b) →
~08-05 P1 (Michael's first editorial act, draft on X:) → the §7.3 cadence through the ~10-12 freeze.
Standing Michael items, all at leisure: the Monday digest glance · the GitHub purge ticket (both
rewrites) · attorney hour #110/#105 (now incl. the revocable r-l ruling) · the DCinbox reply send
(S41) · optional pins/quote-posts.
Grinding lanes open: Deep Archive (111/112 when the crawl reaches 2012; 117–119; SD.8),
HX.1/HX.3/HX.6 design sessions, the October registration wave (incl. banked HX.9).

### 2026-07-22 (Session 41, Fable, same chat)

the DCINBOX answer arrived, the free-bulk era is dead; access is now paid. ruling: DEFER the
purchase; #133 closed (its premise no longer exists).
Also: S40's r-l verification means the visibility flip is now purely Michael's go.
Cormack replied warmly (she read the site), attached a sample CSV (`request_dcinbox.csv`.
Michael to save to `X:\onscript-data\dcinbox\sample\` for the eventual format check), and explained:
ai-scraper traffic destroyed her $15/mo open-hosting model; DCinbox is now a research service.
Option 1: $350 curated 2010–2012 extract · Option 2: $1,300/yr engagement.
Ruling grounds: docs/15 D3-A already classifies the lane not-blocking (the academic lane covers
2005–2008); nothing published or scheduled depends on 2010–2012; the generator policy buys one-time
capex when needed, and the need arrives only when an sd-lane finding in that window reaches its
publication gate wanting the independent cross-check.
Re-file condition (binding): when a specific 2010–2012 claim reaches publication-gating, that
session files "purchase the DCinbox 2010–2012 extract ($350, Option 1)" naming the claim it
validates, never before.
Option 2 is disproportionate to the cost posture absent a major scope change.
Reply drafted to `X:\onscript-data\drafts\EMAIL-dcinbox-reply.txt` (defer-with-warmth: accurate
self-funded posture, sample-fit promised, asks whether Option 1 stays available months out, offers
engineering reciprocity).
Michael's send.
The relationship is the asset; the deferral preserves it at $0.

### 2026-07-22 (Session 40, Opus, the Wednesday prep session, ~01:10–04:00 local, deliberately AHEAD of the 09:30Z cron)

The s35 posting-hygiene order is done (all five, plus S34 follow-ups 1/2/3) and r-l IS built + wired
into both workflows.
433 tests green, every fix mutation-verified.
Nothing posted, no workflow dispatched, `POSTING_ENABLED` untouched, no FEATURES flag moved, repo
still private.
1. `_reconcile_prior` Reproduced before it was fixed, the S8e backstop has been a silent no-op since
   it was written: `_list_manifests` returned glob strings, `util.read_json` calls `path.exists()`,
   so every manifest raised `AttributeError` into the skip-and-log (`alerted=[]`, `ntfy calls=0`).
Now returns `Path`s.
The test is the live fix: every existing reconcile test stubs `_list_manifests` and `read_json`
together, strings on both sides, so the two halves were never run against each other, the suite
stayed green while the feature did nothing.
The new test stubs only ntfy + `config.DERIVED`; filesystem, path types and both JSON helpers are
real.
It is the guard against a hard-kill between the two parties' posts, a durable one-sided thread,
and posting went live 07-21.
2.
Collision recovery now resumes instead of truncating: it returned `posts_written=0`, leaving a bare
head post with no receipts reply, the only post carrying the citation link, which no later run would
add, because the manifest already recorded the party as posted. `_existing_replies` lists what is
already hanging off the recovered root (bounded because of the design: a reply's tid-rkey always
sorts above its root's) and only the missing tail is posted.
If the live replies are not a prefix of the thread in hand the day was re-authored between runs, so
it refuses rather than splicing two threads together; `on_root` has already fired, so the manifest
holds `root_uri`+`partial=True` and the dead-man fires.
3. sentence-aware packing (the live D thread read "our 99 statements today do" / "not converge on
   additional shared messages"), with an abbreviation guard so it never cuts after
   "Rep."/"U.S."/"No."; the old word-packer is kept as `_pack_words` for a sentence longer than one
   post.
The critical test is not the pretty one, the concatenation of the posts is always the
input's words, in order.
An ugly break is cosmetic; a dropped word is a fabricated quote.
4. first-sayer wording on all three surfaces.
P2 v1.3 (public, versioned), the receipts post, and the phrase page (`First said` → `First recorded
in our corpus`).
The launch threads were correct and symmetric (the D voice credited a Republican, the R voice a
Democrat, first-appearance is corpus-wide), but unqualified it reads as a claim the member coined
the phrase, and the live receipts line said "first recorded 2025-01-03", which is the corpus's own
first day: left-censoring rendered as discovery.
5. `post_bluesky.SITE` → `config.SITE_URL` (a second hardcoded literal on the one post that carries
   the citations).
6. r-l shipped: `pipeline/redact.py` + `privacy.redact()`, in the state-persist step of both
   workflows, before the tar, with NO `|| true`, a failure stops the job before the upload (a missed
   upload costs one cycle; a leaked one is permanent).
The design decision that keeps r-l inside its scope: a redaction label is itself suppressed, so
labeled rows are dropped/held/purged by the display paths as named ones were, labels flow
back into the cloud's state and no published site byte moves.
The narrower question "is a name actually written here" is now `contains_admitted_form()`, which the
repo-scan guard uses; conflating the two made that guard fire on the code that writes the label.
Records are parsed, never grepped: with `ensure_ascii=True` a possessive is stored as the six
characters `’`, whose tokens are nothing like the value's, so a grep-shaped scan misses the
possessive forms the gate exists to catch.
Only contaminated records are rewritten (an untouched record keeps its original bytes); distinct
forms get distinct labels so two n-gram keys can never collapse into one, and a collision is a hard
stop; every changed file is immediately re-scanned and must come back clean. proven AT scale on the
real 448 MB `ledger.json`: 156 occurrences redacted, keys 471,810 → 471,810 identical, re-check 0
remaining, 76 keys relabeled, untouched entries byte-identical. `data/reference` measured 0
occurrences across 26 files, so the redactor never modifies a tracked file and cannot fight the `git
checkout -- data/reference` restore.
7.
Two findings about the r-l blocker itself, both of which change the #132 gate spec.
(a) `statements.jsonl.gz` Is a carrier nobody had measured, And it ties for the largest at 205 (the
same count as the raw month it is normalized from).
96.6 MB of gzip inside `state.tar.gz`; a scanner that reads files as text sees gzip as noise and
reports it clean, which is why S38's whole-worktree scan lists seven carriers and not this one.
The redactor decompresses, scans, recompresses.
(b) the assets carry ~8× what the spec says. The numbers reconcile.
S39's rider says "the name 44×/42×".
Measured on the live `data-latest` assets with the production gate,
`data/raw/congress-press/2026-07.jsonl` alone holds 205 occurrences across 52 of its 2,414 records,
and the full census IS 693 IN 4 OF 48 files (raw 2026-07.jsonl 205 · statements.jsonl.gz 205 ·
ledger.json 156 · extractions.jsonl 127), with `data/reference` at 0 across 26 files (so the
redactor never touches a tracked file) and all 20 earlier raw months clean, the incident is
localized to the July 2026 shard, matching the rider's "1 monthly shard", and the per-form breakdown
explains the gap to the unit: form `447bf804…` accounts for 42, matching S38's number.
S38 measured the one form it was scrubbing from git history; all four admitted forms, both
suppressed people, are present, adding 163 more.
Also measured: `ledger.json` 156, `extractions.jsonl` 127.
Not a defect in S38 (its job was the git scrub), but the gate spec's figures describe one form, not
the payload.
8. cost, measured, not guessed: payload ~890 MB uncompressed (state 593 + raw 300).
A whole-string memo (the ledger carries every n-gram twice; `daily` is millions of bioguides from a
vocabulary of a few thousand) took `ledger.json` from 204 s → 52 s at an identical 156 occurrences.
The file-level skip cache is keyed on the form list's fingerprint as well as the file's, so
admitting a new name invalidates everything, the one moment a stale "already clean" answer would be
wrong about the whole corpus, and entries outside the roots a run walks are carried forward, because
collect covers `data/raw` and assemble does not.
Peak memory in the production shape is 4.21 GB against the runner's 16 GB, clean containers are
returned AS themselves, not rebuilt; without that the ledger is held twice (~7 GB measured).
Expect the first cloud run to pay a one-time bootstrap over the whole payload (861 s measured
locally, under contention from other probes).
9.
Footgun found by walking into it.
A local dry-run rewrites tracked post manifests.
Previewing the new packing by running `pipeline/post_bluesky.py` locally (fully gated, no creds,
`POSTING_ENABLED` unset, zero network) still calls `_flush()`, which rewrote
`data/derived/manifest/post-2026-07-20.json`. `generated_at` restamped and `posting_enabled` flipped
`true` → `false`, and created a spurious `post-2026-07-21.json`.
That file is the launch day's record and the source `/posts.html` renders as the signed archive;
committing it would have falsified the evidence that the first posts went out under a live gate.
Caught by `git status` before staging, reverted, never pushed; the preview was re-done via
`build_thread()`, which is pure.
A dry run must not be able to write a tracked artifact, a non-flushing preview path is a named
follow-up, deliberately not changed at 3 a.m. on the posting path the morning cron is about to use.
Until then: preview with `build_thread()`, never by running the module.
10.
R-l ran in production and the #132 gate condition IS met, same session, hours later.
The 09:30Z collect (scheduler-delayed to 11:23Z, so it picked up the new code on its own) redacted
732 occurrences in 4 of 48 files in 1039.9 s. `raw/2026-07.jsonl` 223 · `statements.jsonl.gz` 223 ·
`ledger.json` 158 · `extractions.jsonl` 128, then persisted and committed; every step green, no
dead-man, job 1h3m vs the ~43m baseline.
The deltas against the previous day's assets are the finding: raw +18 and statements +18, identical
because statements are normalized from raw, those eighteen arrived in this morning's ingest.
The person is still being named in fresh press releases, so the rider's insistence on a
forward-looking filter rather than a one-time edit of the 11 records was vindicated on day one.
verification, as the ruling specifies: downloaded both freshly-built assets from
`data-latest` (byte-sizes matching the live release: raw 93,026,744 · state 141,799,381, uploaded
12:27:20Z) → `python -m pipeline.redact --check` over all 48 files → 0 occurrences.
A `--check` that finds nothing and a `--check` that is broken look identical, so the positive
control was run too: the published assets contain 732 redaction labels, matching the run's report
file-for-file (223/223/158/128), the same machinery found 732 things to replace and all 732 are
present, which rules out a no-op scan. known limit: `--check` shares its matching engine with the
redactor, so it is not an independent audit; what partially offsets that is S38's
independently-measured 42 for form `447bf804…`, reproduced here from a different session and
tool.
A dispatched collect was cancelled as redundant once the scheduled run was seen mid-redact, and the
lesson generalizes: with `cancel-in-progress: false` a newly queued run displaces an already-pending
one, so dispatching anything while an assemble waits can cancel the post.
11. the morning ran green, And the live thread found a defect the tests did not. run B fired
    13:00:36Z (scheduler ~90 min late, in line with the collect's ~113), green in 1m3s: readiness
    `target=2026-07-21 forced=False :: ready` (233 lane-1 statements vs a 250 Tuesday baseline,
    93.2%), both parties `verifier_passed=True fallback=False`, `atomic_hold=False`,
    `asymmetric=False`, both threads live, receipts page 200, homepage on 07-21, Methodology
    carrying both new r-l disclosures. the redact step cost 0.4 s ("redacted 0 file(s), skipped 29
    unchanged") against the collect's 1039.9 s bootstrap, the file-level cache settles the
    performance question, and the record-level cache named as a follow-up in

8. is not needed.
P2 v1.3 is visibly live: "first recorded in our corpus from Nick LaLota (r-ny)".
But the d thread still cut mid-clause ("...as a common" / "thread today.").
Cause, from the live composite: `_sentences` returned 3 sentences with the middle one 272 chars
against a 262-char post, because two sentences had merged, the boundary sits after `implemented."`,
terminal period inside the closing quote, so the lookbehind `(?<=[.!?])` inspected the quote and
found no boundary.
Prompt rule 2 requires verbatim member quotes, so `..."` at a sentence end is this voice's normal
register, not an edge case, my packing fixtures were prose I wrote, and I wrote it without
quotations; that was the one shape they never contained.
Fixed (optional closing quote/bracket in the lookbehind); on the live 07-21 composite the thread
goes from 3 body posts with a mid-clause cut to 2, each ending on a complete sentence, still
word-exact; mutation-verified against the version shipped this morning.
435 tests green. next: (i) the r-l verification the flip is gated on. done (above), so the flip is
now purely Michael's go, subject to whatever #110 makes of the revocable r-l ruling; the
re-verification command for any future run is `gh release download data-latest` + `python -m
pipeline.redact --check`, after a cron has rebuilt the assets, `gh release download data-latest`
then `python -m pipeline.redact --check` on both tarballs, expecting zero (that tooling is now
tracked, not a scratchpad script, the S18/S37 lesson); (ii) #132 stays open and is still only "make
repo public", now gated on that verification, deliberately not re-filed; (iii) named follow-up,
deliberately not built tonight: a record-level clean-cache, if the added cron minutes prove
annoying.

### 2026-07-21 (Session 39, Fable, same chat, ~18:10Z)

both workers validated + closed out; the release-asset gate ruled (r-l); the operation consolidates
back to one chat.
Validation (independent, Art. xvi): the S38 scrub verified from MY side, pre- vs post-rewrite trees
byte-identical at the same commit point (`git diff a111469 1eeec8c` empty), 252 commits in / 252
out, both workers' pushes present in the rewritten history (the S36 handshake reconciliation worked
as designed: the shard commits rode into the snapshot).
S37's masked-200 metadata trap + settled-unavailable semantics and S38's hmac-provable exhaustive
discovery are both ratified as built. r-l. the release-asset ruling (revocable; expressly flagged
for the #110 attorney hour): the S38-measured blocker (the name 44×/42× inside
`raw.tar.gz`/`state.tar.gz` on release `data-latest`, refreshed every cron, public the moment the
repo is) is resolved by redacted-view releases: the published release assets get the same
salted-label redaction as every other published surface, applied in the state-persist step of both
workflows; the pristine append-only archive stays on X: untouched, the constitution is satisfied,
not amended (append-only governs the archive; Art. xiii, unamendable, governs every published
surface, and a release asset is a published surface); the About/Methodology "verbatim" wording gains
one accurate clause ("verbatim except privacy-floor redactions, each labeled in place"); side effect:
the restored cloud state carries labels, so the S38-flagged regenerable search-index rows become
clean automatically.
Sequencing: r-l implementation folds into the Wednesday posting-hygiene session (both are ops-path
work); the visibility flip (#132) happens only after r-l ships + verifies (zero admitted-form
occurrences in freshly-built assets), on Michael's go. r-l rider (the S37 closeout's loose thread,
carried here because the bus can't hold detail, vtask has no comment facility, and It is the #132
gate's spec): the raw carrier is localized.
11 records in 1 monthly shard under `data/raw` (re-locate via the S38 HMAC window-scan
tooling during implementation; occurrences 44 per S38).
The two build points the redaction filter must cover: `collect.yml:79-82` (builds + uploads both
`state.tar.gz` and `raw.tar.gz`, the raw tarball's only uploader, refreshed every collect run) and
`assemble.yml:105-106` (state only).
The filter is a redact-on-persist pass using the live gate's own salted-HMAC matching, applied at
tar-build time every run, forward-looking, not a one-time patch (future press releases can name the
person again; a one-time edit of the 11 records would silently re-leak on the next converged
statement).
Semantics: the cloud's restored store becomes the sticky redacted view; the pristine append-only
archive is X: (already true).
Verification before the flip: download both freshly-built assets from `data-latest` and scan them
with the S38 tooling, zero admitted-form occurrences in each.
Also ruled: the contaminated local `wip/nomenclature` branch, recommendation delete (work merged,
keeping it invites an accidental push of pre-rewrite history); Michael's one-word act.
The scrub's scratch clone must be deleted at closeout (it holds pre-rewrite contaminated history, a
re-leak vector).
GitHub purge ticket now covers both rewrites, at leisure.
Deep Archive lane state: 107–110 + 113–116 shards audited; 111/112 wait on the restarted crawl
(2009–2012 first, X:-only, alive across the rewrite); next session = `scripts/deep/crec_state.py`
first, then 111/112 + 117–119, then SD.8, per S37's own next line.
The operation is now: Wednesday session (posting hygiene + r-l) → visibility flip on go → Mon 07-27
nomenclature flip → the §7.3 schedule.

### 2026-07-21 (Session 38, Opus, the Article XIII history scrub, the scrub worker in the S36 two-worker protocol)

The exhaustive scrub is done and pushed.
Git history is clean, verified by re-cloning from GitHub, not from local state.
401 tests green, HEAD tree byte-identical, collateral provably nil.
The repo is still private; the visibility flip waits for Michael's go, and a new pre-flip blocker
was measured that the git scrub cannot reach.
1.
Discovery was exhaustive because of the design, which is the whole S35 correction.
Session 17 under-reached because `extract_names.py:24` scoped discovery to the paths one commit
touched; this pass slid the live gate's own token windows (sizes 1–3) over every blob (4,746), every
path (1,327), and every commit message (255).
Completion is provable, not asserted: each recovered span is hmac'd against the committed form
hashes, so "we found them all" is a checkable claim.
Result: 1 of the 4 admitted forms was in history (2 tokens, 15 chars) across 20 blobs / 12 paths /
152 of 255 commits, as 1 literal variant, 45 occurrences; the other 3 forms were already
absent (S17 did clean those).
0 path hits and 0 commit-message hits ⇒ `--replace-text` sufficed; no `--filename-callback`, no
`--replace-message`.
Both canon claims reconcile: the 4 phrase files carry plaintext in every version `ca3ca2c`→`c44579c`
(S34's "~148 commits", measured 152) plus the 07-20 launch-day pair.
Label `<private-individual-A>` chosen on evidence, history contains `the killing of {form}`,
precisely the test S17's own labeller used.
2. four gates, all passed, on a fresh clone of origin: zero occurrences of every admitted form (0
   blobs/0 paths/0 messages); HEAD tree `34f44e73…` byte-identical; 401 passed, 0 failed; collateral
   20 blobs out / 20 in, each explained, 4,726 untouched.
The suite's one fresh-clone failure (`test_no_form_collides_with_the_roster`) was proven
environmental by running the pristine clone as a control, it fails identically; `roster.json` is a
gitignored cache.
3. pushed 16:44:34Z, fetch→push gap ~10 s, zero runs in flight (crons 09:30/19:30Z, 11:30/21:30Z):
   `main c63fd24→18d533f`, `wip/nomenclature c4fe386→920067d`, `data-latest 4502a78→a110efd`.
The Phase-1 rewrite reproduced Phase 0's SHAs bit-for-bit, determinism as corroboration.
4.
The remaining finding.
The release assets carry the name and git cannot reach them.
A whole-worktree scan (1,710 files, 13.57 GB) found 7 carriers, all gitignored/untracked (zero
tracked, independent confirmation the history is clean).
Five are not search indexes: `data/raw/congress-press/2026-07.jsonl`

42. and `data/raw/bluesky/lane2.jsonl`

2. ship in `raw.tar.gz`; `data/state/ledger.json` (14), `alexandria/ledger-119.json`

14. and `lanes/ledger-119.scraped.json`

14. ship in `state.tar.gz`.
Grounded in source, not inferred (`collect.yml:79-82` tars `data/state`/`data/raw` and `gh release
upload data-latest`): 44 occurrences in raw.tar.gz, 42 in state.tar.gz, refreshed every cron run,
attached to release `data-latest`, private only because the repo is. not acted on, deliberately, the
raw mirror is constitutionally append-only and editing 3 GB of ledger state is an instrument
decision, not a cleanup.
It is the "raw-mirror/attorney question" canon already flagged, now measured, and it gates the
visibility flip.
Rides on #132; deliberately not re-filed.
5. phase 2: the 14 gitignored search-index rows purged (`phrase_index.jsonl` 7 of 3,087,497;
   `phrase_index.scraped.jsonl` 7 of 865,189 → 0 remaining); main tree reset via `fetch`+`reset
   --hard` (Michael ran it, the harness gate refused the destructive op); stale local tag
   `data-latest` force-updated off origin.
Those purged rows are regenerable, they are built from `ledger.json`, which still carries the name,
so the index builder brings them back unless it applies the privacy gate.
6. the local `wip/nomenclature` branch IS still contaminated (`fb6ac6a`, 16 carrier blobs, 178
   unpushed commits), see the Worktrees bullet; local-only, never published, its work already merged
   to main, disposition reserved for Michael.
7. the ruled residual, disclosed: the scrub removes admitted forms; one name token is a 7-letter
   word the gate deliberately refused to admit (several unrelated legitimate bearers, gate (c)
   protecting real speech).
Post-rewrite it still occurs 159× in 62 blobs (from 204/82); the other token drops to 0; and zero
blobs anywhere now contain both tokens at any distance (was 20), the person is not reconstructable
by co-occurrence. next: the visibility flip is Michael's go, and it should not happen until the
release-asset question is ruled.

### 2026-07-21 (Session 37, Opus, the Deep Archive lane, the archive worker in the S36 two-worker protocol)

CREC congresses 113–116 built + audited; 111/112 Were blocked on a crawl that never ran them; and
the `/bulkdata` Masked-error trap turns out to live on the metadata path too.
401 tests green.
Zero daily-pipeline surfaces, zero Actions, X:-only bulk.
Pushed, tree clean, then paused for the scrub per S36.
1. the crawl was DEAD, and the named deliverable was blocked before it began. `CRAWL-RUNNING.lock`
   named pid 17728, not running (started 07-17T04:11Z, dead ~25 min later).
Its year order was `[2013…2026, 2009…2012]` and it reached 2022, so 2009–2012 was never crawled at
all, and congresses 111/112 are 2009–2010 / 2011–2012.
Restarted detached with the order inverted (2009–2012 first, then 2022–2026) so the blocked
deliverable unblocks soonest; resumable, keyless, $0, X:-only so it is unaffected by the history
rewrite and keeps running across it.
2. the finding.
GovInfo serves "Page Not Found" as HTTP 200 with an HTML body on `/metadata/pkg/{pkg}/mods.xml`.
The `/bulkdata` behavior docs/15 §D1.a warns about, on a path we trusted. `urlopen` raises nothing
and the status is 200, so the payload is the only signal: 10 sitemap-listed days across 2013–2022
(the Jan-3 convening days + 2022-05-11/05-19) return an identical 44,165-byte error page, re-fetched
live to confirm it is upstream and permanent.
Two self-perpetuating consequences: the error page was hash-manifested into the append-only raw
mirror as archival evidence, and it was cached, so every resume read it back off disk.
The same 10 days failed on every run for six days and could never heal.
Fixed (`crec.looks_like_mods` + `crawl_extensions`): a non-mods payload never enters the mirror; a
poisoned cache entry is quarantined to `raw/mods/_rejected/`, never deleted (what upstream served is
part of the record); the day is recorded `day-nomods:` = settled-unavailable, not pending, the
distinction that makes "complete" mean anything, since counting permanently-unfetchable days as
pending puts 100% out of reach because of the design.
4 tests, mutation-verified 3/3.
3.
113–116 built + audited (shards on X:, audit JSONs committed to `data/derived/crec/audit/`; ledger
schema verified identical to 107–110, so the Search reader queries them unchanged).
Every window passes symmetric two-party.
113 (2013 D=200/R=214 · 2014 D=196/R=212), 114 (2015 D=189/R=221 · 2016 D=183/R=221), 115 (2017
D=189/R=220 · 2018 D=187/R=214), 116 (2019 D=231/R=192 · 2020 D=220/R=179); member-symmetry
0.81–0.93, ~180–230 members/party/year, 45,366 statements. *(Ratios are on distinct members; the
core corpus's D:R figures are statement-shares, different estimators (docs/12 L4), so the tempting "the
deep lane is more symmetric than the core corpus" line is not licensed by these numbers.
That comparison is SD.8's job.)*

4. congress 117 refused, deliberately: 2021 is complete but 2022 stops at 87 of 200 sitemap days
   (where the old crawl died), and a truncated year inside a shard is indistinguishable from a quiet
   one, it just looks like less speech.
The builder verifies each year's settled days against the published sitemap and refuses;
`--allow-partial` exists and stamps `"partial":true` into the audit.
5. the shard stays raw. `crec_boilerplate.suppress()` runs in the acceptance smoke query, not at
   build time: 107–110 were built raw by design (D4-pre, the ledger keeps every n-gram, the
   suppressor filters what a *view* may surface), and suppressing at build time would fork the
   instrument mid-lane and silently invalidate every within-lane cross-era comparison, the
   genre-confound failure wearing the costume of a fix. `lanes.lane_of()` is asserted on the loaded
   set before each build.
6. smoke query re-confirms both D4-pre residuals on fresh data, full bill titles dominate, sub-grams
   fill five rows with one phrase, plus a new residual (c): missed-vote explanations ("i would have
   voted yea", "on roll call no") are a high-volume Extensions formula the seed list misses, ranking
   as top "R coordination" in congress 115.
All three close before any crec phrase-coordination card; none touches the speaker-attribution bets
(SD.2/SD.3/SD.6), still the ripe ones.
7.
SD.8 not started, precondition unmet: calibration needs the CREC half of the full 2013–2026 overlap;
2013–2020 is now shelved, 117 needs 2022, 118/119 need 2023–2026, all in the running crawl.
A concordance on a partial overlap is the "fake-complete" failure §8 exists to prevent.
8. drivers are tracked now (`scripts/deep/{crawl_crec,build_crec_shards,crec_state}.py`), prior
   sessions ran them from gitignored `scratchpad/` and re-hand-rolled them every time (the
   Session-18 lesson); the crawl driver also neutralizes the known `crec.py:217` trap (it overwrites
   `crawl-stats.json` with only the current run, it had already destroyed the 2001–2002 record and
   the entire 2013–2021 campaign's stats) by snapshotting before and merging after. next
   deep-archive session: run `scripts/deep/crec_state.py` first, then build 111/112 + 117–119, then
   freeze and run SD.8.
The crawl now running started under the pre-fix code, so it will re-poison any Jan-3 days it meets,
the next crawl invocation auto-quarantines them, and the builder reads the on-disk evidence
directly, so no build is misled meanwhile.
No bus errand (nothing blocked on Michael).

### 2026-07-21 (Session 36, Fable, same chat, ~14:15Z)

two-worker coordination protocol, the history scrub × the live Deep Archive session (uncommitted
crec.py + 113/114 audits in the main tree now).
A filter-repo force-push is stop-the-world; interleaving is forbidden. the two-phase protocol
(binding on both): Phase 0 (parallel-safe, starts now): the scrub session works only in a fresh
scratch clone. never the main tree, the archive worker owns it.
There: build the exhaustive replacement list (S35 scope, every admitted suppression form), dry-run
`git filter-repo`, verify zero occurrences across all history + head-tree byte-identity + full suite
green in the scratch clone, then stop and report "ready for the handshake." Phase 1 (only after
Michael relays "archive worker paused, everything pushed"): re-fetch the fresh snapshot. the shard
commits being IN the snapshot is what makes reconciliation automatic, re-run the rewrite, confirm a
clear cron window (`gh run list` + nothing due; keep the final fetch→force-push gap to minutes),
force-push all refs.
Phase 2: purge the 7 gitignored `data/derived/search/*.jsonl` rows in the main tree, then reset the
main tree with `git fetch origin && git reset --hard origin/main`. never pull: pulling pre-rewrite
local history onto the rewritten remote re-imports the contamination, verify, re-map the sha-notice
anchors (all SHAs change a second time), stop; the visibility flip waits for Michael's go.
Archive-worker rules: work normally to a natural stopping point → commit + push everything incl.
your canon row → confirm `git status` clean → hold and say "paused for the scrub"; after Michael
relays that the force-push landed: `git fetch origin && git reset --hard origin/main` (never pull),
re-run your own test files, resume.
Your pushed commits survive the rewrite content-identical under new SHAs, cite post-rewrite SHAs in
rows written after the reset.
Residual race, accepted + recovery named: a cron push landing inside the final fetch→push gap would
be overwritten by the force-push, mitigated by the window check and the minutes-long gap; if it
happens anyway, the lost data commit is rebuildable by re-dispatch (the state tarball persists
independently of git).
Michael is the relay between the two sessions.

### 2026-07-21 (Session 35, Fable, same chat, ~13:50Z)

the launch validated independently + the scrub scope sharpened.
Verified from the live surfaces, not S34's summary: homepage = the 07-20 Monday reading with party
columns + Days/Phrases/Search nav; the announce live at 13:24Z (opening text verbatim);
`blue.onscript.news` posting at 13:27Z with the  marker on every post unit (the §4c belt working in
the wild); FEATURES = the three launch flags; `post-2026-07-20` symmetric, both roots.
S34's in-session rulings ratified (launch-with-repo-held; first-sayer wording ship-as-is).
The step-1 record check catching a live Art. xiii violation ~1h before the announce is the launch
order's most valuable line, it goes in the methods story. ruling. the scrub IS exhaustive, not
name-scoped: Session-17's rewrite missing a third person proves name-scoped scrubs under-reach.
The history scrub verifies zero occurrences of every admitted suppression-list form across every
commit, purges the gitignored `data/derived/search/*.jsonl` rows in the same pass, and proves
head-tree byte-identity + full suite green before force-pushing; all SHAs change again (re-clone,
never pull); the force-push lands in a clear cron window (`gh run list`, never mid-run).
The visibility flip happens only on Michael's go after the verification prints.
The GitHub server-side purge ticket now covers both rewrites (same at-his-leisure posture, risk
accepted eyes-open). wednesday order (posting freeze lifts for this session), priority:

1. `_reconcile_prior` repair first, the S8e asymmetric-post backstop has been a silent no-op (`'str'
   has no attribute 'exists'`) and posting is now live daily;

2. collision-recovery truncation (replies after a recovered root);

3. sentence-aware thread packing (the mid-sentence cut on the live D thread);

4. `SITE`/`config.SITE_URL` dedup;

5. first-sayer wording ("first recorded in our corpus").
Failure tests on all of it.
Watch: tonight's cron is the first fully-unattended posted day.
The Deep Archive grinding prompt (S33) stands unrun and unaffected.

### 2026-07-21 (Session 34, Opus)

onscript IS launched.
The announce is live, both composite accounts have posted their first real threads, and three
features flipped, but the repo is still private, deliberately, on Michael's in-session ruling,
because a launch-morning audit found Article xiii contamination in git history. docs/23 §7.5
amendment 3 executed in full except step 5's `repo public`. the launch acts (all on Michael's
explicit go, given in-session at step 4): `POSTING_ENABLED=true` → announce posted from the house
account (`announce.yml`, the affirmed recommended 4-post thread verbatim, extracted programmatically
from the draft so the posted bytes provably equal the approved bytes; dry-run previewed first, then
`confirm=POST`; root `3mqzyfaak2223`, 259/248/259/248 chars) → flip commit `d7c93ac`
(`party_columns` + `owners_brief` + `phrase_search` = True, all three in `DELIBERATELY_RELEASED`) →
re-dispatch 07-20 so the composites posted in the announce's own morning window (D 3 posts, R 3
posts, `atomic_hold=False`, `asymmetric=False`).
Verified live from the public API and the deployed site: all three accounts posting, homepage = the
Monday reading, party columns rendering, `phrases/search.html` 200, og cards incl. `og.png` (163 KB)
serving, corrections page reads 4.
The morning finding.
A live article xiii violation on the home page, found during the step-1 record check, ~1h before the
announce.
07-20's top synchronized phrases included the name of a private individual, a man fatally shot by an
ice officer, converged on by 5 D offices, rendering on the home page, the launch day page, and the
phrases index of the already-public site.
Cause (the docs/16 occurrence-not-phrase lesson, now applied to the privacy gate): an n-gram slides
across a name, so one name spans several token windows, and the suppression list carried only one of
them.
A neighbouring form of the same name was already suppressed, the gate knew this person and still
leaked them.
Fixed under the standing R5 remedy: the remaining forms admitted (gate (a) roster, (b) allowlist,
(c) archive scan over the full corpus and the 25-year Alexandria ledgers, every occurrence is this
one incident, zero legitimate uses; the bare surname was not admitted, it has several unrelated
legitimate bearers, gate (c) protecting real speech as designed), site re-rendered, day JSON
repaired through the sanctioned dispatch path, corrections log 3 → 4 (public), commit `6b1c8ce`.
Every citation was valid and every number correct. the verifier has no opinion about privacy because
of the design, so no receipts audit could ever have caught this.
Why the repo is still private.
The next session's first item.
The same name sits in ~148 commits of tracked history (`ca3ca2c`..`c44579c`, 2026-07-10 → 07-16),
and history IS publication.
Proven directly: in `ca3ca2c` other phrase files carry `private-individual` redaction labels. so the
Session-17 `filter_repo` rewrite ran and simply missed this third person, while this one carries the
plaintext name. #160/#161 were closed as "sufficient" on the belief history was clean; that belief
is falsified.
Michael ruled: launch now, scrub history first, flip visibility after.
A `git filter-repo` rewrite over that range is the next Opus session's first act (Session-17
precedent; all SHAs change again; re-clone, never pull).
The gitignored `data/derived/search/*.jsonl` Search indexes also carry 7 rows each. never published,
but purge them in the same pass. r-e worked as designed and was time-critical: 07-19 had
reached `MAX_WAIT_DAYS=2`, so the next scheduled pass would have force-finalized it degraded; the
explicit dispatch preempted that (D 0 / R 2, `forced=False`, `degraded=False`, the thin accurate
Sunday), then 07-20 last → `assemble-latest` = 07-20.
Step-6's `passes:False` streak read appeared as documented and was left alone.
Digest all green (reds `[]`, degraded_days `[]`, spend $0.074, verifier drop 7.4%). r-f shipped
first (`0b3f335`): `phrase_search_index()` called `.get()` on whatever a phrase JSON deserialized
to, so one malformed file crashed the whole build, the page loop already failed soft; the two guards
now agree.
Mutation-verified.
397 tests green at every gate, incl. with all three flags live. follow-ups (none launch-blocking,
all for Wed 07-22 with r-g):

1. thread splitter cuts mid-sentence, the live D thread reads "our 99 statements today do" / "not
   converge on additional shared messages"; cosmetic, and the posting path was frozen per r-g so it
   shipped as-is deliberately.
2. `_reconcile_prior` is broken. `'str' object has no attribute 'exists'` skipped 7 post manifests
   every run; alert-only + skip-and-log so nothing failed, but the asymmetric-post reconciliation
   S8e built has been a no-op.
3. each party's composite cites a cross-party first-sayer (the D voice crediting Ted Cruz (r-tx);
   the R voice crediting a Democrat), factually correct (first-appearance is corpus-wide) and
   symmetric, so ruled ship-as-is under Michael's delegation; the fix is wording ("first recorded
   anywhere in our corpus") or same-party-only attribution, and belongs in the normal queue, never a
   launch-morning patch.
4.
Monday 07-20 is accurate but procedural (`homeland security dhs`, `house floor in`), a weak content
day, disclosed to Michael before his go.
Bus: #158 closed (owners_brief flipped); #132 stays open and is now only "make repo public", gated
on the history scrub, reused, not re-filed.

### 2026-07-21 (Session 33, Fable, same chat, ~03:15Z)

The dedicated hx session validated + The launch-eve search program is complete.
Cards stay at 5; the discipline caught everything it was built to catch.
HX.4-D HELD ratified, the r-j precondition did its job: the decomposition partitions the parent
cells (no leakage) and shows the "minority persists 3×" effect is carried by the Democrats
alone (D drops hard in both lanes.
10→44 and 9→55 median active days, with opposite calendar directions across lanes, killing the
era-artifact reading; R is flat where powered, r=−0.004 p=0.85).
The symmetric institutional card ("the minority messages, the majority legislates") is dead as
written; the parent measurement stands.
The exposed asymmetry (D message-persistence is majority-sensitive; R's is majority-invariant) is
banked as a reservoir candidate for the October registration wave, its own pre-registration required
+ the scraped-R power gap (136 units) named; the session correctly refused to headline it post-hoc
on the same data.
HX.5 ARTIFACT ratified → graveyard: the "opposition reused more than celebration" signal died
against its own within-valence placebo, the S4.2 law working as designed. *(Record note: HX.5's row
cites freeze SHA `16db1d8`, the pre-rebase label for `f339785`, the session rebased over the evening
crons after writing the row; freeze-before-measure order survives rebase and stays git-verifiable.)*
Tonight's crons: both succeeded, the --autostash push-recovery fix survived its first live exercise
(collect 20:46Z 47m, assemble 22:31Z); the 22:31Z assemble was another 07-19 hold (assemble-latest
still 07-18), so tomorrow's worker runs both r-e dispatches as ordered.
Launch-eve Search totals (two sessions): 1 new card (S5.2 ~92%), 1 high-grade null (S3.7), 1 placebo
kill (HX.5), 1 held-with-honor (HX.4/4-D), 2 methods descriptives (HX.2/HX.8), substrate audit
6/8-runnable, zero launch-surface bytes across all of it.
Next grinding lane (Fable ruling): deep archive.
108–112 CREC shards + per-year D1.d audits, then SD.8 calibration prep if the 2009–2026 crawl is
complete (check the crawl log first); remaining HX items (HX.1 gdelt-anchor design · HX.3
cadence-normalized registration · HX.6) are design-heavy dedicated post-launch sessions, sequenced
after the Wednesday r-g fixes.
The Tuesday launch order is unchanged; nothing tonight touched it.
-  2026-07-20 (dedicated HX session, Opus, post-S32 R-J/R-H): The two hx items run, Both
  freeze-before-measure in separate commits, both pushed.
Program confirmed-tier cards unchanged (stay at 5), the session produced a HELD and an ARTIFACT,
both the discipline working.
Launch-eve rules honored throughout: `scripts/search/` + `data/reference/search/` + `docs/13` + X:
evidence only; never imports the daily pipeline; `git status` clean at start; each push after `gh
run list` clean (the HX.5 push rebased cleanly over the evening cron commits `7631767`/`543d0bc`,
freeze→measure order preserved). zero launch-surface bytes; tomorrow's launch tree untouched.
1.
HX.4-D, the within-party decomposition (HX.4's registered publication-precondition, S32 r-j): freeze
`1783987` → measure `693d781`. verdict HELD.
The decomposition reproduces HX.4's cells (propublica maj 23,392 = D-maj 15,820 + R-maj
7,572; etc.) and shows the majority-persistence effect is carried entirely by the Democrats: D
coordinated phrases persist ~4–6× shorter in D-majority congresses (median active-days 10/44
propublica, 9/55 scraped), robust across opposite era-directions (D-majority is late in
propublica/early in scraped) so it is not an era artifact; Republicans are flat where powered
(propublica maj 7,572/min 962, r=−0.004, p=0.85), scraped-R underpowered (min n=136).
Frozen proceed-criterion fails condition 1 (powered contradiction: propublica·R) and condition 2 (no
powered R drop) → HELD.
HX.4's number stands as measured, but its implied symmetric institutional reading ("the minority
messages; the majority legislates," for *both* parties) is not supported → the card does not advance
(It is why CONFIRMED cards stay at 5, not the 6 the S32 line pended).
The asymmetric structure (D persistence is majority-sensitive; R is majority-invariant) is Art.
iv-permissible but would be a new hypothesis measured post-hoc on the same data. needs its own
registration; deliberately not run in-session.
Registration `data/reference/search/hx_4d-registration.json`.
2.
HX.5, opposition-vs-celebration reuse (S32 next-HX item, under the S4.2 placebo law): freeze
`16db1d8`(→rebased `f339785`) → measure `b80ecea`(→`29bf412`). verdict ARTIFACT.
A pre-freeze substrate audit (marginals only, no effect measured) killed two naive metrics:
phrase-level valence is empty (peak≥15 phrases almost never carry a valence token; R = 0 opposition
phrases in both lanes), and carry-rate against the peak≥15 oracle is boilerplate-invalid (measured
~92% carry base rate, the peak≥15 set is procedural-dominated, not a clean "talking points" list for
occurrence-level metrics, a banked caution).
Chosen metric = within-class distinctive reuse (size-matched `repeat_rate` of content 4–6-grams;
shared boilerplate cancels in the opp−cel difference).
3 of 4 (lane,party) cells show opposition reused more than celebration and significant (propublica D
+0.049 / R +0.135, scraped R +0.051; scraped D null). but the within-valence placebo (conA-vs-conB)
reproduces and exceeds the effect in every one (+0.14 to +0.22 > the live gap) → the metric is
driven by lexical-class homogeneity, not valence → ARTIFACT (the S4.2 placebo law doing its
job; pairs with S1.10).
A graveyard/methods-transparency result (docs/20), not a card.
Disclosed benign implementation deviation (registration JSON left pristine): the bootstrap used
numpy `default_rng(0)` instead of the frozen `random.Random(0)` because pure-Python resampling at
n≈50k is infeasibly slow (~2–3h); deterministic seed-0, preserves the frozen
metric/size-match(n=min)/placebo/B=500/verdict precisely, CI shifts only by ~3rd-decimal Monte-Carlo
noise (verified 0.138 vs 0.13825 on a fixture), recorded in the script +
`result.bootstrap_rng_deviation` + docs/13 (also two result-preserving fixes: an oom avoided by
hashing n-grams, and `repeat_rate` via the `Σ(df≥2)=Σ_c df(c)·[df(c)≥2]` numpy-bincount identity).
Registration `data/reference/search/hx_5-registration.json`.
Per S32, HX.3 (#143 chamber trap) and HX.6 (complex) were out of scope; HX.1 is network-blocked,
HX.7 source-blocked, they await a future registration wave.
No bus errand (both measurements complete, nothing blocked on Michael).

### 2026-07-20 (Session 32, Fable, same chat)

The launch-eve search session validated from the record + four rulings.
Program cards 4 → 5.
Validation (Art. xvi, not the worker's summary): all five rows check out. freeze-before-measure is
verifiable in git order (S5.2 `5cd27da`→`882f7d7`; HX.4 `bc4d0d1`→`423702d`); surface check = 15
files, all additive, all in sanctioned lanes (scripts/search/ + data/reference/search/ + docs/13;
zero launch-surface bytes); evidence tracked in-repo (the S18 lesson fixed); the S3.7 join audit
names its 2 failures (GA dual-runoff) at 99.9%; the 0.20 effect-size gate earned its keep (scraped·B
p=0.012 at ρ=−0.12 correctly suppressed, the S4.2 lesson institutionalized); HX.4's session resisted
running the decomposition post-hoc on the same data, the discipline holding under temptation.
One accepted implementation note: S3.7's MoV window-reduction was disclosed-not-registered
(rank-inert, fine). r-h: the worker's hold on HX.5/HX.3/HX.6 ratified, dedicated-session work, not
late-eve work. r-i: S5.2 APPROVED to the docs/20 shelf (It is its Fable/neutrality review) with
two publication riders:

1. the card's headline carries the operational definition.
"never followed by the same member sponsoring an on-topic bill within 180 days," a follow-through
metric, never a "Congress does nothing" claim, and prints the K-range (63.2/92.0/98.3/99.3);

2. the party comparative publishes in absolute pp with CIs (D 8.6% vs R 6.8%, +1.8pp), never
   relative framing.
Publication stays Michael's editorial act. r-j: HX.4's measurement stands as measured; the card
stays HELD pending the within-party decomposition, now a registered precondition (frozen gate,
separate commit, later session): the card proceeds only if each party's own persistence drops in its
majority congresses (both lanes where the ≥200/cell floor holds).
Framing rider at publication: lead with the measured rates; "the minority messages; the majority
legislates" is labeled interpretation (correlation-not-cause). r-k: S3.7 banked as the program's
second high-grade publishable null (pairs with S1.12; graveyard/methods shelf); HX.2/HX.8 are
methods-shelf descriptives, correctly not cards.
Next session (dedicated HX): register+run the HX.4 decomposition, then HX.5 under the S4.2 placebo
law (placebo against the exact headline statistic, S4.1 valence lexicons); HX.3/HX.6 out of scope.
Tuesday's launch order unchanged and unaffected.

### 2026-07-20 (Session 31, Fable, same chat as S29)

sessions 30/30b adjudicated, docs/23 §7.5 amendment 3 is the FINAL tuesday order.
All worker-raised decisions are ruled; nothing remains before the launch morning except running it.
r-d: S30's repair deviation ratified (restore-from-published-bytes was right three independent ways,
streak evidence, Art.
II, provenance; `repair_safe_manifest` is the standing repair semantics; never `--day` 07-12/07-18).
S30b's corrections-clobber fix, `DELIBERATELY_RELEASED` mechanism, and privacy-ruled og cards
ratified as built. r-e: 07-19 policy, daily-always is locked, so dispatch 07-19 iff count ≥1 (a thin
accurate Sunday beats a Wednesday degraded force-finalize; at 0 the skip is accurate), then always
dispatch 07-20 last (assemble-latest → the Monday reading; S30b proved the natural cron structurally
cannot reach 07-20). r-f: the `phrase_search_index` non-dict guard is Tuesday step 0, pre-authorized
(a known build-crash surface must not go live with its flag). r-g: the posting path stays frozen
through launch, collision-truncation + site dedup are Wednesday's first post-launch fixes; the
rare-case remedy is a manual in-app reply with the receipts link.
The go stays Michael's, given IN the Tuesday worker session at step 4.
Also noted: today's 12:00Z collect shows failure in `gh run list`, that is the S30-documented push
collision (fixed `93660f2`, `--autostash`); the ~12:42Z dead-man alert was that event, not a
pipeline fault; archive intact, evening pass rebuilds.
Tuesday prompt (new chat, model = Opus): "read claude.md and docs/23 §7.5, run the launch morning."
the launch-eve parallel lane (ruled, same session): tonight's grinding session runs the search, not
the build.
S5.2 is the designated item (§7.2.5: freeze the three companion registrations as a committed ledger
registration first, concern lexicon into the repo, 180-day window, on-topic match rule, then measure
at the confirmed 300/cell floor, then ledger the verdict; the p-hacking hole §4 names is closed by
freezing before measuring).
Rationale: Search work is the only lane with zero shared surface with tomorrow's launch morning
(scripts/search/ + X: + docs/13; never imports the daily pipeline). silence_board wiring is
explicitly not tonight's work (it edits the daily path on launch eve; its deadline is 08-03 with two
weeks of slack).
If S5.2 finishes clean, the next runnable docs/13 item that touches no daily surface (HX
registrations per docs/05 §3 qualify; docs/11 renders do not). post-launch build order (Wed 07-22
onward):

1. r-g posting fixes (collision-recovery truncation + site dedup, posting is live by then),

2. silence_board wiring dark by Mon 08-03 (r-b),

3. docs/11 shelf: 1.6 floor render + 1.10 memo-cadence,

4.
S3.7 whole-run when #177 lands,

5.
Deep Archive 108–112 shards / SD.8 (last, per yield order).
-  2026-07-20 (launch-eve Search lane, Opus, cont.): HX.2 per-topic script-proneness measured
  (descriptive, commit `11286d2`).
Index = coordinated peak≥15 phrases per 1k on-topic statements, per party/lane.
Each party's coordination portfolio differs and shifts across the 2021 seam: propublica D =
crime/energy/healthcare, R = abortion/israel_gaza/taxes; scraped D = guns/taxes/abortion, R =
immigration/veterans/elections, symmetric instrument, asymmetric portfolios (Art.
IV).
The cross-topic ranking is seed-breadth confounded (narrow seeds score higher mechanically) → the
clean signal is cross-party within a topic (seeds cancel): propublica healthcare D 8.9 vs R 4.5,
entitlements D 6.5 vs R 4.8.
Seed-proxy ⇒ C/V are lower bounds, comparative interpretation only.
A methods/transparency-shelf descriptive (docs/20), not a card.
`scripts/search/hx_2_topic_scriptproneness.py`; pushed after `gh run list` clean; zero launch
surface.
Remaining runnable HX: HX.5 (needs the S4.1 `_framing_lexicon` + a placebo per S4.2's law), HX.3
(#143 chamber trap), HX.6 (complex).
-  2026-07-20 (launch-eve Search lane, Opus, cont.): HX.4 phrase half-life × majority-status.
  registered (`bc4d0d1`, freeze before measure) then CONFIRM.
Minority-party coordinated talking points persist ~3× longer than the majority's (median active-days
maj/min = 14/41 propublica, 15/51.5 scraped; rank-biserial r=−0.258/−0.380, both p≪0.05, robust on
the calendar-span metric; frozen gate |r|≥0.10 ∧ p<0.05 ∧ same-direction-both-lanes all met).
"The minority messages; the majority legislates." Symmetric because of the design (House control
flips between parties).  disclosed confound: propublica's majority is party-collinear (R held
113–115), so the scraped lane, mixed D/R majority (117 D, 118–119 R), r=−0.380, is the critical
evidence that the effect is institutional, not partisan; a within-party decomposition is the flagged
publication-precondition, deliberately not run post-hoc in-session.
Candidate card pending Fable/neutrality review + Michael's editorial publication; confirmed-tier
cards 5→6 pending that review. `scripts/search/hx_4_halflife_majority.py` (reads
member_index+daily_series+chambers-control caches, no normalize); pushed `423702d` after `gh run
list` clean; zero launch surface.
Next runnable HX: HX.2 / HX.5.
-  2026-07-20 (launch-eve Search lane, Opus, cont.): HX registration-wave substrate audit (docs/05
  §3) + HX.8 measured (docs/13, commit `fc82262`).
Ran the mandated audit-substrate-against-disk step for all 8 HX: 6 runnable now with local data
(HX.2/3/4/5/6/8), HX.1 blocked-on-network (no persisted GDELT baseline, needs a live doc 2.0 query),
HX.7 blocked-on-source (no floor-calendar, as flagged), the runnable/blocked map for the October
registration wave, so nothing is specced against an imagined table.
HX.8 (prolific-office concentration + intensity-vs-reach; descriptive self-audit, floors
pre-declared MIN_STMTS=10/MIN_OFFICES=30, chambers never pooled #143, lanes never pooled L1,
denominators in view):

1. volume concentration is moderate + party-symmetric (top decile ~36% of statements / Gini ~0.5 in
   2013-20, falling to 0.17-0.25 share / 0.34-0.44 Gini post-2021 as volume spread more evenly);

2. intensity strongly predicts reach in every powered cell (Spearman ρ 0.55-0.91, all p≪1e-16), a
   prolific office is a coordination hub, not a loud self-repeater.
Methods/transparency-shelf descriptives, symmetric because of the design;
`scripts/search/hx_8_office_concentration.py` reads pre-built caches only.
Pushed after `gh run list` clean; zero launch surface.
Next runnable HX (per the audit): HX.2 / HX.4 / HX.5 (all local).
-  2026-07-20 (launch-eve Search lane, Opus, cont.): S5.2 the concern conversion rate, the
  S31-designated item. registered then measured. finding: ~92% of expressed congressional concern is
  never followed by the same member sponsoring an on-topic bill within 180 days (pooled at the
  pre-registered K=2 match, n=28,106 eligible, 95% CI ±0.3pp; non-conversion ranges 63%→92%→98%
  across K=1/2/3, the range is the accurate finding, headlined at K=2).
The p-hacking hole docs/12:457 named is closed by the freeze-before-measure protocol (docs/23
§7.2.5): the four companions, a 31-phrase directed concern lexicon, the 180-day window, the on-topic
rule (≥2 shared content tokens between the concern sentence and the bill's title+crs
policyArea+subjects), and the 300/cell floor + comparative gate, were frozen and committed
(`5cd27da`, `data/reference/search/s5_2-registration.json`) before the measurement (`882f7d7`), so
the freeze provably precedes the result in git history.
Floor/gate = Michael's §4 confirm; K=2 primary = his 2026-07-20 confirm (asked in-session).
All 11 cells powered (107,481 authored bills / 1,048 members, billstatus 113–119; 994 right-censored
past the 2026-07-15 latest bill, 11 no-topic, both excluded, reported).
Party gate passes: D 8.6% vs R 6.8% conversion (both still ~92% non-converting), an asymmetric
finding from a symmetric instrument (identical lexicon/match/threshold, party-blind; Art.
IV protected), robust in propublica-B + scraped-B.
Conservatism (all frozen+disclosed, all push non-conversion UP): authored sponsorship only
(cosponsorship excluded), exact-token match (no stemming), 180-day window.
A stark T1 rate-report card → enters the docs/20 shelf pending Fable/neutrality review + Michael's
editorial publication (publication is his act, never a session's); program confirmed-tier cards 4 →
5 pending that review. zero launch surface (scripts/search + docs/13 + the committed
registration/lexicon + X: evidence; never imports the daily pipeline); `git status` verified, both
commits pushed after `gh run list` clean.
Next docs/13 Search item (per S31): the next runnable item touching no daily surface.
HX registrations (docs/05 §3) qualify; silence_board wiring is explicitly not a Search item (it
edits the daily path; deadline Mon 08-03).
-  2026-07-20 (launch-eve Search lane, Opus): S31 post-launch item (4).
S3.7 the safe-seat vessel test. run early (because #177 closed → the House medsl file is now local)
and REFUTED. zero launch surface touched: only `docs/13` (verdict row), `scripts/search/` (2 scripts
+ result json), a committed `data/reference/search/mov-by-member.json`, and X: evidence, no
daily-pipeline import, no render, no FEATURES/workflow/`derived/days` write; `git status` verified =
those 5 files; pushed `4e29170` after `gh run list` confirmed no cron in flight.
Step 1: the audited medsl margin-of-victory table.
99.9% bioguide join (House 100.0% every cycle 2012–24; surname-disambiguated; independents
King/Sanders matched exact; the only 2 gaps = the GA 2020/21 dual-runoff, accurate).
Step 2: S3.7 run as registered, no knob/floor/rescope added (frozen: PEAK_FLOOR 15 /
MIN_STATEMENTS 10 / effect gate |ρ|≥0.20 / p<0.05 / ≥100 members per cell; the concordance built
read-only via `build.build_concordance(out_dir=None)` over lazily-normalized per-lane-half solo
Lane-1 statements, kept set = the committed `phrase_index` peak≥15, `peak`≡`peak_units` verified).
Verdict REFUTE, a member's seat safety neither frees nor assimilates their party voice: all four
House cells well-powered (n=399/510/226/422), every |ρ|≤0.12, all below the 0.20 effect-size gate
(scraped-B is significant at p=0.012 but ρ=−0.12, the effect-size gate doing its job against a
large-n triviality); the registered MoV-quintile artifact is flat in every cell.
Senate underpowered as pre-registered, the ProPublica/legacy lane carried 2 senators in 2013–16 (vs
494 House), so no Senate cell reaches ≥100; the within-chamber MoV-row filter also caught + dropped
83 corpus chamber-mislabels (senators the corpus tagged `House`), protecting the House ρ.
Program CONFIRMED tally unchanged (4); S3.7 exits the runnable-findings backlog → the next docs/13
Search item is S5.2 (its 300/cell floor freeze before measuring is the p-hacking guard, §7.2.5).
No bus errand, measurement complete, nothing blocked on Michael.

### 2026-07-20 (Session 30b, Opus)

launch-eve polish run, docs/23 §7.5 amendment 2 duties done, commit `eca9153` pushed.
396 tests green, verified green both dark and with all three launch flags flipped.
No launch acts: `POSTING_ENABLED` off, repo private, all FEATURES dark, nothing posted.
1.
Main finding.
Tuesday's natural cron cannot publish day 07-20.
Amendment 2's premise is FALSE AS written and Michael must know before he says go.
Today's 13:26Z assemble no-OPed: `2026-07-19 not ready (only 1 vs same-weekday median 5.5, 18% <
55%) and only 0d old — HOLD`. `readiness.select_target_day` walks oldest-first and returns on the
first non-final day; `product_day` is 07-20 at both Tuesday passes (11:30Z and 21:30Z), so 07-19 is
age 1 all day, under `MAX_WAIT_DAYS=2`.
Simulated across the full count range: 07-19 count 0–3 → no-op; count ≥4 → targets 07-19 (a
4-statement Sunday, which would make the launch homepage thinner than today's).
07-20 is unreachable in every branch, structurally, while an older non-final day sits in the window.
Remedy needs NO new code and is already sanctioned: `--day` bypasses the gate and `assemble.yml`
wires the dispatch input to it (the same path amendment 2(c) uses).
Verified: dispatching 07-20 sets `is_repair=False` → `assemble-latest.json` does repoint to 07-20,
what 2(c) needs.
No hole: 07-19 stays non-final and is re-examined (force-finalized degraded Wed if count ≥1,
costlessly skipped at 0); archive order is safe (`all_day_files` sorts by filename).  expected and
alarming-looking: a dispatch writes `unattended:False`, so `ops.unattended_streak` reads
`passes:False` right after.
That is not a gate failure. §1.4.1 already passed on the historical record (07-16/17/18, Art. xvi);
it gates on evidence already collected.
2.
The public corrections log was silently reset 3→0 BY production today. `corrections.json` held 3
entries; the live `methodology.html` said "Corrections to date: 0.
No published line has yet required a correction.", rendered by assemble `14af2f0`.
Cause (both workflows): `tar -xzf state.tar.gz -C .` extracts the tarball's `data/reference/` over
the git checkout, and 21 files there are tracked with git as their authority, corrections.json, the
Art. xiii privacy form list + allowlist, the nomenclature index.
The commit step stages only `data/derived`+`site/public`, so the rollback never shows in a diff, it
renders wrong and re-uploads itself, self-perpetuating.
On announce eve the site was denying its own error record; the latent privacy-form rollback is worse
(a stale allowlist silently weakens suppression).
Fixed with `git checkout -- data/reference` after the extract (tracked paths only, so the gitignored
roster cache still comes from the tarball).
Re-rendered: "Corrections to date: 3".
3.
The suite was red and would have gone red again on the flip.
(a) `test_tests_never_write_into_the_real_derived_tree` asserted a brief for the hardcoded day
`2026-07-20` never exists, production published that day today, so the canary went permanently red
for a calendrical reason on launch eve; re-pointed at `1999-01-04` (impossible: `STAGE1_EPOCH` is
2025-01-03).
(b) six tests asserted the shipped value of FEATURES flags, not the gating behaviour, every one
fails the instant a flag is deliberately flipped, so the launch commit itself would have reddened
the health gate and the fastest fix would have been deleting the gate tests.
Rewritten to force the flag and assert behaviour, + an explicit `DELIBERATELY_RELEASED` allowlist so
a release is a named reviewable act that still catches an accidental flip.
4. link cards shipped (duty b): the site emitted zero og: tags across all 291 pages.
Added og:type/site_name/title/description/url/image + width/height/alt, twitter:card, rel=canonical
in `site.page()`.
Privacy rule IS the design: og values come from `page()`'s own arguments and never from composite
prose, composites pass `privacy_correct_line()` which can WITHHOLD/RECOMPOSE under Art. xiii, and a
meta tag is a surface no audit scans; locked by an AST test (a substring grep would fire on the
comment explaining the rule) and mutation-verified. `path=` is hand-passed at 16 call sites so the
critical test checks og:url against each file's actual location, every page. `og.png` 1200×630 from
the house seismograph identity; `brand.py` no longer writes to a dead scratchpad path at import, is
`__main__`-guarded + repo-relative, and regeneration is byte-stable (verified: the avatars/banners
live on the three Bluesky profiles did not churn).
5. `phrase_search` verified, flip not taken (per amendment 2 the flip is Tuesday's act): 275 index
   rows / 275 pages, 0 broken links both directions, privacy filter applied, no new derived
   artifact.
The Tuesday flip is two lines: `config.FEATURES["phrase_search"]=True` (with
party_columns+owners_brief) and adding all three to `tests/test_wave0.DELIBERATELY_RELEASED`.
6.
Follow-ups recorded, not done: `site.phrase_search_index()` crashes the whole build on a non-dict
phrase JSON (the page loop guards, the index does not, matters once the flag is live);
`post_bluesky` returns `recovered=True` before posting replies on an rkey collision, leaving a
1-post thread with no receipts post; `post_bluesky.SITE` duplicates the new `config.SITE_URL`
(posting path deliberately frozen for launch). tuesday order, amended BY (1): after the 09:30Z
collect lands Monday's data, read the 11:30Z log for 07-19's real count and 07-20's completeness vs
the ~161 Monday baseline → if 07-19 count ≥1 and you want no gap, `gh workflow run assemble.yml -f
day=2026-07-19` first → then `gh workflow run assemble.yml -f day=2026-07-20` last (so
assemble-latest points at the Monday reading) → verify the homepage → on Michael's go:
POSTING_ENABLED → repo public → announce → flip party_columns+owners_brief+phrase_search (two lines)
→ re-dispatch per 2(c) if needed.

### 2026-07-20 (Session 30, Opus)

The monday repair is run, docs/23 §7.5 steps 1–3 done.
The P0 is closed, {07-12, 07-18} are restored, 386 tests green, commit `1543c0e` pushed.
NO launch acts: `POSTING_ENABLED` untouched, repo private, all 19 FEATURES dark, nothing posted.
Streak re-confirmed `passes:True` value:3 [07-16,07-17,07-18], no manifest touched.
1. the guard: `build_derived` wrote `days/{day}.json` as a full-object overwrite carrying
   `daily_lines: None`, so any run A pass landing on a published day deleted its composites.
   `util.day_is_final()` + one check at that write; `run_assemble._is_final` delegates to the same
   function so the readiness gate and the write guard can never disagree about which days are
   published, that disagreement is how a day got clobbered.
Scoped to `days/` only (discipline/coverage/phrases are the system's current state; the
per-phrase files are living adoption curves that would strand if frozen).
Back-compat is critical: only 4 of 9 published manifests carry a `final` field, so `m.get("final",
True)` is correct and `is True` would leave 5 of 10 days clobberable including 07-12, the day that
proves the bug (mutation-verified).
Fails closed on an unreadable manifest, an adversarial pass caught that the guard had introduced a
new crash surface in run A. `regen_derived --force` is the escape hatch;
`deterministic.run`/`alexandria.merge` never pass it (locked test). `alexandria.merge` was a second,
unfired instance of the same defect, closed for free.
2. the repair.
I deviated from §7.5's named mechanism, deliberately, And this needs michael's eye: `run_assemble
--day` executed literally would have failed the launch gate it is sequenced in front of.
Three measured reasons: (a) it rewrites `assemble-{day}.json`, recomputing `event`/`unattended` from
`GITHUB_EVENT_NAME`, a repair is never `schedule`, `unattended_streak` breaks on the first falsy
`unattended`, and 07-18 is the streak HEAD: simulated `passes:True → passes:False`, unrecoverable
until Wed 07-22, i.e. through launch morning; (b) local state ends 2026-07-09, so a local
re-assemble writes "We released 0 statements today." over days that released 11/12 and 5/3 (Art.
II); (c) it re-authors under FALSE provenance.
07-12's composite is `dry_run`/`P3:dry_run`/1.0 and the cloud would restamp it
`sonnet_direct`/`claude-sonnet-5`/1.1.
So the composites were restored from the exact published bytes (`af36b2a`→07-12, `fb9e447`→07-18) by
surgical key merge; whole-document canonical equality verified both days; deterministic halves
asserted identical, never rewritten.
Proof it is a restore not a regeneration: 07-12's published version carried NO
`duets`/`rejected_keys` and the restore does not synthesize them, while 07-18 gets both back.
`day/2026-07-18.html` re-renders byte-identical, the "stale orphan" was showing the pre-null content
all along.
07-09 not repaired (no committed version ever carried composites; manufacturing one would fabricate,
Art.
II), the archive now marks one day "phrases only".
3. §7.5's repair path itself amended (`repair_safe_manifest`, pure + mutation-verified):
   trigger-provenance (`event`, `unattended`, `run_id`, `forced_finalize`, `readiness`) preserved
   from the published manifest, repair recorded additively; `degraded` not preserved (it describes
   content, a repair that degrades should break the streak); `forced_finalize` IS preserved (the
   `--day` path hard-codes forced=False, so recomputing would launder a force-finalized day into a
   streak-eligible one); a field the original never carried is dropped, never invented (inventing
   `unattended` would manufacture streak evidence).
A repair no longer repoints `assemble-latest.json`, repairing 07-12 would have aimed the first live
post at a nine-day-stale day.
4.
Art. xvi record check: 07-16/17/18 each `event=schedule · unattended=True · degraded=False ·
final=True`, symmetry `degraded=false` (which lives in `derived/symmetry/{day}.json`, not the
assemble manifest), governor nominal, verifier passed/no-fallback both parties every day.
S28's Open check is resolved favourably: `concordance.json` + `awards.json` were both added by cloud
bot commit `0a66cea` and no other commit has ever touched either, production emits both every run,
so the 08-24/09-07 flip confidence now rests on production evidence.
Guard verified not to suppress them.
5. monday digest: `RED: streak, coverage`, both benign. streak red is a timing artifact (today's
   assemble had not run yet); coverage red is the genuine quiet 07-18 weekend (D 5/135, R 3/84).
   spend $0.058 mtd / $0.14 projected, verifier_drop 7.7%, degraded_days [], all green.
6. `scratchpad/` was never gitignored despite canon asserting it since Session 18: `git add -A`
   staged 21 files incl. the Art. xiii name-extraction tooling, onto a repo going PUBLIC tomorrow.
Now ignored.
7. found BY causing IT, the workflows' push-recovery path could never have worked.
My 12:26Z push landed mid-run (today's collect started 12:00Z, ~2.5h scheduler-delayed); its push
was rejected and the fallback died: `cannot pull with rebase: You have unstaged changes` (exit 128).
Both workflows leave files unstaged, so `git pull --rebase` always refuses, the path was unreachable
because of the design and had never once been exercised.
Fixed both with `--autostash`.
This matters for tomorrow: the launch morning commits `party_columns`+`owners_brief` while the
21:30Z pass is live.
Blast radius today: none permanent, the collect step and the state-persist step both succeeded (archive
intact), only the derived commit was lost and the 19:30Z pass rebuilds it; the guard was not
implicated (focus day was the fresh 07-20).
The dead-man fired correctly at ~12:42Z, that ntfy alert was this session's push, not a pipeline
fault.
8. the homepage moved 07-17 → 07-18 (the quiet Saturday).
Michael must know before Tuesday.
That is the accurate consequence of the fix: 07-18 is genuinely the newest lined day, and the 07-17
reading he ruled on was the P0's symptom.
It self-resolves when Tuesday's ~11:30Z assemble lands day 07-20, but today the 11:30Z assemble did
not run at all (scheduler), so that timing is not guaranteed; the launch-morning homepage check must
be made from the record, not assumed.
The §4 quiet-weekend concern is back, not cancelled. never run `run_assemble --day` on 07-12/07-18,
they are already repaired and it would regenerate, not restore.
Corrections-log entry filed (public).
Follow-ups (not blockers): 07-09 is the one published day the invariant does not cover (public page,
no assemble manifest → `regen_derived 2026-07-09` needs no `--force`); `sync_by_party` absent from
all 10 day JSONs so `party_columns` falls back everywhere and would render empty columns on 07-18;
canon correction. `coverage.json` 2 years / `discipline.json` 561 days are correct
(`STAGE1_EPOCH=2025-01-03`), not clobber damage.
Standing rule earned: never push to main while a cron is in flight (`gh run list`).

### 2026-07-20 (Session 29, Fable)

The three s28 findings ruled, docs/23 §7.5 (binding, delegation re-affirmed in-session).
And michael moved launch to tuesday 07-21 (editorial timing, not a gate pause: the announce lands on
the Monday reading, a full weekday page, instead of Sunday's quiet one, he ruled after confirming
the live homepage correctly shows 07-17, the P0's expected symptom).
Monday = the repair day (§7.5 steps 1–3 only, NO launch acts; the guard landing Monday also protects
the Monday reading itself from a later collect nulling it).
Tuesday = the launch morning (after the ~11:30Z assemble lands day 07-20: verify the homepage, then
on Michael's "go" → `POSTING_ENABLED` → repo public → announce → `party_columns`+`owners_brief`).
The "go" stays pending until Tuesday, the point of waiting is that he sees the page before the
announce points the world at it.
Rest of the schedule unmoved. amendment 2 (launch-eve scope, on Michael's ask): three additions, all
inside the one-day vet envelope.
(a) `phrase_search` joins the launch window (the direct navigability answer: 276 phrase pages, only
top-40 tables reach them; built+tested S13; a utility, not a content moment. `duet` keeps 08-17);
(b) link cards: the site emits zero og: meta (verified), every Bluesky share unfurls bare; Monday
adds og:title/description/url + static brand og:image served from site/public, locked test; (c)
first-post timing fix: with the go landing after the 11:30Z assemble, the composites' first threads
wouldn't post until 21:30Z, the announce would point at two silent accounts all day.
Tuesday brief now includes: after go+flips, re-dispatch `assemble.yml day=2026-07-20` (documented
repair path, idempotent posting) so the first threads land in the announce's morning window; the
11:30Z dry-run log is the final preview, eyeballed before the flip. `archive` stays dark for 08-03
(biggest content moment = the second attention spike; deepest-scrutiny surface shouldn't debut on
the loudest day).
NO embed/quote-post wiring on launch eve, house-account quote-posts are Michael's in-app act; member
quotes inside threads = post-launch (new surface, own verifier/privacy gates).
Monday prompt: "read claude.md and docs/23 §7.5, run the Monday repair + launch-eve polish." r-a
(#179 closed): the aca rider's operative rule stands on corrected facts, the measured behavior IS
the system working.
Neither party's ordinary framing tags (`affordable care act` 0.0049/1,820 docs · `the affordable
care act` 0.0008 · `obamacare` no row); only `the unaffordable care act` tags (1.0, hr6300, an
actual introduced bill).
Occurrence-not-phrase (docs/16): 99.5% of aca uses are message, so no tag; every "unaffordable" use
references an official title, so tag.
The asymmetry traces to the parties' own conduct, one caucus legislated its counter-brand, the
other's ("the big ugly bill", 0.000) never became a title.
One rule, both parties = an asymmetric finding from a symmetric instrument (Art. iv's protected
category, a better demonstration than the imaginary asymmetry the original rationale accepted).
07-27 flip re-authorized + riders: descriptive-citational chip copy only · Methodology's worked
example = the aca family · §9-5 bar extended (never claim "D vocabulary tags"). r-b: silence_board
dates hold behind a wiring deadline, boards accumulating dark in production by Mon 08-03 or the
08-10 flip slips week-by-week; `awards` (08-24) ships whole-or-slips (The Void live-fed at flip;
UNAVAILABLE is a degradation state, not a launch state).
Opus work, no errand. r-c: the daily_lines nulling is a P0, the §7.3 health gate's first catch is
US, before the first flip; that goes in the methods story. invariant ordered + locked test: a
`final:True` day is immutable to run A; the only write path to a published day is `run_assemble
--day` (repair).
Evidence correction to S28: repairs = {07-12, 07-18}.
07-12 proven (af36b2a carried 2 composites → collect-07-14 6459640 carries 0); 07-18 proven
(0a66cea, −85 lines); 07-09 was never damaged, no committed version of its file ever carried
daily_lines (verified across its full history); it is an accurate phrases-only backfill day, and
repairing it would fabricate (Art.
II).
Never unlink a public day page.
Launch-morning order (docs/23 §7.5):

1. guard + 2 repairs + suite + site coherent →

2.
Art.-xvi record check of the morning cloud commits incl. whether concordance.json/awards.json landed
→

3.
Monday digest green →

4. on Michael's "go": POSTING_ENABLED → repo public → announce (recommended 4-post affirmed,
   verbatim, confirm=POST) → flip party_columns + owners_brief →

5. any failure: ntfy, slip day-by-day.
The delegation does not consume §7.4.2, the first public words get a human eye by design.
Monday worker prompt: "read claude.md and docs/23 §7.5, run the Monday repair." Tuesday worker
prompt: "read claude.md and docs/23 §7.5, run the launch morning."

### 2026-07-19 (Session 28, Opus)

The pre-launch duties are run, docs/23 §7.3's worker list is done; launch is ready pending Michael's
one "go".
Nothing flipped, nothing posted, all FEATURES dark, `POSTING_ENABLED` off, streak `passes:True`
re-confirmed at close.
370 tests green.
Commit `fc8f80f`.
1. day navigation fixed, the day pages were permanent and unreachable: `index.html` linked to zero
   of them (the `is_today` branch swapped prev/next for a phrases link), so the prev/next chain had
   no entry point and ten days of published record were reachable only by typing a URL.
Nav gains Days; new `/day/index.html` archive (newest first, by month, phrases-only days marked not
dropped); the homepage links the previous day + the archive.
Built from the same `rendered` list the pages come from, so it can't list a 404 or omit a live page.
`tests/test_day_nav.py` locks that both directions, plus "no FEATURES flag" (gating navigation to
already-public pages would re-orphan every day page).
2. the announce path wired. `pipeline/announce.py` + a `workflow_dispatch`-only `announce.yml`,
   reusing the Session-8d live-smoke-tested at-Proto primitives.
Gates failure tested alone: no `--confirm` ⇒ dry run · `POSTING_ENABLED` off holds even with
`--confirm` + real creds · missing creds hold · absent variable reads off.
The approved text never lives in-repo (it is the dispatch input, so pasting IS approving); `---`
lines are author-chosen post boundaries and an over-length authored post is refused, never silently
re-split; `verbatim_ok()` locks word-for-word reconstruction; no automated-composite marker (that
marker labels the machine-distilled party voice, stamping human-approved copy would be a FALSE
label).
A locked test asserts no cron trigger ever appears.
3. announce DRAFT at `X:\onscript-data\drafts\ANNOUNCE-launch.md` (never in-repo): 4-post
   recommended thread + 2 alternatives, every char count measured through the live builder.
It corrects canon: "53 D on 'born in the united states'" is the Unison office-share numerator, a
different estimator, the page a reader lands on says 36, so the copy says 36.
4. flip audit, two schedule findings.  `nomenclature_tags` (07-27): §7.2.1's aca rationale is
   factually inverted.
Measured at the live threshold (0.8) via `nomenclature.tag()`: `affordable care act` 0.0049 → not
tagged · `the affordable care act` 0.0008 → not tagged · `obamacare` → not tagged · but
`unaffordable care act`/`the unaffordable care act` = 1.0 → tagged (hr6300).
The asymmetry runs opposite to the one the ruling accepted: neither party's ordinary framing tags,
and the only aca-family phrase that does is a Republican counter-brand. span may be working precisely
as designed, so this may need no code change, but the ratified rationale is backwards and it
authorizes the flip. #179 filed; blocks 07-27 only, not launch.  `silence_board` (08-10) is not a
one-commit flip. `silence.silence_board()` has NO caller anywhere and `data/derived/silence/` has
never been built; flipping renders nothing, and it cascades to The Void half of `awards` (08-24).
Both need a build session (future-Opus work, deliberately not a bus errand).
Pure one-line flips confirmed: `party_columns` (fallback verified on real days), `owners_brief`,
`archive`, `duet`/`phrase_search`/`authors_vessels`. `concordance.json`/`awards.json` absent locally
because local state (07-10/07-12) predates the Session-23/24 code, production builds them in-process
each run; a direct re-verify was abandoned, not completed (it re-parses the 3.08 GB ledger).
Confirm the next cloud run emits both before 08-24/09-07.
5. launch-timing note (Michael's call, unchanged): the newest day 07-18 (Sat) ingested 5 D / 3 R
   statements (vs 82/55 and 159/84 the two days prior) → zero synchronized phrases, accurate quiet
   composites.
The guard worked and `degraded=False` is correct, but a Mon 07-20 announce lands on a homepage
showing Sunday's quiet weekend day; the flagship convergence demo is a weekday phenomenon.
The day-nav fix softens it (a rich day is now one click away).
6.
Bus: #176 closed (packet ratified), #179 filed, Session-26 vtask pagination fix verified present.
7. found AT close (00:45Z). run A nulls `daily_lines` ON already-published (`final:True`) days.
   `collect 2026-07-19` (`0a66cea`) rewrote `days/2026-07-18.json` to `"daily_lines": null` (−85
   lines), deleting a published day's composites; the later assemble targeted 07-19 and never
   restored them.
Systemic: 3 of 10 published days are now nulled.
07-09 (19 phrase rows), 07-12 (14 rows, nulled by `collect 2026-07-14`), 07-18 (0 rows, tonight).
The "phrases only" days the new archive marks are not a natural category, they are this bug's scar
tissue.
Two live consequences: (a) a stale orphan page is public. `day/2026-07-18.html` still renders "We
released 5 statements today" with no backing data (`build_site` only writes, never unlinks, the
exact hazard `privacy.purge_derived` already names); (b) the homepage moved to 07-17 (Fri), since
"today" = most recent day with daily_lines, which incidentally cancels the §4 quiet-weekend
launch-timing concern (the landing page is now a 20-phrase weekday).
A defect improving the optics is not a reason to keep it. not fixed here, deliberately: unlinking
orphaned pages treats the symptom and would delete public pages the project treats as permanent; the
real fix is upstream (run A must not null a `final:True` day) plus repairing the 3 days via
`run_assemble.py --day <day>`, the documented gate-bypassing repair path.
It is the next worker's first item, ahead of the docs/11 shelf.
Launch impact: nothing mechanical (site coherent, no 404s, posting path untouched), but the announce
points at a site with one stale day page and two days missing composites.
Michael should know before he says go.
Next worker:

1. the daily_lines nulling fix + repair the 3 days,

2. wire `silence_board` before 08-10,

3. the docs/11 dark shelf.

### 2026-07-19 (Session 27, Fable)

The flip packet is ratified, docs/23 §7 is the binding launch + release schedule. go-live IS mon
2026-07-20, pending two Michael acts (#131 passwords + one "go" reply approving the announce
text).
Michael's gate rulings: #129 done · #110/#105 waived for launch (open post-launch) · #160/#161
sufficient (closed) · GitHub purge DEFERRED at his leisure.
All remaining reserved decisions were delegated to Fable and are made in §7.2: nomenclature riders
resolved (aca = cumulative index, tag-is-annotation; NO quiet-day floor; §9-5 framing bar),
Concordance/Awards knobs ratified as measured, fold-vs-isolate = fold (P4 unblocked), S5.2 floor =
300 CONFIRMED (companions freeze in the ledger before measurement). §7.3 is the standing conditional
release schedule: launch Mon 07-20 (+ party_columns + owners_brief) → nomenclature_tags 07-27 →
archive 08-03 → P1 ~08-05 → silence_board 08-10 → duet 08-17 → P2 ~08-19 → awards 08-24 →
authors_vessels + fall-lock 08-31 → concordance 09-07 → freeze ~10-12.
Every flip is health-gated (Monday digest green · no open P0 · clean audits · site current); any
failure pauses the schedule and escalates via ntfy; Michael holds a standing veto.
Worker-session pre-Mon duties (docs/23 §7.3): announce + P1/P2 drafts to `X:\onscript-data\drafts\`
(never in-repo) · fix the vtask pagination bug · prep each flip as a ready one-commit change · final
end-to-end dry-run.
Stale tasks #129/#145/#159/#160/#161 closed.
Next worker prompt: "read claude.md and docs/23 §7, run the pre-launch duties." After launch,
workers run the schedule + the docs/11 build queue + the docs/20 drip + HX registration waves as
capacity allows.

### 2026-07-19 (Session 26, Opus)

the flip packet delivered + two runnable findings.
No code, no flips, nothing published; 348 green at open and close.
Ran docs/22 (the flip-packet brief). `docs/23-FLIP-PACKET.md` (DRAFT.
Michael to ratify; commit `d31f447`, vtask #176): every reserved decision from Sessions 12–24 swept
exhaustively into one doc, three tiers.
Tier 1 launch acts (only these gate launch: #129/#110 status → #160/#161 privacy-history residuals
(+GitHub server-side purge) → real passwords/`POSTING_ENABLED`/public/announce; the 5 docs/16 §9
rulings dispositioned.
4 gate feature flips, not launch), Tier 2 feature flips (all built-dark, none launch-blocking; rec:
flip `party_columns`+`owners_brief`, schedule the rest as docs/20 moments, knobs listed), Tier 3
publication acts (S1.9/S2.9/Intensification, calendar-paced; fold-vs-isolate `page_html` a
precondition).
Packet also carries S5.2's floor pre-registration (§4, binomial-power, min-cell 300, awaiting
Michael's one-line confirm, not self-supplied) and flags #145/#159 stale-open (suppression live,
salt set). findings (docs/13 rows; commit `ffd52ea`): S1.12 Leadership Ignites REFUTED both lanes
(false block resolved, roster on disk; core-leadership offices first-say big ignitions at 0.82/0.89×
propublica, 1.61/0.95× scraped their statement share, never ≥3×, all cells powered, robust;
tie-inclusive day-0-cosayer variant 1.9–2.7× is the accurate nuance, still <3×; publishable null;
floors frozen before measuring, script `scripts/search/s1_12_leadership.py`).
S3.7 registered + BLOCKED.
Senate medsl is ungated CC0 (local), the House file is behind a required Dataverse guestbook (id
458) the "keyless CC0" check missed (`gbrecs=true` fails; the only path submits personal data, not
fabricated); errand #177 filed, S3.7 floors pre-registered now (member-level Spearman
within-chamber/within-lane, ≥100/cell power floor = why Senate-alone isn't run).
Two August drips drafted to `X:\onscript-data\drafts\` (P1 Self-Audit/S1.9, P2 Boogeyman/S2.9),
never in-repo.
Streak re-confirmed `passes:True` at open and close; all FEATURES dark, `POSTING_ENABLED` off.
Reserved (untouched): the packet IS the reserved list.
Michael rules it.
Next Opus: docs/11 dark shelf (1.6 floor render, 1.10 memo-cadence); when #177 lands, the whole S3.7
run.  tooling fix (global, not this repo): `vtask list`/dedupe silently truncated to the oldest 50
tasks (Vikunja caps `per_page`=50, no sort), the session-start ritual showed 10 open when there are
13, hiding the launch-blocking #161 and creating a dup (#178, closed).
Fixed `~/.claude/vtask/vtask.py:get_open_tasks` to paginate; every prior session on a >50-task
project read a truncated bus.

### 2026-07-19 (Session 25, Fable)

sessions 23–24 recovered + the flip-packet brief authored.
Two interrupted Opus sessions had completed 1.4 (Concordance) and 1.5 (Unison/Void), code, tests,
and their own canon entries, but died before committing; Fable re-verified (full suite 348 green,
observed not trusted) and committed the recovered work with dual attribution.
Build-order 6 is complete and on main.
With §1.4.1 passed, the constraint has moved from build to decisions: a dozen reserved
knobs/flags/framings are scattered across Sessions 12–24.
Next Opus session: `docs/22-FLIP-PACKET-BRIEF.md` (binding), start it with "read claude.md and run
the flip-packet brief." It assembles `docs/23-FLIP-PACKET.md` (DRAFT.
Michael ratifies: Tier 1 launch acts / Tier 2 feature flips / Tier 3 publication acts; Fable's
standing steer = launch minimal, Tier 1 + at most party_columns/nomenclature_tags, every other flip
a scheduled docs/20 content moment), then runs the runnable findings (S1.12 · S3.7-MoV · S5.2 after
its floor is confirmed, the p-hacking hole is not self-suppliable) and drafts the August pieces to
X:, never in-repo.
-  2026-07-19: §1.4.1 has passed, the unattended streak is 3/3, verified from the record (Art. xvi,
  not run status).
Days 07-16, 07-17, 07-18 are each `event=schedule · unattended=True · degraded=False · final=True ·
symmetry.degraded=False` (the 07-19 cron landed the 07-18 day);
`ops.unattended_streak('2026-07-19')` returns `passes=True`.
It is the S2→S3 readiness gate the whole daily pipeline existed to clear, three consecutive clean
unattended real runs incl. a weekend day.
The gate is cleared; the S3 launch acts remain Michael's reserved acts (real Bluesky app passwords →
flip `POSTING_ENABLED` → repo public → announce; #131/#132).
Nothing about It is a launch decision, it is the evidence that unblocks one.

### 2026-07-19 (Session 24, Opus)

build-order 6 complete.
1.5 The Unison + The Void (R2) built dark, 348 tests green.
The symmetric weekly awards that R2 substituted for the killed Ventriloquism Award ("most on-script
member" is dead: 318/538 tie at zero, and naming a "vessel" is a chamber/tenure/nomenclature + Art.
X confound).
Both awards are PHRASE-/TOPIC-level, never member-level.
Behind `FEATURES["awards"]` (the 1.5 slot / A9; default off, the flip is Michael's).
`build.build_awards` → `derived/awards.json` every run (from `deterministic.run`, wrapped
skip-and-log). the unison = each party's largest single-day office-share phrase over a trailing
7-day window (offices that used one exact phrase in a solo release ÷ offices that published any solo
release that day, numerator = ledger `members_{party}` ∩ the day's active-solo set, so share ∈
[0,1]); span-gated (a bill title never wins), privacy/boilerplate filtered, joint releases excluded,
both parties one rule; the numerator IS the coordination magnitude so no phrase-peak floor needed.
Reuses the flagship `collapse_and_rank` so near-dup fragments don't clutter (real-data finding:
"united states of" + "the united states of" were showing as two rows, fixed). the void = the
window's loudest silence, both directions, rolled up from the 1.2 absence-map boards; degrades
accurately to UNAVAILABLE when no scored board exists for the window (a gap is never a silence, the
state on real data today, since silence_board is dark). `UNISON_MIN_ACTIVE=20` measured, not
guessed: active-solo-offices/day is bimodal, normal weekdays 40–112 D / 24–77 R (median 47/36) vs a
thin-day cluster ≤17 (July 4th, weekends); 20 sits in the empty gap for both parties, excluding
holidays symmetrically (at floor 15 the D winner was July-4th commemoration on 17 offices while R's
4-of-10 fell below the bar, an asymmetric artifact).
The metric's real signal shows on a news day: 2026-06-30 "born in the united states" = 53/102 D =
52% office-share; a quiet week surfaces generic/commemorative language, which is accurate (no
blocklist, docs/16 anti-pattern).
Render `site.awards_body` written only when the flag flips; Methodology + nav gated; flag-off = zero
public bytes (locked tests: nav absent, `methodology_body()` byte-identical).
Validated end-to-end on real data (awards.json round-trips, render 16 KB, dark gating holds).
`tests/test_awards.py` (19 tests). reserved for Michael at flip (not self-authorized): the flip; the
`MIN_ACTIVE`(20)/`WINDOW_DAYS`(7)/`TOP_N`(5) defaults; the framing (is a thin-holiday commemoration
or a ~20% normal-day fragment worth headlining as "The Unison"?; does The Void ship before the
absence map is publicly live?); an optional content-floor on the winning phrase (deliberately not
added, the min-active floor + "descriptive overlap, not motive" banner are the accurate controls).
Build-order 6 (rulings-shaped 1.3/1.4/1.5) is done.
1.3 origination + R3 columns (S22) + 1.4 Concordance (S23) + 1.5 Unison/Void (this session), all
dark, span-gated, behind their flags.
Streak unchanged (the daily pipeline doesn't import the awards render; the 3/3 §1.4.1 pass stands).
next dark-shelf (docs/11): 1.6 floor render + coverage metric, 1.10 memo-cadence, 1.9 (gated on
`DATA_GOV_API_KEY`).

### 2026-07-19 (Session 23, Opus)

build-order 6 cont..
1.4 The Concordance (R4) built dark, 329 tests green.
The per-member on-script index (the discipline index is only per-party-per-day), behind
`FEATURES["concordance"]` (the 1.4 slot; the unused pre-ruling `the_script` key renamed to match
R4). `build.build_concordance` → `derived/concordance.json` every run (from `deterministic.run`,
skip-and-log so a dark feature can't crash run A): of a member's solo (non-joint) Lane-1 releases,
the share using a phrase their party genuinely converged on. span-gated (official names excluded per
the statement's congress via committed `is_nomenclature`), Art. xiii privacy + display-boilerplate
filtered, ≥3 receipts/named member, both parties, ranked within-party (a reference index, not the
#143/R2 leaderboard/Ventriloquism award). key finding, the metric saturates at ~1.00 for everyone
against the raw ledger (a real 45-day window = 41k phrases → 91% of members read ≥0.99; nearly every
release shares some 3-member-co-used gram, member names/titles, agency names, generic language), a
misleading Art.
IV artifact, the #143 confound family.
Fixed with Session 22's control: `CONCORDANCE_PEAK_FLOOR` (a phrase is "party script" only if it hit
≥floor members in one day). measured the named-member index distribution across floors:
`0→mean.99/91%sat · 10→.63 · 15→.32 (IQR.18–.43) · 20→.20 · 30→.04/64%zero(10 phrases)`; default 15
(best spread; = `ORIGINATION_PEAK_FLOOR`; disclosed/movable). `CONCORDANCE_MIN_STATEMENTS=10` naming
floor (no tied-at-zero swarm; below-floor disclosed in aggregate).
Render `site.concordance_body` written only when the flag flips (built-dark = absent from output);
Methodology gains a gated section; flag-off = zero public bytes (locked tests: nav link absent,
`methodology_body()` byte-identical). `tests/test_concordance.py` (14 tests). reserved for Michael
at flip (not self-authorized): the flip itself; the `PEAK_FLOOR`(15)/`MIN_STATEMENTS`(10) defaults;
the leaderboard-vs-reference framing (the dark render is a neutral within-party-sorted table + heavy
no-motive caveats, a "most on-script member" headline is a publication act).
Two metric defs matched to the existing discipline index, flagged for review: on-script counts a
phrase synced by either party (own-party-only = possible tightening) and counts it any time it's in
the kept set (not only its sync day). not built (its own session): 1.5 The Unison + The Void (R2).
Streak unchanged (the 3/3 §1.4.1 pass stands).

### 2026-07-19 (Session 22, Opus)

build-order 6 begins.
1.3 origination (R2) built dark, 310 tests green.
First increment of rulings-shaped 1.3/1.4/1.5 (docs/21 §3.2.
Opus implements to the rulings; the flip stays Michael's). `site._origination_line` replaces the
retired author leaderboard (#143 = tenure+chamber+nomenclature confound, "Chip Roy authored the save
Act"): a per-phrase origination claim only under three controls. span (a nomenclature phrase via
committed `is_nomenclature` gets NO authorship claim), the #143 coordination floor
(`ORIGINATION_PEAK_FLOOR=15`, else it's a chamber artifact), and born-coordinated (multiple day-0
sayers = no single author).
Behind `FEATURES["authors_vessels"]` (dark; flag-off = phrase page byte-identical, locked test,
nothing live changed, no re-render).
The live phrase page had made the raw "First said by {member}" claim for bill titles too, now
span-gated when the flag flips. not built (future increments): a dedicated origination surface /
phrases-index treatment, 1.4 The Concordance (R4: denominators every line, no predictive claim,
span-gated), 1.5 The Unison + The Void (R2). `tests/test_origination.py`.
R3 / #146 also built dark behind `FEATURES["party_columns"]`: the pooled `collapse_and_rank(k=20)`
makes the flagship table 88% D (measured 20 D / 0 R on 2026-07-15), a live Art.
IV artifact; the fix puts it in the view not the threshold. `build.top_synchronized_by_party` (each
party its own top-k, ranked within-party) + `site.party_columns_table` (two columns, N-of-caucus
denominator per row); `run_assemble` writes `day_json["sync_by_party"]` every day so the flip is
pure release; flag-off = current pooled `sync_table` byte-identical (locked test); historical days
fall back to the stored top-20 (bounded pre-flip limitation: a minority column can read empty).
`tests/test_party_columns.py`.
315 tests green. next: 1.4 Concordance (per-member on-script, new data layer) + 1.5.
Streak unchanged 2/3.

### 2026-07-19 (Session 22, Fable)

the external hypothesis backlog adjudicated and banked. `docs/05-HORIZON.md` §3.
Kept 8 registration-wave candidates (HX.1–HX.8, headlined by the gdelt-anchored script-formation
nulls, which dissolve the crisis-events.json disease by using the built silence-detector baseline as
the event anchor), the upstream-lane hypothesis set (banked for v3, with the unpriced
symmetric-instrument cost flagged), and two  historical acquisitions (Clinton-era CREC 1994+ probe;
Watergate bound-edition downgraded to medium, new parser, no mods).
Adjudicated out: Friday-diffusion variants (S4.4's corpse), pre-span member constructs (#143's
corpse), motive framing, social ingestion.
Most of its "prestige historical" list is already inside the crawled 2001–2026 CREC span, analysis,
not acquisition.
Nothing jumps the queue.
Also noted from Session 21's close: the §4b flip-block is satisfied (P0 fixed always-on, 19 findings
across 7/10 days corrected + logged) and the §4 rider passed with the findings sharpened (S1.1′
11.33→12.0×, S1.3′ 0.373→0.381 tag-stripped), the Aug/Sep drip gate is cleared; the Intensification
publication conditions (#174) are now fully met pending only Michael's editorial act.

### 2026-07-18 (Session 21, Opus)

the nomenclature wiring ran, docs/19 executed in full (incl.
Michael's mid-session second-pass `df6e2d6`), merged dark to main, 304 tests green.
Build-order step

5. is done. §2 wiring, all dark behind `FEATURES["nomenclature_tags"]` (default off; the flip is
   Michael's one commit): §2a measure `nomenclature_rate` per party in the nightly audit is
   unconditional (does not read the flag; denominator = the full sync set, not the top-20, so the
   103-D/15-R skew can't fake asymmetry); `thresholds_sha` folds the knob+index-version only when
   live. §2b `nomenclature.tag()` at render time in `sync_table` + `phrase_page_body` (tags copies;
   a `_nomenclature_chip` cites the official record). §2c `build_stats` annotates a bill-name key +
   `_compose_llm` appends a runtime voice clause (committed prompts byte-stable dark; `prompts_sha`
   discloses the clause when live). §3 acceptance all pass, flag-off = zero public bytes is a locked
   test; the verdicts re-derivation reproduced the spec anchors (sync 461,501, covered
   14,175). §4b the connective-cluster P0. fixed, always-on (a correctness fix, not the dark
   feature): `boilerplate.is_scaffold_key` (deterministic, party-blind key-admission gate: trailing
   function-word/possessive or attribution frame) + a key-span-gated family quorum in `verify`
   (`key_carrying_units` counts only families whose source carries the key, via `contains_gram`;
   `_citations` filters to the same set).
Both live 07-17 defect keys die; both flagships survive.
The audit (`scripts/audit_connective_keys.py`) found 19 inadmissible talking points across 7/10
published days, D 15 / R 4 (party-blind; skew tracks the caucus). systemic. `daily_line_panel` drops
them at render and re-derives the composite deterministically (the reviewer's P1: the stale Sonnet
prose would otherwise narrate the interlopers over "nothing cleared the threshold", an Art.
II fabricated silence; fixed on the privacy re-composition path, new "readmitted" state, accurate
banner, verified on real 07-17 D).
Receipts gain span-highlighting + per-test chips (req 3).
Corrections-log entry filed (req 4).
Second-pass (`df6e2d6`) folded in: stable rejection reason codes (`boilerplate.scaffold_reason` →
REJECT_ATTRIBUTION_FRAME / REJECT_INCOMPLETE_SYNTACTIC_SPAN) covering both directions, the audit
categorizes the backward view over published days (18 span / 1 attribution, rejected-candidates log)
and `run_assemble._reject_reason` emits the forward view into `day_json["rejected_keys"]` (Art. xiii
guard: never a private-name label); the receipt aggregate is a derived conjunction
(verified-or-UNAVAILABLE, no reduced-confidence middle); support-graph validity queued in docs/11 §4
(the free-text voice can't bind clauses to cluster ids, the render-time re-composition is the
interim "no proposition outlives its evidence" guarantee); the human sample audit of
admitted+rejected clusters folds into #129. §4 rider, all three exposed CONFIRMEDs survive
tag-stripping (S1.9 D>R 68% of weeks; S1.1′ ratio 11.33→12.0, S1.3′ drop 0.373→0.381, removing the
1.4% nomenclature phrases sharpened the intensification; not a bill-title artifact); clears the §4
gate on the Aug/Sep drip pieces.
Ledger row in docs/13. §4c: per-post ai-composite marker now on every post unit (was a live-post
gap).
Adversarial review confirmed the four hard invariants hold.
Reserved (not self-authorized, unchanged): the 5 spec-§9 rulings, the `nomenclature_tags` flip,
publication of any card, the S1.1′/S1.3′ REFUTED→CONFIRMED publication (Fable/neutrality).
Named follow-ups: scaffold-aware key selection (so a real cluster keeps a better key instead of
dying, the P2 breadth mitigation), per-member ingest-health flags, phrase-page/archive-fingerprint
tag surfaces, the §4c clause-ablation + observed-publishing-member + timestamp-labeling items.
Streak from the record: 2/3 (07-16, 07-17 clean unattended), earliest §1.4.1 pass Sat 07-19,
consistent with docs/19 §0. next (build order 6): rulings-shaped 1.3/1.4/1.5 (span-gated, behind
this merge).

### 2026-07-18 (Session 20 close, Fable)

continuity secured. `docs/21-CONTINUITY.md` authored (binding).
Fable may become unavailable; the succession is now on disk: Michael takes the ruling seat (he
always held it.
Fable only drafted), Opus drafts decision memos and draft-marked briefs but never self-authorizes
the reserved list, the October reversal re-registrations and the 1.3/1.4/1.5 shapes have explicit
no-Fable dispositions (docs/21 §3), and every binding doc executes as written without me.
The full pathway for the next Opus session is: claude.md → docs/19 (incl. §4b P0 + §4c riders) →
rider rows to docs/13 → then the post-merge queue (rulings-shaped 1.3/1.4/1.5, per R2/R3/R4 +
docs/21 §3.2).
Start it with "read claude.md and run the nomenclature wiring brief." Nothing critical lives outside
the repo.

### 2026-07-18 (Session 20 cont., Fable)

external review adjudicated, a P0 defect class confirmed on the live site (two instances reproduced;
historical extent unknown until the §4b all-days audit runs), docs/19 amended (§4b), fix blocks the
launch flip.
A ChatGPT critique flagged 07-17 D talking points whose receipts don't support the message;
reproduced from the day JSON: cluster keys `into the trump administration's` (Padilla+Goldman
Army-Corps investigation + Booker's unrelated flood bill) and `democratic colleagues in demanding
the` (Kelly+Rosen, the same fema joint letter, one document family. + Krishnamoorthi's unrelated
Blanche release).
The receipts are not fake, every citation contains its cluster key verbatim (that's why they
clustered; the verifier accurately verified it).
The defect: connective-frame/attribution-boilerplate cluster keys admit semantically incoherent
clusters, docs/16's insight wearing a third face (nomenclature · attribution frames · connective
scaffolding all manufacture non-message co-use).
Fix specified in docs/19 §4b (deterministic key-admission gate, joint-unit quorum check on the
citation path, exact-span receipt highlighting + per-test verifier chips, historical re-render +
corrections log), runs in the nomenclature wiring session, before the flip.
Rest of the critique: ~5 points independently re-derive standing rulings (lineage=R2,
denominators=R3, no-opaque-index=R4, boilerplate-out=docs/16, coverage disclosure=symmetry audit);
its "model-free is inconsistent" claim is FALSE post-#119 (about-page wording verified accurate);
its committee/leadership/caucus source recommendation adopted into v3 upstream-graph planning; its
floor-speech deprioritization misreads why CREC exists (instrument repair, not message-layer bet).

### 2026-07-18 (Session 20 cont., Fable)

#174 CONFIRMED by Michael in-session, the Intensification ruling is now binding (two-panel R6 framing · density caveat · docs/19 §4 rider · correlation labels).
And #157 was a FALSE block, closed: both medsl margin-of-victory datasets on Harvard Dataverse.
"U.S.
House 1976–2024" (doi:10.7910/DVN/IG0UN2, v15 2026-03-09) and "U.S.
Senate statewide 1976–2024" (doi:10.7910/DVN/PEJ5QU, v8), are CC0 1.0 with `fileAccessRequest:
false`, verified via the Dataverse API 2026-07-18: no ToS click-through exists.
The S3.7 unblock is therefore a pure build act (keyless download + offline parse-and-commit to
`bioguide × cycle → margin`, the committee-names pattern), an Opus session does it whole; no human
errand.
Third instance of the elections.json disease inverted: this time the assumed blocker, not the
assumed table, was imaginary.

### 2026-07-18 (Session 20, Fable)

the intensification ruling + the wiring brief + the drip calendar.
The re-validation program (all 34) is closed; this session converts its output into publishable
direction.
Ruling on S1.1′/S1.3′ (CONFIRMED by Michael, see above): publishable as OnScript's 3rd/4th findings
under four conditions.
1. two-panel framing per R6: each lane its own panel with the system change labeled at
   2021-01-03; the claim is "confirmed acceleration within 2013-2020" + "no acceleration detectable
   within 2021-26", never a single joined "then it stopped" series (the stop-claim would cross the
   seam interpretively);

2. the density caveat (count-matched, not statement-density-matched) printed on the card;

3. the docs/19 §4 nomenclature robustness rider passes (bursts may be bill-title driven, the 11.3×
   must survive tag-stripping; S1.9's launch essay carries the same rider; S2.9 exempt);

4. correlation-not-cause labels. `docs/19-NOMENCLATURE-WIRING-BRIEF.md` authored (binding), next
   Opus session starts with "read claude.md and run the nomenclature wiring brief": rebase
   `wip/nomenclature`, wire tag() at three points (audit metric live; site display-time +
   pre-distill behind a default-off `nomenclature_tags` flag, the flip is Michael's), the §4 rider,
   adversarial review, merge dark. `docs/20-DRIP-CALENDAR.md` authored (operating plan), the accurate
   answer to "we don't have much": three shelves ≈ 20+ content moments over 12 months with zero new
   CONFIRMED needed (launch essays Aug, myth-busts Sep–Oct, freeze from mid-Oct, product carries
   November, methods flagship + graveyard annual Dec, euphemism series + CREC cross-confirms + live
   scotus season 2027).
Streak instrument read 0 this morning (consistent, evidentiary runs are the 07-17/18/19 crons;
earliest pass Sat 07-19).
No discrepancies.

### 2026-07-17 (Session 19, Opus)

the shard lanes (docs/18), the eleven blocked-on-shards items re-validated within lane; two new
CONFIRMED.
Per-lane alexandria shards built for 113-119 (`ALEX/lanes/`, merge() untouched); all 7 congresses
reconcile (records partition exact, 0 statement delta, 0 cross-lane id-dups, incl. c118/c119
where propublica is 0 records, the seam on record).
The eleven ran within each lane; zero false-positive flips across all 22 (11×2 lanes).
Headline: S1.1′/S1.3′ (the "Great Intensification") CONFIRM within the propublica lane, ignition
width collapsed 34d→3d (11.3×) and burst lifespan −37% through 2013-2020, both surviving the density
control, and are ARTIFACT/absent in the scraped lane (2021-26).
They were REFUTED across the seam only because the post-2021 plateau broke the monotone gate; lane
isolation, on docs/18-§5 pre-registered halves, made them confirmable.
Program CONFIRMED tally 2→4, pending Fable/neutrality review (REFUTED→CONFIRMED movements; disclose
the density caveat, count-matched, not statement-density-matched, on any card).
The rest stand: S1.1/S1.3 ARTIFACT in both lanes (sawtooth is a per-shard artifact,
seam-independent), S1.2/S1.5/S1.7/S1.8/S1.11 refuted-stand, S1.6/S1.4-proper accurately underpowered
in-lane.
Also fixed: a file-level cache corruption (raw byte under concurrent X: I/O) crashed the first run,
hardened the jsonl readers to skip+warn, propublica caches scanned clean so the CONFIRMEDs rest on
good data.
263 tests green.
Nothing published changed (the daily pipeline doesn't import alexandria). next (build-order 5):
nomenclature wiring.

### 2026-07-17 (Session 18, Opus)

the re-validation, the runnable half of the 34 re-measured within one lane; the seam overturned zero
runnable verdicts.
Both CONFIRMEDs survive: S2.9 is now twice-confirmed (CONFIRMED in propublica on its own split and
in scraped on its own split) and S1.9 re-affirmed (the 144 legacy 2021-01-03 records in congress 117
are a measured no-op.
"lane-clean because of the design" is really 99.6%).
S2.3's kill was not plumbing.
REFUTED in both lanes, well-powered in every cell (the ledger's proof-the-control-works holds).
Full S2 wave + S1.4 + S1.10 re-run within lanes; 7/8 S2 verdicts identical across lanes, only S2.7
moved (propublica-only confirm → reversal candidate, not a card); S1.4's "D copy-paste rose both
halves" sub-claim was the seam and does not survive; S1.10 ARTIFACT robust (placebo 7/7 after
dropping the seam-straddling 2020 cycle).
Code migrated (`wave_s2`/`wave_s1`/`wave_s4` lane-explicit; `text_features` rebuilt with lane tags),
re-validation scripts in tracked `scripts/search/`, ledger rows appended (`supersedes` named), 259
tests green.
Two canon corrections filed: `confirms_in_both_halves` is unreachable from production (waves
hand-roll `split_direction`, no lane guard → un-migrated sites fail silently); the
`scratchpad/adv_partymix` evidence is untracked. next (build order 4): the ~3GB alexandria shard
lane-tag rebuild, it is the only thing blocking the other 11 re-validations
(S1.1/1.1′/1.2/1.3/1.3′/1.5/1.6/1.7/1.8/1.11/1.4-proper), which were correctly not re-run on
lane-blind substrate.
Nothing published changed (the Search never touches the daily pipeline); the §1.4.1 streak is
unaffected.

### 2026-07-17 (Session 17, Fable)

outage fixed + history rewritten + Art. xvi ratified (constitution v1.1).
The daily pipeline was down 2026-07-16 22:29Z → 07-17 ~14:00Z: the #145 fail-closed privacy gate
shipped without its `PRIVACY_SALT` secret, every run died at import in 10-20s, and it was silent,
the in-process dead-man can't see a pre-`main()` crash.
Fixed: salt set (canary-verified), preflight secret check + workflow-level `if: failure()` dead-man
in both workflows.
The §1.4.1 streak restarts with tonight's crons; earliest accurate pass Sat 07-19 (dispatch repairs
don't count).
Art. xiii git-history rewrite executed (names → redaction labels in all history, 0 occurrences
remain, HEAD tree byte-identical, all refs force-pushed).
Pre-flip residuals on the bus: GitHub server-side purge (or repo recreate) + the raw-mirror/attorney
question.
Read `verifier_passed`/`fallback` from logs, never run status (Art. xvi).

S2, live Sonnet voice, dark week (ladder: `docs/07-OPERATIONS.md` §1).
S0→S1 gates passed (cloud dry-runs green 07-12/07-13).
The S2 "live voice" criterion is now genuinely met (Session 6b), but read the history: Correction
(Session 5, 2026-07-14): it was *not* met at the time.
The adversarial review found the LLM layer (Haiku extract + Sonnet voice) is built in
`pipeline/llm.py` but never wired into the pipeline, both real-mode branches fall back to
deterministic templates.
So the daily output is the live deterministic engine + a deterministic composite voice (now accurately
labeled `generator: deterministic`, disclosed on the site as "not a language model, deterministic
template"); the previously logged `sonnet_batch` / `$0.0072/day` was a mislabel + a cost projection,
not a live Sonnet run.
Update (Session 6b, 2026-07-14): the live Sonnet voice is now live. `LLM_VOICE_ENABLED=true`, first
run validated on 2026-07-13 (both parties `sonnet_direct`, verifier-clean, $0.0056/day ≈ $0.17/mo,
budget/governor nominal, cost ledger persisting at `data/derived/cost/`, receipts live, posting
still off).
Kill-switch: delete the repo variable → instant $0 deterministic.
Extraction stays deterministic.
Also fixed Session 6b: `[skip ci]` on the daily data commits was making Vercel skip the deploy (the
workflows are schedule-only, never push-triggered), removed, so the live site now auto-updates on
every data commit as intended.
The site is public at [onscript.news](https://onscript.news) (Vercel auto-deploy on every data commit).
All 7 Actions secrets set; $10 Console cap on.
Alexandria (25-yr ledger + 327 chapters), the analysis corpus (docs 08/09/10), and the citation
back-joins are done and pushed.
- The accounts have never posted (correct, dark week).
The hold is now the `POSTING_ENABLED` repo variable (default off), the reliable primary gate built
in Session 5, failure tested: no path posts when it is off, regardless of creds.
The single-space `BSKY_*_PASSWORD` secrets are only a secondary belt (a single space is truthy → at
launch replace with real app passwords; don't rely on the space).
The Session-4 day-selection bug is fixed (post reads the assemble manifest, not `collect-latest`).
`BSKY_RED_HANDLE` should read `red.onscript.news` (stale `.bsky.social` value is harmless while
posting is off).
Profiles are live (all three §7.3 accounts, 2026-07-14): `blue.`/`red.onscript.news` composites +
the apex `@onscript.news` house account (#70 done, handle verified, neutral house avatar/banner in
`site/brand/avatar-brand.png`/`banner-brand.png`); the composites follow only each other, the house
account is the parent for v2 awards / postmortems / the nightly symmetry audit.
All still silent (dark; posting wires to the house account in v2).
- Operating contract (2026-07-14): Michael reports completions in-session; anything he has not
  explicitly reported is not done.
Every session ends by updating this section; the Vikunja `onscript` project is the live human-task
ledger.
- Parallel-session protocol (2026-07-15, Fable ruling): multiple concurrent sessions are sanctioned
  (Search / articles / Deep Archive / launch) with one working tree = one writer, content/article
  forks work in their own git worktree or branch; build sessions keep the main tree; never `git add
  -A` blindly (another fork may have in-flight edits, stage only your own files); pull-rebase before
  every push.
Shared canon files (13-search-ledger, buildlog, this section) are append choke-points: only the
session that ran a measurement writes its ledger row.
Articles draw only from CONFIRMED cards + methods/graveyard material, reversal candidates need
re-pre-registration first, and no pre-2013 claims until the CREC lane passes SD.8 calibration
(docs/15).
Session-yield order when slots conflict: streak > launch > Search > articles-support > Deep Archive.
- Storage (machine-specific): raw corpus + engine state on X:\onscript-data\ via junctions;
  `derived|reference` in-repo.
- Worktrees (consolidated 2026-07-17, Session 17). one tree. `polispeak` = main, the only checkout.
  `polispeak-v2` and `polispeak-nom` are removed (v2's scratch evidence archived to
  `X:\onscript-data\evidence\polispeak-v2-scratch\`; the nomenclature work lives on branch
  `wip/nomenclature`, pushed, re-create a worktree for it only when its wiring session starts).
Merged remote branch `claude/friendly-bardeen-a6aa2d` deleted.  all commit SHAs changed twice.
2026-07-17 and again 2026-07-21.
The first `git filter-repo` rewrite (Art. xiii, Session 17) replaced two names with redaction labels
across all 164 commits.
The second (Session 38, 2026-07-21) is the exhaustive scrub S35 ordered: it rewrote 245 of 255
commits; HEAD tree byte-identical both times.
Every SHA cited in canon before 2026-07-21 is a pre-rewrite label.
Re-mapped anchors: `fdcda1f`→`c44579c`→`e54c90d`, `d816066`→`457f90e`→`be83b05`,
`ca3ca2c`→`1ff7668`, `6b1c8ce`→`af2ee4b`, `d7c93ac`→`b1ffcf6`, `d2d3a34`→`0222f2f`,
`a111469`→`1eeec8c`, `c63fd24`→`18d533f`.
Any stale clone must re-clone, never pull, pulling pre-rewrite local history onto the rewritten
remote re-imports the contamination.  the local `wip/nomenclature` branch (`fb6ac6a`) Still carries
the pre-rewrite contamination (16 carrier blobs, 178 commits never pushed; origin's
`wip/nomenclature` is clean at `920067d`).
It is local-only so nothing is exposed, but it must never be pushed as-is, its S21 work is already
merged into main (`pipeline/nomenclature.py` + `boilerplate.scaffold_reason` verified present), so
the disposition (delete vs rewrite-in-place) is Michael's call, deliberately not self-authorized.
Stage only your own files; pull-rebase before every push.
- Repo PUBLIC as of 2026-07-22 (Constitution xiv satisfied; flipped by Michael after the exhaustive
  Art. xiii history scrub (S38) + r-l redacted-view release assets verified zero (S40), the S3
  launch acts are complete).
-  the provenance seam, Main finding of 2026-07-16, and it invalidates the program's primary control
  (docs/13, Session 13b). `dwillis/congress-press` is a union OF three datasets keyed by the
  record-level `date_source` field: the `legacy` lane (a ProPublica import) runs 2001 → 2021-01-03
  and stops forever (the day the 117th was seated); the `scraper` lane starts ~2018 at 49 offices
  and accretes.
The "2021 coverage collapse" is not behavior, it is the union losing a dataset.
Both adversarial skeptics CONFIRMED (0/2 refuted; one re-derived every number straight from the 303
mirror files, bypassing the harness). split-halves has been comparing ProPublica to a scraper, not
two eras, half A ~95% legacy, half B ~100% scraper, across a 2.6× coverage change and a ~24-point
D:R lane effect with era HELD constant (2013-2020: legacy 1.176 vs scraper 0.937), and the corpus
has three lanes, not two: `page_html` (2,839 records) runs D:R 12.465 in half A, the most
party-skewed lane in the corpus, which a two-valued enum would silently mis-bucket. *(Corrected
2026-07-16, the original `1.538 vs 1.12 / 7.7-point` figure was taken from an agent's output without
reproduction and compared legacy-in-A against scraper-in-B, confounding era with lane: the very
confound the finding is about.
The conclusion stands and was understated.
See docs/13 correction.
Build L1 against the field's real 3-value domain.)*.
Every both-halves PASS survived a weaker test than advertised; every FAIL may be plumbing. including
S2.3, the reversal the ledger sells as proof the control works. all 34 verdicts need revisiting
(S2.3 first, then the only two CONFIRMED, S1.9/S2.9).
S4.7 (Jan 6) is a sign inversion: raw −69.9% = "muted congressional response to January 6"
(maximally quotable, publishable, FALSE) vs lane-isolated +75.5%; the drop is the import ending 3
days earlier.
Only the review gate stopped it.
Remedy = isolation, not normalization: `date_source` must become first-class (`harness.py:399-427`
drops it), enforced like the deep archive's genre-isolation law.
Measure nothing new until it lands.
- the search: waves S3 + S4 are zeros.
15 hypotheses, 0 findings, and the cause is planning, not the system.
9 of 15 blocked before measurement on reference tables docs/12 assumed into existence
(`elections.json` = 7 bare dates, killing S3.2/S3.7/S4.5, one table, four hypotheses;
`crisis-events.json` never existed; no retirement-date table; no historical committee membership).
34 tested / 2 CONFIRMED = 5.9%; the §0 projection of 22–28 CONFIRMED is arithmetically dead (needs
20 of the remaining 14), accurate ceiling 4–6, and the unit was the error: 8 real cards on disk (not
the "45+" an earlier note claimed, that counted candidates, and S4.1 lost its entire 20-ruling
phrase arm to a ~97% nomenclature audit).
Filed #154 for the Fable re-baseline (Opus must not rewrite a Fable phase doc).
The best artifact of both waves is a refutation: S4.4 killed the Friday Night Dump (0.85×/0.96× vs a
≥1.5× gate over 674,970 statements, positive control firing at 2.10×).
New protocol law from S4.2's 3/3 kill: the placebo must run against the exact statistic in the
headline.
But the substrate audit is good news: of 18 remaining, 8 runnable now, and two were FALSE blocks.
S1.12's leadership roster is on disk (mirrored 07-16, one day after S1 ran and found it null) and
S5's "the key never comes local" premise is obsolete (GovInfo billstatus 113-119 keyless + already
local, 332MB).
- running: the CREC 2009-2026 Extensions crawl (detached, keyless GovInfo, $0, zero Anthropic
  usage).
2013-2026 first, the calibration law makes that overlap the gate for SD.1-SD.6.
Pace ~4h.
Log `X:\onscript-data\crec\state\crawl-2009-2026.log`; `CRAWL-RUNNING.lock` names the owner.
`crec.py:217` overwrites `crawl-stats.json` with only the current run, the driver snapshots the
2001-2008 record first and merges at the end; crec.py itself untouched (other lane's file).
This crawl is also the seam's fix: CREC is the only symmetric record spanning 2021-01-03.
- The speaker-attribution gate is now live on the citation path (Session 14, Opus), verified no-op,
  nothing published changed, 228 tests green.
Session 13's "verbatim != attributable" find is closed for `run_assemble._citations`: a press
release is a multi-speaker document, so `verify.is_verbatim` passing does not mean the cited member
said it.
Audit reproduced: 103/103 live quotes clean; the whole `groundable` set 142/142 clean (statement ids
recomputed from upstream, so uncited statements join too), latent, never a live defect.
The Session-13 blocker was wrong and that unblocked it: `verify_talking_point` fixes the >=3-unit
quorum from `tp["statements"]` before `_citations` runs, so the gate cannot move a published number
because of the design; `quote=None` was already a live render state.
Hence demote the quote, never the citation, receipts never thin.
The hazard is real: 27.4% of releases carry a colleague's block (21.8% of all sentences),
near-symmetric D 27.6%/R 26.9%.
The gate over-flags (`continued Republican attacks` parses as "Republican" said, condemning a whole
release) and that bias was kept deliberately, demote-only fails safe, so an over-flag costs a
pull-quote while an under-flag publishes a colleague's words under this member's name; noise is
~1–4% and symmetric (D 4.22%/R 4.12%).
The obvious fix was measured and rejected as an Art.
IV trap: requiring a closing quote before a marker fails because scrapers drop quote marks
per-office (Davis's quote keeps its quote mark in `dondavis.house.gov`, loses it in
`fedorchak`/`fischbach`, where he is the colleague), so sensitivity would vary by whose
scraper ran, the same trap docs/16 rejected capitalization for.
Failure test is mutation-checked on real cross-party text (Fedorchak (R) republished Davis's (D)
quote). `distill.py`'s `groundable` is measured-clean but deliberately not wired, it feeds the live
Sonnet voice, so an over-flag changes published prose; its own session.
- v2 dark shelf.
4 of 10 features `built/verified/UNRELEASED`, 228 tests green, no public surface changed.
Every flag still False; the flip is Michael's act.
From Session 12 (Opus): 1.1 The Archive (era+month chapters, fingerprints, verifier-gated: 340 clean
/ 13 correctly excluded) · 1.2 Silence Detector + "Shouting Into the Void" (GDELT doc 2.0 keyless
baseline whose queries are built from the same taxonomy_v1 seeds as our corpus match, so a silence
claim is third-party reproducible; a gap is not a silence, a failed pull returns None → topic
excluded, verified live on a real 429; thin/one-party days score nothing; both directions ship on
one page or not at all) · 1.8 The Owner's Brief (five health numbers to ntfy Mondays, wired into run
B's both paths incl. the no-op return, skip-and-log).
From Session 13 (a parallel Opus session, commits b9bd3c5/8ed87a5/32e99b8): 1.7 The Duet + phrase
search (`pipeline/duet.py`, prebuilt client-side index; its review found "verbatim != attributable"
and moved the §5.1 lane-1-only guard *inside* `find_duets` rather than trusting its caller).
Remaining v2: 1.3/1.5 blocked on #143; 1.4 + 1.10 (The Script / memo-cadence) open; 1.6 floor.
CREC ingest already built in D1, needs render + coverage metric + Lane-2 machine-block tests; 1.9
gated on `DATA_GOV_API_KEY` via Actions dispatch.
- Two live findings from Session 12 that nobody was auditing for, both verified, both filed: (a)
  #145 URGENT/Art. xiii: apparent private-citizen names render as top synchronized phrases on the
  live site (`<private-individual-A>` 10 D, `<private-individual-B>` 8 D, and `the killing of
  <private-individual-A>` 3 D, i.e. victims in cases members are campaigning about).
The privacy floor is effectively unamendable and says "never private citizens… regardless of how
interesting".
The receipts hand-audit could not have caught this, the citations are all valid. docs/16 explicitly
does not fix person names.
(b) #146 Art.
IV: `collapse_and_rank` pools both parties, ranks by raw `day_peak`, truncates at 20, so the larger
caucus structurally fills the table: 118 D / 16 R = 88.1% D, and 100% D on two days.
The judges rate this as dwarfing the nomenclature contamination.
Any fix puts the denominator in the view, never the threshold (buildlog:608-614 already ruled
per-party threshold normalization an Art.
IV violation).
  *(The two names are redacted here and everywhere in this repo: the repo goes public at S3 and
Article xiii is unamendable, so the canon must describe the defect without being it.
The live gate matches them via salted hashes, see `pipeline/privacy.py`.)*
- #143.
1.3/1.5 are BLOCKED on a Fable/Michael ruling, correctly.
A fan-out reproduced the 10-findings numbers (Roy 31, Cruz 30, Thune 18, 37.8%
born-coordinated) and then asked what the phrases *are*: Roy's "31 solo-launched" is 10 distinct
ideas, 4 of them windows of the save Act's title.
The feature would have published "Chip Roy authored the save Act", he was first in our press corpus
to type the name of a bill he sponsored.
Also measured: `peak_units>=15` is not a knob but the confound control (at peak≥2 the top 12 authors
are 12/12 Democrats and all 12 senators, the naive headline is "Authors are Democrats, Vessels are
Republicans", a pure chamber artifact), yet it lives only as an incidental default at
`search/harness.py:129`; 59% of members (318/538) have solo==0, so 1.5's Ventriloquism Award has 318
tied winners at zero; the #1 author flips Roy→Cruz between floor 15 and 20.

Fable rulings 2026-07-16 (Session 13c, all Michael-confirmed, implementing sessions execute, never
re-litigate): R1 docs/12 A3+L1-L4 (cards not CONFIRMEDs; lane isolation binding; 34 pre-seam
verdicts pending within-lane re-validation, S2.3 then S1.9/S2.9); R2 #143 author-construct dead ->
origination pages (span-gated), author leaderboard dropped, Ventriloquism Award killed -> The Unison
+ The Void; R3 #146 per-party side-by-side columns with N-of-caucus on every row, SYNC_MIN
untouched; R4 The Script = the concordance (denominators on every line, no predictive claim,
span-gated); R5 #145 immediate manual suppression at display + corrections-log disclosure,
principled gate as its own reviewed item.
Next opus session's first act; R6 no raw-volume comparative ever crosses the 2021-01-03 provenance
seam (Jan 6 sign inversion is the standing proof); #119 Haiku extraction retired permanently (§13
closed); launch-flip evidence = `ops.unattended_streak()` passes:True, never run status.
Build order:

1. #145 suppression deploy. done (`c44579c`, pre-rewrite `fdcda1f`).
2.
L1 lane isolation. done (Session 16, `pipeline/search/provenance.py`; 255 tests green; verified on
all 688,820 lane-tagged records).
3. the 34 re-validations. the runnable half done (Session 18, docs/13 "re-validation. within-lane";
   259 tests): the seam overturned zero runnable verdicts.
Both CONFIRMEDs survive.
S2.9 now twice-confirmed (per-lane on each lane's own split), S1.9 re-affirmed (the 144 legacy
2021-01-03 records are a measured no-op).
S2.3's kill was not plumbing (REFUTED both lanes, well-powered).
S1.4/S1.10/full-S2-wave re-run within lanes; only S2.7 moved (propublica-only confirm → reversal
candidate, not a card).
The blocked-on-shards half (S1.1/1.1′/1.2/1.3/1.3′/1.5/1.6/1.7/1.8/1.11/1.4-proper) is not re-run,
it needs step (4).
4. shard-lanes brief (docs/18). done (Session 19): the eleven blocked-on-shards items re-validated
   within lane; per-lane shards built (all 7 congresses reconcile precisely, 0 statement delta, 0
   cross-lane dups). two new CONFIRMED.
S1.1′/S1.3′ (the "Great Intensification": ignition width 34d→3d/11.3×, lifespan −37%) CONFIRM within
the propublica lane (2013-2020, density-survives) and are ARTIFACT/absent in scraped.
REFUTED across the seam only because the post-2021 plateau broke the monotone gate; lane isolation
made them confirmable.
Zero false-positive flips across all 22 (11×2).
Program CONFIRMED 2→4 pending Fable/neutrality review (REFUTED→CONFIRMED movements on docs/18-§5
pre-registered halves; density-caveat = count-matched not statement-density-matched, disclose on any
card).
5. next: nomenclature wiring, brief authored, `docs/19-NOMENCLATURE-WIRING-BRIEF.md` (Fable 07-18,
   binding).
Start the Opus session with "read claude.md and run the nomenclature wiring brief." Scope: rebase
`wip/nomenclature` onto main; wire tag() at three points (nomenclature_rate audit metric live
immediately; site display-time + daily pre-distill behind a default-off `nomenclature_tags` FEATURES
flag, the flip is Michael's); the §4 robustness rider re-runs S1.9/S1.1′/S1.3′ on tag-stripped
substrate and gates the Aug/Sep drip pieces; adversarial review; merge dark. → then rulings-shaped
1.3/1.4/1.5 (span-gated, behind the merge).
  - Two Session-18 findings against canon (docs/13/17): (a) `metrics.confirms_in_both_halves`, the
    L1 CONFIRM gate, is unreachable from production; every wave hand-rolls both-halves via
    `M.split_direction` (no lane guard), so an un-migrated wave site fails silently, not loudly.
The S2 + runnable-S1 sites are now migrated to `load_rows(lane)`/explicit halves; blocked-on-shards
sites are still un-migrated.
(b) The `scratchpad/adv_partymix_pass1-5.py` evidence cited above is untracked (scratchpad is
gitignored → gone on re-clone); Session 18's re-validation scripts live in tracked
`scripts/search/`.

 Four amendments to the seam bullet above, from the L1 build (Session 16, buildlog; evidence
`scratchpad/adv_partymix_pass1-5.py`, re-runnable).
The 13b session's correction landed independently and its three-lane / 1.176-vs-0.937 substance is
right, these are the residue:
1.
"~24-point D:R lane effect" is a unit error, it is +5.67 points. `1.176 − 0.937 = 0.239` is a
difference of *ratios*; canon's original "7.7-point" was a difference of D-share, and on that same
scale the same-era (2013-2020) lane gap is +5.67pt (legacy 54.05% D vs scraper 48.38% D).
Robust: +5.32pt office-matched (144 shared offices), +8.28pt year-standardized, +4.71pt with
`page_html` folded. *(My error, introduced in the L1 session's first report and propagated here, a
ratio gap quoted as percentage points.
State the estimator with the number: docs/12 L4.)*
2.
"the `scraper` lane starts ~2018 at 49 offices" is loose.
It starts 2009-01-06 and is merely tiny until ~2017.
A lane filter trusting "~2018" silently admits 727 pre-2013 scraper records that are ~100%
Republican (2009: D 0 / R 174).
The mirror image: a `legacy` filter does not buy 2001-2021 coverage.
99.67% of that lane is 2013-2020, and its pre-2013 tail is 1,594 records at 99.9% Democrat (D 1,592
/ R 2).
3. `date_source` dies in three places, not one. `harness.py:399-427` is fixed (Session 16).
Still open: `alexandria.load_congress_records` (`pipeline/alexandria.py:30-44`) → every
`ledger-N`/`discipline-N`/`coverage-N` shard is lane-blind, so every S1 phrase hypothesis reads
lane-blind substrate (fixing it needs a ~3GB shard rebuild, its own session); and `wave_s4._collect`
(`wave_s4.py:53-96`), a direct mirror read.
4. open ruling, fold vs isolate `page_html` (an implementer must not self-authorize it).
Folding it into `scraped`, the build's default, because it is the same *instrument*: `page_html` is
scraper-collected and merely date-parsed from the page body, moves the same-era gap +5.67pt →
+4.71pt.
Isolating it as a third lane makes the post-2021 corpus permanently "mixed"; filtering
`date_source=='scraper'` silently drops it.
The code supports both (`provenance.lane_of(by="instrument"|"source")`), so the ruling picks which
number publishes, not the architecture.
Fable/Michael to rule before any lane number is published.

Next gates (in order):

1.
S2 dark week (Michael, #62/#63): hand-audit 5 receipts/day across the live runs + the attorney hour;
first Monday 15-min ritual 2026-07-20.
2.
Sonnet voice live (#81, turned on 2026-07-14): `LLM_VOICE_ENABLED=true`; first run green
($0.0056/day).
Validating over the dark week, watch cost (~$0.006/day) + verifier pass + prose across a few runs;
the $9 code ceiling + $10 Console cap bound it.
Kill-switch = delete the repo variable → $0.
3.
Opus (standing): Wave-0 hardening is done (Session 5, posting day-fix, `POSTING_ENABLED` gate
failure tested, FEATURES registry, receipts, accurate banner + HIGH-1/2/3 + xss + idempotency fixes,
bot self-label, promoted analysis generators, About page; 55 tests green).
The Session-7 pre-launch punch list is done (2026-07-14, commit 54aa81a, copy fixes, P2/P3 v1.1
prompts, cluster-label gate + quote→cite binding, wiring polish; adversarially reviewed, 6 defects
fixed, deployed + verified live on 07-13; 75 tests green).
The bones are launch-strong.
Unattended cron greens. corrected 2026-07-16 (Session 13, measured from the run logs, not the run
status): the §1.4.1 streak is 0/3, not 3/3.
The 07-16 cron did not complete the gate, it broke it. #1 (07-14 run → day 07-13) and #2 (07-15 run
→ day 07-14) were genuinely clean (`verifier_passed=True fallback=False` both parties).
The 07-16 12:59Z run (→ day 07-15) published the apology stub for both parties
(`verifier_passed=False fallback=True`; "Some of our output could not be verified today"), it ran on
the pre-fix code, ~2h before the typography + P2 v1.2 fixes landed at 14:53Z.
The published day was then repaired by dispatch (day 07-15 is now `verifier_passed=True
fallback=False`, degraded=False), so the site is correct but the unattended streak reset to zero.
§1.4.1 is *"three consecutive unattended real runs (≥1 weekend day)"*, the first post-fix unattended
run is 07-17, so the earliest accurate pass is 07-19 (Sun), which conveniently satisfies the
weekend-day clause and lands before the 07-20 Monday ritual.
Lesson: an Actions `success` is not a green, every one of these runs exited 0 while publishing the
fallback.
Read `verifier_passed`/`fallback` from the log or `degraded` from the manifest; never count run
status.
The Session-8 critique adjudication (buildlog) reordered the queue.
Next, in order: (a) unattended greens #2/#3 (07-16, 07-17 crons); (b) the Session-8 pre-posting set
is done (Session 8b, commit f00e27a, atomicity, signed archive /posts.html, golden regression,
said→carried, denominators, inscriptions, speaker-sample; adversarially reviewed, 4 defects fixed,
site regenerated + deployed; 82 tests).
Both posting-launch blockers are now closed (Session 8c, commit 3d6bd60, 88 tests, posting still
off): partial-post duplication → root_uri persisted before replies + deterministic root rkey with
server-side collision recovery; auth-real atomic pre-flight → `createSession` per due party before
any post (bad password holds both).
A third silent-neutrality bug the review caught is also fixed (empty composite for one party →
atomic hold, not a near-empty one-sided post).
Residual pre-flip items: (A) live at-Proto smoke test. done (Session 8d, task #108 closed).
Michael supplied a throwaway account; `scratchpad/smoke_post.py` ran the live primitives live and
caught a launch-blocking bug: `app.bsky.feed.post` rejects a non-TID rkey, so the Session-8c
`onscript-<day>-<party>` rkey would have 400'd on the first real post.
Fixed (commit 9e387f7): `_root_rkey` now emits a valid deterministic TID (verified live,
past+present dates); recovery is probe-existence based (collision is 400-or-500 by pds).
13/13 live checks + 89 unit.
(B) asymmetric-post reconciliation for a hard-kill between the two posts. done (Session 8e, commit
be86eba): `_reconcile_prior()` scans all post manifests at the start of each run and fires the
dead-man once per unacknowledged asymmetric/partial prior day (alert-only, gated on POSTING_ENABLED,
corrupt-manifest-safe); adversarial review confirmed 6 invariants + 3 fixes.
94 tests.
The Opus pre-flip queue is now empty, nothing on the build side blocks the launch flip.
(d) nomenclature segregation, now the top of the build queue, and the common prerequisite for 1.3,
1.5, every "coordination" headline claim, and the CREC lane (docs/15 D1-A). spec:
`docs/16-NOMENCLATURE-SPEC.md` (Session 12, a 10-agent design fan-out; every critical claim verified
against the live 75,989-statement corpus). tagger built + green, not wired, not reviewed, not
merged, it lives on branch `wip/nomenclature` (worktree `../polispeak-nom`), 21/21 fixture + 233
suite.
Winner span: tag by official-name span containment against govinfo billstatus (keyless, 347MB
one-time, congresses 113–119) + a committee lane from congress-legislators; tag, never delete; every
tag cites a party-blind official record.
The insight that kills every obvious design: nomenclature is a property of the occurrence, not the
phrase. `the save act` is nomenclature in "reintroduced the save Act" and messaging in "the save Act
would gut Medicaid", so no dictionary/blacklist can separate them.
Capitalization was rejected as an Article IV violation: R press shops shout 54% more, so its
shouting-skip rule silently under-tags one party for stylebook reasons (an asymmetric *instrument*;
asymmetric *findings* stay always-allowed), and it tags the D counter-brand "the big ugly bill" at
0.908 while span protects it at 0.000.
Measured both directions: kills "21st century road to housing act"/"the one big beautiful bill
act"/appropriations titles (1.000); protects "the big ugly bill", "the save act would", "child tax
credit" (0.003 vs cap's 0.683 false positive), "cuts to medicaid", "birthright citizenship".
Ship display-time first (fixes every historical page, no 3GB ledger rebuild); must tag before the
LLM or the Sonnet voice launders nomenclature into fluent prose *and the verifier passes it* (the
members really did type it).
Per-member ingest-health flags in the nightly audit ride along.
Spec §9 carries 5 rulings an implementer must not self-authorize (#145 privacy, aca, #146 skew,
quiet-day floor, launch bar). state (Session 15, branch `wip/nomenclature`, not on main): reference
data done, govinfo billstatus congresses 113–119 (keyless, ~347MB raw mirrored to X:) + committee
lane from congress-legislators + `verdicts-119.json`; the corpus pass lands on the spec's
predictions (sync 461,501, exact; covered 14,175 vs 14,178 predicted).
Measured KILL/PROTECT both directions, incl. `the big ugly bill` protected at 0.000 and `national
security department` 0.946 via the committee lane.
Two traps a next session must not re-hit:

1. `build_verdicts` is a two-pass scan over 75,757 statements × 552 days, tens of minutes.
Run it backgrounded; an `exit 127` after one line of output is a tool timeout, not an oom (an
earlier session misread it as a crash and "diagnosed" innocent code).
2. `len(short_title) <= 20` is a FALSE premise.
Congress writes 30-token backronyms (`advancing critical connectivity expands service...` IS the
access broadband Act) and hres1225 registers a 22-token sentence under titleTypeCode 101 "Short
Title(s) as Introduced".
The code allowlist is the gate; length is not. remains: wire `tag()` at display time (before
distill, else the Sonnet voice launders nomenclature into fluent prose and the verifier passes it,
since the members really did type it), surface `nomenclature_rate` per party in the nightly audit,
adversarial review, then merge.
(e) citations backfill for historical days; (f) Archive/1.1 streaming ledger reader (may be
satisfied by the Search's S0 shard harness); (g) the search (`docs/12-SEARCH-PROGRAM.md`, Fable
Session 9), the standing Opus content program: 47 pre-registered hypotheses over the 25-year
archive, 5 waves, verdicts to `docs/13-SEARCH-LEDGER.md`; next session starts Wave S0 (inventory +
harness + failure-test metrics + reference tables).
Goal: ~22–28 CONFIRMED finding cards = 1–2 drip pieces/month for 1–2 years; (h) the deep archive
(`docs/15-DEEP-ARCHIVE-PROGRAM.md`, Fable Session 10), the historical expansion `docs/14` proved
feasible, as a parallel-safe program: the symmetric `source=crec` Congressional Record track
2001–2026 (Extensions-first), the LoC extraction probe (D2, a gate not a commitment),
DCinbox/academic cross-check lanes, all behind the 7-gate coverage audit + two binding laws (genre
isolation in code; the calibration law, no crec-only pre-2013 claim without 2013–2026 overlap
concordance, SD.8).
Waves D0–D4; zero Actions, zero daily-pipeline code paths, X:-only storage, last place in the
session-yield order (streak > launch > Search > Deep Archive); deep-annex hypotheses (SD.1–SD.7)
pre-registered there, verdicts to the same 13-search-ledger lane-tagged.
accurate sizing (15 §8): second-biggest lever for what OnScript *becomes* (true 25-year instrument,
twice-confirmed tier, H6/academic ambitions), near-irrelevant to this quarter's launch, sequenced
accordingly.
Wave D0 (the rails) is complete (Session 11, Opus): `pipeline/deep/` lane plumbing + the 7-gate
coverage audit (tested with failure fixtures; adversarial review caught + fixed 1 blocker. `audit_cross_era`
now enforces same-lane genre isolation. + 3 should-fixes) + CREC reference tables + the
hash-manifested mirror (Grimmer mirrored to X:); 126 tests green.
Acceptance refined the value prop: the accurate single-party gap is 2001–2008 (2009+ already
symmetric), so crec's unique fill is 2001–2008.
D1.a/b built + verified (Session 11 cont.): `pipeline/deep/crec.py` (sitemap enumerator · mods
structured-attribution parser · furniture stripper · deep-schema normalizer · resumable polite
crawler), locked by `tests/test_deep_crec.py` (130 tests green).
Proven on crec-2001-01-03: 41 Extensions, 97% attributed, day audit D=10/R=14 members, ratio 0.71,
PASS, symmetric where the press lane is 100% D.
D1.c/d verified on congress 107 (2001–2002): 11,867 symmetric Extensions statements →
schema-identical ledger shard (Search-reader-queryable) + per-year audit PASS (2001 D=211/R=208
ratio 0.99; 2002 D=209/R=211 ratio 0.99), two-party where the press lane is 100% D.
The D1.d audit caught + fixed a real date bug (`published_at` was the package id).
Weak-carrier confirmed (docs/15 §9 amendment D1-A): crec top phrases are procedural/bill-title
formulas, so CREC needs a heavy genre-boilerplate layer before phrase-coordination findings, the
procedural half is now built (`pipeline/deep/crec_boilerplate.py` + failure fixture, 138 tests;
validated on 107, all Committee-of-the-Whole furniture removed, sotu protected); the residuals
before a coordination card are inserted-bill-text/full-bill-title (= the separate
nomenclature-segregation item, needs the congress.gov corpus) + sub-gram collapse (existing layer).
crec's near-term strength is speaker-attribution analysis (SD.2 Voldemort/SD.6
tributes/floor-vs-press), boilerplate-robust.
2003–2008 crawling (background); 108–112 shards next; then 2009–2026 for SD.8 calibration.
(i) the `docs/11-BUILD-PROGRAM.md` queue.
Standing recommendation awaiting Michael's nod: retire Haiku extraction permanently (model-free
measurement path; §13 knob, buildlog Session 8).
Releases are never a build-session side effect.
4.
S2→S3 launch (deliberate, gameplan §9): real passwords + flip `POSTING_ENABLED` + repo public +
announce.
5.
The Build Program (`docs/11-BUILD-PROGRAM.md`), build-dark/release-by-gate: Opus builds the full
v2+v3 backlog to `built/verified/UNRELEASED` behind the FEATURES registry while the streak runs;
each release is one commit, Michael's act. v2 target Aug 10, v3 Oct 5.

## 2026-07-23: Session 45 (Fable). Release and rollout order

Outcome: docs/27-RELEASE-AND-ROLLOUT-ORDER.md (binding) now governs the path from the
local 17-commit stack to a verified deployed release and the calendar through the freeze.

Evidence: baseline re-verified by direct inspection before ruling. Suite 479 of 479 at
local HEAD. Live remote moved past the local cache (f8b77e4 to 6871440), so a rebase
precedes any push. Live site confirmed still pre-stabilization: About denies posting
while posts.html lists two days of posts; a phrase page still shows a 2013 date and a
bare bioguide identifier. Voice rewrite verified compliant except one plain-prose U+2014
in the docs/06 Article XIV title line and the missing exception list required by
docs/25 section 5 gate 2.

Decisions: release sequence R0 to R8 (R0 voice fix and exception list, R1 rebase, R2
stabilization push, R3 production exercise with live-surface checks, R4 wave 2 push,
R5 voice push after #197, R6 two green days, R7 nomenclature flip, R8 rollout).
Freeze ruling: the constitution governs, Oct 15 through Nov 10; the docs/23 Oct 12 row
survives as a quiet-period buffer; last flip Monday is Oct 5. Slip rule: a missed flip
moves one week and never stacks; the Aug 31 lock and freeze dates do not move.
Feature classifications and per-piece editorial gates are in docs/27 sections 5 and 6.
The HX.4 card stays unpublished while HX.4-D is HELD. Task #198 filed for the
silence-board wiring session (deadline Aug 3). The implementation agent's scope is R0
and R1 only; every push, flip, and publication stays with Michael.

Next action: implementation agent runs R0 and R1; Michael pushes the stabilization
prefix in a clean window (#195), then follows docs/27.

## 2026-07-24: Session 45 continued (Fable). The stack is deployed

Outcome: the entire local stack is pushed and the first production day exercised green.

Evidence: R2 (stabilization prefix, 3d9cadd) pushed 2026-07-23 ~17:40Z after independent
validation (479/0). The 20:34Z collect ran green in 61.5 minutes with the phrase-evidence
bootstrap inside budget and below-quorum omissions logged. The 22:3xZ assemble ran the
ruled step order including the same-run post-archive refresh. Live surface verified:
stale posting copy gone, account and repository links live, no pre-epoch dates or bare
bioguide identifiers, peak-day evidence rendering, search index clean of pre-epoch rows.
The claim-binding P0 (docs/28) was implemented (372a06e), adversarially reviewed, and
corrected for a label-unaware quote truncation that could break the streak (4cb2f1a);
suites 490/0 then 492/0 reproduced independently. After a clean rebase over the night's
two data commits, wave 2, the voice rewrite, both release orders, and the claim-binding
fix pushed as 10de6ad..377b638 at 01:30Z.

Decisions: pushing the P0 fix required pushing the validated wave-2 and voice segments
beneath it; ruled acceptable because each segment carried its own completed validation
and the alternative left uneditable wrong claims posting daily. Michael delegated the
push acts for this arc; flips and publications remain his.

Next action: the ~11:30Z posting assemble proves the same-run archive and composes the
first bound claims. On green: acceptance table complete, #195 closes, the Monday
nomenclature gate is live again.

## 2026-07-24: Session 45 close (Fable). Acceptance complete

The 12:5xZ posting assemble proved the release. Commit 31d719c contains the day's post
manifest (both parties posted, real root URIs, no partials) and the posts.html listing
that same thread: the signed archive is now truthful in the same run. The new day page
publishes five verified claims with zero sub-full phrase chips: every quote appears in
every one of its receipts. The 2026-07-22 page renders its historical correction note.
feed.xml and sitemap.xml are live. Collect steady state is under the pre-release
baseline. The docs/27 section 3 acceptance table is complete; #195 and #197 are closed.
Remaining operator acts: the Monday nomenclature gate decision, #198 before Aug 3, and
the standing #105/#110.

## 2026-07-25: Session 46 (Opus). The first startup_failure, and the dead-man that could not fire

Outcome: day 2026-07-24 did not publish and no alert was sent. RUN B's 11:30Z pass was
dispatched 61 minutes late and concluded `startup_failure` at 12:33:55Z with zero jobs
created, so the `if: failure()` dead-man step inside the job never existed. First
startup_failure in the repository's run history. Michael found it by asking.

Evidence: run 30158114594 has an empty jobs list. RUN A had succeeded that morning,
committing 285301c at 11:53:49Z with `focus_day` 2026-07-24, `volume.today` 158 against a
trailing median of 174.5, and `degraded: false`. `assemble-latest.json` still read
2026-07-23, `POSTING_ENABLED` was true, and no `post-2026-07-24.json` exists. `assemble.yml`
is unchanged since b297c06 and had run green twice the day before, so the workflow file was
not at fault.

Decision: build the outermost liveness probe Article XVI already requires, as a separate
workflow rather than a step inside the pipelines. A probe sharing a process with the thing it
watches cannot report that process failing to start. `pipeline/watchdog.py` and
`.github/workflows/watchdog.yml` check run history and the committed manifests twice a day at
13:00Z and 23:00Z, in their own concurrency group, read-only and $0. Suite 492/0 before,
511/0 after, 19 new tests, no existing test changed. Replayed against real recorded state it
pages on the incident tick and stays silent on the healthy tick before it. Detection latency
goes from unbounded to at most about 13 hours.

Residual risk, not covered: a probe inside Actions cannot see Actions failing to schedule the
probe. An external heartbeat closes it, needs an external account and a new secret, and is
filed for Michael.

Next action: the 21:30Z pass should recover 2026-07-24 on its own through the readiness gate,
which takes the oldest not-yet-final day, so the series keeps no hole. If it does not, P12 in
docs/07 covers the manual dispatch. The watchdog is committed locally and unpushed; it
releases under Michael's order like everything else.

## 2026-07-25: Session 47 (Fable). External review adjudicated; docs/29 is the binding work order

Michael supplied a 60-item external strategic review and asked for adjudication and a
Codex work order covering the actionable phases. The review's premises were verified
first: its four central failure claims match recorded incidents (docs/28 claim binding,
the restore rollback, the two privacy escapes, the pre-guard day mutations), which earned
it a full ruling rather than a dismissal.

Dispositions: the integrity core is accepted (occurrence and claim contract, publication
immutability, span privacy, adversarial fixtures, classification layer, document
families, surge statistics, status and static exports, gold-set harness, hardening),
organized as work packages W1 through W11. Rejected for this cycle: demoting the
composite voice and restructuring the party accounts (product identity, post-election
agenda). Deferred: public redaction records (dossier risk, attorney), family pages,
provenance graph, homepage redesign, dynamic API. Amended: concordance and discipline
flips now additionally gate on published W10 metrics; no other docs/27 date moves. The
unverified trademark claim joins the #105 attorney agenda and precedes the October
registration wave.

Reading of scope: review Phase 1 in full plus the machine-buildable part of Phase 2.
Annotation itself is human work; Codex delivers instrumentation. Phases 3 and 4 wait for
validated measurement and the other side of the freeze.

Next action: Michael reviews docs/29, then hands the Codex prompt to the worker. Release
of every package stays under docs/27 discipline. Operator acts are listed in docs/29
section 6.

## 2026-07-25: Session 48 (Fable). Codex W1-W11 delivery validated clean

The codex/w-packages branch delivers all eleven docs/29 packages: eleven ordered
commits plus the delivery packet, rooted at f99a507, main untouched, branch never
pushed. Validation was independent per Article XVI: evidence was rerun, not read.

Reproduced directly: the suite at 572/0 from 511/0 baseline; the W5 mutation harness
reporting 15 of 15 verifier checks load-bearing; W8 ranking determinism byte-identical;
the W11 clean-clone subset byte-identical across two runs; live prompts_sha equal to
the published symmetry audit, proving the W6 prompt candidates (P2 v1.4, P3 v1.2) are
dark. Checked structurally: no site/public or data/derived changes anywhere in the
branch; corrections.json gained schema fields and lost zero lines; config gained only
the provisional document-family knobs; zero added lines carry U+2014.

Four pre-existing tests were modified. All four were examined and all four follow
behavior the work order changed: three encoded the superseded assumption that
nomenclature stays message-eligible (W6 replaces it; the wave0 fixture phrase was
itself a bill title), and test_public_archive.py now asserts the stricter RUN B to
RUN C ordering. The docs/28 tests are unmodified. The packet disclosed each edit.

Production-behavior notes for the release act: merging and pushing activates the RUN C
posting split immediately (workflow_run fires on default-branch workflows only).
post.yml uses the existing repo secrets; no environment migration is required first.
Full credential isolation would need a GitHub environment, an optional operator
follow-up, since repo secrets remain technically visible to all workflows. The
assemble workflow was renamed to "RUN B assemble" for the workflow_run reference; the
watchdog is unaffected because it keys workflows by file path. The posting step keeps
the pre-existing skip-and-log posture, byte-compared against the old assemble. The
status page reports corrections_count as unknown until the first post-merge RUN B
writes the additive field, as the packet disclosed.

Verdict: the delivery is accepted. Merge to main and the push are Michael's acts. The
first post-merge day should be watched through one full cron cycle: RUN A, RUN B, the
workflow_run handoff to RUN C, and the 13:00Z watchdog tick.

## 2026-07-26: Session 49 (Fable). Hotfix aftermath recorded; second review adjudicated; docs/33 is the X work order

Morning outage, recorded: the first post-W3 production cycle failed at restore. Both
runs died on "archive conflicts with repository authority: data/reference/
corrections.json" because every pre-W3 data-latest archive carries the tracked
reference tree and W3's conflict check raised on the schema-upgraded corrections file.
Self-deadlocking: the archive is only rebuilt by a run that gets past restore. RUN C
correctly declined to fire behind the failed assemble. Hotfix 9d3b73f (14:52 CT):
repository-authority files in archives are ignored loudly, never fatally; protection
was always the merge allowlist, which never wrote them; new archives carry only
runtime paths (roster.json is the sole runtime file under data/reference). Suite
572/0; proven against the legacy archive shape before push. Validation lesson filed:
the W3 check was validated against fixtures, never against the actual production
archive; the transition case was foreseeable. The 15:27 CT collect is the first
post-fix production exercise.

Second external review adjudicated into docs/33 (binding). All five headline claims
verified in code before ruling: the surge baseline omits zero-occurrence days
(surges.py line 81); the classifier defaults unmatched phrases to message
(eligibility.py line 41); the on-script index is live on the homepage with mixed
units (0.7692 D, 0.8358 R on the committed snapshot), a v1 surface the R-29.2 dark
statement missed; thresholds_sha omits the live family knobs while hashing a knob
nothing references; the v1.4 prompts are dark by design and gain a shadow-replay
flip gate. Work packages X1 through X15 defined. Release gates A through D adopted
as the public-posture ladder. Composite stays the signature per R-29.1; the index
leaves the public surface until validated (R-33.1 amends R-29.2).

Next action: Michael runs the Codex session against docs/33; the recovery chain
(collect, assemble picking up 2026-07-25, first RUN C firing) proves tonight; Monday
nomenclature decision unchanged.

## 2026-07-26: Session 50 (Fable). Restore deadlock fixed and proven; the watchdog's first catch

Outcome: the first post-W3 cycle failed on both legs at restore (the pre-W3 data-latest
archive conflicts with the W3-upgraded corrections.json; the raise self-deadlocks
because only a successful run rebuilds the archive). Hotfix 9d3b73f: repository files
in archives are ignored loudly, never restored, never fatal; new archives carry only
runtime paths. Pushed 35 minutes before the evening dispatch. The evening cycle then
proved it in production: RUN A green with the IGNORED log line and 25 runtime files
merged, RUN B green with a correct Sunday HOLD of 2026-07-25 (5 statements vs
same-weekday median 11), RUN C's first firing green (no new day, archive
authenticated, phrase pages refreshed). Full evidence in docs/04, Session 50.

The 14:25Z watchdog tick raised 2 alarms and paged on the morning failures: first real
catch, detection latency 1h46m against the prior day's 7h of silence.

Process notes: the S49 numbering belongs to Michael's second-review ruling (docs/33),
committed from a parallel session while this one ran. The X-package branch
(codex/x-packages) was active in the operator checkout during this session; a routine
`pull --rebase` here landed on that branch between two of its commits and rebased it
onto current main. It applied 5/5 clean and the worker continued, but it was an
uninvited touch of an active worker's branch; this record is the disclosure. The
session's docs commits were made from an isolated worktree to avoid a second touch.

Next action: 2026-07-25 publishes at the 09:30Z pass when the gate clears or
force-finalizes per MAX_WAIT_DAYS. The X1-X15 delivery validates under docs/33 gates
A-D when the worker finishes.

## 2026-07-27: Session 51 (Opus). Deep Archive completion: CREC 111/112/117-119, R-S50.1 3-lane substrate, SD.8 HELD

Ran in an isolated worktree `opus/deep-archive` off `origin/main` while the Codex X-worker held the
operator checkout on `codex/x-packages`; every edited file collision-checked clean against the worker's
branch. $0, deterministic, no publication act. Suite 572 -> 578 green.

Built the five remaining per-Congress CREC shards (111, 112, 117, 118, 119) exactly as 113-116; every
window passes symmetric two-party. 119's ongoing 2026 was 4 sitemap-days short, so the tail was crawled
first (+87 statements) and 119 built COMPLETE, not partial. The CREC E-lane now spans 107-119 (2001-2026).

Executed R-S50.1 (Fable ruling): the alexandria substrate lane domain is now THREE-valued on `date_source`
(legacy/scraper/page_html), page_html ISOLATED and never folded into scraper in a primary number; the
folded propublica/scraped view is a labelled robustness check only. Code done and suite-green
(`load_congress_records`/`lane_shard_path`/`wave_s4._collect` 3-lane; daily pipeline unaffected). The full
3-lane substrate was rebuilt for all 113-119 (~2.8h) and the R-S50.1 acceptance passes, the exact partition
legacy + scraper + page_html == combined for every congress (delta 0). Premise correction: the reads were
already 2-lane-aware at base (Session 19), so R-S50.1 was the 2->3-lane isolation, not a from-scratch fix.

Froze SD.8 (instrument concordance) before measuring, then ran it: the press-core president-naming
direction (S2.9, out-party names the president more) reproduces on the CREC Extensions instrument in only
8/14 years, era-split (2013-2020 6/8 but 2021-2026 2/6) -> **HELD**. The CREC lane is not calibrated for the
naming family, so pre-2013 naming claims do NOT advance to publication (the calibration law working; the
verdict is press-only, stated, and a publishable methods card). Delivered on the branch; the SD.8 verdict
is the decision Michael carries back.

## 2026-07-27: Session 52 (Fable). X delivery validated and merged; Deep Archive branch integrated

The Codex X delivery (X1-X15, branch codex/x-packages) validated clean: fifteen ordered
commits from exact base 085184e, suite 647/0 reproduced independently, zero forbidden-path
changes, zero pre-existing tests modified, prompt pins untouched, zero added em dashes,
seven deviations all disclosed and sound. The X7 restore drill caught real nondeterminism
(generated_at sampled per pass in awards.json and concordance.json) and repaired it with
production stamping unchanged; the repaired drill proved byte identity at production scale.
One validator fix at merge: the X7 migration-evidence tests coupled the committed record to
the live manifests tree, which broke on rebase over the 2026-07-27 data commits and would
have broken again at every future cycle. The committed evidence now validates as a pinned
canonical record of the 2026-07-24 migration cycle, and the live-tree test asserts a
complete cycle exists without pinning the day.

The Opus Deep Archive delivery (opus/deep-archive, Session 51) integrated cleanly on top:
CREC shards 111/112/117-119 built and audited, the R-S50.1 three-lane substrate complete
with exact-partition acceptance, SD.8 frozen then measured to HELD (CREC Extensions not
calibrated for the naming family; pre-2013 naming publication stays gated). Its footprint
was verified: site untouched, data/derived limited to the CREC audits and SD.8 result that
docs/15 requires committed. Combined suite 653/0. Merged fast-forward and pushed in one
stack.

Next: the first production cycle on the X code deploys the index removal, participation
measures, fail-closed classification, corrected surges, and status surfaces. The 07-25
force-finalize lands at the Tuesday morning pass. Remaining operator items ride docs/33
section 4 and tasks #105/#110/#198/#203/#204.

## 2026-07-27: Session 53 (Opus). The long-session build tranche: E1 (isolated-substrate S1 re-run), then E2/E3

Branch `opus/s1-tranche` from `6c9b0bd`, baseline 653/0. E1 completes the Session-51 carry-forward:
the eleven S1 hypotheses re-run on the R-S50.1 isolated three-lane substrate (legacy/scraper/page_html).
Freeze-before-measure (`f0c96e9`), then measured. Headline: **isolation changes no verdict.** `legacy`
reproduces the Session-19 propublica column byte-for-byte (shards SHA256-identical), so the pre-seam
isolation is a verified no-op and the two propublica-era CONFIRMEDs (S1.1'/S1.3') stand. `scraper` matches
scraped on ten of eleven; the one move (S1.3' ARTIFACT to REFUTED) is a normalize-version rebuild artifact,
not page_html: the Session-51 scraper shards use the newer W7/X9 document-family collapse the Session-19
scraped shards predate, and page_html contributes zero coordination phrases (ledger 1/congress, empty
peak>=15 member index). `page_html` standalone is UNDERPOWERED for all eleven. Zero false positives.

A power-gate fix (`faebf7f`) stops `s1_4_proper` OOMing at congress scale (the post-Session-19
document-family clustering on the full-corpus normalize); verdict-preserving. Flagged to the orchestrating
session: the R-S50.1 substrate mixes normalize instruments (legacy = old byte copy; scraper/page_html =
fresh new normalize), so isolated-vs-folded scraper comparisons are instrument-confounded, though the
page_html-isolation outcome is determined regardless. Full evidence: docs/04 Session 53, docs/13 "E1"
section, `data/derived/search/revalidate_s1_isolated.json`, `delivery/S1-packet.md`. Suite 662/0.

E2 (task #198): wired `silence.build_day_board` into the deterministic leg (build dark, skip-and-log,
before build_awards so The Void is live-fed), Lane-1 only for the party counts and GDELT held to a Lane-2
salience gate (Article III). The silence module/render/guards already existed; the gap was the missing
caller. The archive surface was already wired dark (render gated, ships off) and needed no change. +5
tests, suite 667/0. You wire; Michael flips.

E3 (dry prep, no GPU): Alexandria Stage 2's deterministic pass is done; the remaining piece is the optional
4080 embedding + local topic-tag layer for Archive exhibits. No embedding code exists, so E3 verified the
inputs and wrote the runbook. `scripts/deep/alexandria_stage2_verify.py` reports READY: press mirror 688,820
records (delta 0 vs every shard), 684,853 embeddable units; CREC E-lane 152,187 statements (the pre-2013
spine), ledgers 107-119 present; ~837,040 vectors total. `docs/34` is the runbook (model all-MiniLM-L6-v2,
lane contract, storage, non-interference); the embed/tag scripts are specified but not committed (torch
stack, untestable without the GPU). Starting the GPU run stays Michael's call. Session close: branch
opus/s1-tranche, six commits, suite 653 -> 667/0, never merged to main, $0, no flips/dispatch/posting.

## 2026-07-28: Session 54 (Fable). S1 tranche validated and merged

The Session 53 delivery (opus/s1-tranche, five commits) validated clean and merged
fast-forward: site untouched, derived additions limited to the docs/12 evidence
fingerprints, silence wiring exactly the ruled pattern (Lane 1 only, GDELT as a
salience gate never a denominator, skip-and-log, dark), zero added em dashes, flags
and prompt pins untouched, suite 667/0 reproduced independently.

Ruling on the E1 substrate flag: accepted as recorded. The isolated substrate mixes
normalize instruments (legacy copies the old propublica shards; scraper and page_html
were rebuilt on the newer W7/X9 collapse), so isolated-versus-folded scraper
comparisons are instrument-confounded. Within-lane verdicts stand; the S1.3-prime
move is recorded as a normalize-version artifact, not a page_html effect, and no
same-instrument rebuild is ordered because page_html provably contributes zero
coordination phrases. Any future cross-instrument comparison must rebuild both sides
on one normalize version first.

Task #198 is satisfied by the silence wiring pending Michael closing it. The
silence_board flip remains his, gated on boards accumulating dark through the 08-03
digest. The docs/34 runbook governs the optional 4080 embedding run.

## 2026-07-28: Session 55 (Fable). Annotation kit merged; third review adjudicated; docs/36 is the Y work order

The annotation-kit delivery (opus/annotation-kit, seven commits) validated clean and
merged: site and derived untouched beyond sealed sample manifests, zero added em
dashes, suite 702/0. The gold-set study can start the moment annotators are hired.

Third external review adjudicated into docs/36 after direct verification: the
instrument fingerprint registry is stale against its owning modules (v1/v2 recorded,
v2/v3 live) and is not inherited across artifacts; the withdrawn discipline metric
still sits in canonical day records at index 1.0 beside participation 0 of N; the
homepage said Today about a force-finalized three-day-old reading; two model calls
were paid to produce nulls; amber short-circuits red in overall status; the phrase
CSV surface_class column is blank; the legacy synchronized tables filter only
unknown. Ruled: work packages Y1 through Y10, a public correction for the
fingerprint defect, the registry-versus-authority invariant class (R-36.1, the
recurring failure shape across three rounds), state-aware temporal labels,
deterministic nulls with state-aware posting, and status precedence critical over
red over amber. R-29.1 stands: the composite remains the front door on days with
something to say; empty days stop pretending.

Next: the Y session runs on the merged base; validation under the standing loop;
the annotation pilot adjudicates the classifier questions Y10 documents.

## 2026-07-28: Session 56 (Fable). Governance hardening: docs/37 and Article XVII

The recurring failure patterns are now institutional, not episodic. docs/37 codifies
fifteen incident-named rule groups binding every implementation session; CLAUDE.md
carries the headline traps and the pointer; the constitution is amended to v1.2 adding
Article XVII (self-description integrity) under the Article XV process. Work orders
cite docs/37 from now on; validation checks deliveries against it. Detail in docs/04
Session 56.

## 2026-07-28: Session 57 (Fable). Y delivery validated and merged; watchdog privacy-gate outage fixed; annotation ruled

The Y delivery (opus/y-packages, eleven commits) validated clean: suite 774/0
reproduced independently after the added fix, both mutation harnesses 15 of 15,
site untouched, prompt pins untouched, corrections append proven pure-addition by
diff (zero removed lines, checkpoint monotonic at 6). One added em dash was ruled
allowed: a verbatim assertion that the legacy em-dash homepage title is absent,
protected as verbatim under docs/25 section 3.1. The Y10 dark-by-design decision
and the deferred pilot re-seal are accepted as disclosed. The push-scope
contradiction the session flagged was our defect; docs/37 rule 14 now requires a
work order to state push scope exactly once.

Production incident found and fixed during validation: the 15:14Z watchdog run
died at import because the instrument fingerprint made privacy a transitive
import of ops, and privacy established the Article XIII gate at import time. The
watchdog holds no salt by design; the pipeline ran unwatched and the watchdog's
own dead-man paged, which is how the outage surfaced. Fix on the merged stack:
the gate establishes on first use through _require_gate, every fail-closed branch
preserved including the canary mismatch, proven by salt-less subprocess tests
reproducing the CI runner exactly. This is docs/37 rule 4 in a new costume: a
fail-closed gate whose blast radius widened past its premise. The 11:32Z
cancelled collect is noted; the readiness gate recovers the day at the evening
pass.

Annotation ruling, amending docs/35 practice (implementation lands with the ops
session): Michael annotates the pilot as the single human rater, blind to
predicted class through the sealed bundles; a frozen-prompt model acts as second
rater for disagreement triage, labeled model-assisted and never counted as human
agreement; every resulting metric is labeled author-annotated, single human
rater, provisional; the bundles and labels publish openly with a standing
re-annotation invitation; Gate B remains unclaimed until independent replication,
which the published bundles enable at zero recruiting cost. Transparency is the
mechanism that replaces personnel independence, and the disclosure is total.
