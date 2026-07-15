"""The Search (docs/12-SEARCH-PROGRAM.md) — pre-registered hypothesis sweep over the archive.

Deterministic, stdlib-only, $0. No LLM in the measurement path; ANTHROPIC_API_KEY never set locally.
Every metric here ships with a kill-fixture test (a synthetic corpus with a known injected confound
the metric must NOT flag) — see tests/test_search_metrics.py. Findings land in docs/13-SEARCH-LEDGER.md.
"""
