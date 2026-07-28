# 06: Constitution and project invariants (v1.2, 2026-07-28)

This document consolidates the rules that apply across every phase, session, model, and operator.
Every future decision is checked against these numbered articles. A proposed action that conflicts
with an article is rejected. Article XV defines amendments. Four articles are effectively
unamendable.

## Articles

**I. Compression, not parody.** OnScript publishes what officials said, compressed and supported by
receipts. Any humor comes from the source material. The system does not add jokes.

**II. Citation or silence.** OnScript publishes only verified material. Every quoted fragment must
be
a verbatim substring. Every claim needs ≥3 distinct members, and every digit must be computed by
code. A claim that fails verification is dropped and logged. It is never patched or hand-edited.
Published errors receive a public correction post and an entry in the public corrections log.
Silent edits are prohibited.

**III. The two lanes.** Lane 1, the symmetric press-release corpus, is the only input to cross-party
numbers. Lane 2 includes Bluesky, floor speech, and any future asymmetric source. It may enrich and
support citations, but code blocks it from comparative metrics. Tests enforce this boundary.

**IV. Symmetric instrument, asymmetric findings.** Both parties use identical pipelines, prompts,
thresholds, and award rules. A public nightly hash audit verifies that symmetry. Findings are
allowed
to differ. Instrument skew is an incident. Finding skew is journalism. Forced balance is prohibited
because it introduces bias.

**V. The streak is sacred.** The system publishes every day. This is the defined meaning of “the
streak.” Budget controls, fallback calls, quiet-day lines, and degraded-mode banners allow the
system
to degrade before it skips. A missed day is an incident and receives a public build-log postmortem.

**VI. Raw-first, append-only, rebuildable.** Every source statement is stored immutably before
processing. Every derived artifact is reproducible from the raw archive. `rebuild.py` is a public
reproducibility promise. Schemas are versioned, breaking changes require migration scripts, and the
ledger epoch is always disclosed.

**VII. Numbers come from code.** Models may copy approved numbers. They never compute them. The
digit-whitelist check remains in force through model swaps and feature changes.

**VIII. Prompts are public.** The methodology page displays the live prompts and their complete git
history. Every prompt change receives a dated public diff and rationale. **Freeze window:** from Oct
15 through Nov 10 of an election year, prompts and thresholds cannot change. The only exception is a
verified defect fix, which requires a public notice.

**IX. Backtest before predict.** A forward-looking claim requires a backtest against the historical
corpus. The backtest and its error rates publish with the claim. See `05-HORIZON.md` §0.

**X. The operator is not the instrument.** Brand accounts do not dunk, editorialize, argue, reply in
anger, or @-mention members. Their voice is limited to reporting measurements. Michael's opinions
remain on his personal accounts, clearly separated from the project. If a brand account starts a
fight, it becomes part of the political speech it measures.

**XI. Funding neutrality.** The project accepts no party-aligned or campaign-adjacent money. Grants,
sponsorships, and revenue sources are disclosed on the methodology page. Acceptable revenue includes
data licensing, API tiers, and institutional subscriptions. Engagement-farming ads are prohibited.
Costs remain at hobby scale until revenue exists.

**XII. Verifiability is the brand's anti-spoof armor.** “Anti-spoof armor” means that every public
artifact can be checked against the archive. The site lists the official accounts. Every artifact
includes its day URL and can be reproduced from public data. The standard response to a disputed
screenshot remains: *“If it can't be reproduced from the archive, it isn't ours.”*

**XIII. The privacy floor.** OnScript covers elected officials through their public official
statements. It never covers private citizens, staffers, personal data, or non-public communications.
The project covers members in their official capacity. Its jurisdiction ends at the office.

**XIV. Continuity: the asset must outlive the operator.** The repository is public, the data is
downloadable, the runbook is current, and the license is open. The raw archive receives a quarterly
Internet Archive snapshot. A competent operator must be able to fork and restart OnScript from a
cold start. That continuity is a feature.

**XV. Amendment.** An amendment requires a dated public commit, a build-log entry explaining the
reason, and a version bump in this header. Articles II, III, IV, and XIII are load-bearing. Here,
“load-bearing” means that changing any of them creates a different project and should be treated as
founding one. When another document conflicts with this one, this document controls.

**XVI. The instrument is verified, not trusted.** Health is measured from the system's records. A
green exit code or CI status is insufficient. A run is green only when its own record confirms
`verifier_passed`, `fallback`, and `degraded` state. A fail-closed gate and its required key ship
together. A live run in the target environment must prove them before the implementing session ends.
A gate without its key is an operator-created outage.

Failure notifications belong at the outermost layer so a scheduled workflow reports failures that
occur before `main()`. A liveness probe observes advancing data rather than its own process. A number
enters the project record only with its estimator, units, window, denominator, and a rerunnable
reproduction script. An unreproducible number is prose rather than evidence. Every work session ends
by comparing expectation with observation across site freshness, streak state, flags, and tests.
Discrepancies are filed instead of assumed away.

**XVII. The instrument describes itself truthfully.** Every published attestation about the
instrument (its fingerprint, method versions, temporal labels, and operating status) derives from
the live authority it describes, is computed once by the stage that owns it, and is inherited
unchanged by every downstream artifact of that cycle. A registry of such facts is verified against
its owners by test, never against its own copy. A withdrawn metric leaves every canonical surface,
machine-readable as well as rendered. A state label (today, current, degraded, delayed) reflects
the measured state under the published ladder. When the instrument cannot say something true about
itself, it says nothing there. Engineering rules implementing this article live in
docs/37-ENGINEERING-DISCIPLINE.md, which binds every implementation session.

*Ratified 2026-07-11. Amended 2026-07-17 to add Article XVI after the salt outage and provenance-seam
findings. Amended 2026-07-28 to add Article XVII after three external review rounds each found the
published self-description trailing the live instrument. Check decisions against this document
instead of deriving the rules again.*
