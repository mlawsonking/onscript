# Release provenance and environment

## Runtime pin

Production uses CPython 3.12.10. That interpreter uses Unicode Character Database 15.0.0. The
deterministic runtime has no third-party packages. `requirements.lock` records that empty dependency
set and requires exact versions and artifact hashes for any future addition.

GitHub Actions are referenced by full commit SHA. Version comments are review hints only. Workflow
permissions are declared at workflow level and limited to the access each job needs.

## Verify release assets

From a clean clone, download the rolling assets and their sidecars:

```text
gh release download data-latest --pattern "state.tar.gz*" --pattern "raw.tar.gz*" --dir release-assets
python -m pipeline.release_provenance verify release-assets/state.tar.gz release-assets/raw.tar.gz
```

Restore through the archive allowlist into the clone:

```text
python -m pipeline.archive_restore release-assets --checkout .
```

The restore command rejects absolute paths, parent traversal, links, special files, and paths outside
the runtime allowlist before copying any file into the checkout.

## Reproduce a committed subset

This command needs no network and writes no repository file:

```text
python scripts/reproduce_subset.py
```

It runs the committed surge and gold-set fixtures twice. Success requires byte-identical canonical
JSON and matching SHA-256 values.

The full raw-mirror reproduction remains:

```text
python pipeline/rebuild.py
```

That command requires the verified raw release asset restored above. It rebuilds twice and compares
the derived-tree hashes.
