# 36: Third external review adjudication and the Y work order (binding)

Authority: Fable, Session 55, 2026-07-28. Third external adversarial review, written
against the merged W plus X plus deep plus S1 state and the live production record of
2026-07-25 through 2026-07-28. Verified before ruling, per the standing protocol; this
reviewer is now three rounds grounded. Release acts remain Michael's. Settled rulings
in docs/29 and docs/33 are not reopened except where amended below.

Verification results:

1. Fingerprint registry staleness: CONFIRMED verbatim. instrument_fingerprint.py
   hardcodes document-families-v1 and surface-eligibility-v2 while the owning modules
   declare v2 and v3. The registry copied strings instead of importing authorities.
2. Fingerprint drift across artifacts: CONFIRMED in effect. The 2026-07-25 post
   manifest does not carry the day record's fingerprint, and code_commit() keys on
   repository HEAD, which data commits move.
3. Legacy discipline field: CONFIRMED verbatim. The 2026-07-25 day record carries
   discipline index 1.0 for both parties beside participation measures of 0 of 3 and
   0 of 2. A withdrawn metric contradicting the corrected model sits as an ordinary
   canonical field.
4. Temporal truthfulness: CONFIRMED from the live site. "Today" rendered a
   force-finalized three-day-old reading; the party threads said "today" on 07-28
   about 07-25.
5. Paid nulls: CONFIRMED from the day record. Two Sonnet calls produced
   withheld_no_eligible_claim output that a template can produce.
6. Status semantics: CONFIRMED. Amber short-circuits red in overall status; the
   30-manifest window is manifests-available, not calendar; transport freshness reads
   as product freshness.
7. Surge party scope: PLAUSIBLE, structure to be settled in the fix. The acceptance
   fixture below decides it regardless of which loop shape holds.
8. CSV surface_class: CONFIRMED. The exporter reads a field the rows never carry.
9. Classifier floor and family fallback: CONFIRMED as described. The floor is
   exclusion-shaped and the family fallback treats missing evidence as statement
   count.
10. Lane discipline: CONFIRMED. The legacy synchronized tables filter only unknown.

## 1. Rulings

### R-36.1 The registry pattern is the defect, not the instance

Three rounds have now found the same failure shape: a package lands a registry and
tests the registry against itself; a later package moves the authority; the suite
stays green. This is ruled a class defect. Every central registry (method versions,
schema versions, public strings, feature flags, API field emitters, threshold
readers, privacy canaries, correction checkpoints) must be tested against its live
owning authorities, not against its own copy. Y9 is the enforcement package and is
the highest-leverage item in this order.

### R-36.2 The fingerprint defect gets a public correction

The product promises a shared audit fingerprint; the shipped fingerprint misdescribed
the live instrument and was rebuilt rather than inherited across artifacts. That is a
correction-log event under the docs/33 severity policy (major, category
wrong-method-attestation). The correction entry lands with the fix, in the same
delivery, and renders at the next cycle.

### R-36.3 Withdrawn metrics leave canonical records

The discipline field is withdrawn from newly generated day records and moves to an
explicitly labeled legacy_unvalidated_metrics carrier with status withdrawn and the
reason stated. Historical committed records are not rewritten; the renderer and
exports treat the legacy field as withdrawn wherever an old record is read. This
extends R-33.1: the index gate now covers the machine-readable surface, not only the
rendered one.

### R-36.4 Time is stated, never implied

The state-based heading ladder is adopted as specified (Today at 36 hours or less and
normal; Latest complete day to 60; Latest available reading when degraded or older;
Publication delayed when an expected day is missing; No current reading when source
completeness is insufficient). Social posts always carry the absolute measured date
and never the word today when post date and measured date differ. Publication lag
renders on the homepage whenever it exceeds one day.

### R-36.5 Nulls are deterministic and posting is state-aware

A day with zero code-selected claims makes no model call; the null text is a
template. When a day is force-finalized with anomalously low volume, zero eligible
claims for both parties, and red instrument status, the party accounts do not post;
the day page and status incident publish, and one neutral service-status note may
post instead. The rule is frozen in config with all four conditions named. This does
not reopen R-29.1: the composite stays the front door on days that have something to
say; this ruling governs days that do not.

### R-36.6 Status tells the operational truth

Three verifier windows publish (latest day, seven calendar days, thirty calendar
days), each as dropped over offered with an unmeasured count; red when the seven-day
rate breaches the SLO or the recent rate materially exceeds the long rate. Severity
precedence is critical, red, amber, green, neutral, unknown, and nothing lower ever
overrides anything higher. The freshness check renames to last successful source
fetch, and the five-way split (transport, content watermark, expected-day
completeness, publication lag, endpoint health) renders as separate labeled checks.

### R-36.7 Statistics stay honest at the edges

The surge baseline is computed per party with no shared mutable state; the acceptance
fixture gives the two parties different denominator histories and asserts different
baselines. Rankings split into qualified_surges (practical gate passed) and
largest_statistical_deviations (screening only); no surface calls a screening result
a surge. The classifier's family fallback becomes unknown on public surfaces when
family evidence is absent; the statement-count fallback survives only inside legacy
fixtures. Exports carry surface_class, surface_eligible, classification_rule,
classifier_version, and family_count, populated at assembly and asserted nonblank
for every nonprivate row.

### R-36.8 Lanes stay separated all the way down

The legacy synchronized tables either filter to the message class or rename to
repeated phrase observations with the unfiltered nature stated in the heading. A
name, a procedure, or a biography never appears under a heading that says message or
synchronized without the lexical-table disclaimer. One rule, applied to the homepage
tables, the party columns, and the day pages.

### R-36.9 What this round does not change

The composite-first identity (R-29.1) stands; this round trims its obligations on
empty days, which strengthens it. The beta label flip, the homepage hierarchy
reorder, recruiting, and all gate declarations remain Michael's. The validation gate
is unchanged: the annotation kit is merged and the human study is the path to Gate B.
The reviewer's product judgment (the data instrument is the durable value; the
composite is a distribution format for strong days) is recorded as the operating
thesis for the post-validation roadmap and does not require code this round.

## 2. The Y work order

Rules as in docs/33 section 2. One commit per package, suite green before and after,
schemas additive, no release acts, evidence with estimator, unit, window, and
denominator. Suite baseline 702.

- **Y1. Fingerprint integrity** (R-36.2). Method versions imported from owning
  modules; a provider-discovery test that fails when any production method module is
  absent from the registry; code identity becomes a measurement-tree hash (pipeline,
  prompts, config, schemas; never data or site output); the fingerprint stamps once
  at assembly and posts and exports inherit it byte-identically; the correction entry
  ships in this package. Acceptance: bumping any live METHOD_VERSION changes the
  fingerprint with no registry edit; a data-only commit does not change it; day,
  post, and API artifacts in one cycle carry one identical fingerprint.
- **Y2. Discipline withdrawal** (R-36.3). Acceptance: a newly generated day record
  has no top-level discipline; the withdrawn carrier appears with reason; reading a
  historical record renders it withdrawn everywhere.
- **Y3. Temporal truthfulness** (R-36.4). Acceptance: fixtures for each of the five
  states render the ruled heading; a delayed-day social fixture contains the absolute
  date and not the word today.
- **Y4. Deterministic nulls and state-aware posting** (R-36.5). Acceptance: a
  zero-claim day produces its day page with zero model calls recorded; the four-flag
  fixture produces no party posts and one status note; a normal day still posts.
- **Y5. Status semantics** (R-36.6). Acceptance: the three windows render from
  fixture manifests with the 48.78 percent seven-day case red while the 30-day case
  alone would be green; an open major correction plus a red check yields red.
- **Y6. Surge scope and ranking split** (R-36.7). Acceptance: the divergent-history
  fixture yields per-party baselines; qualified_surges excludes gate-failing rows
  that appear in largest_statistical_deviations.
- **Y7. Export semantic completeness** (R-36.7). Acceptance: every nonprivate row in
  the phrase CSV and API resources carries a nonblank class and classifier version.
- **Y8. Lane discipline** (R-36.8). Acceptance: a nomenclature row and a procedural
  row in fixtures never render under a message or synchronized heading without the
  lexical-table disclaimer.
- **Y9. Registry-versus-authority invariants** (R-36.1). Tests comparing every
  central registry against its live owners: method versions, schema versions, public
  strings, feature flags, API emitters, thresholds, canaries, correction
  checkpoints. Acceptance: a deliberate one-line bump of any authority fails the
  suite until its registry follows; the mutation harness reports each new invariant
  load-bearing.
- **Y10. Classifier floor hardening** (R-36.7). Public-surface unknown on absent
  family evidence; the generic-survivor list from the review (billions of dollars,
  communities across the country, and kin) becomes a fixture set documenting current
  behavior for the gold set to adjudicate rather than a hand-tuned blocklist.
  Acceptance: family-evidence-absent public claims classify unknown; the fixture set
  is sampled into the pilot annotation queue.

## 3. Operator acts

1. Run the Y session; validate and merge under the standing loop.
2. The annotation study proceeds on the merged kit; the pilot decides the classifier
   questions Y10 documents. Recruiting remains open.
3. Beta label flip, homepage hierarchy, and gate declarations per docs/33, on your
   timeline. The reviewer's recommendation to flip the beta label now is endorsed.
4. The reliability incident is real but self-resolving as the weekend backlog drains;
   the Y5 status semantics make the next one visible honestly.
