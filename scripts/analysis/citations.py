"""Citation back-join: attach >=3 real (member, date, URL) citations to the recorded flagship
findings, pulled from the raw congress-press files on X:. Deterministic + self-verifying: a citation
counts only if the phrase is a verbatim substring of the release text AND the member's party matches.
This is the project's citation-or-silence rule applied to the analysis findings."""
import json, re, sys, os
from datetime import date
RAW=r"X:\onscript-data\raw\congress-press"
OUT=r"C:\Users\bobdo\projects\polispeak\data\derived\citations.json"
_ws=re.compile(r"\s+")
def norm(t): return _ws.sub(" ", (t or "").lower()).strip()

# (finding, phrase, party_letter, [month files to scan])
TARGETS=[
 ("biggest-unison: AHCA (R, 184, 2017-05-04)", "american health care act", "R", ["2017-05"]),
 ("biggest-unison: TCJA (R, 166, 2017-11-16)", "tax cuts and jobs act", "R", ["2017-11"]),
 ("biggest-unison: DACA (D, 153, 2017-09-05)", "deferred action for childhood arrivals", "D", ["2017-09"]),
 ("biggest-unison: HEROES Act (D, 151, 2020-05-15)", "the heroes act", "D", ["2020-05"]),
 ("forbidden-lexicon-R: by an illegal immigrant", "by an illegal immigrant", "R", ["2015-07"]),
 ("forbidden-lexicon-D: medicare the power to negotiate", "medicare the power to negotiate", "D", ["2019-09","2019-10","2019-12"]),
 ("forbidden-lexicon-D: pre-existing conditions framing", "discriminate against people with pre-existing", "D", ["2017-01","2017-02"]),
 ("tick-tock: one big beautiful bill (R, 2025-07-03)", "one big beautiful bill", "R", ["2025-07"]),
]
PARTY={"R":"Republican","D":"Democrat"}

result={}
for label,phrase,pl,months in TARGETS:
    np=norm(phrase); cites=[]; seen=set(); scanned=0
    for m in months:
        fp=os.path.join(RAW, m+".jsonl")
        if not os.path.exists(fp): continue
        with open(fp, encoding="utf-8") as f:
            for line in f:
                try: r=json.loads(line)
                except: continue
                scanned+=1
                mem=r.get("member") or {}
                if not (mem.get("party","")).startswith(PARTY[pl][:3]): continue
                if np in norm(r.get("text","")):
                    u=r.get("url","")
                    if u in seen: continue
                    seen.add(u)
                    cites.append({"member": mem.get("name"), "bioguide": mem.get("bioguide_id"),
                                  "party": mem.get("party"), "state": mem.get("state"),
                                  "date": r.get("date"), "url": u, "title": r.get("title")})
    cites.sort(key=lambda c: c["date"] or "")
    result[label]={"phrase": phrase, "party": pl, "n_citations": len(cites),
                   "meets_min_3": len(cites)>=3, "scanned": scanned, "citations": cites[:6]}
    flag="OK " if len(cites)>=3 else "!! "
    print(f"{flag}{label}")
    print(f"     \"{phrase}\" -> {len(cites)} real {PARTY[pl]} citations (scanned {scanned})")
    for c in cites[:3]:
        print(f"       {c['date']}  {c['member']} ({c['state']})  {c['url']}")
    print()

json.dump(result, open(OUT,"w",encoding="utf-8"), indent=1, ensure_ascii=False)
ok=sum(1 for v in result.values() if v["meets_min_3"])
print(f"WROTE {OUT}")
print(f"{ok}/{len(TARGETS)} findings now have >=3 real citations.")
