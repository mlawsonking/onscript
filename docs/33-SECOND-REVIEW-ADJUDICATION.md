# 33: Second external review adjudication and the X work order (binding)

Authority: Fable, Session 49, 2026-07-26. Michael supplied a second external review, a
residual backlog written against the merged W1-W11 stack. This document rules on it,
folds the accepted work into governance, and defines work packages X1 through X15 for
the external implementation worker. Release acts remain Michael's. docs/29 rulings are
not reopened except where a section below explicitly amends one.

Verification before ruling, per Article XVI. The review's five headline claims were
checked directly against code and the committed site snapshot; all five are real:

1. The surge baseline draws prior days from the phrase's own occurrence map
   (surges.py line 81), so zero-occurrence days are omitted and the baseline biases
   upward. Confirmed.
2. The surface classifier defaults any unmatched phrase to class "message"
   (eligibility.py line 41). Not fail-closed. Confirmed; the committed 2026-07-24
   homepage leads with "the house of representatives" and "letter is available".
3. The on-script index renders live on the homepage (0.7692 D, 0.8358 R on the
   committed snapshot) while mixing count units. Confirmed. This is a party-level v1
   feature that predates the flag system, which is why the docs/29 R-29.2 statement
   that the index is dark missed it: R-29.2 covered the per-member discipline flag,
   not this surface. R-29.2 is amended below.
4. thresholds_sha omits every DOCUMENT_FAMILY_* knob although families now annotate
   the measurement path in normalize, and it hashes NEAR_JOINT_JACCARD, which no
   pipeline module outside the hash references. Confirmed load-bearing.
5. P2 v1.4 and P3 v1.2 are dark while v1.3 and v1.1 run. Confirmed, but this is the
   designed docs/29 W6 state, not a defect; the review's shadow-replay activation
   protocol is adopted as the flip gate.

## 1. Rulings

### R-33.1 The index leaves the public surface (amends R-29.2)

The homepage on-script index divides mixed units and has never been validated. It is
removed from every public surface until rebuilt under the three-measure design (office,
publication, and family participation, each with numerator unit, denominator unit,
window, and method version). The three replacement measures are deterministic and
unit-labeled and may render once implemented; the composite index name returns only
after the W10 gold-set metrics publish. This extends the docs/29 R-29.2 gate from the
discipline and concordance flags to this surface as well.

### R-33.2 Fail-closed classification, with a deterministic floor

The "unknown" class is adopted. A phrase reaches class "message" only through an
affirmative standard; unmatched phrases are "unknown" and are excluded from composite
prose, rankings, social posts, alerts, and awards, while remaining in the concordance
and exports. The deterministic parts of the affirmative standard (substantive content
token, not scaffolding or title-reference, syntactic completeness, at least three
distinct document families) ship now. The gold-set classifier threshold joins the
standard when W10 metrics exist. A quiet day published under this rule is correct
output, not a failure to fill.

### R-33.3 One instrument fingerprint

The narrow thresholds_sha is replaced by a complete instrument fingerprint covering
code commit, schema versions, method versions, live thresholds including the family
knobs, prompts, privacy forms fingerprint, and nomenclature index version, with
component hashes retained so a reader can see which subsystem changed. Every published
day, manifest, API envelope, and correction revision carries it. Mutation tests prove
every live parameter moves the fingerprint and no dead parameter does. thresholds_sha
remains as a component during one transition cycle for symmetry-audit continuity.

### R-33.4 Surges become honest before they become public

The baseline risk set is the eligible calendar window from the denominator series,
zero days included. The output carries the full disclosure fields (calendar days,
observed days, successes, trials, absolute change, ratio, p, q, and the BH family
definition and size). Practical-significance gates ship as provisional frozen config.
The binomial tail is labeled a screening statistic; an overdispersion calibration
harness ships for evaluation, and any model swap is a versioned method change. No
public surface uses the word "surge" until the corrected baseline is live.

### R-33.5 Composite discipline within the R-29.1 frame

docs/29 R-29.1 stands: the composite remains the signature. Within it, the review's
composite items are adopted: a neutral measurement sentence precedes the composite on
every surface including threads; explicit composite states (generated_verified,
deterministic_fallback, withheld_no_eligible_claim, withheld_verifier_failure,
corrected) render everywhere; structured sentence-to-claim output is persisted with
request and response hashes before prose assembly; the meaningful null replaces
filler; and the style-leakage ban list (including "Clinically,") lands in the dark
v1.4 prompt lineage, never in the live prompt without the shadow gate.

### R-33.6 The shadow replay is the prompt flip gate

P2 v1.4 and P3 v1.2 activate only after a replay harness compares them against the
live versions over at least 60 complete days and 200 party-days, with the verifier
run on both sides and the review's zero-tolerance checks (unit mixing, quote
extension, topic-label assertions, multi-claim sentences) plus a fallback-rate
ceiling. The harness ships now and runs in dry-run for free; the live replay spends
real API money and is Michael's act under the budget governor.

### R-33.7 Denominators become date-effective

The corpus-wide caucus proxy is replaced by a date-effective roster table (term and
party intervals, chamber, voting status, vacancy handling) built from an authoritative
open source committed as reference data with provenance. Daily output distinguishes
eligible caucus offices, source-supported offices, observed publishing offices,
publications, and families. The office-source coverage registry ships to the extent
the upstream mirror can attest it, with unattestable states labeled rather than
guessed.

### R-33.8 Families get stable identity and validated retrieval

Family IDs become content-derived and immutable with a revision chain; published
claims pin the revision they used. The candidate window widens to a bounded temporal
window (36 hours) while daily counts stay day-scoped. A MinHash recall harness
measures candidate recall against exhaustive comparison on a bounded subset with a
0.995 target. Family diagnostics (medoid, member similarities, retrieval path,
duplicate class, versions) are stored. Public family counts always ride beside office
and publication counts, and one family is one support unit, stated in those words.

### R-33.9 Corrections, status, and SLOs

The correction schema gains the review's lifecycle fields, the three-tier severity
policy with response targets is adopted as written, open corrections gate the status
page, and original and corrected renderings both remain reachable. The streak splits
into publication streak and clean-run streak. Verifier drop rates publish over
declared windows as dropped over offered. Posting states adopt the seven-value
enumeration; disabled is never red. The review's SLO targets are adopted as
provisional, published on the status page, and marked provisional until Michael
ratifies them.

### R-33.10 Provenance, privacy, and the API label

Upstream data revisions pin in every collect manifest (commit, content hash, ETag,
collection time). Timezone database, locale, and day-boundary semantics pin with DST
transition tests. An SBOM publishes. Artifact attestation is adopted where GitHub
provides it natively; external signing infrastructure is deferred. The privacy
heuristic gains the review's test battery, the typed entity hierarchy, production
canaries that block publishing on failure, and aggregate telemetry; occurrence-level
public redaction records remain deferred per R-29.3. The static API is labeled
experimental under /api/, documented as such, with the resource endpoints, envelope
fields, and normalized CSV exports adopted; the supported-API commitment waits for
Gate B.

### R-33.11 Release gates A through D join governance

The review's four gates are adopted as the public-posture ladder: Gate A integrity
beta, Gate B validated instrument, Gate C professional service, Gate D paid product.
Gate definitions live in this document; gate transitions are Michael's acts. The
"public beta measurement instrument" label is implemented as a centralized string and
its deployment is Michael's call. Nothing may describe the project as open source
until counsel resolves licensing (task #110); "public source" is the permitted term.

### R-33.12 What is deferred or declined, with reasons

Human annotation execution, counsel work, design-partner recruitment, and gate
transitions are operator acts, not work-order items. The neutral-first homepage
reorder beyond the R-33.5 frame stays deferred per R-29.1; the homepage does gain the
instrument-status header, the class lanes (messages, shared names, procedure, raw),
and the corrections link, which the review and docs/29 both support. A hidden
composite importance score stays banned. Stance classification ships as deterministic
guards (negation, quotation attribution, mixed-stance rejection) with model-assisted
stance dark until validated. Advanced interpretive features stay dark per docs/29 and
P13-2. The external heartbeat remains task #203.

## 2. The X work order

Rules as in docs/29 section 4: packages in order, one commit each, suite green before
and after, validation evidence in the commit body, schemas additive, no release acts.
Baseline: the commit named in the operator prompt. Suite baseline 572.

- **X1. Instrument fingerprint** (R-33.3). Fingerprint module, carriage on every
  published artifact, mutation tests, transition-cycle compatibility. Acceptance: the
  parameter-mutation matrix passes; two clean builds at one commit agree.
- **X2. Surge correction** (R-33.4). Calendar-window risk set, disclosure fields,
  frozen provisional gates, BH family declaration, weekday-aware baseline option,
  calibration harness. Acceptance: the two-of-28-days fixture yields the full-window
  baseline and a fixture proves the old selection differed; rankings remain
  deterministic.
- **X3. Index removal and participation measures** (R-33.1). Remove the homepage
  index; implement the three labeled participation measures. Acceptance: no public
  surface renders "on-script index"; each measure names both units and its window.
- **X4. Fail-closed classification** (R-33.2). Unknown class, affirmative message
  standard, surface exclusions, concordance retention. Acceptance: the committed
  2026-07-24 fixtures reclassify "the house of representatives", "member of the
  house", "in sending a letter", and "letter is available" away from message; a
  fixture day with no affirmative message yields the meaningful null.
- **X5. Composite discipline** (R-33.5). Neutral lead sentence, composite states,
  structured persistence, null output, style-ban list in the dark prompt lineage.
  Acceptance: every rendered day and thread carries a state and a neutral lead; the
  banned style tokens fail the verifier when a model output contains them.
- **X6. Shadow replay harness** (R-33.6). Replay tooling, comparison report, zero-
  tolerance checks, dry-run mode. Acceptance: the harness runs end to end in dry-run
  on committed days and emits the full comparison report; no live API call without an
  explicit operator flag.
- **X7. Migration and drill evidence** (P0-1, P7-6). Machine-readable migration
  manifest generated from the recorded run evidence once the production cycle
  completes; a scripted quarterly restore drill. Acceptance: the drill script runs
  from a clean clone against release assets and reports byte-identical rebuilds.
- **X8. Date-effective denominators and source coverage** (R-33.7). Roster table with
  provenance, five distinguished daily measures, office-source registry with labeled
  unattestable states. Acceptance: a fixture spanning a vacancy and a party switch
  yields correct per-day denominators; no surface calls an office covered on corpus
  presence alone.
- **X9. Family hardening** (R-33.8). Stable IDs with revisions, temporal window,
  recall harness, diagnostics, unit-explicit display. Acceptance: a late-arriving
  publication changes no existing family ID; the recall harness reports against the
  0.995 target on the bounded subset.
- **X10. Corrections and status** (R-33.9). Schema expansion, severity policy,
  status integration, revision timelines, split streaks, windowed drop rates, posting
  states, provisional SLO publication. Acceptance: an open major correction turns the
  status amber; a degraded day breaks the clean-run streak but not the publication
  streak; disabled posting renders neutral.
- **X11. Provenance pinning** (R-33.10). Upstream revision pinning in manifests,
  timezone and locale pinning with DST tests, SBOM, native attestation where
  available. Acceptance: a collect manifest names the exact upstream commit and
  content hashes; the DST fixtures pass on both transition days.
- **X12. Privacy battery and canaries** (R-33.10). Heuristic test battery across the
  review's name-shape list, typed entity hierarchy, production canaries wired to
  refuse publication, aggregate telemetry. Acceptance: every battery case passes;
  a seeded canary failure blocks the publish step in a dry-run rehearsal.
- **X13. Experimental API and exports** (R-33.10). Endpoint set, envelope fields,
  experimental labeling, normalized CSVs, field documentation with deprecation
  policy. Acceptance: every envelope self-verifies (payload hash matches); the
  documented field list matches the emitted fields exactly.
- **X14. Deterministic context guards** (R-33.12). Occurrence context fields
  (sentence and clause offsets, adjacent tokens, quoted-speaker detection),
  negation and attribution guards, mixed-stance rejection for message eligibility.
  Acceptance: the "this is not a stock trading ban" fixture never merges with its
  affirmative counterpart into one message claim.
- **X15. Homepage lanes and beta string** (R-33.11, R-33.12). Instrument-status
  header, class lanes, corrections link, centralized beta label string (deployment
  flag dark). Acceptance: the lanes render from the classification layer with the
  composite prominent per R-29.1; the beta string renders only behind its flag.

## 3. Calendar integration

Immediate (this Codex delivery): X1 through X15, validated and merged under the
docs/29 control loop, released in Michael's Monday waves under docs/27. The Monday
2026-07-27 nomenclature decision is unchanged and remains Michael's. Medium term
(August): the live shadow replay, gold-set annotation under W10 plus X-fixes,
SLO ratification, license resolution, Gate A declaration when its conditions hold.
Long term (post-validation, post-election): Gate B, activation of validated
surfaces, family and propagation pages, the homepage-hierarchy question, source-lane
expansion one lane at a time. The election freeze (Oct 15 through Nov 10) binds all
of it; the last flip Monday remains Oct 5.

## 4. Operator acts

1. Approve this order and run the Codex session (prompt supplied in chat).
2. The Monday nomenclature flip decision, unchanged.
3. Live shadow replay authorization when X6 lands (real API spend).
4. Annotation recruiting once X-fixes stabilize the classes W10 samples.
5. SLO ratification, Gate A declaration, beta-label deployment.
6. Counsel: licensing and trademark (#105, #110). External heartbeat (#203).
