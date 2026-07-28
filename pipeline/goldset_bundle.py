"""Render annotator packets from a sealed gold-set sample.

Each packet is a self-contained HTML page (no external assets, works offline) plus a
machine-readable CSV answer sheet keyed by candidate ID. Item order is randomized per
annotator with a recorded seed. Every shown phrase and sentence passes through the
hardened label path so no admitted private-person form is written into a packet.

The packet shows exactly the ruled context: the candidate phrase, its full sentence, one
sentence before and after, the release title, the office (party, state, chamber), the date,
and, for items with a support set, the other offices carrying the same phrase. It never
shows the predicted class, rankings, surge scores, publication decisions, or corrections.

Two renderings share that context. ``render_html`` produces a read-only packet paired with a
blank CSV answer sheet. ``render_app`` produces an interactive offline app: the annotator
clicks the class, assigns a family, and sets the optional tasks, with autosave and resume in
the browser and one-click export to the same CSV the intake tool ingests.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import gzip
import html
import io
import json

from . import contracts, post_bluesky, privacy, util


BUNDLE_METHOD_VERSION = "gold-set-bundle-v1"
SUPPORT_CAP = 6
ANSWER_COLUMNS = [
    "candidate_id", "gold_class", "gold_family_id", "phrase_complete",
    "proposition_consistent", "stance", "claim_supported", "notes",
]
CLASS_CHOICES = "message | unknown | nomenclature | procedural | biographical | private"
GOLD_CLASSES = ["message", "unknown", "nomenclature", "procedural",
                "biographical", "private"]
STANCE_CHOICES = ["affirmative", "negated", "mixed"]


def load_statements(path) -> tuple[dict, dict]:
    """Return (by_id, by_day) indexes of the lane-1 statements corpus."""
    by_id: dict[str, dict] = {}
    by_day: dict[str, list[dict]] = defaultdict(list)
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("lane")) != "1":
                continue
            by_id[row.get("id")] = row
            by_day[str(row.get("published_at") or "")[:10]].append(row)
    return by_id, by_day


def _split_with_offsets(text: str) -> list[tuple[int, int, str]]:
    """Split into display sentences, recovering each sentence's character span."""
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for sentence in post_bluesky._sentences(text):
        index = text.find(sentence, cursor)
        if index < 0:
            index = cursor
        spans.append((index, index + len(sentence), sentence))
        cursor = index + len(sentence)
    return spans


def _neighbor_sentences(text: str, occurrence_start: int | None) -> tuple[str, str, str]:
    """Return (before, containing, after) sentences around the occurrence, redacted."""
    spans = _split_with_offsets(text)
    if not spans:
        return "", privacy.redact(text)[0].strip(), ""
    target = 0
    if occurrence_start is not None:
        for position, (start, end, _sentence) in enumerate(spans):
            if start <= occurrence_start < end:
                target = position
                break
    before = spans[target - 1][2] if target > 0 else ""
    sentence = spans[target][2]
    after = spans[target + 1][2] if target + 1 < len(spans) else ""
    return (
        privacy.redact(before)[0].strip(),
        privacy.redact(sentence)[0].strip(),
        privacy.redact(after)[0].strip(),
    )


def _office(statement: dict) -> str:
    member = statement.get("member") or {}
    party = member.get("party") or "?"
    state = member.get("state") or "?"
    chamber = (member.get("chamber") or "").title() or "?"
    return f"{party}-{state} {chamber}".strip()


def _phrase_sentence(statement: dict, phrase: str) -> str:
    """Return the redacted sentence in ``statement`` that first carries ``phrase``."""
    occurrences = contracts.phrase_occurrences(statement, phrase, "support")
    if not occurrences:
        return ""
    _before, sentence, _after = _neighbor_sentences(
        statement.get("text") or "", occurrences[0].get("start_char")
    )
    return sentence


def support_set(candidate: dict, by_day: dict) -> list[dict]:
    """Collect up to ``SUPPORT_CAP`` distinct-family offices carrying the phrase that day.

    One document family counts once. Skipped for redacted phrases, whose raw text is
    intentionally unavailable.
    """
    if candidate.get("phrase_redacted"):
        return []
    phrase = candidate.get("ngram") or ""
    if int(candidate.get("member_count") or 0) < 2:
        return []
    party, day = candidate.get("party"), candidate.get("day")
    wanted = phrase.split()
    seen_families: set = set()
    rows: list[dict] = []
    pool = sorted(by_day.get(day, []), key=lambda statement: statement.get("id") or "")
    for statement in pool:
        if (statement.get("member") or {}).get("party") != party:
            continue
        tokens = [token for token, _s, _e in contracts._token_spans(statement.get("text") or "")]
        if not _contains(tokens, wanted):
            continue
        family = statement.get("joint_group") or statement.get("id")
        if family in seen_families:
            continue
        seen_families.add(family)
        rows.append({
            "office": _office(statement),
            "date": str(statement.get("published_at") or "")[:10],
            "url": statement.get("url") or "",
            "title": privacy.redact(statement.get("title") or "")[0],
            "sentence": _phrase_sentence(statement, phrase),
        })
        if len(rows) >= SUPPORT_CAP:
            break
    return rows


def _contains(tokens: list[str], wanted: list[str]) -> bool:
    width = len(wanted)
    for index in range(len(tokens) - width + 1):
        if tokens[index:index + width] == wanted:
            return True
    return False


def build_item(candidate: dict, by_id: dict, by_day: dict) -> dict:
    """Assemble one rendered item: masked context, office, date, title, and support set."""
    anchor = by_id.get(candidate.get("anchor_statement_id")) or {}
    before, sentence, after = _neighbor_sentences(
        anchor.get("text") or "", candidate.get("occurrence_start_char")
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "phrase": privacy.redact(candidate.get("ngram") or "")[0],
        "before": before,
        "sentence": sentence,
        "after": after,
        "title": privacy.redact(anchor.get("title") or "")[0],
        "office": _office(anchor) if anchor else "unknown",
        "date": str(anchor.get("published_at") or candidate.get("day") or "")[:10],
        "support": support_set(candidate, by_day),
    }


def annotator_order(candidates: list[dict], seed: str, annotator_id: str) -> list[dict]:
    """Return candidates in a per-annotator randomized but deterministic order."""
    return sorted(
        candidates,
        key=lambda row: util.sha256_hex(f"{seed}\n{annotator_id}\n{row['candidate_id']}"),
    )


def _highlight(sentence: str, phrase: str) -> str:
    """HTML-escape the sentence and bold the first case-insensitive phrase match."""
    escaped = html.escape(sentence)
    if not phrase:
        return escaped
    needle = html.escape(phrase)
    lower_hay, lower_needle = escaped.lower(), needle.lower()
    position = lower_hay.find(lower_needle)
    if position < 0:
        return escaped
    end = position + len(needle)
    return f"{escaped[:position]}<mark>{escaped[position:end]}</mark>{escaped[end:]}"


def render_html(items: list[dict], *, annotator_id: str, sample: str, seed: str) -> str:
    """Render the self-contained annotator packet as one offline HTML page."""
    parts: list[str] = []
    parts.append("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    parts.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
    parts.append(f"<title>OnScript gold-set packet: {html.escape(annotator_id)}</title>")
    parts.append("<style>" + _CSS + "</style></head><body>")
    parts.append("<header><h1>OnScript gold-set annotation packet</h1>")
    parts.append(
        f"<p class=\"meta\">Annotator <b>{html.escape(annotator_id)}</b>. "
        f"Sample <b>{html.escape(sample)}</b>. Items <b>{len(items)}</b>. "
        f"Order seed <code>{html.escape(seed)}</code>.</p>")
    parts.append(
        "<p class=\"note\">Read the guide before you start. Record every answer in the CSV "
        "answer sheet, matched by the item ID shown on each card. Judge each phrase in the "
        "context shown. Do not look up the live site.</p>")
    parts.append(
        f"<p class=\"note\">Classes: {html.escape(CLASS_CHOICES)}. "
        "Stance: affirmative | negated | mixed.</p></header>")
    parts.append("<main>")
    for position, item in enumerate(items, 1):
        parts.append("<article class=\"item\">")
        parts.append(
            f"<div class=\"idline\"><span class=\"num\">{position}</span>"
            f"<code class=\"cid\">{html.escape(item['candidate_id'])}</code></div>")
        parts.append(
            f"<div class=\"phrase\">Candidate phrase: <b>{html.escape(item['phrase'])}</b></div>")
        parts.append("<div class=\"context\">")
        if item["before"]:
            parts.append(f"<p class=\"ctx before\">{html.escape(item['before'])}</p>")
        parts.append(f"<p class=\"ctx sentence\">{_highlight(item['sentence'], item['phrase'])}</p>")
        if item["after"]:
            parts.append(f"<p class=\"ctx after\">{html.escape(item['after'])}</p>")
        parts.append("</div>")
        parts.append(
            f"<div class=\"src\">{html.escape(item['office'])} &middot; "
            f"{html.escape(item['date'])} &middot; "
            f"<span class=\"title\">{html.escape(item['title'])}</span></div>")
        if item["support"]:
            parts.append("<details class=\"support\"><summary>Support set "
                         f"({len(item['support'])} offices carrying this phrase)</summary><ul>")
            for row in item["support"]:
                parts.append(
                    "<li><span class=\"soffice\">" + html.escape(row["office"]) + "</span> "
                    "<span class=\"sdate\">" + html.escape(row["date"]) + "</span>"
                    "<div class=\"ssent\">" + html.escape(row["sentence"]) + "</div></li>")
            parts.append("</ul></details>")
        parts.append("</article>")
    parts.append("</main></body></html>")
    return "".join(parts)


def render_csv(items: list[dict]) -> str:
    """Render the empty answer sheet: one row per item, answer columns blank."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(ANSWER_COLUMNS)
    for item in items:
        writer.writerow([item["candidate_id"]] + [""] * (len(ANSWER_COLUMNS) - 1))
    return buffer.getvalue()


def render_app(items: list[dict], *, annotator_id: str, sample: str, seed: str) -> str:
    """Render the interactive offline annotation app as one self-contained HTML file.

    All state lives in the browser. The annotator clicks the class, assigns a family, and
    sets the four optional tasks; every change autosaves to localStorage and resumes on
    reload. The export button downloads the exact CSV the intake tool ingests. No network,
    no external asset, no predicted class or other machine signal is present.
    """
    payload = {
        "annotator": annotator_id,
        "sample": sample,
        "seed": seed,
        "columns": ANSWER_COLUMNS,
        "classes": GOLD_CLASSES,
        "stances": STANCE_CHOICES,
        "items": [
            {
                "candidate_id": item["candidate_id"],
                "phrase": item["phrase"],
                "before": item["before"],
                "sentence": item["sentence"],
                "after": item["after"],
                "title": item["title"],
                "office": item["office"],
                "date": item["date"],
                "support": [
                    {"office": row["office"], "date": row["date"], "sentence": row["sentence"]}
                    for row in item["support"]
                ],
            }
            for item in items
        ],
    }
    # Escape the closing tag so the embedded JSON cannot break out of the script element.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>OnScript gold-set annotator: {html.escape(annotator_id)}</title>"
        f"<style>{_CSS}{_APP_CSS}</style></head><body>"
        f"<script id=\"goldset-data\" type=\"application/json\">{data}</script>"
        "<header class=\"appbar\"><div class=\"barrow\">"
        f"<b>OnScript gold set</b> &middot; annotator <b>{html.escape(annotator_id)}</b> "
        f"&middot; sample <b>{html.escape(sample)}</b>"
        "<span class=\"progress\" id=\"progress\">0 / 0 labeled</span>"
        "<button id=\"export\" class=\"btn\">Export answer CSV</button></div>"
        "<div class=\"barnote\">Autosaves in this browser. Reopen this file to resume. "
        "Class and family are required; the other tasks are optional per the guide.</div>"
        "</header><main id=\"items\"></main>"
        "<datalist id=\"families\"></datalist>"
        f"<script>{_APP_JS}</script></body></html>"
    )


_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.5; margin: 0;
  padding: 1.5rem; max-width: 46rem; margin-inline: auto; color: #1a1a1a; background: #fff; }
header h1 { font-size: 1.4rem; margin: 0 0 .5rem; }
.meta, .note { font-size: .9rem; color: #444; margin: .3rem 0; }
code { font-family: ui-monospace, 'Courier New', monospace; font-size: .85em; }
main { margin-top: 1rem; }
.item { border: 1px solid #ccc; border-radius: 8px; padding: 1rem 1.1rem; margin: 0 0 1.1rem;
  page-break-inside: avoid; }
.idline { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
  border-bottom: 1px solid #eee; padding-bottom: .4rem; margin-bottom: .6rem; }
.num { font-weight: bold; font-size: 1.1rem; }
.cid { color: #666; }
.phrase { font-size: .95rem; margin-bottom: .5rem; }
.context { background: #f7f7f5; border-radius: 6px; padding: .6rem .8rem; margin: .4rem 0; }
.ctx { margin: .25rem 0; }
.ctx.before, .ctx.after { color: #666; font-size: .92rem; }
.ctx.sentence { font-size: 1rem; }
mark { background: #ffe58a; padding: 0 .1em; }
.src { font-size: .85rem; color: #555; margin-top: .5rem; }
.src .title { font-style: italic; }
.support { margin-top: .6rem; font-size: .9rem; }
.support summary { cursor: pointer; color: #33527a; }
.support ul { margin: .4rem 0 0; padding-left: 1.1rem; }
.support li { margin: .35rem 0; }
.soffice { font-weight: bold; }
.sdate { color: #666; margin-left: .4rem; }
.ssent { color: #333; margin-top: .15rem; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #161616; }
  .meta, .note { color: #aaa; }
  .item { border-color: #3a3a3a; }
  .idline { border-color: #2a2a2a; } .cid { color: #999; }
  .context { background: #202020; } .ctx.before, .ctx.after { color: #aaa; }
  mark { background: #6b5d1a; color: #fff; }
  .src { color: #aaa; } .support summary { color: #9db6df; } .ssent { color: #cfcfcf; }
}
"""


_APP_CSS = """
.appbar { position: sticky; top: 0; z-index: 5; background: #fff; border-bottom: 2px solid #ccc;
  margin: -1.5rem -1.5rem 1rem; padding: .7rem 1.5rem; }
.barrow { display: flex; align-items: center; gap: .8rem; flex-wrap: wrap; }
.progress { margin-left: auto; font-weight: bold; }
.btn { font: inherit; padding: .35rem .8rem; border: 1px solid #33527a; border-radius: 6px;
  background: #33527a; color: #fff; cursor: pointer; }
.btn:hover { background: #26406a; }
.barnote { font-size: .82rem; color: #555; margin-top: .35rem; }
.controls { border-top: 1px solid #eee; margin-top: .7rem; padding-top: .6rem;
  display: grid; gap: .45rem; }
.task { display: flex; align-items: baseline; gap: .6rem; flex-wrap: wrap; }
.tlabel { min-width: 11rem; font-size: .85rem; color: #444; }
.opts { display: flex; gap: .3rem; flex-wrap: wrap; }
.opt { font: inherit; font-size: .85rem; padding: .2rem .6rem; border: 1px solid #bbb;
  border-radius: 999px; background: #f4f4f2; color: #222; cursor: pointer; }
.opt:hover { border-color: #33527a; }
.opt.sel { background: #33527a; border-color: #33527a; color: #fff; }
.fam, .notesin { font: inherit; font-size: .88rem; padding: .25rem .5rem; border: 1px solid #bbb;
  border-radius: 5px; min-width: 18rem; background: #fff; color: #111; }
@media (prefers-color-scheme: dark) {
  .appbar { background: #161616; border-color: #3a3a3a; }
  .barnote { color: #aaa; } .tlabel { color: #bbb; }
  .opt { background: #242424; border-color: #444; color: #ddd; }
  .opt.sel { background: #33527a; border-color: #33527a; color: #fff; }
  .fam, .notesin { background: #1d1d1d; border-color: #444; color: #eee; }
}
"""


_APP_JS = r"""
(function(){
  const DATA = JSON.parse(document.getElementById('goldset-data').textContent);
  const KEY = 'onscript-goldset-' + DATA.sample + '-' + DATA.annotator;
  let answers = {};
  try { answers = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { answers = {}; }
  const itemsEl = document.getElementById('items');
  const progressEl = document.getElementById('progress');
  const familiesEl = document.getElementById('families');

  function esc(s){ const d = document.createElement('div'); d.textContent = (s==null?'':String(s)); return d.innerHTML; }
  function get(cid){ return answers[cid] || (answers[cid] = {}); }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(answers)); } catch (e) {} updateProgress(); updateFamilies(); }

  function updateProgress(){
    const done = DATA.items.filter(it => { const a = answers[it.candidate_id]||{}; return a.gold_class && a.gold_family_id; }).length;
    progressEl.textContent = done + ' / ' + DATA.items.length + ' labeled';
  }
  function updateFamilies(){
    const set = new Set();
    Object.values(answers).forEach(a => { if (a.gold_family_id) set.add(a.gold_family_id); });
    familiesEl.innerHTML = Array.from(set).sort().map(f => '<option value="' + esc(f) + '">').join('');
  }
  function highlight(sentence, phrase){
    const s = esc(sentence); if (!phrase) return s;
    const p = esc(phrase); const i = s.toLowerCase().indexOf(p.toLowerCase());
    if (i < 0) return s; return s.slice(0,i) + '<mark>' + s.slice(i, i+p.length) + '</mark>' + s.slice(i+p.length);
  }
  function group(field, label, values, current, required){
    const btns = values.map(v => '<button class="opt' + (current===v?' sel':'') + '" data-field="' + field + '" data-value="' + esc(v) + '">' + esc(v) + '</button>').join('');
    return '<div class="task"><span class="tlabel">' + label + (required?' *':'') + '</span><div class="opts">' + btns + '</div></div>';
  }
  function boolGroup(field, label, current){
    const opts = [['true','yes'],['false','no']];
    const btns = opts.map(o => '<button class="opt' + (String(current)===o[0]?' sel':'') + '" data-field="' + field + '" data-value="' + o[0] + '">' + o[1] + '</button>').join('');
    return '<div class="task"><span class="tlabel">' + label + '</span><div class="opts">' + btns + '</div></div>';
  }
  function controls(cid, a){
    return '<div class="controls" data-cid="' + cid + '">' +
      group('gold_class','A. surface class', DATA.classes, a.gold_class, true) +
      '<div class="task"><span class="tlabel">E. document family *</span><input class="fam" list="families" data-field="gold_family_id" value="' + esc(a.gold_family_id||'') + '" placeholder="family id, reuse to group items"></div>' +
      boolGroup('phrase_complete','B. phrase complete', a.phrase_complete) +
      boolGroup('proposition_consistent','C. proposition consistent', a.proposition_consistent) +
      group('stance','D. stance', DATA.stances, a.stance, false) +
      boolGroup('claim_supported','F. claim supported', a.claim_supported) +
      '<div class="task"><span class="tlabel">notes</span><input class="notesin" data-field="notes" value="' + esc(a.notes||'') + '"></div>' +
      '</div>';
  }

  DATA.items.forEach((it, idx) => {
    const a = get(it.candidate_id);
    const card = document.createElement('article');
    card.className = 'item'; card.dataset.cid = it.candidate_id;
    let support = '';
    if (it.support && it.support.length){
      support = '<details class="support"><summary>Support set (' + it.support.length + ' offices carrying this phrase)</summary><ul>' +
        it.support.map(s => '<li><span class="soffice">' + esc(s.office) + '</span> <span class="sdate">' + esc(s.date) + '</span><div class="ssent">' + esc(s.sentence) + '</div></li>').join('') + '</ul></details>';
    }
    card.innerHTML =
      '<div class="idline"><span class="num">' + (idx+1) + '</span><code class="cid">' + esc(it.candidate_id) + '</code></div>' +
      '<div class="phrase">Candidate phrase: <b>' + esc(it.phrase) + '</b></div>' +
      '<div class="context">' +
        (it.before ? '<p class="ctx before">' + esc(it.before) + '</p>' : '') +
        '<p class="ctx sentence">' + highlight(it.sentence, it.phrase) + '</p>' +
        (it.after ? '<p class="ctx after">' + esc(it.after) + '</p>' : '') +
      '</div>' +
      '<div class="src">' + esc(it.office) + ' &middot; ' + esc(it.date) + ' &middot; <span class="title">' + esc(it.title) + '</span></div>' +
      support + controls(it.candidate_id, a);
    itemsEl.appendChild(card);
  });

  itemsEl.addEventListener('click', function(e){
    const btn = e.target.closest('button.opt'); if (!btn) return;
    const panel = btn.closest('.controls'); const cid = panel.dataset.cid;
    const field = btn.dataset.field; let value = btn.dataset.value;
    if (value === 'true') value = true; else if (value === 'false') value = false;
    const a = get(cid);
    if (a[field] === value) { delete a[field]; } else { a[field] = value; }
    panel.querySelectorAll('button.opt[data-field="' + field + '"]').forEach(b => {
      let bv = b.dataset.value; if (bv === 'true') bv = true; else if (bv === 'false') bv = false;
      b.classList.toggle('sel', a[field] === bv);
    });
    save();
  });
  itemsEl.addEventListener('input', function(e){
    const inp = e.target.closest('input[data-field]'); if (!inp) return;
    const panel = inp.closest('.controls'); const cid = panel.dataset.cid;
    const field = inp.dataset.field; const val = inp.value.trim();
    const a = get(cid);
    if (val) a[field] = val; else delete a[field];
    save();
  });

  function csvCell(v){ if (v === true) v = 'true'; else if (v === false) v = 'false'; v = (v==null?'':String(v)); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g,'""') + '"' : v; }
  function exportCSV(){
    const cols = DATA.columns; const lines = [cols.join(',')];
    DATA.items.forEach(it => {
      const a = answers[it.candidate_id] || {};
      lines.push(cols.map(c => c === 'candidate_id' ? it.candidate_id : csvCell(a[c])).join(','));
    });
    const blob = new Blob([lines.join('\n') + '\n'], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = DATA.annotator + '.answersheet.csv';
    document.body.appendChild(link); link.click(); link.remove();
    URL.revokeObjectURL(url);
  }
  document.getElementById('export').addEventListener('click', exportCSV);

  updateProgress(); updateFamilies();
})();
"""
