"""The Deep Archive (docs/15-DEEP-ARCHIVE-PROGRAM.md) — the historical Congressional Record track and
its audited cross-check lanes.

NON-INTERFERENCE CONTRACT (docs/15 §1), enforced by construction:
  * NEW code only. This package imports the daily pipeline and the Search READ-ONLY (additive helpers);
    it never edits `pipeline/phrases.py`, `normalize.py`, any RUN A/RUN B module, or `pipeline/search/`.
  * Zero GitHub Actions. Ingest is one-time local capex via resumable, throttled background crawls.
  * Storage on X: only (the onscript-data root via the state junction). In-repo: small derived JSON +
    reference tables + docs.
  * Two binding laws live here in CODE: GENRE ISOLATION (`lanes.lane_of`) and, downstream, the
    CALIBRATION LAW (no CREC-only pre-2013 claim without 2013-2026 overlap concordance, SD.8).
"""
