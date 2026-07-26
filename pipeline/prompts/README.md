# Prompts: versioned public inputs (§5.3)

These are the *only* LLM prompts in the v1 daily pipeline (gameplan §6.2). They live in
the public repo and the Methodology page renders their live text **and their git history**.

Treat prompt text as schema. Every prompt change is versioned, committed, and publicly diffable. It
also needs a dated rationale. The public history shows whether a prompt was tuned against a party.

- Files are named `P<n>_<name>.v<major>.<minor>.txt`. Bump the version on any wording change;
  keep old versions in git history (never rewrite them).
- `{party}` is the only variable that differs between the two parties. D and R use the same text,
  order, and thresholds (§5.1–5.2).
- `SYSTEM:` and (where present) a `---USER---` delimiter separate the two message roles.
- Template variables filled by code: `{party}`, `{day}`, `{taxonomy_v1}`,
  `{code_computed_stats_json}`, `{talking_points_json}`.

| Prompt | Model (routing §6.1) | When |
|---|---|---|
| P1 extraction | Haiku (batch) | once per new statement |
| P2 Daily Line | Sonnet (batch; fallback direct) | once per party per day |
| P3 quiet day  | Haiku | only if new Lane-1 statements < 15 |

The verifier (§6.3, `pipeline/verify.py`) is deterministic and does not depend on the generator. It
checks the output from any model, including subscription-scripted `claude -p` for one-time backfill
chapters (§1.3). Publication depends on verification, not on which generator produced the text.

Dark review candidates: `P2_daily_line.v1.4.txt` and `P3_quiet_day.v1.2.txt`. They are not referenced
by `pipeline/llm.py`. Activation requires Michael's prompt review and a separate release commit.
