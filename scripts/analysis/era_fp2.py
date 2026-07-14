"""Era Fingerprints v2: same log-odds distinctiveness, + a procedural-token stoplist so the
front-page artifact isn't topped by boilerplate ('of the united states', 'a member of the senate').
Writes data/derived/era_fingerprints.json (committed artifact the Archive can render)."""
import json, sys, math, time
from collections import defaultdict
sys.path.insert(0, r"C:\Users\bobdo\projects\polispeak")
from pipeline import util
LEDGER=r"X:\onscript-data\state\ledger.json"
OUT=r"C:\Users\bobdo\projects\polispeak\data\derived\era_fingerprints.json"
# procedural / function tokens: drop any phrase made ENTIRELY of these (keeps content phrases)
STOP=set("of the a an u s united states member members senate house representatives congress "
         "to and in for on that this with as at by is are was were be been being will would has have had "
         "i we our my me his her their they it he she you your from or not but which who what when act".split())
t0=time.time()
print("[EF2] loading merged ledger …", flush=True)
ledger=json.load(open(LEDGER,encoding="utf-8"))
print(f"[EF2] {len(ledger):,} phrases in {time.time()-t0:.0f}s", flush=True)
cnt=defaultdict(lambda: defaultdict(int)); tot=defaultdict(int)
for ng,e in ledger.items():
    pk=max((max(d.get("D",0),d.get("R",0)) for d in e["daily"].values()), default=0)
    if pk<15: continue
    for day,d in e["daily"].items():
        if day<"2013-01-01": continue
        cg=util.congress_for_date(day)
        for P in ("D","R"):
            c=d.get(P,0)
            if c: cnt[(cg,P)][ng]+=c; tot[(cg,P)]+=c
print(f"[EF2] bucketed {time.time()-t0:.0f}s", flush=True)
def is_proc(w): return all(t in STOP for t in w.split())
def collapse(rows,k=10):
    kept=[]
    for sc,c,ng in rows:
        if not any(f" {ng} " in f" {k2} " for _,_,k2 in kept): kept.append((sc,c,ng))
        if len(kept)>=k: break
    return kept
CONG={113:"2013-14",114:"2015-16",115:"2017-18",116:"2019-20",117:"2021-22",118:"2023-24",119:"2025-26"}
out={}
for cg in range(113,120):
    for P in ("D","R"):
        here=cnt.get((cg,P),{}); n_here=tot.get((cg,P),0)
        if n_here<1000: continue
        rest=defaultdict(int); n_rest=0
        for (c2,p2),d2 in cnt.items():
            if p2==P and c2!=cg:
                n_rest+=tot[(c2,p2)]
                for w,v in d2.items(): rest[w]+=v
        rows=[]
        for w,y in here.items():
            if y<20 or is_proc(w): continue     # <-- stoplist filter
            score=math.log((y+0.5)/(n_here+0.5))-math.log((rest.get(w,0)+0.5)/(n_rest+0.5))
            rows.append((score,y,w))
        rows.sort(reverse=True)
        top=[{"phrase":w,"uses":c} for sc,c,w in collapse(rows)]
        out[f"{cg}-{P}"]={"congress":cg,"years":CONG[cg],"party":P,"top":top}
        print(f"\n=== {cg}th ({CONG[cg]}) · {P} ===")
        for t in top: print(f"    {t['uses']:>5}x  \"{t['phrase']}\"")
json.dump(out, open(OUT,"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"\n[EF2] wrote {OUT} ({len(out)} era-party fingerprints) in {time.time()-t0:.0f}s")
