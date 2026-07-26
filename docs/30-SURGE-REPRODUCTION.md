# Surge ranking reproduction

Run this command from the repository root:

```text
python scripts/rank_surges.py tests/fixtures/w8_rankings.json
```

The command writes one deterministic JSON object to standard output. It does not write repository
files. The fixture uses distinct offices as the binomial successes and eligible offices as the
trials. The baseline is the prior 28 observed days with Jeffreys smoothing. Benjamini-Hochberg
q-values are computed across every phrase-party test for the target day.

The export keeps five separate rankings: most repeated, largest surge, most skewed, fastest spread,
and widest family spread. It has no composite score. Repeating the command against the same input
must produce identical bytes.
