# 19: Nomenclature wiring brief (Fable, 2026-07-18, binding)

**Who runs this: Opus, in the main tree, after reading CLAUDE.md.** Build-order step (5). The SPAN
tagger exists and is green on branch `wip/nomenclature` (Session 15: reference data mirrored, 21/21
fixtures, corpus pass lands on the spec's predictions). This brief wires it, measures it, reviews it,
and merges it, **dark wherever it touches a public surface**. Spec: `docs/16-NOMENCLATURE-SPEC.md`.
Fable pre-registers here; the implementing session executes and does not re-litigate.

## §0 Session start (Art. XVI)

`git pull` (pull-rebase before every push, data crons land mid-session). Read the streak from the
RECORD (`verifier_passed`/`fallback` in the assemble logs for the 07-17/07-18/07-19 runs; run
statuses are inadmissible; earliest accurate §1.4.1 pass is Sat 07-19). `python tests/run_tests.py` ,
**263+ green** before touching anything (bare `python` is a 0-byte stub on this box; use
`C:\ProgramData\miniconda3\python.exe`). `vtask list`, reuse, never re-file.

## §1 Branch first

All refs were force-pushed in the 07-17 history rewrite, and main has moved four sessions since the
branch was cut. **Rebase `wip/nomenclature` onto current main** (expect minimal conflicts, the
tagger files are new; reference data lives on X:). Run the branch's 21 fixtures + the FULL suite on
the rebased branch BEFORE any wiring. A worktree is optional; if used, one tree = one writer.

## §2 Wiring points (pre-registered; tag, never delete)

- **(a) MEASURE, live immediately.** `nomenclature_rate` per party per day in the nightly symmetry
  audit, + the per-member ingest-health flags (Session-15 spec). Measurement-only: no public surface
  changes, so it does not wait for a flag.
- **(b) SITE display-time, behind a FEATURES flag (`nomenclature_tags`), default OFF.** Phrase
  surfaces (top-synchronized lists, phrase/curve pages, archive chapters' `top_phrases`) render the
  tag. Display-time fixes every historical page with **no ledger rebuild**.
- **(c) DAILY pre-distill, same flag.** Tagged occurrences are annotated in the P2/P3 inputs so the
  Sonnet voice cannot launder a bill title into message-coordination prose *and have the verifier
  pass it* (the members really did type it). Tagging is ANNOTATION: the citation path, quotes, and
  `verify.is_verbatim` are untouched. Anything that could change published prose ships dark; **the
  flag flip is Michael's one-commit act after the review.**

## §3 Acceptance (pre-registered)

1. Rebased branch: 21/21 fixtures + full suite green.
2. Spec predictions re-land on the CURRENT corpus, re-derive, never assume the counts froze
   (Session-15 anchors: sync 461,501 exact; covered ≈14,175).
3. KILL/PROTECT re-verified in both directions: "one big beautiful bill act" / appropriations titles
   ≈1.0 KILL; "the big ugly bill" ≈0.000 PROTECT; "child tax credit" PROTECT; "national security
   department" via the committee lane.
4. Flag OFF ⇒ **zero public bytes change** (golden render). Flag ON in a LOCAL render ⇒ tags appear,
   nothing is deleted, symmetry audit output shape unchanged.

## §4 Robustness rider (Fable-mandated; converts "pending review" into a completed review)

Three of the four CONFIRMED findings are nomenclature-exposed (they count phrase/n-gram co-use, and
docs/16's core insight is that bill titles manufacture co-use). Re-run each on **tag-stripped
substrate** and append a ledger row either way (`supersedes` noted):

- **S1.9** (weekly 5-gram overlap, congress 117): exclude 5-grams that overlap a tagged span.
  Pre-registered expectation: **D > R holds, ≥60% of matched weeks.**
- **S1.1′ / S1.3′** (bursts, propublica lane): a phrase whose in-congress occurrences are
  majority-tagged is a nomenclature phrase, drop it; re-run. Pre-registered expectation: **dir < 0
  in both within-lane halves and density-survives**; ratio/drop may shrink, report both numbers.
- **S2.9 exempt** (president name-tokens are not bill nomenclature).

If a gate fails, the finding is AMENDED, not suppressed (e.g. "coordination including bill-branding")
and its publication stays blocked pending Fable. **This rider gates the August/September drip pieces
(docs/20), so it runs in THIS session, not later.**

## §4b Connective-cluster defect (P0, external review 2026-07-18, reproduced by Fable; fix in this session before the launch flip)

An external (ChatGPT) review of the live 07-17 day found Democratic talking points whose receipts
don't support the apparent message. Fable reproduced both from `data/derived/days/2026-07-17.json`:

- cluster key **"into the trump administration's"**, Padilla + Goldman (Army Corps investigation)
  + **Booker (an unrelated flood-protection bill)**;
- cluster key **"democratic colleagues in demanding the"**, Kelly + Rosen (**the same FEMA joint
  letter, one document family**) + **Krishnamoorthi (Blanche/Epstein, unrelated)**.

**The diagnosis is NOT "receipts are fake."** Every citation contains its cluster-key phrase
verbatim, that is *why* they clustered, and the verifier honestly verified it. The defect is that
the admitted cluster keys are **connective frames and attribution boilerplate**, not substantive
messages, so a semantically incoherent cluster sails through a verifier that checks verbatim-ness,
quorum, and attribution, everything except *whether the shared span is a message*. It is the
docs/16 insight wearing a third face: bill titles (nomenclature), attribution frames ("proud to
join", "democratic colleagues in demanding the"), connective scaffolding ("into the trump
administration's") all manufacture phrase co-use that is not message coordination.

Required in this session (it is the same machinery as the wiring):

The one-line law (adopt the reviewer's wording, it is precisely right): **string correctness without
message admissibility is insufficient for publication.** Three properties, checked separately:
string validity (span in every source, already verified) · cluster admissibility (the span is a
message, not scaffolding, MISSING) · rendering validity (the prose characterizes what the admitted
receipts jointly say, unchecked).

1. **A deterministic cluster-key admission gate**: a talking-point cluster key must be substantive ,
   reject attribution-frame and connective-scaffold keys (extend the weak-label/boilerplate layers).
   Candidate criteria, implementer picks and failure fixtures decide: minimum content-word count ·
   max function-word share · rejects attribution templates ("colleagues in demanding", "joins/joined
   … in") · rejects spans that terminate before the policy object (trailing possessive/preposition:
   "into the trump administration's") · DF penalty for generic scaffolding · the hard one, applied
   conservatively: the span must retain meaning displayed alone. **Conservative is correct here, a
   missed valid finding costs a line; an admitted scaffold key anchors unrelated claims on the
   flagship surface.** Deterministic, party-blind, tested with failure fixtures both directions (the two
   clusters above must die; the birthright-citizenship 06-30 flagship must survive).
   **Every rejection emits a stable reason code** (REJECT_ATTRIBUTION_FRAME ·
   REJECT_INCOMPLETE_SYNTACTIC_SPAN · REJECT_GENERIC_CONNECTIVE · REJECT_ENTITY_ONLY ·
   REJECT_TITLE_FRAGMENT · REJECT_LOW_INFORMATION_CONTENT · REJECT_FAMILY_QUORUM · …), and rejected
   candidates are LOGGED with reason + would-have-been output (a dark-shelf view, the only accurate
   way to audit false negatives before tuning a conservative gate).
2. **The family-quorum invariant, enforced after ALL collapsing and before anything is renderable**:
   `eligible_cluster_units = distinct collapsed document families passing span + admissibility;
   publish only when count(eligible_cluster_units) >= quorum.` Kelly+Rosen are one family and must
   count once toward the threshold; member REACH is still reported separately (a family with 25
   signatories is 25 endorsements, one publication unit). If the citation path counts raw members
   today, fix and failure tests.
3. **Receipt display**: highlight the exact matching span in every receipt, and replace the single
   "verifier passed" badge with the per-test breakdown (span present n/n · spans highlighted ·
   distinct members · distinct document families · admissibility · attribution gate · URLs). The
   aggregate "Publication verified" state is a derived CONJUNCTION: it exists only when every chip is
   independently computed and passes; **a failed or unavailable check makes the aggregate
   UNAVAILABLE, never a reduced confidence.**
4. **Audit ALL published days for inadmissible keys**, it is a defect CLASS whose historical
   extent is unknown until the audit runs, not a 07-17 event. **Categorize the failures by reason
   code, don't merely count them**; add a regression fixture per discovered class; re-render
   affected days; every change is a dated corrections-log entry.

**Session-close evidence (Art. XVI, the P0 closes on evidence, not on edits):** the two named 07-17
clusters die for the correct deterministic reason · a known-good substantive cluster survives ·
family collapse runs before quorum on every publication path · spans highlighted on every receipt ·
chips independently computed · the all-days audit has run over the complete archive with failures
categorized · affected pages rebuilt or visibly corrected · a HUMAN sample audit covers both admitted
AND rejected clusters (fold into the #129 dark-week receipts ritual) · the live page no longer shows
the known-invalid interpretations.

**This blocks the launch flip** (Constitution Art. I, citation-or-silence: a receipt that does not
support its line's meaning is a silent integrity failure even when every string check passes).

## §4c Riders from the review's revision (non-blocking, do if cheap, else queue with the item named)

- **Support-graph validity** (the reviewer's best new idea, hardened on their second pass, the law
  is *no rendered proposition may outlive its evidence*): every factual rendered clause carries
  non-empty machine-readable `support_cluster_ids`; removing a cluster from the render input must
  remove every clause exclusively supported by it or leave those clauses supported by another mapped
  cluster; no factual clause may survive with zero valid supports. **The binding invariant is the
  support GRAPH, not textual difference**, a "materially altered prose" comparison would fail on
  harmless rewording and pass a renderer that preserved an unsupported claim in different words.
  Literal ablation snapshots are retained only as regression fixtures. If the current render path
  can bind clauses to cluster ids cheaply, land it now; if not, queue it in docs/11 as a named
  pre-v2-Concordance requirement.
- **Per-post composite label**: the AI-composite marker must survive a cropped screenshot, it goes
  in EVERY post unit of a thread, not the thread head or the bio. Posting is off; land it before the
  flip.
- **"Observed publishing member" definition** for the R3 denominator work: source successfully
  checked AND ≥1 eligible document in the window, not merely a reachable site.
- **Timestamp labeling**: keep source-claimed publication, first OnScript observation, and
  earliest-in-lane distinct wherever "first" renders (backfill makes them diverge).

## §5 Adversarial review, then merge

Independent adversarial review of the wiring diff (the Session-13 convention, the reviewer tries to
make the tagger delete, mutate a citation, or shift a published number with the flag off). Then merge
`wip/nomenclature` → main with the flag OFF. The merge is a build act (dark); the flip is not.

## §6 Traps (all previously paid for, do not re-buy)

`build_verdicts` is a two-pass scan over the full corpus, tens of minutes; run it BACKGROUNDED; an
exit-127 after one line of output is a TOOL TIMEOUT, not a crash. `len(short_title) <= 20` is a FALSE
premise (30-token backronyms are real; the code allowlist is the gate). PYTHONHASHSEED=0 for anything
shard-adjacent. Foreground tool timeouts are timeouts. Stage only your own files.

## §7 Reserved (never self-authorize)

The five spec-§9 rulings (privacy interplay, ACA, #146 skew interaction, quiet-day floor, launch
bar); the `nomenclature_tags` flag flip; publication of any card. All Michael/Fable.

## §8 Session end (Art. XVI)

Full suite green · rider ledger rows pushed · BUILDLOG entry · CLAUDE.md You-are-here updated ·
expectation-vs-observation check (streak from the record, site day, flags) with discrepancies FILED.
