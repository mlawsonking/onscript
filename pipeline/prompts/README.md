# Prompts — the instrument, versioned in public (§5.3)

These are the *only* LLM prompts in the v1 daily pipeline (gameplan §6.2). They live in
the public repo and the Methodology page renders their live text **and their git history**.

**Treat prompt text as schema.** A change to any prompt is a versioned, committed, publicly
diffable event with a dated rationale line — nobody can claim the instrument was quietly
tuned against a party, because the tuning log *is* the page.

- Files are named `P<n>_<name>.v<major>.<minor>.txt`. Bump the version on any wording change;
  keep old versions in git history (never rewrite them).
- `{party}` is the ONLY variable that differs between the two parties. Same text, same order,
  same thresholds for D and R — this is neutrality-by-construction (§5.1–5.2).
- `SYSTEM:` and (where present) a `---USER---` delimiter separate the two message roles.
- Template variables filled by code: `{party}`, `{day}`, `{taxonomy_v1}`,
  `{code_computed_stats_json}`, `{talking_points_json}`.

| Prompt | Model (routing §6.1) | When |
|---|---|---|
| P1 extraction | Haiku (batch) | once per new statement |
| P2 Daily Line | Sonnet (batch; fallback direct) | once per party per day |
| P3 quiet day  | Haiku | only if new Lane-1 statements < 15 |

The verifier (§6.3, `pipeline/verify.py`) is deterministic code, generator-agnostic: it
checks the *output text* regardless of which model (or subscription-scripted `claude -p`,
for one-time backfill chapters, §1.3) produced it. The generator is a commodity; the
verifier is the product.
