"""Render annotator packets from a sealed gold-set sample.

Each packet is a self-contained HTML page (no external assets, works offline) plus a
machine-readable CSV answer sheet keyed by candidate ID. Item order is randomized per
annotator with a recorded seed. Every shown phrase and sentence passes through the
hardened label path so no admitted private-person form is written into a packet.

The packet shows exactly the ruled context: the candidate phrase, its full sentence, one
sentence before and after, the release title, the office (party, state, chamber), the date,
and, for items with a support set, the other offices carrying the same phrase. It never
shows the predicted class, rankings, surge scores, publication decisions, or corrections.
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
