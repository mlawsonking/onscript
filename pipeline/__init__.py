"""OnScript pipeline (repo codename: polispeak).

The daily streak machine: ingest -> distill -> verify -> publish -> post -> audit.
Built to gameplan docs/03-GAMEPLAN.md §1. Stdlib-only in the deterministic core so it
runs identically on the Ubuntu Actions runner and a dev box.
"""

SCHEMA_VERSION = 1
