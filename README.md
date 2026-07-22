# OnScript

OnScript is a live, daily measurement of the exact language U.S. members of Congress publish.
Every complete day is compressed into one composite voice per party, mechanically verified against
member statements, published with receipts, and posted by two automated Bluesky accounts. The same
pipeline, prompts, and thresholds run for both parties.

- Live instrument: [onscript.news](https://onscript.news)
- Methodology and nightly audit: [onscript.news/methodology.html](https://onscript.news/methodology.html)
- Rolling raw/state release: [data-latest](https://github.com/mlawsonking/onscript/releases/tag/data-latest)
- Governing invariants: [`docs/06-CONSTITUTION.md`](docs/06-CONSTITUTION.md)
- Build and operating record: [`docs/04-BUILDLOG.md`](docs/04-BUILDLOG.md) and
  [`docs/07-OPERATIONS.md`](docs/07-OPERATIONS.md)

## Production rhythm

GitHub Actions is the runtime. Two scheduled passes let a late upstream day recover without skipping:

- **RUN A — collect**, at 09:30Z and 19:30Z: mirror the press-release corpus, normalize Lane 1,
  update the deterministic phrase ledger, submit/cache extraction work, redact the published view,
  and refresh `data-latest`.
- **RUN B — assemble**, at 11:30Z and 21:30Z: select the oldest ready day, cluster and distill,
  run the blocking verifier and symmetry audit, render the static site, post both party threads
  atomically when enabled, persist state, and commit the derived/site output for Vercel.

The exact scheduler may start late. Health is read from manifests and advancing data, never from a
green workflow badge alone. See `docs/07-OPERATIONS.md` for health thresholds and incident playbooks.

## State and reproducibility

- `data/raw/` — immutable source mirror; published in `raw.tar.gz` on `data-latest`
- `data/state/` — normalized statements, extraction cache, and phrase ledger; published in
  `state.tar.gz` on `data-latest`
- `data/derived/` — small committed manifests and public JSON
- `site/public/` — committed static site generated from the derived record

Use Python 3.11+. On the Windows operator machine the configured interpreter is
`C:\ProgramData\miniconda3\python.exe`.

```powershell
# Restore raw/state by downloading and extracting both data-latest assets first, then:
& 'C:\ProgramData\miniconda3\python.exe' pipeline/rebuild.py

# A faster single rebuild without the second determinism pass:
& 'C:\ProgramData\miniconda3\python.exe' pipeline/rebuild.py --once

# Verify that release files contain no admitted private-name form:
& 'C:\ProgramData\miniconda3\python.exe' -m pipeline.redact --check data/raw data/state data/reference

# Full stdlib test suite:
& 'C:\ProgramData\miniconda3\python.exe' tests/run_tests.py
```

`pipeline/rebuild.py` runs from the raw mirror and proves deterministic output. Published release
assets are a privacy-redacted view; the pristine append-only operator archive is not rewritten.

## Operational controls

- `POSTING_ENABLED` is the outbound Bluesky kill switch. Off means no authentication or posting.
- `LLM_VOICE_ENABLED` is the metered composite-voice switch. Off selects the deterministic fallback.
- The code-side monthly voice ceiling is below the separate Console hard cap.
- A verifier failure drops the claim or selects a deterministic fallback; it is never hand-patched.
- Source outages skip and log; asymmetric or partial posting triggers the dead-man path.

Do not run `pipeline/post_bluesky.py` to preview a thread: even a gated local run writes post
manifests. Import and call the pure `build_thread()` helper instead.

## Configuration and secrets

Runtime secrets live only in GitHub Actions. Their names are documented in the workflow files;
values, the ntfy topic, credentials, and app passwords never belong in this repository. The public
repository and downloadable data are sufficient to reproduce the measurement without those secrets;
posting and the optional model voice are separate outbound capabilities.
