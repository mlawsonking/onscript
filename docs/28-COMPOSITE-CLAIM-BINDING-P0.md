# 28: Composite claim binding (P0, binding)

Authority: Fable, Session 45 addendum, 2026-07-23. Reported by the implementation agent,
verified independently before this ruling: the stored record, the live page, all six code
anchors, the corpus sweep, and the blast radius. This is a citation-integrity defect on
the daily core path. It recurs every day and reaches the posted threads, which cannot be
edited. It rides under task #195. The docs/27 sequence continues around it as ruled in
section 5 below.

## 1. The defect

On 2026-07-22 the R composite says 47 of us carried "the stop insider trading act." The
stored talking point (data/derived/days/2026-07-22.json:909) has label "national defense
authorization act", member count 47, and that quote. Dissection of the stored fragments:
13 of 47 units carry the label, 9 carry the printed quote, 25 carry neither and joined
through connective grams ("voted in favor of", "in support of the"). The page shows
"publication verified" beside "phrase shown 0/3".

Mechanism, all anchors verified: cluster.py:38 counts the whole transitive component;
distill.py:71 picks the shortest fragment anywhere in it as the quote; distill.py:102
welds the component count to that quote; distill.py:180 grounds quotes against the whole
day's fragment pool, which is vacuous because the quote comes from that pool;
run_assemble.py:69 selects citations by label, the one surface already bound correctly;
site.py:930 computes "publication verified" without the phrase-shown result.

Corpus measures: the composite quote appears in all three receipts in 2 of 38 stored
blocks and in zero receipts in 14 of 38. The rendered label chip is below full in 28 of
63 receipt blocks. Both parties flow through identical code; the defect is symmetric.

Insulated, verified: the ledger, phrase pages, top-synchronized, discipline index,
symmetry audit, coverage, and duets never read the component count. The damage is the
daily composite prose, its receipts, and the posted threads.

## 2. Required correction: one support set per claim

For every published talking point, one phrase governs everything attached to it.

1. Choose the support phrase P inside the cluster: the admissible gram carried by the
   most distinct units. Tie-break: more carriers, then longer gram, then lexicographic.
   Admission gates (scaffold, weak-label, privacy) run on P; if no admissible P reaches
   quorum, the talking point does not publish. Log the omission.
2. One containment basis everywhere: statement-level contains_gram, the same predicate
   verify.key_carrying_units and run_assemble._citations already use. The count, the
   quorum, the citations, and the quote all bind to P through this one predicate on the
   same text unit.
3. The displayed count is the number of distinct joint-aware units whose statements carry
   P. The joint unit key stays joint_group else bioguide.
4. The displayed quote is drawn from a P-carrying fragment of a P-carrying unit. The
   per-unit representative selection prefers P-carrying fragments.
5. Citations come from P-carrying units and each receipt visibly contains P.
   run_assemble._citations already does this by label; it is the reference behavior.
6. The verifier binds per talking point: the composite quote must carry that talking
   point's P. The combined-pool grounding at distill.py:180 is removed. "Publication
   verified" then means: admissible P, at least three P-carrying units, three P-carrying
   cited receipts. Do not fold the phrase-shown chip into the site-side checks; fix the
   binding upstream so the chip trends to full on its own.
7. Component reach is removed from every public surface. No number derived from the
   transitive component size renders anywhere. The reach-display intent noted at
   verify.py:105 is overruled. No member_reach field is added; a reach statistic would
   need its own ruling and methodology definition.
8. Quorum stays SYNC_MIN_MEMBERS = 3, unchanged. Corrected counts falling below it drop
   the claim; that is the intended behavior, not a threshold change.

Value-only fix: schema_version stays 1; field names stay label, members, quote; no prompt
file changes (P2 consumes the same fields with corrected values); no new LLM cost; the
top-synchronized, duet, and phrases paths are not touched.

## 3. Historical record and corrections

Published day pages and posted threads carry unsupported claims. Posted threads cannot be
edited. History is not silently rewritten.

1. Stored day JSONs and composite prose stay verbatim. No retroactive recomputation of
   numerators for historical pages: stored fragments are per-unit representatives, so a
   recount from them undercounts, and no new number enters the record without its
   estimator (the standing rule).
2. The renderer flags affected historical blocks: any pre-fix talking point whose stored
   quote fails the P-binding check against its own stored fragments and citations gets a
   visible correction note stating that the count overstates support for the quoted
   phrase due to a clustering defect corrected on the fix date, with a link to the
   corrections log. Deterministic, computable at render time from stored data,
   conservative (flags only provable mismatches).
3. One corrections-log entry describes the defect class, the affected window (2026-07-15
   through the fix date), the two full-miss blocks (2026-07-15 D, 2026-07-22 R), and the
   corpus measures from section 1. Entries are append-only, both parties, same wording.
4. Posted threads are covered by the corrections log. posts.html stays a verbatim archive.

## 4. Required tests

1. Bridged-topic regression fixture reproducing the NDAA and insider-trading collision
   with connective grams: the fixed pipeline publishes P-bound claims only; no claim
   welds the component count to any phrase; the 9-carrier phrase either publishes on its
   own support or drops below quorum.
2. Mutation tests, each proven red: component count restored as numerator; quote chosen
   without the P constraint; citations selected without the P constraint; pool grounding
   restored in place of per-talking-point binding.
3. Quorum: fewer than three P-carrying units means no publication, logged, both parties.
4. A joint release counts once in the P-carrier count.
5. The privacy filter sees the corrected label and quote.
6. Receipts header count equals stats members equals the P-carrier count.
7. The historical correction note renders on a pre-fix fixture block that fails the
   binding check and does not render on a post-fix block.
8. Existing symmetry and voice-flag tests stay green. Tests that asserted the old
   component-count behavior may be updated; list each with before and after assertions.

## 5. Release consequence and sequencing

R2 stays pushed: it neither causes nor worsens this defect and fixes unrelated live ones.
R3 observation continues tonight. This fix is one commit on top of the current stack,
validated independently, then pushed alone in the next clean window, targeting before the
09:30 UTC collect on 2026-07-24 so the day's posting run composes bound claims. If
validation is not complete in time, the push waits for the next window and the extra day
joins the corrections window; a core-path change is not rushed. R4 and R5 push after the
posting-run proof per docs/27. The health gate's no-open-P0 condition for the 07-27 flip
is satisfied only when this fix is pushed and exercised green.

Suite floor at execution: 479 plus new tests, zero failures, house runner. Working tree
ends clean except AGENTS.md. The implementation agent does not push, post, dispatch, or
flip anything.
