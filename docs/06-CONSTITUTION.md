# 06-CONSTITUTION — the invariants (v1, 2026-07-11)

> **What this is.** The rules that outlive every phase, session, model, and mood. Everything
> here already exists scattered across the vision, research, gameplan, and horizon docs — this
> consolidates it into one canonical, numbered document that every future decision (Claude's or
> Michael's) is checked against. When a proposed action conflicts with an article, the action
> loses. Amendment rules are Article XV; four articles are effectively unamendable.

---

**I. Compression, not parody.** OnScript publishes what was actually said, compressed, with
receipts. The comedy is emergent from real source material; it is never authored. The system
never jokes — the data is the joke.

**II. Citation or silence.** Nothing publishes unverified: every quoted fragment a verbatim
substring, every claim ≥3 distinct members, every digit code-computed. A claim that fails the
verifier is dropped and logged — never patched, never hand-edited. Errors that ship are
corrected by **public correction posts and a public corrections log — never silent edits.**

**III. The two lanes.** Lane 1 (the symmetric press-release corpus) is the *only* input to any
cross-party number. Lane 2 (Bluesky, floor, and any future asymmetric source) enriches and
cites but is machine-blocked from comparative metrics — enforced in code and covered by tests,
not by intention.

**IV. Symmetric instrument, asymmetric findings.** Identical pipeline, prompts, thresholds,
and award rules for both parties, hash-audited nightly in public. Findings fall where they
fall. Instrument skew is an incident; finding skew is journalism. Forced balance is itself a
bias and is prohibited.

**V. The streak is sacred.** The system degrades before it skips: budget governor, fallback
calls, quiet-day lines, degraded-mode banners — but it publishes every day. A missed day is an
incident with a public postmortem in the build log, not a shrug.

**VI. Raw-first, append-only, rebuildable.** Every source statement is stored immutably before
processing. Every derived artifact is a pure function of the raw archive, reproducible by
anyone (`rebuild.py` is a public promise, not a dev tool). Schemas are versioned; breaking
changes require a migration script; the ledger epoch is always disclosed.

**VII. Numbers come from code.** Models copy numbers; they never compute them. The
digit-whitelist check stands forever, through every model swap and every feature.

**VIII. Prompts are public.** The live prompt text and its full git history render on the
methodology page. Every prompt change is a dated public diff with a rationale line. **Freeze
window:** no prompt or threshold changes from Oct 15 through Nov 10 of an election year except
verified-defect fixes, which get a public notice.

**IX. Backtest before predict.** No forward-looking claim ships without its backtest against
the historical corpus, published alongside it with error rates. Speculation is what everyone
else sells (see `05-HORIZON.md` §0).

**X. The operator is not the instrument.** The brand accounts never dunk, never editorialize,
never argue, never reply in anger, never @-mention members. The voice's only register is the
seismograph. Michael's personal opinions live on Michael's personal accounts, visibly separate.
The moment the instrument picks a fight, it becomes the thing it measures.

**XI. Funding neutrality.** No party-aligned or campaign-adjacent money, ever, at any price.
Any grant, sponsorship, or revenue source is disclosed on the methodology page. Acceptable
revenue is neutrality-compatible (data licensing, API tiers, institutional subscriptions) —
never engagement-farming ads. Until revenue exists, costs stay hobby-scale by design.

**XII. Verifiability is the brand's anti-spoof armor.** The site lists the real accounts.
Every artifact carries its day-URL and is reproducible from the public archive. The standing
answer to any screenshot dispute: *"If it can't be reproduced from the archive, it isn't
ours."*

**XIII. The privacy floor.** Elected officials' public official statements only. Never private
citizens, never staffers, never personal data, never non-public communications — regardless of
how interesting. Members are covered *as officials*; the instrument's jurisdiction ends at the
office.

**XIV. Continuity — the asset must outlive the operator.** Repo public, data downloadable,
runbook current, license open. Quarterly snapshot of the raw archive to the Internet Archive.
Anyone competent could fork OnScript alive from a cold start; that is a feature, not a risk.

**XV. Amendment.** Amending this document requires: a dated public commit, a build-log entry
with rationale, and a version bump in this header. **Articles II, III, IV, and XIII are
load-bearing: amending them makes this a different project and should be treated as founding a
new one.** When any other doc conflicts with this one, this one wins.

---

*Ratified 2026-07-11. Check decisions against it; don't re-derive it.*
