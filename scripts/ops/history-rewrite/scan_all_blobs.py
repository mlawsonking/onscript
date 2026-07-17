"""Scan EVERY blob in the object database for any case-insensitive occurrence of the gated names.
Run before the rewrite (enumerates every literal form -> completes replacements.txt) and after
(expect zero). Displays hashes/counts only, never the strings."""
import subprocess, sys, re, hashlib
from collections import OrderedDict

# The spans come from replacements.txt (already extracted), not from canon.
spans = []
for line in open("scratchpad/replacements.txt", encoding="utf-8"):
    lit = line.split("==>")[0]
    if lit and lit.lower() not in [s.lower() for s in spans]:
        spans.append(lit)
print(f"scanning for {len(spans)} name(s), case-insensitive, across every blob")

pats = [re.compile(re.escape(s).replace(r"\ ", r"[\s]+").encode(), re.IGNORECASE) for s in spans]

p = subprocess.Popen(["git", "cat-file", "--batch-all-objects", "--batch"],
                     stdout=subprocess.PIPE)
forms = OrderedDict()
blob_hits = 0
blobs = 0
while True:
    header = p.stdout.readline()
    if not header:
        break
    parts = header.split()
    if len(parts) != 3:
        continue
    sha, otype, size = parts[0].decode(), parts[1].decode(), int(parts[2])
    body = p.stdout.read(size)
    p.stdout.read(1)          # trailing LF
    if otype != "blob":
        continue
    blobs += 1
    hit = False
    for pat in pats:
        for m in pat.finditer(body):
            forms[m.group(0)] = None
            hit = True
    if hit:
        blob_hits += 1

print(f"blobs scanned: {blobs}")
print(f"blobs containing a name: {blob_hits}")
print(f"distinct literal forms found: {len(forms)}")
for f in forms:
    print(f"  form sha8={hashlib.sha256(f).hexdigest()[:8]} chars={len(f)}")
