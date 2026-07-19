# 19 — THE NOMENCLATURE WIRING BRIEF (Fable, 2026-07-18 — binding)

**Who runs this: Opus, in the main tree, after reading CLAUDE.md.** Build-order step (5). The SPAN
tagger exists and is green on branch `wip/nomenclature` (Session 15: reference data mirrored, 21/21
fixtures, corpus pass lands on the spec's predictions). This brief wires it, measures it, reviews it,
and merges it — **dark wherever it touches a public surface**. Spec: `docs/16-NOMENCLATURE-SPEC.md`.
Fable pre-registers here; the implementing session executes and does not re-litigate.

## §0 Session start (Art. XVI)

`git pull` (pull-rebase before every push — data crons land mid-session). Read the streak from the
RECORD (`verifier_passed`/`fallback` in the assemble logs for the 07-17/07-18/07-19 runs; run
statuses are inadmissible; earliest honest §1.4.1 pass is Sat 07-19). `python tests/run_tests.py` —
**263+ green** before touching anything (bare `python` is a 0-byte stub on this box; use
`C:\ProgramData\miniconda3\python.exe`). `vtask list` — reuse, never re-file.

## §1 Branch first

All refs were force-pushed in the 07-17 history rewrite, and main has moved four sessions since the
branch was cut. **Rebase `wip/nomenclature` onto current main** (expect minimal conflicts — the
tagger files are new; reference data lives on X:). Run the branch's 21 fixtures + the FULL suite on
the rebased branch BEFORE any wiring. A worktree is optional; if used, one tree = one writer.

## §2 Wiring points (pre-registered; tag, NEVER delete)

- **(a) MEASURE — live immediately.** `nomenclature_rate` per party per day in the nightly symmetry
  audit, + the per-member ingest-health flags (Session-15 spec). Measurement-only: no public surface
  changes, so it does not wait for a flag.
- **(b) SITE display-time — behind a FEATURES flag (`nomenclature_tags`), default OFF.** Phrase
  surfaces (top-synchronized lists, phrase/curve pages, archive chapters' `top_phrases`) render the
  tag. Display-time fixes every historical page with **no ledger rebuild**.
- **(c) DAILY pre-distill — same flag.** Tagged occurrences are annotated in the P2/P3 inputs so the
  Sonnet voice cannot launder a bill title into message-coordination prose *and have the verifier
  pass it* (the members really did type it). Tagging is ANNOTATION: the citation path, quotes, and
  `verify.is_verbatim` are untouched. Anything that could change published prose ships dark; **the
  flag flip is Michael's one-commit act after the review.**

## §3 Acceptance (pre-registered)

1. Rebased branch: 21/21 fixtures + full suite green.
2. Spec predictions re-land on the CURRENT corpus — re-derive, never assume the counts froze
   (Session-15 anchors: sync 461,501 exact; covered ≈14,175).
3. KILL/PROTECT re-verified in both directions: "one big beautiful bill act" / appropriations titles
   ≈1.0 KILL; "the big ugly bill" ≈0.000 PROTECT; "child tax credit" PROTECT; "national security
   department" via the committee lane.
4. Flag OFF ⇒ **zero public bytes change** (golden render). Flag ON in a LOCAL render ⇒ tags appear,
   nothing is deleted, symmetry audit output shape unchanged.

## §4 THE ROBUSTNESS RIDER (Fable-mandated — this converts "pending review" into "reviewed with teeth")

Three of the four CONFIRMED findings are nomenclature-exposed (they count phrase/n-gram co-use, and
docs/16's core insight is that bill titles manufacture co-use). Re-run each on **tag-stripped
substrate** and append a ledger row either way (`supersedes` noted):

- **S1.9** (weekly 5-gram overlap, congress 117): exclude 5-grams that overlap a tagged span.
  Pre-registered expectation: **D > R holds, ≥60% of matched weeks.**
- **S1.1′ / S1.3′** (bursts, propublica lane): a phrase whose in-congress occurrences are
  majority-tagged is a nomenclature phrase — drop it; re-run. Pre-registered expectation: **dir < 0
  in both within-lane halves and density-survives**; ratio/drop may shrink — report both numbers.
- **S2.9 exempt** (president name-tokens are not bill nomenclature).

If a gate fails, the finding is AMENDED, not suppressed (e.g. "coordination including bill-branding")
and its publication stays blocked pending Fable. **This rider gates the August/September drip pieces
(docs/20), so it runs in THIS session, not later.**

## §4b THE CONNECTIVE-CLUSTER DEFECT (P0 — external review 2026-07-18, REPRODUCED by Fable; fix in THIS session, before the launch flip)

An external (ChatGPT) review of the live 07-17 day found Democratic talking points whose receipts
don't support the apparent message. Fable reproduced both from `data/derived/days/2026-07-17.json`:

- cluster key **"into the trump administration's"** — Padilla + Goldman (Army Corps investigation)
  + **Booker (an unrelated flood-protection bill)**;
- cluster key **"democratic colleagues in demanding the"** — Kelly + Rosen (**the same FEMA joint
  letter — one document family**) + **Krishnamoorthi (Blanche/Epstein, unrelated)**.

**The diagnosis is NOT "receipts are fake."** Every citation contains its cluster-key phrase
verbatim — that is *why* they clustered, and the verifier honestly verified it. The defect is that
the admitted cluster keys are **connective frames and attribution boilerplate**, not substantive
messages, so a semantically incoherent cluster sails through a verifier that checks verbatim-ness,
quorum, and attribution — everything except *whether the shared span is a message*. This is the
docs/16 insight wearing a third face: bill titles (nomenclature), attribution frames ("proud to
join", "democratic colleagues in demanding the"), connective scaffolding ("into the trump
administration's") all manufacture phrase co-use that is not message coordination.

Required in this session (it is the same machinery as the wiring):

1. **A deterministic cluster-key admission gate**: a talking-point cluster key must be substantive —
   reject attribution-frame and connective-scaffold keys (extend the weak-label/boilerplate layers;
   patterns like leading prepositions/conjunctions + pure-function-word content, "colleagues in
   demanding", "joins/joined … in", etc.). Deterministic, lexicon+shape-based, party-blind,
   kill-fixture-tested both directions (the two clusters above MUST die; a real substantive cluster
   — e.g. the birthright-citizenship 06-30 flagship — MUST survive).
2. **Verify joint-unit counting in the quorum**: Kelly+Rosen are one near-identical document family;
   confirm the ≥3-support quorum counts collapsed units (not raw members) on the citation path, per
   §11 trap 2. If it counts members, fix and kill-test.
3. **Receipt display**: highlight the exact matching span in every receipt, and replace the single
   "verifier passed" badge with the per-test breakdown (phrase present n/n · spans highlighted ·
   distinct members · distinct document families · attribution gate · URLs). No test shown, no badge.
4. Re-render the affected historical days; log the corrections per the corrections process.

**This blocks the launch flip** (Constitution Art. I — citation-or-silence: a receipt that does not
support its line's meaning is a silent integrity failure even when every string check passes).

## §5 Adversarial review, then merge

Independent adversarial review of the wiring diff (the Session-13 convention — the reviewer tries to
make the tagger delete, mutate a citation, or shift a published number with the flag off). Then merge
`wip/nomenclature` → main with the flag OFF. The merge is a build act (dark); the flip is not.

## §6 Traps (all previously paid for — do not re-buy)

`build_verdicts` is a two-pass scan over the full corpus — tens of minutes; run it BACKGROUNDED; an
exit-127 after one line of output is a TOOL TIMEOUT, not a crash. `len(short_title) <= 20` is a FALSE
premise (30-token backronyms are real; the code allowlist is the gate). PYTHONHASHSEED=0 for anything
shard-adjacent. Foreground tool timeouts are timeouts. Stage only your own files.

## §7 Reserved (never self-authorize)

The five spec-§9 rulings (privacy interplay, ACA, #146 skew interaction, quiet-day floor, launch
bar); the `nomenclature_tags` flag flip; publication of any card. All Michael/Fable.

## §8 Session end (Art. XVI)

Full suite green · rider ledger rows pushed · BUILDLOG entry · CLAUDE.md You-are-here updated ·
expectation-vs-observation check (streak from the record, site day, flags) with discrepancies FILED.
