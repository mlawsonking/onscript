"""Extract the Article-XIII-gated name strings from pre-fdcda1f history and build the
git-filter-repo replacements file. Displays NO name strings — counts and hashes only.

Method: pull every blob fdcda1f changed/deleted at its parent revision, tokenize, and slide
2..4-gram windows through pipeline.privacy.is_suppressed (the live salted-HMAC gate). The minimal
tripping spans ARE the gated names, by construction — the same matcher that suppresses them live
identifies them here. Then collect every literal case-variant of those spans present in any
historical blob, and map each to canon's redaction labels.
"""
import subprocess, sys, json, re, hashlib
from collections import OrderedDict

sys.path.insert(0, ".")
from pipeline import privacy

privacy.load()

BAD = "fdcda1f"

def git(*args) -> bytes:
    return subprocess.run(["git"] + list(args), capture_output=True).stdout

# Every path fdcda1f touched, read at the PARENT (the last revision holding the names).
paths = git("diff-tree", "--no-commit-id", "--name-only", "-r", BAD).decode().split()
blobs = {}
for p in paths:
    b = git("show", f"{BAD}^:{p}")
    if b:
        blobs[p] = b

print(f"blobs read at {BAD}^: {len(blobs)} of {len(paths)} paths")

# Find minimal suppressed token spans across all historical content.
tok_re = re.compile(r"[A-Za-z][A-Za-z''-]+")
spans = OrderedDict()          # lowercase span -> None (ordered set)
for p, b in blobs.items():
    text = b.decode("utf-8", errors="replace")
    toks = tok_re.findall(text)
    low = [t.lower() for t in toks]
    for n in (2, 3, 4):
        for i in range(len(low) - n + 1):
            span = " ".join(low[i:i + n])
            if privacy.is_suppressed(span):
                spans[span] = None

# Minimality: drop any span that strictly contains a shorter tripping span.
minimal = []
for s in spans:
    if not any(t != s and t in s for t in spans):
        minimal.append(s)
print(f"suppressed spans found: {len(spans)} total, {len(minimal)} minimal")
for s in minimal:
    print(f"  span sha8={hashlib.sha256(s.encode()).hexdigest()[:8]} tokens={len(s.split())} chars={len(s)}")

# Assign canon labels: A is the name inside the "the killing of ..." phrase (per CLAUDE.md).
label = {}
joined_all = "\n".join(b.decode("utf-8", errors="replace").lower() for b in blobs.values())
for s in minimal:
    if f"the killing of {s}" in joined_all:
        label[s] = "<private-individual-A>"
for s in minimal:
    if s not in label:
        label[s] = "<private-individual-B>" if "<private-individual-A>" in label.values() else "<private-individual-A>"

# Collect literal case-variants of each minimal span across all historical blobs.
variants = OrderedDict()       # literal bytes -> replacement bytes
for s in minimal:
    pat = re.compile(re.escape(s).replace(r"\ ", r"[\s]+"), re.IGNORECASE)
    for p, b in blobs.items():
        for m in pat.finditer(b.decode("utf-8", errors="replace")):
            variants[m.group(0)] = label[s]

print(f"\nliteral variants across history: {len(variants)}")
for v, r in variants.items():
    print(f"  variant sha8={hashlib.sha256(v.encode()).hexdigest()[:8]} chars={len(v)} -> {r}")

with open("scratchpad/replacements.txt", "w", encoding="utf-8") as f:
    for v, r in variants.items():
        f.write(f"{v}==>{r}\n")
print("\nwrote scratchpad/replacements.txt")

# Safety: does the CURRENT tracked tree contain any variant? (Expect zero -> tree-hash invariance.)
tracked = git("ls-files", "-z").decode().split("\0")
hits = 0
for p in tracked:
    if not p:
        continue
    try:
        data = open(p, "rb").read().decode("utf-8", errors="replace")
    except OSError:
        continue
    for v in variants:
        if v.lower() in data.lower():
            hits += 1
            print(f"  CURRENT-TREE HIT: {p}")
print(f"current tracked tree hits: {hits} (0 => HEAD tree must be byte-identical after rewrite)")

# How many historical commits carry at least one variant?
carriers = set()
for v in list(variants)[:1]:
    pass
log = git("rev-list", "--all").decode().split()
print(f"total commits (all refs): {len(log)}")
