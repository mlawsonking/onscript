"""Extend the citation back-join to the Archive front page: for each era-party fingerprint, attach
>=3 real (member, date, URL) citations to its top-2 distinctive phrases, scanned from that era's raw
month-files (early-exit once satisfied). Writes data/derived/citations_era.json."""
import json, re, os
RAW=r"X:\onscript-data\raw\congress-press"
FP=r"C:\Users\bobdo\projects\polispeak\data\derived\era_fingerprints.json"
OUT=r"C:\Users\bobdo\projects\polispeak\data\derived\citations_era.json"
_ws=re.compile(r"\s+")
def norm(t): return _ws.sub(" ", (t or "").lower()).strip()
PARTY={"R":"Republican","D":"Democrat"}
fp=json.load(open(FP,encoding="utf-8"))

def era_months(years):  # "2013-14" -> ['2013-01'..'2014-12']
    a,b=years.split("-"); y0=int(a); y1=int(a[:2]+b)
    return [f"{y}-{m:02d}" for y in range(y0,y1+1) for m in range(1,13)]

result={}
for key,rec in fp.items():
    pl=rec["party"]; targets=[t["phrase"] for t in rec["top"][:2]]
    if not targets: continue
    need={t:[] for t in targets}; nt={t:norm(t) for t in targets}
    for m in era_months(rec["years"]):
        if all(len(v)>=3 for v in need.values()): break   # early exit
        fpath=os.path.join(RAW,m+".jsonl")
        if not os.path.exists(fpath): continue
        with open(fpath,encoding="utf-8") as f:
            for line in f:
                try: r=json.loads(line)
                except: continue
                mem=r.get("member") or {}
                if not (mem.get("party","")).startswith(PARTY[pl][:3]): continue
                tx=norm(r.get("text",""))
                for t in targets:
                    if len(need[t])>=5: continue
                    if nt[t] in tx and r.get("url") not in {c["url"] for c in need[t]}:
                        need[t].append({"member":mem.get("name"),"date":r.get("date"),
                                        "url":r.get("url"),"state":mem.get("state")})
    result[key]={"congress":rec["congress"],"years":rec["years"],"party":pl,
                 "phrases":{t:{"n":len(need[t]),"citations":need[t][:3]} for t in targets}}
    ok=sum(1 for t in targets if len(need[t])>=3)
    print(f"{key}: {ok}/{len(targets)} phrases cited (>=3)  | " +
          " ; ".join(f'\"{t}\" x{len(need[t])}' for t in targets))

json.dump(result,open(OUT,"w",encoding="utf-8"),indent=1,ensure_ascii=False)
tot=sum(len(v["phrases"]) for v in result.values())
ok=sum(1 for v in result.values() for t in v["phrases"].values() if t["n"]>=3)
print(f"\nWROTE {OUT}: {ok}/{tot} era phrases now have >=3 real citations.")
