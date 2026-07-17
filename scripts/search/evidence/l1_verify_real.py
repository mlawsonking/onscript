"""L1 verification on the REAL mirror — the fix is not done until it is proven on real data.

Proves: (1) iter_statements now carries date_source/instrument for all 688,839 records;
(2) the lane filter reproduces the measured lane counts exactly; (3) the filtered streams are
lane_of-clean, i.e. the guard accepts what isolation produces and refuses the union.
"""
import sys, collections
sys.path.insert(0, ".")
from pipeline.search import harness as H
from pipeline.search import provenance as P

print("=== 1. date_source survives iter_statements (full corpus) ===")
src = collections.Counter()
inst = collections.Counter()
seam_by_inst = {}
n = 0
for r in H.iter_statements(with_text=False):
    n += 1
    src[r["date_source"]] += 1
    inst[r["instrument"]] += 1
    lo, hi = seam_by_inst.get(r["instrument"], ("9999", "0000"))
    seam_by_inst[r["instrument"]] = (min(lo, r["date"]), max(hi, r["date"]))
print(f"  streamed {n:,} records")
for k, v in src.most_common():
    print(f"    date_source={str(k):10s} {v:8,}")
for k, v in inst.most_common():
    lo, hi = seam_by_inst[k]
    print(f"    instrument={str(k):11s} {v:8,}   {lo} -> {hi}")

EXPECT = {"legacy": 485_948, "scraper": 200_033, "page_html": 2_839}
ok = all(src[k] == v for k, v in EXPECT.items())
print(f"  matches measured ground truth: {ok}")
assert ok, f"lane counts drifted: {dict(src)}"

print("\n=== 2. the lane filter isolates (real corpus) ===")
pro = sum(1 for _ in H.iter_statements(with_text=False, lane="propublica"))
scr = sum(1 for _ in H.iter_statements(with_text=False, lane="scraped"))
ph = sum(1 for _ in H.iter_statements(with_text=False, lane="page_html"))
print(f"  lane='propublica' -> {pro:8,}   (expect 485,948)")
print(f"  lane='scraped'    -> {scr:8,}   (expect 202,872 = scraper + page_html)")
print(f"  lane='page_html'  -> {ph:8,}   (expect 2,839)")
assert pro == 485_948 and scr == 200_033 + 2_839 and ph == 2_839
print("  isolation exact.")

print("\n=== 3. the guard accepts an isolated stream and refuses the union ===")
import itertools
pro_rows = list(itertools.islice(H.iter_statements(with_text=False, lane="propublica"), 5000))
scr_rows = list(itertools.islice(H.iter_statements(with_text=False, lane="scraped"), 5000))
print(f"  lane_of(propublica sample) = {P.lane_of(pro_rows)!r}")
print(f"  lane_of(scraped sample)    = {P.lane_of(scr_rows)!r}")
try:
    P.lane_of(pro_rows + scr_rows)
    raise AssertionError("REFUSAL FAILED — the union was accepted")
except P.LaneIsolationError as e:
    print(f"  union REFUSED: {str(e)[:88]}...")

print("\n=== 4. the seam is real in the isolated data ===")
pro_dates = [r["date"] for r in H.iter_statements(with_text=False, lane="propublica")]
print(f"  propublica last day: {max(pro_dates)}   (the seam: {P.SEAM})")
assert max(pro_dates) == P.SEAM, "the legacy lane no longer ends on the seam"
print(f"  spans_seam(propublica lane alone) = {P.spans_seam(pro_dates)}  <- False: it dies ON the seam")

print("\nL1 VERIFIED ON REAL DATA.")
