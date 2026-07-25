# 29: External review adjudication and integrity work order (binding)

Authority: Fable, Session 47, 2026-07-25. Michael supplied a 60-item external strategic
review (an outside model's product and methodology audit) and asked for adjudication and
a Codex work order covering the phases that are actionable now. This document rules on
every item, states what is already landed, and defines work packages W1 through W11 for
the external implementation worker. Release acts (push, deploy, flip, post, publish)
remain Michael's throughout. Settled rulings in docs/24, docs/25, docs/27, and docs/28
are not reopened except where a section below explicitly amends one.

Provenance note: the review is external model output. Its factual premises were checked
against the project record before ruling. Four of its central claims correspond to real
recorded incidents: the claim-binding defect (docs/28), the state-restore rollback of
repository files (collect.yml restore note), the two phrase-form privacy escapes
(standing redaction rules), and the published-day mutations that preceded the final-day
guard (docs/23 section 7.5). Its trademark claim cites a third-party database through an
unverified aggregator link and is treated as unconfirmed input for the attorney, not as
fact.

## 1. Reading of the request

"The phases that are now" is read as the review's Phase 1 (integrity freeze) in full and
the machine-buildable part of Phase 2 (measurement validation). Phase 2's exit criteria
require human annotation that no implementation agent can perform; Codex delivers the
instrumentation and the annotation harness, and the validation verdict waits for the
annotated gold set. Phases 3 and 4 (product conversion, provenance expansion) are
deferred: their surface redesigns collide with the docs/27 release calendar and the
Article VIII election freeze, and their exit criteria depend on validated measurement
that does not exist yet. Nothing in this ruling moves the freeze dates or the docs/27
Monday cadence.

## 2. Dispositions

Legend: ACCEPT (as written), MOD (accepted with modification), DONE (already landed,
cited), DEFER (correct but not now, with trigger), REJECT (with reason). Package column
maps to section 4.

| # | Item | Disposition | Package |
|---|---|---|---|
| 1 | Replace product promise | MOD: wording centralized and corrected; final strings are Michael's release review | W1 |
| 2 | Three product layers | ACCEPT: formalizes the existing lane and code-computes-numbers rules | W2, W6 |
| 3 | Retire "coordination" as default noun | MOD: term ladder adopted for public surfaces; thesis prose uses "observable language coordination" | W1 |
| 4 | Rename coverage, three fields | MOD: fields adopted; endpoint health limited to what the mirror architecture can attest, gaps labeled | W1 |
| 5 | Canonical occurrence object | ACCEPT: character spans are the privacy prerequisite | W2 |
| 6 | Canonical claim objects | PARTIAL DONE (docs/28 one-support-set rule); extended to the full object | W2 |
| 7 | Claim invariants fail-closed | ACCEPT | W2 |
| 8 | Count-adjacent text is the counted phrase | PARTIAL DONE (docs/28, quote-window label fix 377b638); codified in verifier | W2 |
| 9 | No transitive cluster counts | PARTIAL DONE (connective-cluster fix); invariant and fixtures added | W2, W5 |
| 10 | Content-addressed day manifests | PARTIAL DONE (final-day guard, signed post archive); revision model added | W3 |
| 11 | Repository vs runtime authority | ACCEPT: the 3-to-0 corrections rollback is recorded history | W3 |
| 12 | Corrections as first-class data | ACCEPT: schema upgrade, monotonic invariant | W3 |
| 13 | Corrections in primary navigation | ACCEPT: static pages and feed; correction replies align with playbook P4; posting changes release-gated | W3 |
| 14 | Span-based privacy suppression | ACCEPT: two phrase-form escapes are enough evidence | W4 |
| 15 | Elected-official allowlist, fail closed | ACCEPT: roster.json exists; quarantine unresolved | W4 |
| 16 | Publish occurrence-level redaction records | DEFER: publishing span pointers into a public raw mirror is a dossier risk; attorney question, rides #105/#110; interim HMAC approach stands | gate |
| 17 | Gold-standard evaluation set | MOD: Codex builds sampler, schema, guide, split tooling; annotation is human work | W10 |
| 18 | Published quality metrics | MOD: metrics machinery now; publication after annotation | W10 |
| 19 | Adversarial fixture suite | ACCEPT: every historical correction becomes a fixture | W5 |
| 20 | Classify phrases, do not delete | ACCEPT: surface-eligibility layer | W6 |
| 21 | Nomenclature as separate mode | ACCEPT: aligns docs/16 and docs/19; flip remains Michael's | W6 |
| 22 | Document families counted explicitly | ACCEPT: thresholds land as provisional config pending gold set | W7 |
| 23 | Statistical surge ranking | ACCEPT: deterministic, stdlib, $0 | W8 |
| 24 | Kill the on-script index | MOD: not killed; concordance and discipline stay dark; their flip now additionally gated on W10 metrics being published (amends docs/27 for those two flags only) | gate |
| 25 | Tighten first-seen | ACCEPT: schema already records precision and ties; surfaces honor it | W8 |
| 26 | Topics as model output | ACCEPT: provenance metadata, epistemic labeling | W6 |
| 27 | Neutral voice primary, composite secondary | REJECT for this cycle: the composite is the locked front door (docs/01, docs/03) and the accounts are live; labeling improvements accepted in W1; revisit post-election | note |
| 28 | Code selects claims | ACCEPT: formalizes the existing rule that code computes and the model copies | W6 |
| 29 | Model output constrained to claim IDs | ACCEPT: typed contract for P2/P3 | W2, W6 |
| 30 | Model never extends counted quotes | ACCEPT: docs/28 direction completed | W2 |
| 31 | Two claims per rendering | MOD: adopted as a cap, not a target; quiet days stay honest | W6 |
| 32 | Remove prompt leakage | ACCEPT: prompt changes are release-sensitive (prompts_sha); land dark for Michael's review | W6 |
| 33 | Restructure the two party accounts | REJECT as written: product identity, Michael's post-election question; the labeling and correction-reply subset is accepted via W1 and W3 | note |
| 34 | Homepage hierarchy redesign | DEFER to Phase 3; the instrument-status card subset lands in W9 | W9 |
| 35 | Phrase page upgrades | MOD: additive fields from W7/W8 land dark; full redesign is Phase 3 | W7, W8 |
| 36 | Document-family pages | DEFER: after family validation | gate |
| 37 | Status page | ACCEPT | W9 |
| 38 | Exports and stable API | MOD: static pre-rendered JSON endpoints with envelopes and checksums; no server exists to rate-limit or authenticate | W9 |
| 39 | Watchlists and alerts | MOD: static filtered Atom feeds first; email and accounts deferred | W9 |
| 40 | Non-GitHub correction channel | MOD: page and templates now; the mailbox is an operator act | W3, op |
| 41 | Source expansion order | DEFER to Phase 4; committee, leadership, and caucus lanes noted as the correct next lanes in docs/05 terms | note |
| 42 | Graph-native schema | DEFER to Phase 4; W2 and W7 objects are its prerequisites | note |
| 43 | Four units in every result | ACCEPT: offices, publications, families, probable origins, wherever counts render | W2, W7 |
| 44 | Source genres isolated | DONE as standing rule (lane rules); reaffirmed for future lanes | note |
| 45 | Daily / Data / Research split | DEFER to Phase 3 | note |
| 46 | Publish nulls deliberately | ACCEPT as editorial policy; feeds the docs/20 calendar | op |
| 47 | Explicit legal permissions | MOD: file set with placeholders now; final license wording is an attorney item on #105/#110 | W11 |
| 48 | Pin the build environment | ACCEPT | W11 |
| 49 | Supply-chain provenance | PARTIAL: checksums, pinned SHAs, reproduction commands now; SBOM and attestation deferred | W11 |
| 50 | Security hardening | PARTIAL: permissions minimization, tar safety, pinning now; posting-job separation accepted but lands release-gated | W11 |
| 51 | Production invariants as property tests | ACCEPT: seeded generators, no new dependency; mutation harness for the verifier | W5 |
| 52 | Explicit SLOs | MOD: adopted as provisional targets published on the status page; Michael ratifies | W9 |
| 53 | External dead-man monitor | DONE in part (watchdog, Session 46) and FILED (task #203 for the external heartbeat); the review's check list folds into #203 | note |
| 54 | Structured review circuit | MOD: sampling tooling from W10; the ritual change is Michael's docs/07 section 3 amendment to accept | op |
| 55 | Professional users first | ACCEPT as strategy; no code | note |
| 56 | Workflow design partnerships | ACCEPT; Michael-led, post Phase 2 | op |
| 57 | Service metrics over followers | MOD: metrics adopted; the docs/23 gate keeps its clean-run requirement, and replacing the follower clause is Michael's amendment | op |
| 58 | Keep the instrument free | ACCEPT; matches current posture | note |
| 59 | Privacy-respecting analytics | MOD: no-tracking posture preserved; any measurement waits for a design that adds no identifiers | note |
| 60 | Resolve the name | ACCEPT: unverified claim, real risk; clearance belongs on the #105 attorney agenda and precedes the October registration wave; W1's string centralization is the cheap rename path | op |

## 3. Rulings on the contested items

### R-29.1 The composite voice stays the front door (items 27, 33)

The review is right that the first-person composite can be mistaken for representation
and that neutral measurement is the more defensible register. It is also asking the
project to demote its locked distribution design eleven weeks before the attention
window it was built for, while the accounts are live and the announcement is out.
Ruled: no hierarchy change this cycle. Accepted now: every public surface carries a
visible automated-measurement label, the neutral measurement sentence leads each thread
where it does not already, and correction replies are permitted under P4. The hierarchy
question is placed on the post-election agenda with this document as its record.

### R-29.2 The index gate (item 24)

The discipline index and concordance are built dark. The review's demand list (public
formula, sensitivity analysis, stability under missingness and deduplication,
uncertainty) is adopted as their flip gate. This amends docs/27 for those two flags
only: their Monday cannot come before the W10 metrics are published. No other flip
moves.

### R-29.3 Redaction records stay private for now (item 16)

Publishing per-statement redaction spans makes suppressed names mechanically
recoverable from the public raw mirror by anyone who diffs. The review's reproducibility
goal is real, but the interim answer is the existing HMAC carrier plus span suppression
internally (W4). Whether span records can ever be published is an attorney question and
rides the #105/#110 agenda.

### R-29.4 The API is static (item 38)

The no-server constraint is constitutional in practice: cron plus static hosting is why
the instrument survives neglect. The accepted form is pre-rendered JSON under /api/v1/
with schema envelopes, checksums, and bulk snapshots. Anything requiring accounts, rate
limits, or dynamic queries is deferred until a server is a deliberate decision.

### R-29.5 Prompt and wording changes land dark (items 1, 3, 32)

Public-string and prompt changes alter the published fingerprint (prompts_sha) and the
public posture. Codex implements them behind review: string changes in a single
reviewable commit, prompt changes as versioned files that do not activate until Michael
accepts them. The election freeze applies from Oct 15 regardless.

## 4. Work order for Codex

Packages run in order. Each package is one commit, suite green before and after, with
validation evidence in the commit body. Baseline: local main at d1d190a, 511 tests.

**W1. Terminology, denominators, and labels** (items 1, 3, 4, 27-subset).
Centralize every public-facing product string in one module. Adopt the term ladder
(repeated phrase, convergence, shared-document reuse, propagation, probable upstream
origin, observable language coordination). Split coverage into
observed_publishing_offices, eligible_caucus_offices, and source collection health with
honest labels for what the mirror cannot attest. Add the automated-measurement label
where missing. Acceptance: no public surface renders a hardcoded promise string; the
old "coverage" field remains for schema compatibility with a deprecation note.

**W2. Occurrence and claim contract** (items 5, 6, 7, 8, 9, 29, 30, 43).
Introduce the canonical occurrence object with character offsets and the canonical claim
object with one support phrase, per the review's schemas adapted to existing field
names. Enforce all six claim invariants fail-closed in the verifier. Constrain P2/P3 to
typed claim IDs; sentences map to claims; the counted phrase is the only quoted phrase.
Report offices, publications, and families as separate labeled units wherever a count
renders. Schemas are additive; existing keys keep meaning; schema_version bumps.
Acceptance: deliberately breaking any single invariant fails the build; the docs/28
tests still pass unmodified.

**W3. Publication immutability and corrections** (items 10, 11, 12, 13, 40-subset).
Content-addressed manifest per published day with publication_state and revision chain.
Restore archives extract to a temporary directory, validate, and merge through an
allowlist; nothing extracts over the checkout. Corrections adopt the structured schema
with severity classes and a monotonic-count invariant. Build /corrections/ static pages,
per-correction permalinks, a corrections feed, and links from every affected surface.
Acceptance: a fixture replaying the stale-archive rollback now fails closed; the
corrections count cannot decrease without a test failure.

**W4. Span privacy** (items 14, 15).
Person-span detection before n-gram generation: deterministic detection first (roster,
allowlist, capitalized-sequence heuristics), quarantine unresolved, suppress every
candidate occurrence intersecting a private span using interval overlap. The roster
allowlist covers in-scope elected officials in official capacity only. The existing
HMAC display-path checks remain. Acceptance: fixtures reconstructing both historical
escapes pass only under span suppression; a synthetic private name with every
overlapping n-gram window is fully suppressed.

**W5. Adversarial fixtures and property tests** (items 19, 51, 9-subset).
Every fixture class the review lists, seeded-random property tests with no new
dependency, and a mutation harness that disables each verifier check in turn and
asserts the suite fails. Acceptance: the mutation harness reports every verifier check
as load-bearing.

**W6. Phrase classification and rendering discipline** (items 20, 21, 26, 28, 31, 32).
Deterministic surface-eligibility layer (message, nomenclature, procedural,
biographical, private) gating daily-line, social, and alert surfaces while the
concordance stays complete. Nomenclature renders as shared nomenclature, never as the
top talking point. Code selects at most two claims per party rendering under the
review's selection criteria. Topic labels carry classifier provenance. Prompt cleanup
lands as versioned prompt files, dark. Acceptance: a day whose top raw count is
procedural produces a daily line led by the top message-class phrase.

**W7. Document families** (items 22, 43-subset, 35-subset).
Shingle, MinHash candidate retrieval, exact similarity, medoid-anchored clustering, no
unrestricted transitive components. Family counts join office and publication counts on
internal surfaces, dark on public surfaces pending validation. Thresholds land in
config marked provisional. Acceptance: the one-joint-release-many-offices fixture
reports 1 family; near-duplicates with local edits cluster; the A-B-C chain does not.

**W8. Surge statistics and first-observed honesty** (items 23, 25).
Binomial tail against a smoothed trailing baseline, Benjamini-Hochberg q-values,
separate rankings (most repeated, largest surge, most skewed, fastest spread, widest
family spread), no composite score. First-observed surfaces show lane, corpus start,
precision, and ties; no originator attribution on day-precision ties. Stdlib only.
Acceptance: rankings are reproducible from committed data by a documented command.

**W9. Status, exports, and feeds** (items 37, 38, 39, 52).
Static /status/ from existing manifests (collection, assembly, freshness, streak,
verifier drop, degraded, posting, corrections count, incident state). Static /api/v1/
JSON with envelopes (schema_version, method_version, generated_at, checksums) plus CSV
and bulk snapshots. Filtered Atom feeds as the first alert surface. Provisional SLO
table rendered on the status page. Acceptance: every status number traces to a manifest
field, never computed ad hoc in the template.

**W10. Gold-set harness** (items 17, 18, 54-subset).
Stratified sampler over candidate events, annotation schema and guide skeleton,
date-based splits, dual-annotation and adjudication tooling, metrics computation
(precision by class, family pairwise precision and recall, party error gap, confusion
matrices). No annotation is performed. Acceptance: the harness runs end to end on a
synthetic annotated sample and emits the full metrics set.

**W11. Hardening and provenance** (items 47, 48, 49, 50).
Actions pinned by full SHA, minimum permissions, tar extraction rejects absolute paths
and traversal, checksums and reproduction commands on release assets, environment
pinning (Python version, lock discipline, Unicode version noted), license file set with
placeholders where attorney input is pending, SECURITY.md and CITATION.cff. The
posting-job separation is implemented but its workflow lands release-gated for
Michael's push order. Acceptance: no third-party action referenced by tag; a traversal
fixture archive is rejected.

## 5. What Codex must not do

Push, deploy, dispatch workflows, post, or change POSTING_ENABLED or any FEATURES
value. Regenerate site/public or data/derived as a local side effect. Stage with git
add -A (AGENTS.md stays untracked). Modify docs/01, 03, 05, 06 (Fable and constitution
surfaces). Change prompts or thresholds outside the packages that name them. Reopen
settled docs/24, 25, 27, 28 rulings. Introduce a dependency into the deterministic
core. Use em dashes in any authored prose (docs/25 section 3).

## 6. Operator acts (Michael)

1. Trademark clearance joins the #105 attorney agenda and precedes the October
   registration wave (item 60). The review's registration claim is unverified input.
2. A corrections mailbox or equivalent channel (item 40).
3. The docs/07 section 3 ritual amendment for the structured review sample (item 54),
   and the docs/23 gate metric amendment (item 57), both his to accept or decline.
4. Annotation: recruiting and completing the gold set after W10 delivers the harness.
5. Release of every W-package per docs/27 discipline; the posting-job workflow change
   in W11 needs his explicit push order.

## 7. Session record

This adjudication is Session 47. The dated entry lives in docs/26-SESSION-HISTORY.md.
